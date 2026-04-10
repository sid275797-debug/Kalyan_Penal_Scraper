#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
multi_market_scraper_fast.py — dpboss.boston Panel Chart Scraper (FAST)

Key improvements over Selenium version:
  - requests + BeautifulSoup instead of headless Chrome (~95% less RAM)
  - ThreadPoolExecutor for concurrent scraping (5 workers default)
  - No fixed 10s waits — pure HTTP, instant response parsing
  - Retry logic with exponential backoff
  - Progress tracking with ETA
  - Session reuse with connection pooling

Expected: 80+ markets in ~5-10 minutes instead of 5 hours.
"""

import os, sys, re, json, time
sys.stdout.reconfigure(encoding="utf-8")

import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

# ===== CONFIG =====
ROOT       = os.path.dirname(os.path.abspath(__file__))
BASE_URL   = "https://dpboss.boston"
URLS_FILE  = os.path.join(ROOT, "all_market_urls_cleaned.json")
OUTPUT_DIR = os.path.join(ROOT, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

MAX_WORKERS   = 5      # concurrent scrapers (increase to 8-10 if site handles it)
REQUEST_GAP   = 0.5    # seconds between requests per worker
MAX_RETRIES   = 3      # retry failed requests
TIMEOUT       = 15     # request timeout in seconds

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}

# Thread-safe print and counters
print_lock = Lock()
stats = {"success": 0, "failed": 0, "total": 0, "start_time": 0}
stats_lock = Lock()


def safe_print(msg):
    with print_lock:
        print(msg, flush=True)


# ===== SESSION FACTORY =====
def make_session():
    """Create a requests session with retry logic and connection pooling."""
    session = requests.Session()
    session.headers.update(HEADERS)

    retry_strategy = Retry(
        total=MAX_RETRIES,
        backoff_factor=1,           # 1s, 2s, 4s between retries
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    adapter = HTTPAdapter(
        max_retries=retry_strategy,
        pool_connections=MAX_WORKERS,
        pool_maxsize=MAX_WORKERS + 2,
    )
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


# ===== LOAD MARKETS =====
def load_markets():
    if not os.path.exists(URLS_FILE):
        safe_print(f"ERROR: '{URLS_FILE}' not found.")
        safe_print("Run  python extract_market_urls.py  first!")
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
    raw = re.sub(r'\s+', ' ', raw.strip())
    part = raw.split("to")[0].strip()
    for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(part, fmt).strftime("%d/%m/%Y")
        except ValueError:
            continue
    return part


# ===== SCRAPE ONE MARKET =====
def scrape_market(session, name, url, index, total):
    """Scrape a single market using requests + BeautifulSoup."""
    try:
        resp = session.get(url, timeout=TIMEOUT)
        resp.raise_for_status()
    except requests.RequestException as e:
        safe_print(f"  [{index}/{total}] FAILED {name}: {e}")
        return name, False

    soup = BeautifulSoup(resp.text, "html.parser")

    # Find data table (first table with >2 rows)
    table = None
    for t in soup.find_all("table"):
        rows = t.find_all("tr")
        if len(rows) > 2:
            table = t
            break

    if not table:
        safe_print(f"  [{index}/{total}] {name}: No data table found")
        return name, False

    records = []
    for row in table.find_all("tr"):
        tds = row.find_all("td")
        if len(tds) < 4:
            continue

        date_raw = tds[0].get_text(strip=True)
        base_date_str = parse_date(date_raw)
        try:
            base_dt = datetime.strptime(base_date_str, "%d/%m/%Y")
        except ValueError:
            continue

        day_offset = 0
        i = 1
        while i + 2 < len(tds):
            open_raw  = tds[i].get_text(strip=True).replace(" ", "")
            jodi_raw  = tds[i+1].get_text(strip=True).replace(" ", "")
            close_raw = tds[i+2].get_text(strip=True).replace(" ", "")

            # Skip blanks / holidays / invalid
            if ('*' in open_raw or '*' in jodi_raw or '*' in close_raw
                    or not open_raw or not jodi_raw or not close_raw):
                i += 3; day_offset += 1; continue

            if not (re.fullmatch(r'\d{3}', open_raw)
                    and re.fullmatch(r'\d{2}', jodi_raw)
                    and re.fullmatch(r'\d{3}', close_raw)):
                i += 3; day_offset += 1; continue

            row_date = (base_dt + timedelta(days=day_offset)).strftime("%d/%m/%Y")

            # Open Digit = sum of open panna digits % 10
            # Close Digit = sum of close panna digits % 10
            open_digit  = str(sum(int(d) for d in open_raw) % 10)
            close_digit = str(sum(int(d) for d in close_raw) % 10)

            records.append({
                "Date":        row_date,
                "Open Panna":  open_raw,
                "Jodi":        jodi_raw,
                "Close Panna": close_raw,
                "Open Digit":  open_digit,
                "Close Digit": close_digit,
            })

            i += 3
            day_offset += 1

    if not records:
        safe_print(f"  [{index}/{total}] {name}: No data parsed")
        return name, False

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

    # Update stats and show progress
    with stats_lock:
        stats["success"] += 1
        done = stats["success"] + stats["failed"]
        elapsed = time.time() - stats["start_time"]
        rate = done / elapsed if elapsed > 0 else 0
        remaining = (total - done) / rate if rate > 0 else 0
        safe_print(
            f"  [{index}/{total}] ✓ {name}: {len(df)} rows  "
            f"({done}/{total} done, ~{remaining:.0f}s remaining)"
        )

    return name, True


def worker(args):
    """Worker function for thread pool."""
    session, name, url, index, total = args
    time.sleep(REQUEST_GAP * (index % MAX_WORKERS))  # stagger initial requests
    try:
        return scrape_market(session, name, url, index, total)
    except Exception as e:
        safe_print(f"  [{index}/{total}] CRASH {name}: {e}")
        with stats_lock:
            stats["failed"] += 1
        return name, False


# ===== MAIN =====
def main():
    markets = load_markets()
    total = len(markets)

    print(f"\n{'='*60}")
    print(f"  dpboss.boston Panel Chart Scraper (FAST)")
    print(f"  Markets  : {total}")
    print(f"  Workers  : {MAX_WORKERS} concurrent")
    print(f"  Output   : {OUTPUT_DIR}")
    print(f"  Retries  : {MAX_RETRIES} per request")
    print(f"{'='*60}\n")

    stats["total"] = total
    stats["start_time"] = time.time()

    session = make_session()
    failed_markets = []

    # Prepare work items
    work = [
        (session, m["name"], m["url"], idx + 1, total)
        for idx, m in enumerate(markets)
    ]

    # Concurrent execution
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(worker, w): w[1] for w in work}

        for future in as_completed(futures):
            name = futures[future]
            try:
                market_name, ok = future.result()
                if not ok:
                    failed_markets.append(market_name)
                    with stats_lock:
                        stats["failed"] += 1
            except Exception as e:
                safe_print(f"  Unhandled error for {name}: {e}")
                failed_markets.append(name)
                with stats_lock:
                    stats["failed"] += 1

    elapsed = time.time() - stats["start_time"]
    success = stats["success"]

    print(f"\n{'='*60}")
    print(f"  Done in {elapsed:.1f}s ({elapsed/60:.1f} min)")
    print(f"  Success: {success}/{total}")
    if failed_markets:
        print(f"  Failed ({len(failed_markets)}): {', '.join(failed_markets[:20])}")
        if len(failed_markets) > 20:
            print(f"    ... and {len(failed_markets) - 20} more")
    print(f"  Speed: {success / elapsed * 60:.1f} markets/minute")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()