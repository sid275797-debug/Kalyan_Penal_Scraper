#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
multi_market_scraperrr_fixed.py — dpboss.boston Panel Chart Scraper
Silent, memory-optimized, with auto chromedriver updates.
"""

import os
import sys
import re
import time
import json
import threading
import gc
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta

# Suppress ALL warnings and logs
warnings.filterwarnings('ignore')
os.environ['WDM_LOG_LEVEL'] = '0'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

sys.stdout.reconfigure(encoding="utf-8")

import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

# ===== CONFIG =====
ROOT = os.path.dirname(os.path.abspath(__file__))
BASE_URL = "https://dpboss.boston"
URLS_FILE = os.path.join(ROOT, "all_market_urls_cleaned.json")
OUTPUT_DIR = os.path.join(ROOT, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

PAGE_WAIT = 4      
REQUEST_GAP = 0.3  
MAX_WORKERS = 3    
BATCH_SIZE = 10    

# ===== TIMING UTILS =====
lock = threading.Lock()

def format_duration(seconds):
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        return f"{seconds/60:.1f}m"
    else:
        return f"{seconds/3600:.1f}h"

def timestamp():
    return datetime.now().strftime("%H:%M:%S")

def log(msg):
    with lock:
        print(msg)

# ===== HEADLESS DRIVER =====
def make_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1280,900")
    options.add_argument("--log-level=3")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-images")
    options.add_argument("--js-flags=--max-old-space-size=512")
    options.add_argument("--single-process")
    options.add_argument("--no-zygote")
    options.add_argument("--disable-logging")
    options.add_argument("--silent")
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    )
    options.add_experimental_option("excludeSwitches", ["enable-logging", "enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_experimental_option("prefs", {
        "profile.managed_default_content_settings.images": 2,
        "disk-cache-size": 4096,
    })
    
    # Silent service
    service = Service(ChromeDriverManager().install(), log_output=os.devnull)
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(30)
    return driver


# ===== LOAD MARKETS =====
def load_markets():
    if not os.path.exists(URLS_FILE):
        log(f"[{timestamp()}] ERROR: '{URLS_FILE}' not found.")
        sys.exit(1)
    with open(URLS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    markets, seen = [], set()
    for m in data:
        name = m.get("name", "")
        url = m.get("url", "")
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
def scrape_market_worker(market_data):
    name = market_data["name"]
    url = market_data["url"]
    start_time = time.time()
    
    driver = None
    try:
        driver = make_driver()
        driver.get(url)
        time.sleep(PAGE_WAIT)

        tables = driver.find_elements(By.TAG_NAME, "table")
        if not tables:
            driver.quit()
            return {"name": name, "success": False, "rows": 0, "duration": time.time() - start_time, "error": "No table"}

        table = None
        for t in tables:
            rows = t.find_elements(By.TAG_NAME, "tr")
            if len(rows) > 2:
                table = t
                break
        
        if not table:
            driver.quit()
            return {"name": name, "success": False, "rows": 0, "duration": time.time() - start_time, "error": "No data table"}

        rows = table.find_elements(By.TAG_NAME, "tr")
        records = []

        for row in rows:
            tds = row.find_elements(By.TAG_NAME, "td")
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
                open_raw = tds[i].text.strip().replace("\n", "").replace(" ", "")
                jodi_raw = tds[i+1].text.strip().replace("\n", "").replace(" ", "")
                close_raw = tds[i+2].text.strip().replace("\n", "").replace(" ", "")

                if '*' in open_raw or '*' in jodi_raw or '*' in close_raw:
                    i += 3; day_offset += 1; continue
                if not open_raw or not jodi_raw or not close_raw:
                    i += 3; day_offset += 1; continue
                if not re.fullmatch(r'\d{3}', open_raw):
                    i += 3; day_offset += 1; continue
                if not re.fullmatch(r'\d{2}', jodi_raw):
                    i += 3; day_offset += 1; continue
                if not re.fullmatch(r'\d{3}', close_raw):
                    i += 3; day_offset += 1; continue

                row_date = (base_dt + timedelta(days=day_offset)).strftime("%d/%m/%Y")
                records.append({
                    "Date": row_date,
                    "Open Panna": open_raw,
                    "Jodi": jodi_raw,
                    "Close Panna": close_raw,
                    "Open Digit": jodi_raw[0],
                    "Close Digit": jodi_raw[1],
                })

                i += 3
                day_offset += 1

        driver.quit()
        driver = None

        if not records:
            return {"name": name, "success": False, "rows": 0, "duration": time.time() - start_time, "error": "No data"}

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

        return {"name": name, "success": True, "rows": len(df), "duration": time.time() - start_time, "error": None}

    except Exception as e:
        if driver:
            try:
                driver.quit()
            except:
                pass
        return {"name": name, "success": False, "rows": 0, "duration": time.time() - start_time, "error": str(e)[:40]}


# ===== PROCESS BATCH =====
def process_batch(batch_markets, batch_num, total_batches, script_start, completed_counter, total_markets):
    batch_start = time.time()
    batch_results = []
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_market = {
            executor.submit(scrape_market_worker, market): market 
            for market in batch_markets
        }
        
        for future in as_completed(future_to_market):
            result = future.result()
            batch_results.append(result)
            
            with lock:
                completed_counter[0] += 1
                completed = completed_counter[0]
                
                name = result["name"]
                success = result["success"]
                rows = result["rows"]
                duration = result["duration"]
                error = result["error"]
                
                elapsed = time.time() - script_start
                progress_pct = (completed / total_markets) * 100
                
                if success:
                    status = f"✓ {rows} rows"
                else:
                    status = f"✗ {error[:25]}"
                
                log(f"[{timestamp()}] [{completed:3d}/{total_markets}] ({progress_pct:5.1f}%) "
                    f"{name:<20} | {format_duration(duration):>5} | {status}")
            
            time.sleep(REQUEST_GAP)
    
    batch_duration = time.time() - batch_start
    return batch_results, batch_duration


# ===== MAIN =====
def main():
    script_start = time.time()
    markets = load_markets()
    total_markets = len(markets)
    
    print(f"\n{'='*65}")
    print(f"  dpboss.boston Panel Chart Scraper - MEMORY OPTIMIZED")
    print(f"  Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Markets: {total_markets} | Workers: {MAX_WORKERS} | Batch: {BATCH_SIZE}")
    print(f"{'='*65}\n")

    batches = [markets[i:i+BATCH_SIZE] for i in range(0, len(markets), BATCH_SIZE)]
    total_batches = len(batches)
    
    all_results = []
    success_count = 0
    failed_list = []
    total_rows = 0
    completed_counter = [0]
    
    for batch_idx, batch in enumerate(batches, 1):
        log(f"[{timestamp()}] >>> BATCH {batch_idx}/{total_batches} ({len(batch)} markets) <<<")
        
        batch_results, batch_duration = process_batch(
            batch, batch_idx, total_batches, script_start, completed_counter, total_markets
        )
        
        for result in batch_results:
            all_results.append(result)
            if result["success"]:
                success_count += 1
                total_rows += result["rows"]
            else:
                failed_list.append(result["name"])
        
        log(f"[{timestamp()}] Batch {batch_idx} done in {format_duration(batch_duration)}\n")
        
        gc.collect()
        time.sleep(0.5)

    script_duration = time.time() - script_start
    
    print(f"\n{'='*65}")
    print(f"  SCRAPING COMPLETE")
    print(f"{'='*65}")
    print(f"  Total Time:  {format_duration(script_duration)}")
    print(f"  Success:     {success_count}/{total_markets}")
    print(f"  Total Rows:  {total_rows:,}")
    print(f"  Throughput:  {total_markets/script_duration:.2f} markets/sec")
    if failed_list:
        print(f"  Failed:      {len(failed_list)} - {', '.join(failed_list[:5])}")
    print(f"  End Time:    {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*65}\n")


if __name__ == "__main__":
    main()