# build_history_json.py

import pandas as pd
import glob, json
from pathlib import Path

# ▲ adjust this to your actual folder
CSV_GLOB = "output/*.csv"
OUT_JSON   = "all_markets_history.json"

def build_history():
    all_data = {}
    for path in glob.glob(CSV_GLOB):
        market = Path(path).stem.upper()
        df = pd.read_csv(path, parse_dates=["Date"])
        # convert every row to a dict (you'll get keys: Date, Open Digit, Close Digit, Jodi, Open Panna, Close Panna, etc.)
        records = df.to_dict(orient="records")
        # if Date is a datetime, convert to ISO strings
        for r in records:
            if isinstance(r.get("Date"), pd.Timestamp):
                r["Date"] = r["Date"].isoformat()
        all_data[market] = records

    # write it out
    with open(OUT_JSON, "w") as f:
        json.dump(all_data, f, indent=2)
    print(f"Wrote history for {len(all_data)} markets to {OUT_JSON}")

if __name__ == "__main__":
    build_history()