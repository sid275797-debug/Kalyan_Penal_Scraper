import json
import requests
from bs4 import BeautifulSoup
from fcm_send import send_result_notification

# ================= CONFIG =================

PREDICTIONS_FILE = "todays_predictions.json"
LIVE_RESULTS_URL = "https://sattamatkadpboss.co/"

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

# IMPORTANT:
# Map your internal market IDs -> display names used on the website
# Start SMALL. Add more mappings gradually.
MARKET_NAME_MAP = {
    "sridevi_night_satta_penal_chart": "Sridevi Night",
}

INVALID_RESULTS = {"", "***", "--", "waiting", "wait"}

# ========================================


def load_today_market_ids():
    with open(PREDICTIONS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    return [m["market"] for m in data.get("markets", [])]


def scrape_live_results():
    """
    Returns a dict:
    {
        "Sridevi Night": "123-45-678",
        "Kalyan": "..."
    }
    """
    resp = requests.get(LIVE_RESULTS_URL, headers=HEADERS, timeout=20)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")

    live_results = {}

    # Strategy:
    # DPBoss pages usually show market name followed by result text
    # We scan visible text blocks and pair names with nearby numbers
    text_blocks = soup.get_text("\n", strip=True).split("\n")

    for i, line in enumerate(text_blocks):
        clean = line.strip()

        for display_name in MARKET_NAME_MAP.values():
            if clean.lower() == display_name.lower():
                # try to read next non-empty line as result
                for j in range(i + 1, min(i + 6, len(text_blocks))):
                    candidate = text_blocks[j].strip()
                    if any(ch.isdigit() for ch in candidate):
                        live_results[display_name] = candidate
                        break

    return live_results


def main():
    today_market_ids = load_today_market_ids()
    live_results = scrape_live_results()

    print("📊 Live Results Detected:")
    for k, v in live_results.items():
        print(f"  {k} → {v}")

    notified = set()

    for market_id in today_market_ids:
        display_name = MARKET_NAME_MAP.get(market_id)
        if not display_name:
            continue  # market not mapped yet

        result = live_results.get(display_name)
        if not result:
            continue

        if result.lower() in INVALID_RESULTS:
            continue

        if display_name in notified:
            continue

        print(f"🔔 Sending notification for {display_name}")
        send_result_notification(display_name)
        notified.add(display_name)


if __name__ == "__main__":
    main()
