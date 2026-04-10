#!/usr/bin/env python3
# caption_generator.py
"""
Generates market-wise titles + unified description, hashtags, CTA, and compact disclaimer
for daily Satta Matka video publishing (YouTube + Instagram unified description).
Output: video_metadata.json
"""

import json
from datetime import datetime
from pathlib import Path
from typing import List

# --------- CONFIG ----------
APP_NAME = "SattaMatkaAI"
APP_LINK = "https://sattamatkaai.app"  # Replace with your real link
PREDICTIONS_FILE = "todays_predictions.json"
OUTPUT_FILE = "video_metadata.json"

# Max hashtags to include
MAX_HASHTAGS = 15

# Hashtags focused on Satta Matka (no AI)
DEFAULT_HASHTAGS = [
    "SattaMatka", "Matka", "Satta", "KalyanMatka", "Rajdhani", "MilanDay",
    "MatkaPrediction", "SattaResults", "DailyMatka", "MatkaCharts",
    "SattaKing", "MatkaToday", "SattaGame", "MatkaWinning", "MatkaCommunity",
]

# ✅ Compact professional disclaimer
DISCLAIMER = (
    "⚠️ Disclaimer: Predictions are for entertainment and informational purposes only. "
    "We do not promote or encourage gambling. Play responsibly and at your own risk."
)

# ---------- Helpers ----------
def load_predictions(path: str) -> dict:
    p = Path(path)
    if not p.exists():
        print(f"⚠️ Predictions file not found: {path}")
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"⚠️ Error reading {path}: {e}")
        return {}

def extract_markets(obj: dict) -> List[str]:
    markets = []
    if not obj:
        return markets

    if isinstance(obj.get("markets"), list):
        for m in obj["markets"]:
            if isinstance(m, dict):
                name = m.get("market") or m.get("name") or m.get("market_name")
                if name:
                    markets.append(str(name).strip())
    elif isinstance(obj.get("markets"), dict):
        markets = list(obj["markets"].keys())

    if not markets:
        ignore = {"date", "generated_at", "meta", "version"}
        for k in obj.keys():
            if k not in ignore and isinstance(k, str):
                markets.append(k.strip())

    seen = set()
    unique_markets = []
    for m in markets:
        if m and m.lower() not in seen:
            seen.add(m.lower())
            unique_markets.append(m)
    return unique_markets

def build_title(market_name: str, dt: datetime) -> str:
    date_str = dt.strftime("%d %b %Y")
    return f"{market_name} Predictions — {date_str} | SattaMatka Results"

def build_unified_description(markets_preview: List[str], dt: datetime, app_link: str,
                              hashtags: List[str], disclaimer: str) -> str:
    date_str_long = dt.strftime("%d %B %Y")
    markets_line = " • ".join(markets_preview) if markets_preview else "All markets"
    desc = [
        f"🔥 Daily Satta Matka Predictions • {date_str_long}",
        "",
        "📌 Markets (highlights):",
        markets_line,
        "",
        "👇 What you get in this video:",
        "• Today's predicted open/close digits, pannas & jodis for each market.",
        "• Focused coverage for Kalyan, Rajdhani, Milan & other major markets.",
        "",
        "📱 Download the official app for full predictions, history & premium picks:",
        app_link,
        "",
        disclaimer,
        "",
        "🔔 Follow us for daily predictions & live market results.",
        ""
    ]
    base = "\n".join(desc).strip()
    hashtag_block = " ".join(f"#{h}" for h in hashtags[:MAX_HASHTAGS])
    unified = f"{base}\n\n{hashtag_block}"

    if len(unified) > 4000:
        trimmed = " • ".join(markets_preview[:8]) + (" • And more..." if len(markets_preview) > 8 else "")
        unified = unified.replace(markets_line, trimmed)
    return unified

# ---------- Main ----------
def main():
    dt = datetime.now()
    raw = load_predictions(PREDICTIONS_FILE)
    markets = extract_markets(raw)

    if not markets:
        print("⚠️ No markets extracted from predictions. Creating a general title.")
        markets = ["All Markets"]

    titles = {m: build_title(m, dt) for m in markets}
    markets_preview = markets[:20]

    hashtags = [h for h in DEFAULT_HASHTAGS if "ai" not in h.lower()]
    hashtags = list(dict.fromkeys(hashtags))[:MAX_HASHTAGS]

    unified_description = build_unified_description(markets_preview, dt, APP_LINK, hashtags, DISCLAIMER)

    output = {
        "generated_at": dt.isoformat(),
        "date": dt.strftime("%Y-%m-%d"),
        "app_name": APP_NAME,
        "app_link": APP_LINK,
        "disclaimer": DISCLAIMER,
        "hashtags": hashtags,
        "unified_description": unified_description,
        "titles": titles
    }

    Path(OUTPUT_FILE).write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"✅ Generated metadata saved to {OUTPUT_FILE}")

    # 🟢 Pretty Preview (shows real line breaks)
    example_market = list(titles.keys())[0]
    print("\n──────────────────────────────")
    print(f"🎯 Example Market: {example_market}")
    print("──────────────────────────────")
    print(f"📺 Title:\n{titles[example_market]}")
    print("\n📝 Unified Description Preview:\n")
    print(unified_description)
    print("\n──────────────────────────────")
    print(f"✅ Total Markets Processed: {len(markets)}")

if __name__ == "__main__":
    main()