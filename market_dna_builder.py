#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
market_dna_builder.py — v10 foundation (Market DNA profiler)

Builds a compact, data-driven "DNA" profile for every market:
- Repeat rates (Open/Close Digit, Jodi exact, Jodi mirror, Jodi ±1 neighbor)
- Panna dynamics (double vs single share, next-day carryover)
- Streak tendencies (2-day, 3-day repeat frequencies)
- Day-of-week bias for repeats
- Entropy/volatility of digits & jodis
- Recency drift (last 7 vs last 30 days)
- Data quality (missing/noisy rates)

Inputs (choose one):
  --history  path/to/all_markets_history.json
  --csv-dir  folder with per-market CSVs (columns: Date, Open Panna, Close Panna, Jodi, Open Digit, Close Digit)

Output:
  --out  path/to/market_dna.json  (default: ./output/market_dna.json)

Example (history JSON):
  python market_dna_builder.py --history "output/all_markets_history.json" --out "output/market_dna.json" --days 180

Example (CSV dir):
  python market_dna_builder.py --csv-dir "markets_csv" --out "output/market_dna.json" --days 180
"""

from __future__ import annotations
import os, json, csv, math, argparse, statistics
from collections import Counter, defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

# ---------- helpers ----------
DATE_KEYS = ("Date", "date")
OP_KEYS = ("Open Panna","open_panna","OpenPanna")
CP_KEYS = ("Close Panna","close_panna","ClosePanna")
J_KEYS  = ("Jodi","jodi","JODI")
OD_KEYS = ("Open Digit","open_digit","opendigit")
CD_KEYS = ("Close Digit","close_digit","closedigit")

def to_date(s: Any) -> Optional[datetime]:
    if s is None: return None
    t = str(s).strip()
    for fmt in ("%Y-%m-%d","%d-%m-%Y","%d/%m/%Y","%Y/%m/%d"):
        try:
            return datetime.strptime(t, fmt)
        except Exception:
            pass
    return None

def last_digit_from(value: Any) -> Optional[str]:
    if value is None: return None
    s = str(value)
    digits = [ch for ch in s if ch.isdigit()]
    if not digits: return None
    return digits[-1]

def normalize_jodi(value: Any) -> Optional[str]:
    if value is None: return None
    s = "".join(ch for ch in str(value) if ch.isdigit())
    if len(s) >= 2:
        return s[-2:]
    return None

def is_double_panna(p: Optional[str]) -> Optional[bool]:
    if not p or not p.isdigit() or len(p) != 3: return None
    return len(set(p)) == 2

def is_single_panna(p: Optional[str]) -> Optional[bool]:
    if not p or not p.isdigit() or len(p) != 3: return None
    return len(set(p)) == 3

def mirror_jodi(j: Optional[str]) -> Optional[str]:
    if not j or len(j) != 2 or not j.isdigit(): return None
    return j[1] + j[0]

def jodi_neighbors(j: Optional[str]) -> List[str]:
    """±1 neighbor on each side digit (wrap 0..9)."""
    if not j or len(j)!=2 or not j.isdigit(): return []
    a, b = int(j[0]), int(j[1])
    def wrap(x): return (x + 10) % 10
    return [f"{wrap(a+1)}{b}", f"{wrap(a-1)}{b}", f"{a}{wrap(b+1)}", f"{a}{wrap(b-1)}"]

def shannon_entropy(counter: Counter) -> float:
    n = sum(counter.values())
    if n <= 0: return 0.0
    ent = 0.0
    for c in counter.values():
        p = c / n
        if p > 0:
            ent -= p * math.log2(p)
    return ent

def weekday_index(dt: datetime) -> int:
    # Monday=0 .. Sunday=6
    return dt.weekday()

def safe_mean(vals: List[float]) -> float:
    vals = [v for v in vals if v is not None and not math.isnan(v)]
    return statistics.mean(vals) if vals else 0.0

# ---------- load ----------
def load_history_json(path: str) -> Dict[str, List[Dict[str, Any]]]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict):
        return {str(k): list(v) for k, v in data.items() if isinstance(v, list)}
    if isinstance(data, list):
        grouped = defaultdict(list)
        for r in data:
            if isinstance(r, dict):
                m = str(r.get("Market") or r.get("market") or r.get("market_name") or "UNKNOWN")
                grouped[m].append(r)
        return dict(grouped)
    return {}

def load_csv_dir(folder: str) -> Dict[str, List[Dict[str, Any]]]:
    out: Dict[str, List[Dict[str, Any]]] = {}
    for fn in os.listdir(folder):
        if not fn.lower().endswith(".csv"):
            continue
        market = os.path.splitext(fn)[0]
        rows: List[Dict[str, Any]] = []
        with open(os.path.join(folder, fn), "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(dict(row))
        out[market] = rows
    return out

# ---------- core analysis ----------
def analyze_market(rows: List[Dict[str, Any]], *, days: int = 180) -> Dict[str, Any]:
    # parse and normalize rows → chronological (oldest → newest), then cut tail window
    parsed = []
    for r in rows:
        dt = None
        for k in DATE_KEYS:
            if k in r:
                dt = to_date(r.get(k))
                if dt: break
        if not dt: 
            continue

        # normalize fields
        op = None
        for k in OP_KEYS:
            if k in r and r.get(k):
                op = str(r.get(k))
                break
        cp = None
        for k in CP_KEYS:
            if k in r and r.get(k):
                cp = str(r.get(k))
                break
        j = None
        for k in J_KEYS:
            if k in r and r.get(k):
                j = normalize_jodi(r.get(k))
                break
        od = None
        for k in OD_KEYS:
            if k in r and r.get(k) is not None:
                od = last_digit_from(r.get(k))
                break
        cd = None
        for k in CD_KEYS:
            if k in r and r.get(k) is not None:
                cd = last_digit_from(r.get(k))
                break
        # fallback digits from pannas
        if od is None and op: od = last_digit_from(op)
        if cd is None and cp: cd = last_digit_from(cp)

        parsed.append({
            "dt": dt, "od": od, "cd": cd, "j": j, "op": op, "cp": cp,
            "double_op": is_double_panna(op), "double_cp": is_double_panna(cp),
            "single_op": is_single_panna(op), "single_cp": is_single_panna(cp),
        })

    if not parsed:
        return {"count": 0, "error": "no_valid_rows"}

    parsed.sort(key=lambda x: x["dt"])
    # time-window tail
    if days and len(parsed) > 2:
        cutoff = parsed[-1]["dt"].date().toordinal() - days
        parsed = [x for x in parsed if x["dt"].date().toordinal() >= cutoff]

    n = len(parsed)
    n = len(parsed)
    if n < 4:
        # Still return minimal DNA so v10 engine can use it
        return {
            "count": n,
            "repeat_rates": {
                "open_digit": 0.0,
                "close_digit": 0.0,
                "jodi_exact": 0.0,
                "jodi_mirror": 0.0
            },
            "volatility": {
                "open_digit_volatility": 0.0,
                "jodi_volatility": 0.0
            },
            "panna": {
                "double_share": 0.5,
                "single_share": 0.5
            },
            "dow_bias": {
                "od_repeat": {},
                "cd_repeat": {},
                "j_repeat": {},
                "j_mirror": {}
            }
        }



    # counters and metrics
    od_rep = cd_rep = 0
    j_rep = j_mirror = j_neighbor = 0
    od_streak2 = od_streak3 = 0
    cd_streak2 = cd_streak3 = 0
    j_streak2 = j_streak3 = 0

    # panna dynamics
    doubles = singles = 0
    next_day_double_keep = 0   # double today & double tomorrow
    next_day_single_keep = 0   # single today & single tomorrow

    # DoW repeat lifts
    dow_od_rep = Counter()
    dow_cd_rep = Counter()
    dow_j_rep  = Counter()
    dow_j_mirror = Counter()

    # entropy/volatility
    od_counter = Counter()
    cd_counter = Counter()
    j_counter  = Counter()

    # recency windows (last7, last30)
    def tail_counts(field: str, k: int) -> Counter:
        c = Counter()
        for x in parsed[-k:]:
            v = x[field]
            if v is not None:
                c[v] += 1
        return c

    # pass 1: counts
    for i, x in enumerate(parsed):
        if x["od"] is not None: od_counter[x["od"]] += 1
        if x["cd"] is not None: cd_counter[x["cd"]] += 1
        if x["j"]  is not None: j_counter[x["j"]]  += 1

        # panna class shares
        if x["double_op"] is True: doubles += 1
        elif x["single_op"] is True: singles += 1

        # next-day carryover
        if i+1 < n:
            nx = parsed[i+1]
            if x["double_op"] is True and nx["double_op"] is True: next_day_double_keep += 1
            if x["single_op"] is True and nx["single_op"] is True: next_day_single_keep += 1

    # pass 2: repeats / mirror / neighbors / streaks / DoW
    for i in range(1, n):
        a, b = parsed[i-1], parsed[i]
        dow = weekday_index(b["dt"])

        # digits repeat
        if a["od"] is not None and b["od"] == a["od"]:
            od_rep += 1; dow_od_rep[dow] += 1
        if a["cd"] is not None and b["cd"] == a["cd"]:
            cd_rep += 1; dow_cd_rep[dow] += 1

        # jodi repeat/mirror/neighbor
        aj, bj = a["j"], b["j"]
        if aj and bj:
            if bj == aj:
                j_rep += 1; dow_j_rep[dow] += 1
            mir = mirror_jodi(aj)
            if mir and bj == mir:
                j_mirror += 1; dow_j_mirror[dow] += 1
            if bj in jodi_neighbors(aj):
                j_neighbor += 1

        # streaks (2+)
        if i >= 2:
            a2 = parsed[i-2]
            if a["od"] and b["od"] and a2["od"] and a2["od"] == a["od"] == b["od"]:
                od_streak2 += 1
            if a["cd"] and b["cd"] and a2["cd"] and a2["cd"] == a["cd"] == b["cd"]:
                cd_streak2 += 1
            if aj and bj and a2["j"] and a2["j"] == aj == bj:
                j_streak2 += 1
        if i >= 3:
            a3 = parsed[i-3]
            if a3["od"] and a["od"] and b["od"] and a3["od"] == a["od"] == b["od"]:
                od_streak3 += 1
            if a3["cd"] and a["cd"] and b["cd"] and a3["cd"] == a["cd"] == b["cd"]:
                cd_streak3 += 1
            if a3["j"] and aj and bj and a3["j"] == aj == bj:
                j_streak3 += 1

    # denominators (valid transitions)
    trans = max(1, n-1)

    # entropy
    od_entropy = shannon_entropy(od_counter)
    cd_entropy = shannon_entropy(cd_counter)
    j_entropy  = shannon_entropy(j_counter)

    # volatility proxy (normalized entropy)
    # Max entropy for 10 digits ≈ log2(10)=3.32; for 100 jodis ≤ log2(unique_jodis)
    vol_od = od_entropy / max(1e-9, math.log2(10))
    vol_cd = cd_entropy / max(1e-9, math.log2(10))
    uniq_j = max(2, len(j_counter))  # avoid /0
    vol_j  = j_entropy / max(1e-9, math.log2(uniq_j))

    # DoW rates (normalize by DoW occurrences)
    dow_counts = Counter([weekday_index(x["dt"]) for x in parsed[1:]])  # transitions count per DoW
    dow_rates = {
        "od_repeat": {str(k): (dow_od_rep[k] / dow_counts[k]) if dow_counts[k] else 0.0 for k in range(7)},
        "cd_repeat": {str(k): (dow_cd_rep[k] / dow_counts[k]) if dow_counts[k] else 0.0 for k in range(7)},
        "j_repeat":  {str(k): (dow_j_rep[k]  / dow_counts[k]) if dow_counts[k]  else 0.0 for k in range(7)},
        "j_mirror":  {str(k): (dow_j_mirror[k] / dow_counts[k]) if dow_counts[k] else 0.0 for k in range(7)},
    }

    # recency drift (last7 vs last30 digit/jodi distribution divergence via simple L1 distance)
    last7_od  = tail_counts("od",  min(7, n))
    last30_od = tail_counts("od", min(30, n))
    last7_j   = tail_counts("j",  min(7, n))
    last30_j  = tail_counts("j", min(30, n))
    def l1_dist(c1: Counter, c2: Counter) -> float:
        keys = set(c1.keys()) | set(c2.keys())
        n1, n2 = sum(c1.values()) or 1, sum(c2.values()) or 1
        return sum(abs((c1.get(k,0)/n1) - (c2.get(k,0)/n2)) for k in keys) / 2.0
    drift_od = l1_dist(last7_od, last30_od)
    drift_j  = l1_dist(last7_j, last30_j)

    # data quality (missing rates)
    miss_od = sum(1 for x in parsed if x["od"] is None) / n
    miss_cd = sum(1 for x in parsed if x["cd"] is None) / n
    miss_j  = sum(1 for x in parsed if x["j"]  is None) / n
    miss_op = sum(1 for x in parsed if x["op"] is None) / n
    miss_cp = sum(1 for x in parsed if x["cp"] is None) / n

    # compile DNA
    dna = {
        "count": n,
        "window_days": days,
        "repeat_rates": {
            "open_digit":  od_rep / trans,
            "close_digit": cd_rep / trans,
            "jodi_exact":  j_rep  / trans,
            "jodi_mirror": j_mirror / trans,
            "jodi_neighbor": j_neighbor / trans
        },
        "streaks": {
            "open_digit_2day": od_streak2 / max(1, trans-1),
            "open_digit_3day": od_streak3 / max(1, trans-2),
            "close_digit_2day": cd_streak2 / max(1, trans-1),
            "close_digit_3day": cd_streak3 / max(1, trans-2),
            "jodi_2day": j_streak2 / max(1, trans-1),
            "jodi_3day": j_streak3 / max(1, trans-2),
        },
        "panna": {
            "double_share": doubles / max(1, (doubles + singles)),
            "single_share": singles / max(1, (doubles + singles)),
            "next_day_double_keep": next_day_double_keep / max(1, trans),
            "next_day_single_keep": next_day_single_keep / max(1, trans),
        },
        "dow_bias": dow_rates,
        "volatility": {
            "open_digit_entropy": od_entropy,
            "close_digit_entropy": cd_entropy,
            "jodi_entropy": j_entropy,
            "open_digit_volatility": vol_od,  # 0..1
            "close_digit_volatility": vol_cd, # 0..1
            "jodi_volatility": vol_j,         # 0..1
        },
        "recency_drift": {
            "open_digit_drift_l1_7_vs_30": drift_od,
            "jodi_drift_l1_7_vs_30": drift_j
        },
        "data_quality": {
            "missing_open_digit": miss_od,
            "missing_close_digit": miss_cd,
            "missing_jodi": miss_j,
            "missing_open_panna": miss_op,
            "missing_close_panna": miss_cp
        }
    }
    return dna

# ---------- main ----------
def main():
    ap = argparse.ArgumentParser(description="Build per-market DNA profiles for v10.")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--history", help="Path to all_markets_history.json")
    src.add_argument("--csv-dir", help="Folder of per-market CSVs")
    ap.add_argument("--days", type=int, default=180, help="Tail window of days to profile (default 180)")
    ap.add_argument("--out", default=os.path.join("output", "market_dna.json"), help="Output JSON path")
    ap.add_argument("--restrict", nargs="*", help="Optional list of market keys to include")
    args = ap.parse_args()

    if args.history:
        markets = load_history_json(args.history)
    else:
        markets = load_csv_dir(args.csv_dir)

    if not markets:
        raise SystemExit("No markets found in the provided source.")

    os.makedirs(os.path.dirname(args.out), exist_ok=True)

    dna_out: Dict[str, Any] = {"generated_at": datetime.now().isoformat(), "window_days": args.days, "markets": {}}
    total = 0
    for mkt, rows in markets.items():
        if args.restrict and str(mkt) not in set(args.restrict):
            continue
        try:
            dna = analyze_market(rows, days=args.days)
            dna_out["markets"][str(mkt)] = dna
            total += 1
        except Exception as e:
            dna_out["markets"][str(mkt)] = {"error": f"analysis_failed: {e}"}

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(dna_out, f, ensure_ascii=False, indent=2)

    # Tiny console summary
    print(f"✅ DNA built for {total} markets → {args.out}")
    # Print a few guidance hints to wire into v10 later
    print("\nNext (in v10): per-market overrides suggestion — use repeat_rates, panna.double_share, volatility, and dow_bias to set:")
    print("  • Strategy mix (REPEAT/TRAP/FAKE) per market")
    print("  • Yesterday penalties tuned by repeat_rates")
    print("  • Protected repeat slots when repeat rates > thresholds")
    print("  • DoW nudges using dow_bias (lift repeats on high-repeat days)")

if __name__ == "__main__":
    main()