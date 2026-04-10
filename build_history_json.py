# build_history_json.py

import pandas as pd
import glob, json
from pathlib import Path

# ▲ adjust this to your actual folder
CSV_GLOB = "output/*.csv"
OUT_JSON = "all_markets_history.json"

# Files/patterns to skip (non-market CSVs that land in output/)
SKIP_PREFIXES = [
    "engine_compare",
    "prediction_score",
    "debug_",
    "test_",
    "backup_",
]

def build_history():
    all_data = {}
    skipped = []

    for path in sorted(glob.glob(CSV_GLOB)):
        stem = Path(path).stem
        market = stem.upper()

        # Skip known non-market files by prefix
        if any(stem.lower().startswith(p) for p in SKIP_PREFIXES):
            skipped.append(stem)
            continue

        # Peek at columns before full parse
        try:
            cols = pd.read_csv(path, nrows=0).columns.tolist()
        except Exception as e:
            print(f"  ⚠️ Skipped {stem}: cannot read headers ({e})")
            skipped.append(stem)
            continue

        if "Date" not in cols:
            print(f"  ⚠️ Skipped {stem}: no 'Date' column (cols: {cols[:5]}...)")
            skipped.append(stem)
            continue

        try:
            df = pd.read_csv(path, parse_dates=["Date"], dayfirst=True)
        except Exception as e:
            print(f"  ⚠️ Skipped {stem}: parse error ({e})")
            skipped.append(stem)
            continue

        records = df.to_dict(orient="records")
        for r in records:
            if isinstance(r.get("Date"), pd.Timestamp):
                r["Date"] = r["Date"].isoformat()
        all_data[market] = records

    # write it out
    with open(OUT_JSON, "w") as f:
        json.dump(all_data, f, indent=2)

    print(f"✅ Wrote history for {len(all_data)} markets to {OUT_JSON}")
    if skipped:
        print(f"⚠️ Skipped {len(skipped)} non-market files: {', '.join(skipped)}")

if __name__ == "__main__":
    build_history()