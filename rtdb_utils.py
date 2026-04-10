# rtdb_utils.py
import os
import logging
from datetime import datetime
try:
    import firebase_admin
    from firebase_admin import credentials, db
except Exception:
    firebase_admin = None

SA_PATH = os.environ.get("FIREBASE_ADMIN_KEY")
RTDB_URL = os.environ.get("FIREBASE_RTDB_URL")

def init_firebase():
    if not firebase_admin:
        logging.warning("firebase-admin not installed; RTDB writes disabled.")
        return False
    if not SA_PATH or not RTDB_URL:
        logging.warning("FIREBASE_ADMIN_KEY or FIREBASE_RTDB_URL not set; RTDB writes disabled.")
        return False
    if not firebase_admin._apps:
        try:
            cred = credentials.Certificate(SA_PATH)
            firebase_admin.initialize_app(cred, {"databaseURL": RTDB_URL})
        except Exception as e:
            logging.exception("Failed to initialize firebase-admin: %s", e)
            return False
    return True

def rtdb_set(path: str, obj: dict) -> bool:
    try:
        if not init_firebase():
            return False
        ref = db.reference(path)
        ref.set(obj)
        logging.info("RTDB set -> %s", path)
        return True
    except Exception as e:
        logging.exception("RTDB set failed: %s", e)
        return False

def rtdb_push_archive(base_path: str, date_str: str, obj: dict) -> bool:
    try:
        return rtdb_set(f"{base_path}/{date_str}", obj)
    except Exception as e:
        logging.exception("RTDB archive failed: %s", e)
        return False