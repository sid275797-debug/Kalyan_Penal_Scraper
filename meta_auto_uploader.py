#!/usr/bin/env python3
"""
meta_auto_uploader_v2.py — Direct Upload Mode for Scheduled Pipeline
=====================================================================
CHANGES FROM v1:
  ✅ DEFAULT MODE: Scans today's video folder, uploads all new videos, exits
     (No more watchdog watcher sitting in RAM forever)
  ✅ Designed for BAT file scheduling — run once, upload, done
  ✅ --watch mode still available if you want the old behavior
  ✅ --date flag to upload a specific date's videos
  ✅ Cleaner logging with summary at end

TOKEN SETUP (one time only):
    python meta_auto_uploader_v2.py --set-token

DAILY USE (scheduled via BAT file):
    python meta_auto_uploader_v2.py              # upload today's videos and exit
    python meta_auto_uploader_v2.py --date 2026-04-09
    python meta_auto_uploader_v2.py --watch      # old watchdog mode (runs forever)

REQUIREMENTS:
    pip install requests watchdog
"""

import os
import sys
import time
import json
import argparse
import requests
import threading
from pathlib import Path
from datetime import datetime

# ══════════════════════════════════════════════
#  ▶▶  EDIT THESE VALUES  ◀◀
# ══════════════════════════════════════════════
APP_ID     = "799756459263010"
APP_SECRET = "ddd7e3e918c1f42a2c2f3e9e9834748b"
PAGE_ID    = "836377599555364"
PAGE_NAME  = "Sattamatkaai"

# Folder where your reels_builder saves videos
WATCH_ROOT = r"C:\Users\VCOM\Desktop\Kalyan_Penal_Scraper\video_output"

# Caption template — {market} and {date} will be filled automatically
CAPTION_TEMPLATE = "\U0001f3af {market} Prediction | {date}\n\n\u2705 Follow @sattamatkaai for daily updates!\n#sattamatka #kalyan #matka #prediction"

# Instagram Business account enabled
ENABLE_INSTAGRAM     = True
INSTAGRAM_ACCOUNT_ID = "17841476770906932"  # @sattamatkaai

# Delay between uploads (seconds) — prevents API rate limiting
DELAY_BETWEEN_UPLOADS = 30

# ══════════════════════════════════════════════

SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
TOKEN_FILE   = os.path.join(SCRIPT_DIR, "token.json")
UPLOADED_LOG = os.path.join(SCRIPT_DIR, "uploaded_videos.json")
VIDEO_EXTS   = {".mp4", ".mov"}

PAGE_ACCESS_TOKEN = ""  # loaded at runtime from token.json


# ── Logging ──────────────────────────────────
def log(msg: str, level="INFO"):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    prefix = {"INFO": "i ", "OK": "OK", "WARN": "!!", "ERR": "XX", "SKIP": ">>"}.get(level, "")
    print(f"[{ts}] {prefix} {msg}", flush=True)


# ══════════════════════════════════════════════
#  TOKEN MANAGEMENT (unchanged)
# ══════════════════════════════════════════════

def _exchange_long_lived(short_token: str) -> str:
    r = requests.get(
        "https://graph.facebook.com/oauth/access_token",
        params={
            "grant_type":        "fb_exchange_token",
            "client_id":         APP_ID,
            "client_secret":     APP_SECRET,
            "fb_exchange_token": short_token,
        },
        timeout=15,
    ).json()
    if "access_token" not in r:
        raise RuntimeError(f"Long-lived exchange failed: {r}")
    log("Short-lived -> long-lived user token exchange successful", "OK")
    return r["access_token"]


def _get_page_token(long_lived_user_token: str) -> str:
    r = requests.get(
        "https://graph.facebook.com/v25.0/me/accounts",
        params={"fields": "id,name,access_token", "access_token": long_lived_user_token},
        timeout=15,
    ).json()
    for page in r.get("data", []):
        if page.get("id") == PAGE_ID:
            log(f"Permanent Page Token obtained for: {page.get('name')}", "OK")
            return page["access_token"]
    raise RuntimeError(
        f"Page {PAGE_ID} ({PAGE_NAME}) not found under this user's accounts. "
        "Make sure the token owner is an Admin of the page."
    )


def _is_token_alive(token: str) -> bool:
    try:
        r = requests.get(
            "https://graph.facebook.com/v25.0/me",
            params={"fields": "id", "access_token": token},
            timeout=10,
        ).json()
        return "id" in r and "error" not in r
    except Exception:
        return False


def _save_token(page_token: str):
    with open(TOKEN_FILE, "w") as f:
        json.dump({"page_token": page_token}, f, indent=2)
    log(f"Token saved to token.json", "OK")


def _load_token() -> str:
    if os.path.exists(TOKEN_FILE):
        try:
            with open(TOKEN_FILE) as f:
                return json.load(f).get("page_token", "")
        except Exception:
            pass
    return ""


def setup_token_interactive():
    print("\n" + "=" * 60)
    print("  META TOKEN SETUP")
    print("=" * 60)
    print("  1. Go to: https://developers.facebook.com/tools/explorer/")
    print("  2. Select your App -> click 'Generate User Token'")
    print("  3. Add these permissions:")
    print("       pages_manage_posts")
    print("       pages_read_engagement")
    print("       instagram_basic")
    print("       instagram_content_publish")
    print("  4. Copy the token shown and paste it below.")
    print("=" * 60)
    raw = input("\nPaste token here: ").strip()
    if not raw:
        print("No token entered. Aborting.")
        sys.exit(1)

    print()
    log("Step 1/2 — Exchanging for long-lived user token...")
    try:
        ll_token = _exchange_long_lived(raw)
    except RuntimeError as e:
        log(f"{e}", "WARN")
        log("Trying token directly (may already be long-lived)...", "WARN")
        ll_token = raw

    log("Step 2/2 — Deriving permanent Page Token...")
    try:
        page_token = _get_page_token(ll_token)
    except RuntimeError as e:
        log(str(e), "ERR")
        sys.exit(1)

    _save_token(page_token)
    print()
    print("=" * 60)
    print("  Done! Token setup complete.")
    print()
    print("  This token NEVER expires. You only need to redo this if:")
    print("    - You change your Facebook password")
    print("    - You revoke the app in Facebook Settings -> Security")
    print("=" * 60)


def get_valid_page_token() -> str:
    token = _load_token()

    if not token:
        log("No token.json found.", "ERR")
        log("Run this once to set up:  python meta_auto_uploader_v2.py --set-token", "ERR")
        sys.exit(1)

    if _is_token_alive(token):
        log("Page token loaded and valid", "OK")
        return token

    log("=" * 60, "ERR")
    log("Saved token is no longer valid.", "ERR")
    log("Most likely cause: you changed your Facebook password", "ERR")
    log("or revoked the app in Facebook Settings.", "ERR")
    log("Fix:  python meta_auto_uploader_v2.py --set-token", "ERR")
    log("=" * 60, "ERR")
    sys.exit(1)


# ══════════════════════════════════════════════
#  VIDEO HELPERS
# ══════════════════════════════════════════════

def reencode_for_instagram(input_path: str) -> str:
    import subprocess
    out_path = input_path.replace(".mp4", "_ig.mp4")
    if os.path.exists(out_path):
        return out_path
    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,setsar=1",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        "-movflags", "+faststart",
        "-pix_fmt", "yuv420p",
        "-r", "30",
        out_path
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=300)
        if result.returncode == 0 and os.path.exists(out_path):
            log(f"  Re-encoded for Instagram: {os.path.basename(out_path)}", "OK")
            return out_path
        else:
            log(f"  ffmpeg re-encode failed: {result.stderr.decode()[:200]}", "WARN")
            return input_path
    except FileNotFoundError:
        log("  ffmpeg not found — using original video (may fail)", "WARN")
        return input_path
    except Exception as e:
        log(f"  Re-encode error: {e}", "WARN")
        return input_path


def load_uploaded() -> set:
    if os.path.exists(UPLOADED_LOG):
        try:
            with open(UPLOADED_LOG) as f:
                return set(json.load(f))
        except Exception:
            pass
    return set()

def mark_uploaded(path: str):
    uploaded = load_uploaded()
    uploaded.add(path)
    with open(UPLOADED_LOG, "w") as f:
        json.dump(list(uploaded), f, indent=2)


def extract_market_name(filepath: str) -> str:
    import re
    stem = Path(filepath).stem
    # Remove trailing date-time stamp: _YYYYMMDD_HHMMSS
    stem = re.sub(r"_\d{8}_\d{6}$", "", stem)
    # Remove trailing _YYYYMMDD if no time part
    stem = re.sub(r"_\d{8}$", "", stem)
    return stem.replace("_", " ").title()


# ══════════════════════════════════════════════
#  UPLOAD FUNCTIONS
# ══════════════════════════════════════════════

def upload_to_facebook(video_path: str, caption: str) -> bool:
    log(f"Facebook upload: {os.path.basename(video_path)}")
    file_size = os.path.getsize(video_path)
    log(f"  File size: {file_size/1024/1024:.1f} MB")
    try:
        with open(video_path, "rb") as f:
            resp = requests.post(
                f"https://graph.facebook.com/v25.0/{PAGE_ID}/videos",
                data={
                    "description":  caption,
                    "access_token": PAGE_ACCESS_TOKEN,
                },
                files={
                    "source": (os.path.basename(video_path), f, "video/mp4"),
                },
                timeout=600
            ).json()
    except Exception as e:
        log(f"Facebook upload exception: {e}", "ERR")
        return False

    if "id" in resp:
        log(f"Facebook video published! ID: {resp['id']}", "OK")
        return True
    else:
        log(f"Facebook upload error: {resp}", "ERR")
        return False


def upload_to_instagram(video_path: str, caption: str) -> bool:
    if not ENABLE_INSTAGRAM or not INSTAGRAM_ACCOUNT_ID:
        log("Instagram upload skipped (disabled or no account ID)", "SKIP")
        return False

    log(f"Instagram upload: {os.path.basename(video_path)}")
    ig_video_path = reencode_for_instagram(video_path)

    import subprocess, http.server, socketserver, re, random
    port = random.randint(19000, 29000)
    video_dir  = os.path.dirname(ig_video_path)
    video_file = os.path.basename(ig_video_path)

    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=video_dir, **kwargs)
        def log_message(self, fmt, *args): pass

    socketserver.TCPServer.allow_reuse_address = True
    httpd = socketserver.TCPServer(("", port), Handler)
    server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    server_thread.start()
    log(f"  Local HTTP server on port {port}")

    tunnel_proc = None
    video_url = ""
    try:
        tunnel_proc = subprocess.Popen(
            ["cloudflared", "tunnel", "--url", f"http://localhost:{port}"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        )
        public_url = ""
        for _ in range(30):
            line = tunnel_proc.stdout.readline().decode("utf-8", errors="ignore")
            if "trycloudflare.com" in line or "cloudflare.com" in line:
                match = re.search(r"https://[\w\-]+\.trycloudflare\.com", line)
                if match:
                    public_url = match.group(0)
                    break
            time.sleep(0.5)

        if public_url:
            video_url = f"{public_url}/{video_file}"
            log(f"  Cloudflare tunnel: {video_url}", "OK")
        else:
            log("  Could not get cloudflared URL", "ERR")
            httpd.shutdown()
            if tunnel_proc: tunnel_proc.terminate()
            return False
    except FileNotFoundError:
        log("  cloudflared not found. Install: winget install Cloudflare.cloudflared", "ERR")
        httpd.shutdown()
        return False
    except Exception as e:
        log(f"  cloudflared error: {e}", "ERR")
        httpd.shutdown()
        if tunnel_proc: tunnel_proc.terminate()
        return False

    try:
        container = requests.post(
            f"https://graph.facebook.com/v25.0/{INSTAGRAM_ACCOUNT_ID}/media",
            data={
                "media_type":   "REELS",
                "video_url":    video_url,
                "caption":      caption,
                "access_token": PAGE_ACCESS_TOKEN,
            },
            timeout=60
        ).json()
    except Exception as e:
        log(f"  IG container request failed: {e}", "ERR")
        return False

    if "id" not in container:
        log(f"  IG container error: {container}", "ERR")
        return False

    container_id = container["id"]
    log(f"  Container created: {container_id}, waiting...")

    for i in range(12):
        time.sleep(10)
        try:
            status = requests.get(
                f"https://graph.facebook.com/v25.0/{container_id}",
                params={"fields": "status_code,status", "access_token": PAGE_ACCESS_TOKEN},
                timeout=15
            ).json()
            code = status.get("status_code", "")
            log(f"  IG processing: {code}")
            if code == "FINISHED":
                break
            elif code == "ERROR":
                err_detail = requests.get(
                    f"https://graph.facebook.com/v25.0/{container_id}",
                    params={
                        "fields": "status_code,status,error_type,error_message",
                        "access_token": PAGE_ACCESS_TOKEN,
                    },
                    timeout=15
                ).json()
                log(f"  IG error details: {err_detail}", "ERR")
                return False
        except Exception:
            pass

    try:
        pub = requests.post(
            f"https://graph.facebook.com/v25.0/{INSTAGRAM_ACCOUNT_ID}/media_publish",
            data={"creation_id": container_id, "access_token": PAGE_ACCESS_TOKEN},
            timeout=60
        ).json()
    except Exception as e:
        log(f"  IG publish request failed: {e}", "ERR")
        return False

    httpd.shutdown()
    if tunnel_proc: tunnel_proc.terminate()
    try:
        if ig_video_path != video_path and os.path.exists(ig_video_path):
            os.remove(ig_video_path)
    except: pass

    if "id" in pub:
        log(f"Instagram Reel published! @sattamatkaai", "OK")
        return True
    else:
        log(f"  IG publish error: {pub}", "ERR")
        return False


def handle_video(video_path: str) -> dict:
    """
    Upload a single video. Returns result dict for summary.
    """
    uploaded = load_uploaded()
    basename = os.path.basename(video_path)

    if video_path in uploaded:
        log(f"Already uploaded, skipping: {basename}", "SKIP")
        return {"file": basename, "status": "skipped"}

    if not os.path.exists(video_path):
        log(f"File disappeared: {video_path}", "WARN")
        return {"file": basename, "status": "missing"}

    file_size_mb = os.path.getsize(video_path) / 1024 / 1024
    log(f"Processing: {basename} ({file_size_mb:.1f} MB)")

    market  = extract_market_name(video_path)
    date    = datetime.now().strftime("%d %b %Y")
    caption = CAPTION_TEMPLATE.format(market=market, date=date)

    fb_ok = upload_to_facebook(video_path, caption)
    ig_ok = upload_to_instagram(video_path, caption) if ENABLE_INSTAGRAM else False

    if fb_ok or ig_ok:
        mark_uploaded(video_path)
        log(f"Done: {basename} -> FB:{'OK' if fb_ok else 'FAIL'} IG:{'OK' if ig_ok else 'SKIP'}", "OK")
        return {"file": basename, "status": "uploaded", "fb": fb_ok, "ig": ig_ok}
    else:
        log(f"Upload failed for: {basename}", "ERR")
        return {"file": basename, "status": "failed", "fb": False, "ig": False}


# ══════════════════════════════════════════════
#  v2: DIRECT UPLOAD MODE (default — upload today's folder and exit)
# ══════════════════════════════════════════════

# Premium markets — uploaded FIRST for maximum reach
PREMIUM_KEYWORDS = [
    "kalyan", "rajdhani", "milan", "time_bazar", "time bazar",
    "sridevi", "main_bazar", "main bazar", "main_mumbai", "main mumbai",
]

def _is_premium_video(filepath):
    """Check if video filename contains any premium market keyword."""
    name_lower = Path(filepath).stem.lower()
    return any(kw in name_lower for kw in PREMIUM_KEYWORDS)


def get_video_folder(date_str=None):
    """Same logic as fb_group_poster — find today's or most recent folder."""
    root = Path(WATCH_ROOT)
    if date_str:
        return root / date_str
    today        = datetime.now().strftime("%Y-%m-%d")
    today_folder = root / today
    if today_folder.exists():
        return today_folder
    folders = sorted(
        [d for d in root.iterdir()
         if d.is_dir() and len(d.name) == 10 and d.name[4] == "-"],
        reverse=True
    )
    if folders:
        log(f"Today's folder not found -- using most recent: {folders[0].name}", "WARN")
        return folders[0]
    return today_folder


def upload_todays_videos(date_str=None):
    """
    v2 DEFAULT MODE: Find today's video folder, upload all new videos,
    print summary, exit. Premium videos (Kalyan, Rajdhani, Milan, etc.) go FIRST.
    """
    folder = get_video_folder(date_str)

    if not folder.exists():
        log(f"Video folder not found: {folder}", "ERR")
        return

    # Find all uploadable videos
    all_videos = [
        v for v in folder.glob("*.mp4")
        if not v.name.endswith("_ig.mp4")
        and not v.name.endswith("_ig_ig.mp4")
    ]

    # Sort: premium videos first, then alphabetical within each group
    premium = sorted(v for v in all_videos if _is_premium_video(v))
    regular = sorted(v for v in all_videos if not _is_premium_video(v))
    videos  = premium + regular

    if not videos:
        log(f"No videos found in: {folder}", "WARN")
        return

    uploaded = load_uploaded()
    new_videos = [v for v in videos if str(v) not in uploaded]

    log("=" * 55)
    log(f"  Sattamatkaai Meta Auto Uploader v2")
    log(f"  Page     : {PAGE_NAME} ({PAGE_ID})")
    log(f"  Facebook : Enabled")
    log(f"  Instagram: {'Enabled' if ENABLE_INSTAGRAM else 'Disabled'}")
    log(f"  Folder   : {folder}")
    log(f"  Videos   : {len(videos)} total ({len(premium)} premium FIRST, {len(regular)} regular)")
    log(f"  New      : {len(new_videos)} to upload")
    log("=" * 55)

    if not new_videos:
        log("All videos already uploaded. Nothing to do.", "OK")
        return

    results = []
    for idx, vp in enumerate(new_videos, 1):
        log(f"\n[{idx}/{len(new_videos)}] {vp.name}")
        result = handle_video(str(vp))
        results.append(result)

        if idx < len(new_videos):
            log(f"  Waiting {DELAY_BETWEEN_UPLOADS}s before next upload...", "INFO")
            time.sleep(DELAY_BETWEEN_UPLOADS)

    # Print summary
    uploaded_count = sum(1 for r in results if r["status"] == "uploaded")
    skipped_count  = sum(1 for r in results if r["status"] == "skipped")
    failed_count   = sum(1 for r in results if r["status"] == "failed")

    log("\n" + "=" * 55)
    log(f"  UPLOAD COMPLETE")
    log(f"  Uploaded : {uploaded_count}")
    log(f"  Skipped  : {skipped_count}")
    log(f"  Failed   : {failed_count}")
    log("=" * 55)


# ══════════════════════════════════════════════
#  WATCHDOG MODE (old behavior — --watch flag)
# ══════════════════════════════════════════════

def run_watch_mode():
    """Original watchdog watcher — runs forever watching for new files."""
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler

    class VideoHandler(FileSystemEventHandler):
        def on_created(self, event):
            if not event.is_directory:
                ext   = Path(event.src_path).suffix.lower()
                fname = os.path.basename(event.src_path)
                if ext in VIDEO_EXTS and not fname.endswith("_ig.mp4"):
                    t = threading.Thread(target=handle_video, args=(event.src_path,), daemon=True)
                    t.start()

        def on_moved(self, event):
            if not event.is_directory:
                ext = Path(event.dest_path).suffix.lower()
                if ext in VIDEO_EXTS:
                    t = threading.Thread(target=handle_video, args=(event.dest_path,), daemon=True)
                    t.start()

    os.makedirs(WATCH_ROOT, exist_ok=True)
    observer = Observer()
    observer.schedule(VideoHandler(), WATCH_ROOT, recursive=True)
    observer.start()
    log(f"Watching for new videos in: {WATCH_ROOT}", "OK")
    log("Press Ctrl+C to stop.\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log("Stopping watcher...")
        observer.stop()
    observer.join()
    log("Stopped.", "OK")


# ══════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Meta Auto Uploader v2 — Scheduled Pipeline Mode")
    parser.add_argument("--set-token", action="store_true", help="One-time token setup")
    parser.add_argument("--date",      default=None,        help="Upload videos from specific date folder (e.g. 2026-04-09)")
    parser.add_argument("--watch",     action="store_true", help="Old watchdog mode (runs forever)")
    args = parser.parse_args()

    # Token setup mode
    if args.set_token:
        setup_token_interactive()
        return

    # Load and validate token
    global PAGE_ACCESS_TOKEN
    PAGE_ACCESS_TOKEN = get_valid_page_token()

    if args.watch:
        # Old watchdog mode
        log("=" * 55)
        log(f"  Watch Mode (runs forever)")
        log(f"  Page    : {PAGE_NAME} ({PAGE_ID})")
        log(f"  Facebook: Enabled")
        log(f"  Instagram: {'Enabled' if ENABLE_INSTAGRAM else 'Disabled'}")
        log(f"  Folder  : {WATCH_ROOT}")
        log("=" * 55)
        run_watch_mode()
    else:
        # v2 DEFAULT: upload today's folder and exit
        upload_todays_videos(date_str=args.date)


if __name__ == "__main__":
    main()