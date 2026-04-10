import json
import time
from datetime import datetime

import requests
from bs4 import BeautifulSoup

from fcm_send import send_result_notification

# ================= CONFIG =================

POLL_INTERVAL = 60  # seconds

MARKET_TIMINGS_FILE = "market_timings.json"
PREDICTIONS_FILE = "todays_predictions.json"
MARKET_URLS_FILE = "all_market_urls_cleaned.json"
STATE_FILE = "state.json"

# ================= HELPERS =================

def load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return default


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def now_hhmm():
    return datetime.now().strftime("%H:%M")


def in_window(start, end, now):
    # Handles midnight crossing
    if end < start:
        return now >= start or now <= end
    return start <= now <= end

# ================= LOADERS =================

def load_predictions():
    raw = load_json(PREDICTIONS_FILE, {})
    normalized = {}

    for entry in raw.get("markets", []):
        market = entry["market"]
        p = entry["predictions"]

        normalized[market] = {
            "open_digit": p.get("Open Digits", []),
            "close_digit": p.get("Close Digits", []),
            "open_panna": p.get("Open Pannas", []),
            "close_panna": p.get("Close Pannas", []),
            "jodi": p.get("Jodis", [])
        }

    return normalized


def load_market_urls():
    raw = load_json(MARKET_URLS_FILE, [])
    return {m["name"]: m["url"] for m in raw}

# ================= LIVE SCRAPER =================

def extract_live_values(market_url):
    """
    Lightweight live result extractor (NO Selenium)
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0"
        }

        r = requests.get(market_url, headers=headers, timeout=10)
        if r.status_code != 200:
            return {}

        soup = BeautifulSoup(r.text, "html.parser")
        table = soup.select_one("table.pchart")
        if not table:
            return {}

        rows = table.find_all("tr")
        if len(rows) < 2:
            return {}

        # First data row = latest result
        row = rows[1]
        ths = row.find_all("th")
        tds = row.find_all("td")

        if len(ths) < 3 or len(tds) < 1:
            return {}

        open_panna = ths[1].get_text(strip=True)
        close_panna = ths[2].get_text(strip=True)
        jodi = tds[0].get_text(strip=True)

        if len(jodi) != 2:
            return {}

        return {
            "open_digit": jodi[0],
            "open_panna": open_panna,
            "jodi": jodi,
            "close_panna": close_panna,
            "close_digit": jodi[1]
        }

    except Exception:
        return {}

# ================= MAIN ENGINE =================

def main():
    timings = load_json(MARKET_TIMINGS_FILE, {})
    predictions = load_predictions()
    urls = load_market_urls()
    state = load_json(STATE_FILE, {})

    print("🚀 Notification monitor started")

    while True:
        now = now_hhmm()

        for market, timing in timings.items():
            if market not in predictions:
                continue
            if market not in urls:
                continue
            if not in_window(timing["monitor_start"], timing["monitor_end"], now):
                continue

            live = extract_live_values(urls[market])
            if not live:
                continue

            state.setdefault(market, {})

            for key in ["open_digit", "open_panna", "jodi", "close_panna", "close_digit"]:
                val = live.get(key)
                if not val:
                    continue

                if state[market].get(key) == val:
                    continue

                if val in predictions[market].get(key, []):
                    message = f"{market.replace('_',' ').title()} {key.replace('_',' ').title()} {val} PASSED"
                    send_result_notification(message)

                    state[market][key] = val
                    save_json(STATE_FILE, state)

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
