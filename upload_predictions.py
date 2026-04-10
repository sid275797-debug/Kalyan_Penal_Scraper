# upload_predictions.py
import json
import firebase_admin
from firebase_admin import credentials, firestore
from typing import Any, Dict, List

# ---------- CONFIG ----------
SERVICE_ACCOUNT = "serviceAccount.json"   # path to your Firebase service account JSON
JSON_INPUT = "predictions_v4.json"        # path to your engine output
COLLECTION = "app_data"                   # change if your app expects another collection
DOC = "todays_predictions"                # change if your app expects another doc id
# ----------------------------

def ensure_list_of_strings(v: Any) -> List[str]:
    """Convert numeric/list/whatever to list[str] safely for UI expectation."""
    if v is None:
        return []
    if isinstance(v, list):
        return [str(x) for x in v]
    # scalar -> single-element list
    return [str(v)]

def normalize_market_entry(raw: Any) -> Dict[str, Any]:
    """
    Accepts either:
      - Map with keys (marketKey/market/marketName, predictions)
      - Map-of-markets: { "kalyan": { predictions... } }
    Returns: { 'market': <name>, 'predictions': {...} }
    """
    if not isinstance(raw, dict):
        return {}

    # prefer explicit fields
    mk = None
    if isinstance(raw.get("marketKey"), str) and raw.get("marketKey").strip():
        mk = raw.get("marketKey").strip()
    if mk is None and isinstance(raw.get("market"), str) and raw.get("market").strip():
        mk = raw.get("market").strip()
    if mk is None and isinstance(raw.get("marketName"), str) and raw.get("marketName").strip():
        mk = raw.get("marketName").strip()

    # map-of-markets style: { "kalyan": { ... } }
    if mk is None:
        keys = [k for k in raw.keys() if isinstance(k, str) and k.strip()]
        if keys:
            first = keys[0]
            maybe = raw.get(first)
            if isinstance(maybe, dict):
                m = dict(maybe)  # copy
                m["market"] = first
                return {"market": first, "predictions": m.get("predictions", m)}

    # normal case
    preds = raw.get("predictions") or {}
    # sometimes the raw itself *is* the predictions object, handle that
    if not preds and any(k in raw for k in ("open_digits", "open_pannas", "jodis", "close_pannas", "close_digits", "Open Pannas", "Open Digits")):
        preds = raw

    # Normalize keys that UI might expect; keep original keys too
    normalized_preds: Dict[str, Any] = {}

    # keep numeric arrays as-is for digits, but convert pannas/jodis to strings lists
    # convert any list fields named like open_pannas / close_pannas / jodis to list[str]
    for k, v in preds.items():
        kl = k.lower()
        if kl in ("open_pannas", "close_pannas", "open_panna", "close_panna", "openpannas", "closepannas", "open panna", "close panna", "open p"): 
            normalized_preds["open_pannas"] = ensure_list_of_strings(v)
            normalized_preds[k] = ensure_list_of_strings(v)
        elif kl in ("close_pannas", "close_panna", "closepannas"):
            normalized_preds["close_pannas"] = ensure_list_of_strings(v)
            normalized_preds[k] = ensure_list_of_strings(v)
        elif kl in ("jodis", "jodi", "jodies"):
            normalized_preds["jodis"] = ensure_list_of_strings(v)
            normalized_preds[k] = ensure_list_of_strings(v)
        elif kl in ("open_digits", "close_digits", "open digit", "close digit"):
            # digits can remain numeric list but ensure list
            if isinstance(v, list):
                normalized_preds[k] = v
            else:
                normalized_preds[k] = [v]
        else:
            # fallback: store exactly as provided, converting nested maps/lists to plain python structures
            normalized_preds[k] = v

    # Always ensure open_pannas/close_pannas/jodis keys exist (avoid UI crashing)
    normalized_preds.setdefault("open_pannas", [])
    normalized_preds.setdefault("close_pannas", [])
    normalized_preds.setdefault("jodis", [])
    normalized_preds.setdefault("open_digits", [])
    normalized_preds.setdefault("close_digits", [])

    market_name = mk or raw.get("market") or raw.get("marketName") or preds.get("market") or preds.get("marketName") or ""
    return {"market": market_name, "predictions": normalized_preds}

def main():
    # init firebase
    cred = credentials.Certificate(SERVICE_ACCOUNT)
    firebase_admin.initialize_app(cred)
    db = firestore.client()

    # load JSON
    with open(JSON_INPUT, "r", encoding="utf-8") as f:
        data = json.load(f)

    markets_list = []

    # If top-level is a dict with 'markets' key, use that
    if isinstance(data, dict) and "markets" in data:
        raw_markets = data["markets"]
    else:
        raw_markets = data

    # Accept either a list of markets or a dict-of-markets
    if isinstance(raw_markets, dict):
        # { "kalyan": {predictions...}, ... }
        for k, v in raw_markets.items():
            entry = normalize_market_entry({k: v})
            if entry and entry.get("market"):
                markets_list.append(entry)
    elif isinstance(raw_markets, list):
        for item in raw_markets:
            entry = normalize_market_entry(item)
            if entry and entry.get("market"):
                markets_list.append(entry)
    else:
        # unknown shape: try to wrap single predictions object
        entry = normalize_market_entry(raw_markets)
        if entry and entry.get("market"):
            markets_list.append(entry)

    # Build doc payload — keep 'markets' key because Flutter read showed it expects that.
    payload = {"markets": markets_list}

    # write to Firestore
    doc_ref = db.collection(COLLECTION).document(DOC)
    doc_ref.set(payload)
    print(f"Uploaded {len(markets_list)} markets to {COLLECTION}/{DOC}")

if __name__ == "__main__":
    main()