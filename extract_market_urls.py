#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
extract_market_urls.py
Auto-discovers ALL panel chart URLs from dpboss.boston
Scans EVERY <a href> on the homepage — catches all 100+ market [Panel] links.
Output: all_market_urls_cleaned.json
"""

import sys, json, re, time
sys.stdout.reconfigure(encoding="utf-8")

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://dpboss.boston"
OUT_FILE = "all_market_urls_cleaned.json"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

# Known slugs that exist on the site but may not appear in homepage links.
# Add more here any time you discover new markets.
EXTRA_SLUGS = [
    "madhur-night",
    "rajdhani-day",
    "rajdhani-morning-main",
    "main-bazar-morning",
    "main-bazar-day",
    "sridevi-morning",
    "sridevi-day",
    "karnataka-day",
    "karnataka-night",
    "time-bazar-morning",
    "time-bazar-day",
    "new-time-bazar",
    "prabhat",
    "prabhat-night",
    "diamond",
    "diamond-night",
    "bombay-day",
    "bombay-night",
    "bombay-rajshree-day",
    "bombay-rajshree-night",
    "maharani",
    "maharani-day",
    "maharani-night",
    "supreme-day",
    "supreme-night",
    "worli-morning",
    "worli-night",
    "worli-mumbai",
    "worli-mumbai-day",
    "worli-mumbai-night",
    "tara-mumbai-day",
    "tara-mumbai-night",
    "laxmi-day",
    "laxmi-night",
    "mumbai-morning",
    "mumbai-bazar",
    "mahadevi",
    "mahadevi-morning",
    "mahadevi-night",
    "gujrat-morning",
    "gujrat-night",
    "star-tara-morning",
    "star-tara-day",
    "star-tara-night",
    "kamal-morning",
    "kamal-day",
    "kamal-night",
    "andhra-morning",
    "andhra-day",
    "andhra-night",
    "mangal-morning",
    "mangal-day",
    "mangal-night",
    "mangal-bazar",
    "super-morning",
    "super-day",
    "super-night",
    "super-milan-day",
    "super-milan-night",
    "super-king",
    "super-king-night",
    "ratna-morning",
    "ratna-day",
    "ratna-night",
    "ratan-khatri",
    "main-mumbai-rk",
    "main-mumbai-night",
    "kalyan-sridevi",
    "kalyan-sridevi-night",
    "kalyan-day",
    "kalyan-night",
    "kalyan-express",
    "shri-day",
    "shri-night",
    "sunday-bazar",
    "delhi-bazar",
    "puna-bazar",
    "puna-night-main",
    "sita-morning",
    "sita-day",
    "sita-night",
    "central-mumbai",
    "central-bombay",
    "meena-morning",
    "meena-bazar-day",
    "meena-bazar-night",
    "meena-bazar",
    "milan-bazar-morning",
    "milan-bazar-day",
    "milan-bazar-night",
    "lokseva-day",
    "mohini",
    "parel-day",
    "sahara",
    "country-bazar",
    "samrat-bazar",
    "rose-bazar-day",
    "rose-bazar-night",
    "janta-morning",
    "janta-day",
    "teen-patti",
    "durga-night",
    "parvati",
    "super-time",
    "super-goa-day",
    "kaali",
    "cb",
    "chandni-morning",
    "gowa",
    "rakhi-morning",
    "geeta-morning",
    "tulsi-morning",
    "srilakshmi",
    "srilaxmi-day",
    "sri-dhanalaxmi",
    "ntr-morning",
    "ntr-day",
    "ntr-night",
    "khatri-morning",
    "maya-bazar",
    "day-bombay",
    "night-bombay",
    "sitara-bazar",
    "apla-bazar-day",
    "apla-bazar-night",
    "asha-bazar",
    "kalyan-sai-day",
    "jay-shree-day",
    "padmavathi-night",
    "worli-mumbai",
    "bombay-rajshree-day",
    "bombay-rajshree-night",
    "time-night",
]


def slug_to_name(slug):
    return slug.replace("-", "_").strip("_").lower()


def fetch(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        r.raise_for_status()
        return r.text
    except Exception as e:
        print(f"  Fetch failed: {e}")
        return None


def verify_url(url):
    """Check if a panel chart URL actually returns real content (not 404)."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        # Valid if 200 and has 'panel' content
        return r.status_code == 200 and "panel" in r.text.lower()
    except Exception:
        return False


def extract_all_panel_links(html):
    """Extract every /panel-chart-record/*.php link from the page HTML."""
    soup = BeautifulSoup(html, "html.parser")
    seen = {}

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        m = re.search(r'/panel-chart-record/([^/?#\s]+)\.php', href)
        if not m:
            continue
        slug = m.group(1)
        if slug in seen:
            continue
        full_url = href if href.startswith("http") else BASE_URL + href
        seen[slug] = full_url

    return seen  # {slug: url}


def main():
    print("=" * 60)
    print("  dpboss.boston — Panel Chart URL Extractor")
    print("=" * 60)

    # Step 1: Scrape homepage — gets all [Panel] links from market blocks
    print(f"\n Fetching homepage: {BASE_URL}")
    html = fetch(BASE_URL)
    if not html:
        print("ERROR: Could not fetch homepage.")
        return

    found = extract_all_panel_links(html)
    print(f"  Found {len(found)} links on homepage.")

    # Step 2: Add known extra slugs (from our curated list)
    print(f"\n Adding {len(EXTRA_SLUGS)} known extra slugs...")
    added = 0
    for slug in EXTRA_SLUGS:
        if slug not in found:
            found[slug] = f"{BASE_URL}/panel-chart-record/{slug}.php"
            added += 1
    print(f"  Added {added} new slugs. Total so far: {len(found)}")

    # Step 3: Verify each URL actually exists (optional but recommended first run)
    # Comment this block out after first run to save time
    print(f"\n Verifying all {len(found)} URLs (this may take a minute)...")
    valid = {}
    for i, (slug, url) in enumerate(found.items(), 1):
        ok = verify_url(url)
        status = "OK" if ok else "SKIP"
        print(f"  [{i:>3}/{len(found)}] {status}  {slug}")
        if ok:
            valid[slug] = url
        time.sleep(0.3)  # polite delay

    print(f"\n  Valid URLs: {len(valid)} / {len(found)}")

    # Step 4: Build final list and save
    markets = []
    for slug, url in sorted(valid.items()):
        markets.append({
            "name": slug_to_name(slug),
            "slug": slug,
            "url":  url
        })

    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(markets, f, indent=2, ensure_ascii=False)

    print(f"\n Saved {len(markets)} markets to '{OUT_FILE}'")
    print("\nMarkets found:")
    for i, m in enumerate(markets, 1):
        print(f"  {i:>3}. {m['name']:<40} -> {m['url']}")

    print(f"\n{'='*60}")
    print(f"  Total: {len(markets)} markets")
    print(f"  Next:  python multi_market_scraperrr.py")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
