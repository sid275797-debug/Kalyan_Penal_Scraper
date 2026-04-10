#!/usr/bin/env python3
"""
unified_prediction_uploader.py

- Calls a local prediction engine module (optional) which should expose a `main()` function.
- Loads todays_predictions.json (or path provided via --predictions-file).
- Optionally writes the payload into Firebase Realtime Database (RTDB) under the specified path.
- Usage:
    python unified_prediction_uploader.py --service-account serviceAccount.json --db-url https://<PROJECT>.firebaseio.com/ [--engine prediction_engine_v4] [--db-path app_data/todays_predictions] [--predictions-file todays_predictions.json] [--dry-run]
"""

import argparse
import importlib
import json
import os
import sys
import traceback
from datetime import datetime

# firebase_admin imports are optional until we need them
try:
    import firebase_admin
    from firebase_admin import credentials, db
except Exception:
    firebase_admin = None
    credentials = None
    db = None


def try_call_engine(engine_module_name: str):
    """
    Import and call engine_module_name.main() if possible.
    Returns tuple (result, error) where error is None if success.
    """
    if not engine_module_name:
        return None, None

    try:
        mod = importlib.import_module(engine_module_name)
    except Exception as e:
        tb = traceback.format_exc()
        return None, f"Failed to import engine module '{engine_module_name}': {e}\n{tb}"

    # prefer main(), fallback to run() or predict()
    for fn_name in ("main", "run", "predict"):
        fn = getattr(mod, fn_name, None)
        if callable(fn):
            try:
                # call and capture return (engines might write files instead)
                res = fn()
                return res, None
            except Exception as e:
                tb = traceback.format_exc()
                return None, f"Engine function {engine_module_name}.{fn_name}() raised: {e}\n{tb}"

    return None, f"Engine module '{engine_module_name}' imported but no callable main/run/predict() found."


def find_predictions_file(candidate: str = None):
    """
    Return path to predictions JSON file. Priority:
      1. candidate argument if provided and exists
      2. './todays_predictions.json'
      3. './output/todays_predictions.json'
      4. search common fallback files in cwd
    Returns path or None if not found.
    """
    candidates = []
    if candidate:
        candidates.append(candidate)
    candidates.extend([
        "todays_predictions.json",
        os.path.join("output", "todays_predictions.json"),
        "predictions_v4.json",
        os.path.join("output", "predictions_v4.json"),
    ])

    for c in candidates:
        if c and os.path.isfile(c):
            return os.path.abspath(c)
    return None


def load_json_file(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def normalize_payload(raw):
    """
    Normalize several shapes into a JSON-serializable payload.
    Accepts:
      - list (of predictions)
      - dict with 'data' or 'markets' (extract)
      - map-of-markets -> convert values to list
    Returns a structure (list or dict) that will be uploaded as wrapper['data'].
    """
    if raw is None:
        return []

    if isinstance(raw, list):
        return raw

    if isinstance(raw, dict):
        # common shapes
        if "data" in raw and isinstance(raw["data"], list):
            return raw["data"]
        if "markets" in raw and isinstance(raw["markets"], list):
            return raw["markets"]
        # sometimes root is map-of-markets e.g. { "kalyan": {...}, ... }
        # convert values that are dicts into a list
        entries = [v for v in raw.values() if isinstance(v, dict)]
        if entries:
            return entries

    # fallback: return raw as-is (best-effort)
    return raw


def normalize_entry_keys_for_app(payload):
    """
    Transform each market entry to the key names expected by the mobile app.
    Specifically: rename 'predictions' -> 'p' (if present).
    Works in-place on lists; returns the transformed payload.

    Accepts:
      - list of entries (most common)
      - dict (if someone passed a map-of-markets - convert values)
    """
    if payload is None:
        return payload

    # If payload is a dict that itself is a map-of-markets, convert to list of dicts
    if isinstance(payload, dict):
        # If dict has numeric keys or market keys mapped to objects, keep values
        values = [v for v in payload.values() if isinstance(v, dict)]
        if values:
            payload = values
        else:
            # single object - normalize it if it has 'predictions'
            # e.g. {"market": "x", "predictions": {...}}
            if "predictions" in payload and "p" not in payload:
                payload = [ { **payload, "p": payload.get("predictions") } ]
                payload[0].pop("predictions", None)
            else:
                # unknown shape; return as-is
                return payload

    # If payload is a list, normalize each entry in list
    if isinstance(payload, list):
        new_list = []
        for item in payload:
            if not isinstance(item, dict):
                new_list.append(item)
                continue

            # If item already has p, leave it
            if "p" in item:
                new_list.append(item)
                continue

            # If item has 'predictions', rename to 'p'
            if "predictions" in item:
                # move predictions to p and remove predictions
                new_item = dict(item)  # shallow copy
                new_item["p"] = new_item.get("predictions")
                new_item.pop("predictions", None)
                new_list.append(new_item)
                continue

            # Sometimes nested key might be 'preds' or 'prediction' or 'data'
            # Try a few heuristics (non-destructive)
            if "prediction" in item and "p" not in item:
                new_item = dict(item)
                new_item["p"] = new_item.get("prediction")
                new_item.pop("prediction", None)
                new_list.append(new_item)
                continue

            if "data" in item and isinstance(item["data"], dict) and "p" not in item:
                new_item = dict(item)
                new_item["p"] = new_item.get("data")
                new_item.pop("data", None)
                new_list.append(new_item)
                continue

            # fallback: leave item unchanged
            new_list.append(item)

        return new_list

    return payload


def init_firebase(service_account_path: str, db_url: str):
    if firebase_admin is None:
        raise RuntimeError("firebase_admin is not installed. Run: pip install firebase-admin")

    # If already initialized with a different app, reuse it only if config matches
    try:
        # If default app exists, we won't attempt to create another
        firebase_admin.get_app()
    except Exception:
        # initialize new
        cred = credentials.Certificate(service_account_path)
        firebase_admin.initialize_app(cred, {"databaseURL": db_url})


def write_to_rtdb(db_path: str, payload, dry_run: bool = False):
    wrapper = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "source": "unified_prediction_uploader",
        "data": payload,
    }

    if dry_run:
        print("DRY RUN - would write wrapper to RTDB path:", db_path)
        print(json.dumps(wrapper, indent=2, ensure_ascii=False)[:4096])
        return

    # ensure firebase_admin initialized
    if firebase_admin is None or db is None:
        raise RuntimeError("firebase_admin is not available. Cannot write to RTDB.")

    ref = db.reference(db_path)
    ref.set(wrapper)
    print(f"Uploaded predictions to RTDB path: {db_path}")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Upload predictions to Firebase RTDB.")
    parser.add_argument(
        "--service-account", "-s", required=False,
        help="Path to Firebase service account JSON (required unless --dry-run and no RTDB write)."
    )
    parser.add_argument(
        "--db-url", "-u", required=False,
        help="Firebase RTDB URL (ex: https://PROJECT.firebaseio.com/) - required unless --dry-run."
    )
    parser.add_argument(
        "--engine", "-e", default=None,
        help="Optional python module name to call before uploading e.g. prediction_engine_v4"
    )
    parser.add_argument(
        "--db-path", "-p", default="app_data/todays_predictions",
        help="RTDB path to write to (default: app_data/todays_predictions)"
    )
    parser.add_argument(
        "--predictions-file", default=None,
        help="Path to local predictions JSON file to upload (default: picks todays_predictions.json or output/predictions_v4.json)"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Don't write to RTDB; just print what would be written."
    )

    args = parser.parse_args(argv)

    # ensure we always have a db_path (CLI can override it)
    db_path = args.db_path if getattr(args, "db_path", None) else "app_data/todays_predictions"
    predictions_file_arg = args.predictions_file
    dry_run = bool(args.dry_run)
    engine_module = args.engine

    print("Engine module:", engine_module)
    print("DB path:", db_path)
    print("Dry run:", dry_run)

    # 1) Try call engine module (if provided)
    if engine_module:
        print(f"Trying engine function: {engine_module}.main()")
        result, err = try_call_engine(engine_module)
        if err:
            print("❌ Engine error:", err)
            # do not abort here — the engine might have produced a file already; continue
        else:
            print("✅ Engine executed successfully (result may be None).")

    # 2) Locate predictions file
    predictions_path = find_predictions_file(predictions_file_arg)
    if not predictions_path:
        msg = "No predictions file found. Provide --predictions-file or ensure todays_predictions.json exists in cwd/output."
        print("❌", msg)
        if dry_run:
            print("Dry-run mode: exiting without writing.")
            return 0
        else:
            raise FileNotFoundError(msg)

    print("✅ Using predictions file:", predictions_path)

    # 3) Load file
    try:
        raw = load_json_file(predictions_path)
    except Exception as e:
        print("❌ Failed to load JSON from predictions file:", e)
        traceback.print_exc()
        raise

    payload = normalize_payload(raw)
    # --- NEW: ensure entries use the 'p' key expected by the app ----
    try:
        payload = normalize_entry_keys_for_app(payload)
    except Exception as e:
        print("Warning: normalize_entry_keys_for_app failed:", e)
    # ---------------------------------------------------------------

    print("Normalized prediction entries count:", (len(payload) if isinstance(payload, (list, dict)) else "unknown"))
    if isinstance(payload, list) and len(payload) > 0:
        sample = payload[0]
    else:
        sample = payload
    print("Sample first item:\n", json.dumps(sample, indent=2, ensure_ascii=False)[:2048])

    # 4) If dry-run only, print and exit
    if dry_run:
        print("DRY RUN complete — not writing to RTDB.")
        return 0

    # 5) Validate CLI args for RTDB write
    if not args.service_account or not args.db_url:
        raise ValueError("RTDB write requires --service-account and --db-url unless --dry-run is used.")

    # 6) Initialize firebase and write
    try:
        print("Initializing firebase_admin...")
        init_firebase(args.service_account, args.db_url)
    except Exception as e:
        print("❌ Failed to initialize firebase_admin:", e)
        traceback.print_exc()
        raise

    try:
        write_to_rtdb(db_path, payload, dry_run=dry_run)
    except Exception as e:
        print("❌ Failed to write to RTDB:", e)
        traceback.print_exc()
        raise

    print("Done successfully.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as e:
        print("Fatal error:", e)
        traceback.print_exc()
        sys.exit(2)