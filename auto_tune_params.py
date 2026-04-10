# auto_tune_params.py
import json, os, math
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
PARAMS_PATH = os.path.join(BASE, "prediction_params.json")
SCORE_PATH  = os.path.join(BASE, "sattaboss-data", "data", "prediction_score_report.json")

# Bounds & default starting point (kept small/safe)
DEFAULT = {
    "half_life_days": 21.0,      # lower => more weight on recent draws
    "exploration_rate": 0.15,    # chance to mix uncommon digits
    "streak_boost": 0.0          # small bias to repeats (0..0.3)
}
BOUNDS = {
    "half_life_days": (7.0, 45.0),
    "exploration_rate": (0.05, 0.30),
    "streak_boost": (0.0, 0.30),
}

def _clamp(v, lo, hi): return max(lo, min(hi, v))

def load_scores(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def load_params(path):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"_meta": {"last_updated": None}, "markets": {}}

def save_params(path, data):
    data["_meta"]["last_updated"] = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def tune_one(p, market_score):
    """Small, safe nudges based on *yesterday vs today* score file."""
    # Unpack (missing keys default to 0)
    od = market_score.get("open_digit_hit", 0)
    cd = market_score.get("close_digit_hit", 0)
    jd = market_score.get("jodi_hit", 0)
    op = market_score.get("open_panna_hit", 0)
    cp = market_score.get("close_panna_hit", 0)
    # If your score JSON stores booleans, convert to ints:
    od = int(bool(od)); cd = int(bool(cd)); jd = int(bool(jd)); op = int(bool(op)); cp = int(bool(cp))

    # Make sure defaults exist
    half = float(p.get("half_life_days", DEFAULT["half_life_days"]))
    eps  = float(p.get("exploration_rate", DEFAULT["exploration_rate"]))
    sb   = float(p.get("streak_boost", DEFAULT["streak_boost"]))

    # Rules (tiny steps, clamped):
    # 1) If Jodi missed, lean a bit more to recency + explore slightly more.
    if jd == 0:
        half = _clamp(half * 0.90, *BOUNDS["half_life_days"])
        eps  = _clamp(eps  + 0.01,  *BOUNDS["exploration_rate"])
    else:
        # If Jodi hit, trust history a bit more, reduce explore a touch
        half = _clamp(half * 1.05, *BOUNDS["half_life_days"])
        eps  = _clamp(eps  - 0.01,  *BOUNDS["exploration_rate"])

    # 2) If both open & close digits missed, bump exploration slightly again
    if od == 0 and cd == 0:
        eps = _clamp(eps + 0.005, *BOUNDS["exploration_rate"])

    # 3) If either panna hit, give a small streak bias; else decay it slightly
    if op == 1 or cp == 1:
        sb = _clamp(sb + 0.01, *BOUNDS["streak_boost"])
    else:
        sb = _clamp(sb * 0.98, *BOUNDS["streak_boost"])

    # Pack back
    p.update({
        "half_life_days": round(half, 3),
        "exploration_rate": round(eps, 3),
        "streak_boost": round(sb, 3),
    })
    # keep a tiny moving confidence (optional)
    hist = p.get("_stats", {"days": 0, "jodi_hits": 0})
    hist["days"] = int(hist.get("days", 0)) + 1
    hist["jodi_hits"] = int(hist.get("jodi_hits", 0)) + (1 if jd else 0)
    p["_stats"] = hist
    return p

def main():
    scores = load_scores(SCORE_PATH)
    params = load_params(PARAMS_PATH)
    markets_params = params.setdefault("markets", {})

    # Expect scores shape:
    # { "generated_at": "...", "summary": {...}, "markets": { "market_key": { open_digit_hit: 0/1, ... }, ... } }
    per_market = scores.get("markets", {})

    updated = 0
    for mkt, mscore in per_market.items():
        cur = markets_params.get(mkt, DEFAULT.copy())
        markets_params[mkt] = tune_one(cur, mscore)
        updated += 1

    save_params(PARAMS_PATH, params)
    print(f"✅ Auto-tuned params for {updated} markets → {PARAMS_PATH}")

if __name__ == "__main__":
    main()