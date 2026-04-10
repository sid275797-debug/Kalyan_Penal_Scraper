import requests
from bs4 import BeautifulSoup
from fcm_send import send_result_notification

URL = "https://sattamatkadpboss.co/"
MARKET_NAME = "Sridevi Night"

def check_sridevi_night():
    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    resp = requests.get(URL, headers=headers, timeout=20)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")

    text = soup.get_text(" ", strip=True).lower()

    # very simple presence check
    if "sridevi night" in text:
        # crude but effective: look for digits near market name
        import re
        match = re.search(r"sridevi night\s+(\d{3}|\d{1,2})", text)

        if match:
            print("✅ Result detected for Sridevi Night")
            send_result_notification(MARKET_NAME)
        else:
            print("⏳ Sridevi Night result not live yet")
    else:
        print("❌ Market name not found on page")

if __name__ == "__main__":
    check_sridevi_night()
