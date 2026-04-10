#!/usr/bin/env python3
import os, json
from collections import Counter
from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Optional

# --------------- FIREBASE ----------------
try:
    import firebase_admin
    from firebase_admin import credentials, db
except ImportError:
    firebase_admin = None

# ✅ your real Firebase details
FIREBASE_CRED_PATH = r"C:\Users\VCOM\Desktop\Kalyan_Penal_Scraper\serviceAccount.json"
FIREBASE_DB_URL    = "https://sattamatkaai-77102-default-rtdb.firebaseio.com/"

# optional local outputs
WRITE_FLUTTER_ASSET = True
FLUTTER_ASSETS_DIR  = r"C:\Users\VCOM\AndroidStudioProjects\multi_market_predictions_v3\assets"

def _init_firebase():
    if firebase_admin is None:
        raise RuntimeError("firebase-admin not installed. pip install firebase-admin")
    if not firebase_admin._apps:
        if not os.path.isfile(FIREBASE_CRED_PATH):
            raise FileNotFoundError(f"Service account not found: {FIREBASE_CRED_PATH}")
        cred = credentials.Certificate(FIREBASE_CRED_PATH)
        firebase_admin.initialize_app(cred, {"databaseURL": FIREBASE_DB_URL})

# --------------- DATE HELPERS ---------------
def _parse_date_str(s: str) -> Optional[date]:
    s = (s or "").strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(s.split("T")[0], fmt).date()
        except ValueError:
            continue
    return None

def _norm_date(d: Optional[date]) -> str:
    return (d or (date.today() - timedelta(days=1))).strftime("%Y-%m-%d")

# --------------- BUILD LATEST ---------------
def _latest_row_per_market(history: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Dict[str, str]]:
    latest: Dict[str, Dict[str, str]] = {}
    for mk, recs in history.items():
        if not recs: 
            continue
        r = recs[-1]  # safe now (aggregate script sorts)
        d = _parse_date_str(r.get("Date", "")) or (date.today() - timedelta(days=1))
        latest[mk] = {
            "market": mk,
            "Date": _norm_date(d),
            "Open Digit": str(r.get("Open Digit", "")),
            "Close Digit": str(r.get("Close Digit", "")),
            "Open Panna": str(r.get("Open Panna", "")),
            "Close Panna": str(r.get("Close Panna", "")),
            "Jodi": str(r.get("Jodi", "")),
        }
    return latest

def _choose_publish_date(latest_rows: Dict[str, Dict[str, str]]) -> str:
    counts = Counter(r["Date"] for r in latest_rows.values())
    if not counts:
        return _norm_date(None)
    max_count = max(counts.values())
    candidates = [d for d, c in counts.items() if c == max_count]
    chosen = max(candidates)  # newest among most-common dates
    print(f"📅 Date distribution: {dict(counts)}  → chosen: {chosen}")
    return chosen

def _to_rtdb_payload(latest_rows: Dict[str, Dict[str, str]]) -> Dict[str, Dict[str, str]]:
    return {
        mk: {
            "Open Digit": r["Open Digit"],
            "Close Digit": r["Close Digit"],
            "Open Panna": r["Open Panna"],
            "Close Panna": r["Close Panna"],
            "Jodi": r["Jodi"],
        }
        for mk, r in latest_rows.items()
    }

# --------------- MAIN ---------------
def generate_yesterday_results():
    project_root = os.path.dirname(os.path.abspath(__file__))

    # ✅ read canonical history
    history_file = os.path.join(project_root, "sattaboss-data", "data", "all_markets_history.json")
    if not os.path.isfile(history_file):
        print(f"❌ Missing history file: {history_file}")
        return

    with open(history_file, "r", encoding="utf-8") as f:
        history = json.load(f)

    latest_rows = _latest_row_per_market(history)
    market_count = len(latest_rows)
    if market_count < 5:
        print(f"⚠️ Only {market_count} markets detected — aborting upload.")
        return

    publish_date = _choose_publish_date(latest_rows)

    # write local files
    if WRITE_FLUTTER_ASSET:
        os.makedirs(FLUTTER_ASSETS_DIR, exist_ok=True)
        with open(os.path.join(FLUTTER_ASSETS_DIR, "yesterday_results.json"), "w", encoding="utf-8") as f:
            json.dump(list(latest_rows.values()), f, ensure_ascii=False, indent=2)

    out_dir = os.path.join(project_root, "output")
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "yesterday_results.json"), "w", encoding="utf-8") as f:
        json.dump({"date": publish_date, "markets": latest_rows}, f, ensure_ascii=False, indent=2)

    print(f"✅ Prepared yesterday_results.json → {market_count} markets, node date: {publish_date}")

    # upload to RTDB
    try:
        _init_firebase()
        payload = _to_rtdb_payload(latest_rows)
        node = f"sattaboss/yesterday_results/{publish_date}"
        ref = db.reference(node)
        ref.set(payload)
        snap = ref.get() or {}
        print(f"✅ Uploaded {len(payload)} markets to RTDB → {node}")
        print(f"🔍 Verified in DB: {len(snap)} markets present")
    except Exception as e:
        print(f"❌ Firebase upload failed: {e}")

if __name__ == "__main__":
    generate_yesterday_results()