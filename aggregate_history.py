#!/usr/bin/env python3
import os, json, glob
import pandas as pd
import sys
sys.stdout.reconfigure(encoding='utf-8')

ROOT = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(ROOT, "output")
PRIMARY_JSON = os.path.join(ROOT, "sattaboss-data", "data", "all_markets_history.json")

# Optional copy targets (keep / edit as you like)
COPY_TARGETS = [
    os.path.join(OUTPUT_DIR, "all_markets_history.json"),
    os.path.join(ROOT, "kalyan", "assets", "all_markets_history.json"),
    os.path.join(OUTPUT_DIR, "history", "all_markets_history.json"),
    os.path.join(ROOT, "..", "all_markets_history.json"),
    os.path.join(ROOT, "AndroidStudioProjects", "multi_market_predictions_v3", "assets", "all_markets_history.json"),
]

EXPECTED_COLS = ["Date", "Open Digit", "Close Digit", "Open Panna", "Close Panna", "Jodi"]

def _parse_date(x):
    if pd.isna(x): return pd.NaT
    s = str(x).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return pd.to_datetime(s, format=fmt, errors="raise")
        except Exception:
            continue
    return pd.NaT

def _normalize_df(df: pd.DataFrame) -> pd.DataFrame:
    # standardize column names you rely on
    ren = {
        "date": "Date",
        "open digit": "Open Digit",
        "close digit": "Close Digit",
        "open panna": "Open Panna",
        "close panna": "Close Panna",
        "jodi": "Jodi",
    }
    df.rename(columns=ren, inplace=True)
    keep = [c for c in EXPECTED_COLS if c in df.columns]
    df = df[keep].copy()

    # parse/sort/dedupe by date
    df["__dt"] = df["Date"].apply(_parse_date)
    df = df[df["__dt"].notna()].sort_values("__dt")
    df = df.drop_duplicates(subset=["__dt"], keep="last")
    df.drop(columns=["__dt"], inplace=True)

    # stringify cells (avoid NaN/None)
    for c in df.columns:
        df[c] = df[c].map(lambda v: "" if pd.isna(v) else str(v))
    return df

def main():
    os.makedirs(os.path.dirname(PRIMARY_JSON), exist_ok=True)
    os.makedirs(os.path.join(OUTPUT_DIR, "history"), exist_ok=True)

    history = {}
    csvs = sorted(glob.glob(os.path.join(OUTPUT_DIR, "*.csv")))
    if not csvs:
        print(f"❌ No CSVs found in {OUTPUT_DIR}")
        return

    for csv_path in csvs:
        market = os.path.splitext(os.path.basename(csv_path))[0]
        try:
            df = pd.read_csv(csv_path)
            df = _normalize_df(df)
            records = df.to_dict(orient="records")
            history[market] = records
            print(f"  • Loaded {len(records)} rows for '{market}'")
        except Exception as e:
            print(f"⚠️ Skipped {market}: {e}")

    # write primary file
    with open(PRIMARY_JSON, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Aggregated {len(history)} markets into '{PRIMARY_JSON}'")

    # copy to optional targets
    for t in COPY_TARGETS:
        try:
            os.makedirs(os.path.dirname(t), exist_ok=True)
            with open(t, "w", encoding="utf-8") as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
            print(f"📁 Copied {PRIMARY_JSON} -> {t}")
        except Exception as e:
            print(f"⚠️ Could not copy to {t}: {e}")

if __name__ == "__main__":
    main()