#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
multi_market_scraperrr.py — dpboss.boston Panel Chart Scraper
Headless Chrome. Parses actual table structure:
  Row 0 : header (th only)
  Row 1+: data — all td, 22 per row:
    td[0]  = date range
    td[1]  = open_panna Mon,  td[2]  = jodi Mon,  td[3]  = close_panna Mon
    td[4]  = open_panna Tue,  td[5]  = jodi Tue,  td[6]  = close_panna Tue
    ... (7 days)
"""

import os, sys, re, time, json
sys.stdout.reconfigure(encoding="utf-8")

import pandas as pd
from datetime import datetime, timedelta

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

# ===== CONFIG =====
ROOT       = os.path.dirname(os.path.abspath(__file__))
BASE_URL   = "https://dpboss.boston"
URLS_FILE  = os.path.join(ROOT, "all_market_urls_cleaned.json")
OUTPUT_DIR = os.path.join(ROOT, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

PAGE_WAIT   = 10   # seconds for JS to render
REQUEST_GAP = 2    # seconds between markets


# ===== HEADLESS DRIVER =====
def make_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1280,900")
    options.add_argument("--log-level=3")
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    )
    options.add_experimental_option("excludeSwitches", ["enable-logging"])
    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(30)
    return driver


# ===== LOAD MARKETS =====
def load_markets():
    if not os.path.exists(URLS_FILE):
        print(f"ERROR: '{URLS_FILE}' not found.")
        print("Run  python extract_market_urls.py  first!")
        sys.exit(1)
    with open(URLS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    markets, seen = [], set()
    for m in data:
        name = m.get("name", "")
        url  = m.get("url", "")
        if "panel-chart-record" not in url and m.get("slug"):
            url = f"{BASE_URL}/panel-chart-record/{m['slug']}.php"
        if name and url and name not in seen:
            seen.add(name)
            markets.append({"name": name, "url": url})
    return markets


# ===== DATE PARSING =====
def parse_date(raw):
    """
    Handles:  '14-11-2022\nto\n20-11-2022'  →  '14/11/2022'
              '28/12/2020 to 02/01/2021'     →  '28/12/2020'
    """
    raw = re.sub(r'\s+', ' ', raw.strip())
    part = raw.split("to")[0].strip()
    for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(part, fmt).strftime("%d/%m/%Y")
        except ValueError:
            continue
    return part


# ===== SCRAPE ONE MARKET =====
def scrape_market(driver, name, url):
    print(f"\n[{name}]  {url}")

    try:
        driver.get(url)
        time.sleep(PAGE_WAIT)
    except Exception as e:
        print(f"  FAILED to load: {e}")
        return False

    # Find any table on the page
    tables = driver.find_elements(By.TAG_NAME, "table")
    if not tables:
        print(f"  No table found on page.")
        return False

    # Use first table with actual data rows
    table = None
    for t in tables:
        rows = t.find_elements(By.TAG_NAME, "tr")
        if len(rows) > 2:
            table = t
            break
    if not table:
        print(f"  No data table found.")
        return False

    rows = table.find_elements(By.TAG_NAME, "tr")
    records = []

    for row in rows:
        tds = row.find_elements(By.TAG_NAME, "td")

        # Data rows have all td (no th), 22 cells:
        # td[0]=date, then groups of 3: open_panna, jodi, close_panna per day
        if len(tds) < 4:
            continue

        # Parse date from td[0]
        date_raw = tds[0].text.strip()
        base_date_str = parse_date(date_raw)
        try:
            base_dt = datetime.strptime(base_date_str, "%d/%m/%Y")
        except ValueError:
            continue

        # Walk td[1], td[2], td[3] ... in groups of 3
        # Each group = one day: open_panna, jodi, close_panna
        day_offset = 0
        i = 1
        while i + 2 < len(tds):
            open_raw  = tds[i].text.strip().replace("\n", "").replace(" ", "")
            jodi_raw  = tds[i+1].text.strip().replace("\n", "").replace(" ", "")
            close_raw = tds[i+2].text.strip().replace("\n", "").replace(" ", "")

            # Skip blanks and holidays
            if '*' in open_raw or '*' in jodi_raw or '*' in close_raw:
                i += 3; day_offset += 1; continue
            if not open_raw or not jodi_raw or not close_raw:
                i += 3; day_offset += 1; continue

            # Validate: 3-digit panna, 2-digit jodi
            if not re.fullmatch(r'\d{3}', open_raw):
                i += 3; day_offset += 1; continue
            if not re.fullmatch(r'\d{2}', jodi_raw):
                i += 3; day_offset += 1; continue
            if not re.fullmatch(r'\d{3}', close_raw):
                i += 3; day_offset += 1; continue

            row_date = (base_dt + timedelta(days=day_offset)).strftime("%d/%m/%Y")

            records.append({
                "Date":        row_date,
                "Open Panna":  open_raw,
                "Jodi":        jodi_raw,
                "Close Panna": close_raw,
                "Open Digit":  jodi_raw[0],
                "Close Digit": jodi_raw[1],
            })

            i += 3
            day_offset += 1

    if not records:
        print(f"  No data parsed.")
        return False

    df = pd.DataFrame(records)
    df["__dt"] = pd.to_datetime(df["Date"], dayfirst=True, errors="coerce")
    df = df[df["__dt"].notna()].sort_values("__dt").drop_duplicates(subset=["__dt"], keep="last")
    df.drop(columns=["__dt"], inplace=True)

    cols = ["Date", "Open Digit", "Close Digit", "Open Panna", "Close Panna", "Jodi"]
    for c in cols:
        if c not in df.columns:
            df[c] = ""
    df = df[cols]

    out_path = os.path.join(OUTPUT_DIR, f"{name}.csv")
    df.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"  OK: {len(df)} rows -> {out_path}")
    return True


# ===== MAIN =====
def main():
    markets = load_markets()
    print(f"\n{'='*60}")
    print(f"  dpboss.boston Panel Chart Scraper (Headless Chrome)")
    print(f"  Markets : {len(markets)}")
    print(f"  Output  : {OUTPUT_DIR}")
    print(f"  Wait    : {PAGE_WAIT}s per page")
    print(f"{'='*60}\n")

    driver  = make_driver()
    success = 0
    failed  = []

    try:
        for m in markets:
            try:
                if scrape_market(driver, m["name"], m["url"]):
                    success += 1
                else:
                    failed.append(m["name"])
            except Exception as e:
                print(f"  CRASH on {m['name']}: {e}")
                failed.append(m["name"])
                try: driver.quit()
                except Exception: pass
                driver = make_driver()
            time.sleep(REQUEST_GAP)
    finally:
        try: driver.quit()
        except Exception: pass

    print(f"\n{'='*60}")
    print(f"  Done : {success}/{len(markets)} markets scraped.")
    if failed:
        print(f"  Failed ({len(failed)}): {', '.join(failed)}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
