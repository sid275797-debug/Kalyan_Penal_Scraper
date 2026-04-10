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

CHANGES vs original:
  - Auto ChromeDriver : webdriver-manager auto-downloads the matching driver
                        (fixes "chromedriver 145 vs Chrome 146" mismatch)
  - Smart wait  : polls for <table> instead of sleeping a fixed 10s
  - Parallel    : WORKERS=2 Chrome instances (site throttles >2 parallel)
  - Retry       : up to MAX_RETRIES attempts with backoff on timeout/crash
  - Timestamps  : each row gets a 'Scraped_At' column
  - Per-market  : elapsed time printed in console
  - Summary     : total wall-clock time printed at end

INSTALL (one-time):
    pip install webdriver-manager
"""

import os, sys, re, time, json, threading
sys.stdout.reconfigure(encoding="utf-8")

import pandas as pd
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Auto-matching ChromeDriver — resolves version mismatch
try:
    from selenium.webdriver.chrome.service import Service as ChromeService
    from webdriver_manager.chrome import ChromeDriverManager
    _USE_WDM = True
except ImportError:
    _USE_WDM = False   # fallback: rely on PATH chromedriver as before

# ===== CONFIG =====
ROOT       = os.path.dirname(os.path.abspath(__file__))
BASE_URL   = "https://dpboss.boston"
URLS_FILE  = os.path.join(ROOT, "all_market_urls_cleaned.json")
OUTPUT_DIR = os.path.join(ROOT, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

WORKERS        = 2     # keep at 2 — site throttles/drops connections beyond that
TABLE_TIMEOUT  = 20    # max seconds to wait for <table> (raised; site is slow)
PAGE_LOAD_MAX  = 45    # selenium page load timeout (raised from 30)
MAX_RETRIES    = 3     # retry each market this many times on failure
RETRY_BACKOFF  = 5     # seconds to wait between retries

# Thread-safe print lock
_print_lock = threading.Lock()

def tprint(*args, **kwargs):
    """Thread-safe print with IST timestamp prefix."""
    ts = datetime.now().strftime("%H:%M:%S")
    with _print_lock:
        print(f"[{ts}]", *args, **kwargs)


# ===== HEADLESS DRIVER =====
def make_driver():
    options = Options()
    # --headless=new crashes on Chrome 146 + Windows 10 (known bug).
    # Legacy headless is stable and works fine for table scraping.
    options.add_argument("--headless=old")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1280,900")
    options.add_argument("--log-level=3")
    # port=0 → OS picks a free port; prevents collisions between parallel instances
    options.add_argument("--remote-debugging-port=0")
    # Extra stability flags for Windows 10
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-background-networking")
    options.add_argument("--disable-default-apps")
    options.add_argument("--disable-sync")
    options.add_argument("--metrics-recording-only")
    options.add_argument("--mute-audio")
    options.add_argument("--no-first-run")
    # Disable images/CSS — speeds up page load noticeably
    options.add_argument("--blink-settings=imagesEnabled=false")
    prefs = {
        "profile.managed_default_content_settings.images": 2,
        "profile.managed_default_content_settings.stylesheets": 2,
    }
    options.add_experimental_option("prefs", prefs)
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36"
    )
    options.add_experimental_option("excludeSwitches", ["enable-logging"])

    if _USE_WDM:
        # webdriver-manager auto-downloads the correct chromedriver for your Chrome
        service = ChromeService(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
    else:
        # Fallback: use whatever chromedriver is in PATH
        driver = webdriver.Chrome(options=options)

    driver.set_page_load_timeout(PAGE_LOAD_MAX)
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


# ===== SMART WAIT FOR TABLE =====
def wait_for_table(driver, timeout=TABLE_TIMEOUT):
    """
    Instead of sleeping a fixed N seconds, poll until a <table> with
    real data rows appears — or give up after `timeout` seconds.
    Returns the matching table element, or None.
    """
    try:
        # Wait until at least one <table> is present in DOM
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.TAG_NAME, "table"))
        )
    except Exception:
        return None

    # Among all tables, pick the first one with >2 rows
    tables = driver.find_elements(By.TAG_NAME, "table")
    for t in tables:
        rows = t.find_elements(By.TAG_NAME, "tr")
        if len(rows) > 2:
            return t
    return None


# ===== SCRAPE ONE MARKET =====
def scrape_market(driver, name, url):
    t0 = time.time()
    tprint(f"→ START  [{name}]  {url}")

    scraped_at = datetime.now().strftime("%d/%m/%Y %H:%M:%S")  # timestamp for all rows

    try:
        driver.get(url)
    except Exception as e:
        tprint(f"  FAILED to load [{name}]: {e}")
        return False

    table = wait_for_table(driver)
    if not table:
        tprint(f"  No data table found [{name}]")
        return False

    rows = table.find_elements(By.TAG_NAME, "tr")
    records = []

    for row in rows:
        tds = row.find_elements(By.TAG_NAME, "td")

        # Data rows have all td (no th), 22 cells:
        # td[0]=date, then groups of 3: open_panna, jodi, close_panna per day
        if len(tds) < 4:
            continue

        date_raw = tds[0].text.strip()
        base_date_str = parse_date(date_raw)
        try:
            base_dt = datetime.strptime(base_date_str, "%d/%m/%Y")
        except ValueError:
            continue

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
                "Scraped_At":  scraped_at,   # ← NEW timestamp column
            })

            i += 3
            day_offset += 1

    if not records:
        tprint(f"  No data parsed [{name}]")
        return False

    df = pd.DataFrame(records)
    df["__dt"] = pd.to_datetime(df["Date"], dayfirst=True, errors="coerce")
    df = df[df["__dt"].notna()].sort_values("__dt").drop_duplicates(subset=["__dt"], keep="last")
    df.drop(columns=["__dt"], inplace=True)

    cols = ["Date", "Open Digit", "Close Digit", "Open Panna", "Close Panna", "Jodi", "Scraped_At"]
    for c in cols:
        if c not in df.columns:
            df[c] = ""
    df = df[cols]

    out_path = os.path.join(OUTPUT_DIR, f"{name}.csv")
    df.to_csv(out_path, index=False, encoding="utf-8-sig")

    elapsed = time.time() - t0
    tprint(f"  ✓ OK  [{name}]  {len(df)} rows  ({elapsed:.1f}s)  → {out_path}")
    return True


# ===== WORKER (one Chrome instance handles its own market queue) =====
def worker(markets_chunk, results):
    """
    Each worker owns one Chrome driver and processes its assigned markets
    sequentially, retrying up to MAX_RETRIES times on failure.
    Results (name → True/False) are written to the shared dict.
    """
    driver = make_driver()
    try:
        for m in markets_chunk:
            name, url = m["name"], m["url"]
            ok = False
            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    ok = scrape_market(driver, name, url)
                    if ok:
                        break
                    # Not a crash but returned False (no table / no data)
                    if attempt < MAX_RETRIES:
                        tprint(f"  ↺ retry {attempt}/{MAX_RETRIES} [{name}] in {RETRY_BACKOFF}s...")
                        time.sleep(RETRY_BACKOFF)
                except Exception as e:
                    tprint(f"  CRASH [{name}] attempt {attempt}: {type(e).__name__}")
                    # Restart driver after any crash
                    try: driver.quit()
                    except Exception: pass
                    time.sleep(RETRY_BACKOFF * attempt)   # back off longer each time
                    driver = make_driver()
            results[name] = ok
    finally:
        try: driver.quit()
        except Exception: pass


# ===== MAIN =====
def main():
    markets = load_markets()
    wall_start = time.time()

    print(f"\n{'='*65}")
    print(f"  dpboss.boston Panel Chart Scraper  (Headless Chrome)")
    print(f"  Markets  : {len(markets)}")
    print(f"  Workers  : {WORKERS}  (parallel Chrome instances)")
    print(f"  Retries  : up to {MAX_RETRIES}x per market")
    print(f"  Output   : {OUTPUT_DIR}")
    print(f"  Max wait : {TABLE_TIMEOUT}s per page  |  Page load: {PAGE_LOAD_MAX}s")
    print(f"  Driver   : {'webdriver-manager (auto)' if _USE_WDM else 'PATH chromedriver'}")
    print(f"{'='*65}\n")

    # Split market list evenly across workers
    chunks = [markets[i::WORKERS] for i in range(WORKERS)]

    results = {}  # name → True/False, written by workers

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = [pool.submit(worker, chunk, results) for chunk in chunks if chunk]
        for f in as_completed(futures):
            exc = f.exception()
            if exc:
                tprint(f"Worker crashed: {exc}")

    success = sum(1 for v in results.values() if v)
    failed  = [k for k, v in results.items() if not v]
    wall_elapsed = time.time() - wall_start

    print(f"\n{'='*65}")
    print(f"  Done   : {success}/{len(markets)} markets scraped")
    print(f"  Time   : {wall_elapsed:.1f}s total  "
          f"({wall_elapsed/60:.1f} min)  with {WORKERS} workers")
    if failed:
        print(f"  Failed ({len(failed)}): {', '.join(failed)}")
    print(f"{'='*65}\n")


if __name__ == "__main__":
    main()