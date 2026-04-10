#!/usr/bin/env python3
import random
import string
import datetime as dt
import json
import firebase_admin
from firebase_admin import credentials, db

# ================= CONFIG =================
DATABASE_URL = "https://sattamatkaai-77102-default-rtdb.firebaseio.com/"
SERVICE_ACCOUNT_FILE = "serviceAccount.json"

TIERS = {
    "1-day": 1,
    "7-day": 7,
    "15-day": 15,
    "30-day": 30,
}
CODES_PER_TIER = 100
CODE_LENGTH = 8
LOCAL_BACKUP_FILE = "unlock_codes_backup.json"

# ================= INITIALIZE =================
if not firebase_admin._apps:
    cred = credentials.Certificate(SERVICE_ACCOUNT_FILE)
    firebase_admin.initialize_app(cred, {"databaseURL": DATABASE_URL})

ref = db.reference("unlock_codes")

def new_code():
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=CODE_LENGTH))

def generate_and_upload_unlock_codes():
    payload = {}
    
    # 1. Master Test Code (Default 30 days)
    payload["TESTPREM1"] = {
        "tier": "test",
        "used": False,
        "duration_days": 30,
        "expires": "2099-12-31T23:59:59", # Keep master code long-lived
    }

    existing = {"TESTPREM1"}

    # 2. Generate Duration-Based Codes
    for tier_name, days in TIERS.items():
        for _ in range(CODES_PER_TIER):
            code = new_code()
            while code in existing:
                code = new_code()
            existing.add(code)

            payload[code] = {
                "tier": tier_name,
                "used": False,
                "duration_days": days,  # 🔥 The app will use this to start the timer
                "expires": "1970-01-01T00:00:00", # Dummy date to avoid null errors
            }

    # 3. 🔥 PUSH TO FIREBASE
    ref.update(payload)

    # 4. 💾 SAVE LOCAL BACKUP
    with open(LOCAL_BACKUP_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    print(f"✅ Successfully uploaded {len(payload)} codes.")
    print(f"🚀 Model: Activation-on-Entry (Days granted based on tier)")

if __name__ == "__main__":
    generate_and_upload_unlock_codes()