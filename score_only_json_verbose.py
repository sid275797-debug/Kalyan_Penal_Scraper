#!/usr/bin/env python3
"""
score_predictor_v2.py (fixed, cleaned, deterministic copy)
- Auto-detects predictions/yesterday shapes
- Normalizes keys consistently
- Logs unmatched keys into sattaboss-data/data/unmatched_keys.json
- Writes:
    - prediction_score_report.json (full)
    - score_hits_YYYYMMDD.json (hits-only structured as mapping)
    - score_hits.json  (flat list for apps)
    - score_hits_list.json (flat list duplicate for compatibility)
- Pushes to Firebase
- Copies final JSONs to Flutter assets (deterministic & reliable)
"""
from __future__ import annotations
import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

# --- config ---
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FLUTTER_ASSETS = r"C:\Users\VCOM\AndroidStudioProjects\multi_market_predictions_v3\assets"
DATA_FOLDER = os.path.join(ROOT, "sattaboss-data", "data")

FAMILY_CANDIDATES = [
    os.path.join(ROOT, "kalyan", "families.json"),
    os.path.join(ROOT, "assets", "families.json"),
    os.path.join(ROOT, "config", "families.json"),
    os.path.join(ROOT, "families.json"),
]

DEFAULT_PRED = os.path.join(DATA_FOLDER, "todays_predictions.json")
DEFAULT_YEST_1 = os.path.join(ROOT, "output", "yesterday_results.json")
DEFAULT_YEST_2 = os.path.join(DATA_FOLDER, "yesterday_results.json")

# ---------- helpers ----------
def die(msg: str):
    print(f"❌ {msg}")
    sys.exit(1)


def load_json(path: str) -> Optional[Any]:
    if not path or not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️ Failed to parse JSON {path}: {e}")
        return None


def norm_key(s: Optional[str]) -> str:
    if not s:
        return ""
    return str(s).strip().lower().replace(" ", "_")


def safe_digit(val) -> Optional[int]:
    if val is None:
        return None
    s = str(val).strip()
    for ch in reversed(s):
        if ch.isdigit():
            return int(ch)
    return None


def safe_jodi(val) -> Optional[str]:
    if val is None:
        return None
    digits = "".join(ch for ch in str(val) if ch.isdigit())
    if not digits:
        return None
    return digits[-2:].zfill(2)


def z3(x) -> Optional[str]:
    if x is None:
        return None
    s = "".join(ch for ch in str(x) if ch.isdigit())
    if not s:
        return None
    return s.zfill(3)[-3:]


# ---------- loaders ----------
def load_predictions(path: str) -> Dict[str, Dict[str, Any]]:
    data = load_json(path)
    if data is None:
        die(f"Predictions file not found or invalid: {path}")

    out: Dict[str, Dict[str, Any]] = {}

    if isinstance(data, dict) and all(isinstance(v, dict) for v in data.values()) and "data" not in data:
        for k, v in data.items():
            out[norm_key(k)] = v
        return out

    if isinstance(data, dict) and "data" in data and isinstance(data["data"], list):
        items = data["data"]
    elif isinstance(data, dict) and "markets" in data and isinstance(data["markets"], list):
        items = data["markets"]
    elif isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        items = [data]
    else:
        die("Predictions JSON format not recognized.")

    def normalize_pred_keys(preds: dict) -> dict:
        new = {}
        for k, v in (preds or {}).items():
            nk = str(k).strip().lower().replace(" ", "_")
            new[nk] = v
        return new

    for item in items:
        if not isinstance(item, dict):
            continue
        raw_market = item.get("market") or item.get("Market") or item.get("name") or ""
        mkt = norm_key(raw_market)
        if not mkt:
            continue
        preds = item.get("predictions", {}) or {}
        preds_norm = normalize_pred_keys(preds)
        out[mkt] = {
            "predicted": {
                "open_digits": [str(x) for x in preds_norm.get("open_digits", preds_norm.get("open_digit", []))],
                "close_digits": [str(x) for x in preds_norm.get("close_digits", preds_norm.get("close_digit", []))],
                "jodis": [str(x).zfill(2) for x in preds_norm.get("jodis", preds_norm.get("jodi", []))],
                "open_pannas": [str(x).zfill(3) for x in preds_norm.get("open_pannas", preds_norm.get("open_panna", []))],
                "close_pannas": [str(x).zfill(3) for x in preds_norm.get("close_pannas", preds_norm.get("close_panna", []))],
            },
            "meta": item.get("meta", {}) or {},
            "raw": item,
        }
    return out


def load_yesterday(path: str) -> Dict[str, Dict[str, Any]]:
    data = load_json(path)
    if data is None:
        die(f"Yesterday file not found or invalid: {path}")

    if isinstance(data, dict) and len(data.keys()) == 1:
        first_val = list(data.values())[0]
        if isinstance(first_val, list):
            data = first_val

    for key in ("data", "markets", "results"):
        if isinstance(data, dict) and key in data and isinstance(data[key], list):
            print(f"🕰 Detected yesterday with top-level '{key}' list — normalizing.")
            data = data[key]
            break

    if isinstance(data, list) and len(data) == 1 and isinstance(data[0], dict) and "market" not in data[0]:
        inner = data[0].get("data") or data[0].get("markets")
        if isinstance(inner, list):
            data = inner

    out: Dict[str, Dict[str, Any]] = {}
    if isinstance(data, list):
        for item in data:
            if not isinstance(item, dict):
                continue
            m = item.get("market") or item.get("Market") or item.get("name") or ""
            out[norm_key(m)] = item
        print(f"🕰 Detected yesterday as list-of-records ({len(out)} markets)")
        return out
    if isinstance(data, dict) and "data" in data and isinstance(data["data"], list):
        for item in data["data"]:
            if not isinstance(item, dict):
                continue
            m = item.get("market") or item.get("Market") or item.get("name") or ""
            out[norm_key(m)] = item
        print(f"🕰 Detected yesterday as object with data[] ({len(out)} markets)")
        return out
    if isinstance(data, dict) and all(isinstance(v, dict) for v in data.values()):
        for k, v in data.items():
            out[norm_key(k)] = v
        print(f"🕰 Detected yesterday as dict-of-markets ({len(out)} markets)")
        return out
    if isinstance(data, dict):
        mk = norm_key(data.get("market") or data.get("name") or "single_market")
        print(f"🕰 Detected single-record yesterday JSON; key: {mk}")
        return {mk: data}
    die("Yesterday JSON unrecognized format.")


def load_families() -> Dict[str, List[str]]:
    for p in FAMILY_CANDIDATES:
        d = load_json(p)
        if d and isinstance(d, dict):
            nf = {str(fid): [str(m).zfill(3) for m in members] for fid, members in d.items()}
            print(f"🧩 Loaded families from {p} ({len(nf)} groups)")
            return nf
    print("🧩 No families.json found — family checks disabled.")
    return {}


def find_family_of_panna(panna: Optional[str], families: Dict[str, list]) -> Optional[str]:
    if panna is None:
        return None
    p = str(panna).zfill(3)
    for fid, members in families.items():
        if p in members:
            return fid
    return None


# ---------- scoring ----------
def score_market(pred: Dict[str, Any], actual: Dict[str, Any], families: Dict[str, list]) -> Dict[str, Any]:
    predicted = pred.get("predicted", {})
    actual_rec = actual
    if isinstance(actual, dict) and "predictions" in actual and isinstance(actual["predictions"], dict):
        actual_rec = actual["predictions"]

    def first_of(v):
        if v is None:
            return None
        if isinstance(v, list) and len(v) > 0:
            return v[0]
        return v

    od_val = (actual_rec.get("Open Digit") or actual_rec.get("open_digit") or actual_rec.get("OpenDigit")
              or first_of(actual_rec.get("Open Digits")) or first_of(actual_rec.get("open_digits")))
    cd_val = (actual_rec.get("Close Digit") or actual_rec.get("close_digit") or actual_rec.get("CloseDigit")
              or first_of(actual_rec.get("Close Digits")) or first_of(actual_rec.get("close_digits")))
    j_val = (actual_rec.get("Jodi") or actual_rec.get("jodi") or actual_rec.get("JODI")
             or first_of(actual_rec.get("Jodis")) or first_of(actual_rec.get("jodis")))
    op_val = (actual_rec.get("Open Panna") or actual_rec.get("open_panna") or actual_rec.get("OpenPanna")
              or first_of(actual_rec.get("Open Pannas")) or first_of(actual_rec.get("open_pannas")))
    cp_val = (actual_rec.get("Close Panna") or actual_rec.get("close_panna") or actual_rec.get("ClosePanna")
              or first_of(actual_rec.get("Close Pannas")) or first_of(actual_rec.get("close_pannas")))

    def sanitize_panna(x):
        if x is None:
            return None
        s = "".join(ch for ch in str(x) if ch.isdigit())
        if not s:
            return None
        s = s.zfill(3)[-3:]
        if s == "000" or s.lower() == "none":
            return None
        return s

    def sanitize_jodi(x):
        if x is None:
            return None
        s = "".join(ch for ch in str(x) if ch.isdigit())
        if not s:
            return None
        s = s[-2:].zfill(2)
        if s == "00" or s.lower() == "none":
            return None
        return s

    od = safe_digit(od_val)
    cd = safe_digit(cd_val)
    j = sanitize_jodi(j_val)
    op = sanitize_panna(op_val)
    cp = sanitize_panna(cp_val)

    hits = {
        "open_digit": (od is not None) and (str(od) in predicted.get("open_digits", [])),
        "close_digit": (cd is not None) and (str(cd) in predicted.get("close_digits", [])),
        "jodi": (j is not None) and (j in predicted.get("jodis", [])),
        "open_panna": (op is not None) and (op in predicted.get("open_pannas", [])),
        "close_panna": (cp is not None) and (cp in predicted.get("close_pannas", [])),
    }

    family_hit = False
    matched = []
    if families:
        fop = find_family_of_panna(op, families) if op else None
        fcp = find_family_of_panna(cp, families) if cp else None
        if fop:
            for mem in families.get(fop, []):
                if mem in predicted.get("open_pannas", []):
                    family_hit = True
                    matched.append({"family": fop, "member": op, "side": "open", "matched_via": "predicted_member"})
                    break
        if fcp:
            for mem in families.get(fcp, []):
                if mem in predicted.get("close_pannas", []):
                    family_hit = True
                    matched.append({"family": fcp, "member": cp, "side": "close", "matched_via": "predicted_member"})
                    break

    line_match = None
    line_pred = pred.get("meta", {}).get("line") or pred.get("meta_line")
    if line_pred:
        prev = actual_rec.get("prev_open_panna") or actual_rec.get("previous_open_panna") or actual_rec.get("prev_panna")
        if prev and op:
            try:
                prev_i = int(str(prev).zfill(3))
                op_i = int(op)
                if op_i > prev_i:
                    line_actual = "up"
                elif op_i < prev_i:
                    line_actual = "down"
                else:
                    line_actual = "flat"
                line_match = (line_pred.get("direction") == line_actual) if isinstance(line_pred, dict) else None
            except Exception:
                line_match = None

    any_hit = any(hits.values()) or family_hit or (line_match is True)

    return {
        "hits": hits,
        "family_hit": family_hit,
        "matched_families": matched,
        "line_predicted": line_pred,
        "line_match": line_match,
        "any_hit": any_hit,
        "actual": {"open_digit": od, "close_digit": cd, "jodi": j, "open_panna": op, "close_panna": cp},
        "predicted": predicted,
    }


# ---------- main ----------
def main():
    ap = argparse.ArgumentParser(description="Score predictions vs yesterday (robust).")
    ap.add_argument("--pred", help="Path to todays_predictions.json (optional)")
    ap.add_argument("--yest", help="Path to yesterday_results.json (optional)")
    ap.add_argument("--out", help="Output path for full report (optional)")
    args = ap.parse_args()

    # prefer local files if present (run from Kalyan folder)
    cwd = os.getcwd()
    local_pred = os.path.join(cwd, "todays_predictions.json")
    local_yest = os.path.join(cwd, "yesterday_results.json")

    if os.path.exists(local_pred):
        pred_path = os.path.abspath(local_pred)
        print(f"🔎 Using local predictions: {pred_path}")
    elif args.pred:
        pred_path = os.path.abspath(args.pred)
    else:
        pred_path = os.path.abspath(DEFAULT_PRED)

    if os.path.exists(local_yest):
        yest_path = os.path.abspath(local_yest)
        print(f"🕰 Using local yesterday results: {yest_path}")
    elif args.yest:
        yest_path = os.path.abspath(args.yest)
    else:
        if os.path.exists(DEFAULT_YEST_1):
            yest_path = DEFAULT_YEST_1
        elif os.path.exists(DEFAULT_YEST_2):
            yest_path = DEFAULT_YEST_2
        else:
            yest_path = os.path.join(os.path.dirname(pred_path), "yesterday_results.json")

    print("🔎 Using:")
    print(" predictions:", pred_path)
    print(" yesterday: ", yest_path)

    preds_map = load_predictions(pred_path)
    yest_map = load_yesterday(yest_path)
    families = load_families()

    print(f"📦 Markets in predictions: {len(preds_map)}")
    print(f"📦 Markets in yesterday : {len(yest_map)}")

    pred_keys = set(preds_map.keys())
    yest_keys = set(yest_map.keys())
    common = sorted(pred_keys & yest_keys)
    print(f"🔗 Overlapping markets: {len(common)}")

    # samples & unmatched logging
    sample_pred_keys = sorted(list(pred_keys))[:8]
    sample_yest_keys = sorted(list(yest_keys))[:8]
    print(" sample_pred_keys:", sample_pred_keys)
    print(" sample_yest_keys:", sample_yest_keys)

    unmatched_preds = sorted(list(pred_keys - yest_keys))
    unmatched_yest = sorted(list(yest_keys - pred_keys))
    unmatched_out = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "pred_only_count": len(unmatched_preds),
        "yest_only_count": len(unmatched_yest),
        "pred_only_sample": unmatched_preds[:40],
        "yest_only_sample": unmatched_yest[:40],
    }
    try:
        os.makedirs(DATA_FOLDER, exist_ok=True)
        with open(os.path.join(DATA_FOLDER, "unmatched_keys.json"), "w", encoding="utf-8") as f:
            json.dump(unmatched_out, f, indent=2, ensure_ascii=False)
        print(f"📝 Wrote unmatched_keys.json ({len(unmatched_preds)} pred-only, {len(unmatched_yest)} yest-only)")
    except Exception as e:
        print("⚠️ Could not write unmatched_keys.json:", e)

    per_market = {}
    hits_only = {}
    totals = {"open_digit": 0, "close_digit": 0, "jodi": 0, "open_panna": 0, "close_panna": 0, "markets": 0, "markets_with_hits": 0}

    for mkt in common:
        actual = yest_map[mkt]
        scored = score_market(preds_map[mkt], actual, families)
        per_market[mkt] = scored
        totals["markets"] += 1
        for k, v in scored["hits"].items():
            totals[k] += int(bool(v))
        if scored.get("any_hit"):
            hits_only[mkt] = scored
            totals["markets_with_hits"] += 1

    # --- add friendly score_details for UI ---
    for mkt, scored in per_market.items():
        actual = scored.get("actual", {}) or {}
        hits = scored.get("hits", {}) or {}

        od = actual.get("open_digit")
        cd = actual.get("close_digit")
        j = actual.get("jodi")
        op = actual.get("open_panna")
        cp = actual.get("close_panna")

        def badge_obj(val, symbol, passed):
            return {
                "passed": bool(passed),
                "value": val if val is not None else None,
                "display": f"{symbol} {val}" if val is not None else None,
                "status": "PASS" if passed else "FAIL",
            }

        scored["score_details"] = {
            "open": badge_obj(od, "↑", hits.get("open_digit", False)),
            "close": badge_obj(cd, "↑", hits.get("close_digit", False)),
            "jodi": badge_obj(j, "★", hits.get("jodi", False)),
            "open_panna": badge_obj(op, "→", hits.get("open_panna", False)),
            "close_panna": badge_obj(cp, "→", hits.get("close_panna", False)),
        }

    n = max(1, totals["markets"])
    summary = {
        "markets_scored": totals["markets"],
        "markets_with_hits": totals["markets_with_hits"],
        "hit_counts": {k: totals[k] for k in ["open_digit", "close_digit", "jodi", "open_panna", "close_panna"]},
        "hit_rates": {k: round(totals[k] / n, 4) for k in ["open_digit", "close_digit", "jodi", "open_panna", "close_panna"]},
    }

    report = {
        "generated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "inputs": {"predictions_path": pred_path, "yesterday_path": yest_path},
        "summary": summary,
        "markets": per_market,
    }

    # output paths -> write directly into FLUTTER_ASSETS (this is your desired behavior)
    out_path = args.out or os.path.join(FLUTTER_ASSETS, "prediction_score_report.json")
    out_path = os.path.abspath(out_path)
    save_dir = os.path.dirname(out_path)
    os.makedirs(save_dir, exist_ok=True)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    ts = datetime.utcnow().strftime("%Y%m%d")
    hits_path = os.path.join(save_dir, f"score_hits_{ts}.json")
    with open(hits_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "generated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
                "inputs": {"predictions_path": pred_path, "yesterday_path": yest_path},
                "summary": summary,
                "hits": hits_only,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    # flat outputs
    flat_hits_list = []
    for k, v in hits_only.items():
        flat_hits_list.append(
            {
                "market": k,
                "hits": v.get("hits"),
                "predicted": v.get("predicted"),
                "actual": v.get("actual"),
                "family_hit": v.get("family_hit"),
                "line_match": v.get("line_match"),
            }
        )
    flat_static_path = os.path.join(save_dir, "score_hits.json")
    flat_list_path = os.path.join(save_dir, "score_hits_list.json")
    try:
        with open(flat_static_path, "w", encoding="utf-8") as f:
            json.dump({"generated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z", "hits": flat_hits_list}, f, ensure_ascii=False, indent=2)
        with open(flat_list_path, "w", encoding="utf-8") as f:
            json.dump(flat_hits_list, f, ensure_ascii=False, indent=2)
        print(f"📝 Wrote flat hits -> {flat_static_path} and {flat_list_path}")
    except Exception as e:
        print("⚠️ Could not write flat hits files:", e)

    # ---- RTDB push (kept) ----
    try:
        from rtdb_utils import rtdb_set, rtdb_push_archive

        tsd = datetime.utcnow().date().isoformat()
        rtdb_set("/app_data/prediction_score_report", report)
        rtdb_push_archive("/app_data/history/prediction_score_report", tsd, report)
        flat_payload = {"generated_at": report["generated_at"], "hits": flat_hits_list}
        rtdb_set("/app_data/score_hits", flat_payload)
        rtdb_push_archive("/app_data/history/score_hits", tsd, flat_payload)
        print("📡 Pushed scoring results to Firebase.")
    except Exception as e:
        print("⚠️ Firebase push skipped/failed:", e)

    # --- deterministic final copy (guaranteed write to Flutter assets) ---
    try:
        os.makedirs(FLUTTER_ASSETS, exist_ok=True)

        # Ensure full report is copied to flutter assets
        try:
            dst_report = os.path.join(FLUTTER_ASSETS, "prediction_score_report.json")
            shutil.copy2(out_path, dst_report)
            print(f"✅ Ensured report: {out_path} -> {dst_report}")
        except Exception as e:
            print(f"⚠️ Could not copy full report to assets: {e}")

        # Ensure dated hits exists and copy to both dated and legacy static name
        try:
            if os.path.exists(hits_path):
                dst_hits = os.path.join(FLUTTER_ASSETS, os.path.basename(hits_path))
                shutil.copy2(hits_path, dst_hits)

                legacy_hits = os.path.join(FLUTTER_ASSETS, "score_hits.json")
                shutil.copy2(hits_path, legacy_hits)
                print(f"✅ Ensured hits: {hits_path} -> {dst_hits} and {legacy_hits}")
            else:
                # fallback: if flat_static_path exists, copy it too
                if os.path.exists(flat_static_path):
                    shutil.copy2(flat_static_path, os.path.join(FLUTTER_ASSETS, "score_hits.json"))
                    print(f"✅ Copied flat_static_path -> score_hits.json")
                else:
                    print(f"⚠️ hits_path missing (expected): {hits_path}")
        except Exception as e:
            print(f"⚠️ Could not ensure hits files in assets: {e}")

    except Exception as e:
        print("⚠️ Deterministic copy step failed:", e)

    # Attempt to git add/commit/push (non-fatal)
    try:

        def git_available() -> bool:
            try:
                subprocess.run(["git", "--version"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return True
            except Exception:
                return False

        if git_available():
            files_to_add = [
                os.path.join(save_dir, os.path.basename(out_path)),
                os.path.join(save_dir, os.path.basename(hits_path)),
                flat_static_path,
                flat_list_path,
                os.path.join(DATA_FOLDER, "unmatched_keys.json"),
            ]
            files_to_add = [f for f in files_to_add if f and os.path.exists(f)]
            if files_to_add:
                try:
                    subprocess.run(["git", "add"] + files_to_add, check=True)
                    res = subprocess.run(["git", "diff", "--cached", "--name-only"], stdout=subprocess.PIPE, text=True)
                    if res.stdout.strip():
                        commit_msg = f"chore: automated JSON update ({datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')})"
                        subprocess.run(["git", "commit", "-m", commit_msg], check=True)
                        try:
                            subprocess.run(["git", "push", "origin", "HEAD:main"], check=True)
                            print("✅ Pushed updated JSON files to origin/main")
                        except Exception as e:
                            print("⚠️ git push failed (non-fatal):", e)
                    else:
                        print("✅ No git-staged changes to commit.")
                except Exception as e:
                    print("⚠️ Git add/commit step failed (non-fatal):", e)
            else:
                print("ℹ️ No files found to git-add.")
        else:
            print("ℹ️ Git not available on PATH — skipping git actions.")
    except Exception as e:
        print("⚠️ Skipping git push from script — exception:", e)

    print("🎯 Done. Report written to:", out_path)


if __name__ == "__main__":
    main()