import json
import time
import re
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

# ================= CONFIG =================
URL = "https://sattamatkadpboss.co/"
OFFSET_MINUTES = 20
OUTPUT_FILE = "market_timings.json"

# ================= HELPERS =================
def normalize_market_key(name: str) -> str:
    return (
        name.lower()
        .replace("&", "and")
        .replace("-", " ")
        .strip()
        .replace("  ", " ")
        .replace(" ", "_")
    )

def add_minutes(time_str, minutes):
    dt = datetime.strptime(time_str, "%H:%M") + timedelta(minutes=minutes)
    return dt.strftime("%H:%M")

def extract_from_visible_dom(driver, markets):
    elements = driver.find_elements(
        By.XPATH,
        "//*[contains(text(),'(') and contains(text(),')') and contains(text(),'-')]"
    )

    for el in elements:
        text = el.text.strip()
        match = re.search(r"\((\d{2}:\d{2})\)\s*-\s*\((\d{2}:\d{2})\)", text)
        if not match:
            continue

        start, end = match.groups()

        try:
            parent = el.find_element(By.XPATH, "./ancestor::*[self::div or self::td][1]")
            block = parent.text.strip().split("\n")
        except:
            continue

        if len(block) < 2:
            continue

        name = block[0].strip()

        if "jodi" in name.lower() or len(name) < 3:
            continue

        key = normalize_market_key(name)

        if key in markets:
            continue

        markets[key] = {
            "display": name,
            "start": start,
            "end": end,
            "monitor_start": add_minutes(start, OFFSET_MINUTES),
            "monitor_end": end
        }

# ================= SELENIUM SETUP =================
options = Options()
options.add_argument("--headless")
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")
options.add_argument("--log-level=3")

driver = webdriver.Chrome(options=options)
driver.get(URL)
time.sleep(5)

markets = {}

# ================= CLICK ALL FILTER BUTTONS =================
buttons = driver.find_elements(By.XPATH, "//button | //a")

clicked_texts = set()

for btn in buttons:
    try:
        label = btn.text.strip().lower()
        if not label:
            continue

        # Target known market section buttons
        if any(k in label for k in ["morning", "day", "night", "live"]):
            if label in clicked_texts:
                continue

            clicked_texts.add(label)
            driver.execute_script("arguments[0].click();", btn)
            time.sleep(3)

            extract_from_visible_dom(driver, markets)

    except:
        continue

# ================= FINAL EXTRACTION PASS =================
extract_from_visible_dom(driver, markets)

driver.quit()

# ================= SAVE OUTPUT =================
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(markets, f, indent=2)

print(f"\n✅ Extracted {len(markets)} markets")
print(f"📄 Saved → {OUTPUT_FILE}")

for i, (k, v) in enumerate(markets.items()):
    if i >= 10:
        break
    print(k, "=>", v)