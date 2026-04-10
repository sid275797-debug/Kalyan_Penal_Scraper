#!/usr/bin/env python3
"""
import_groups.py
================
Reads group_ids.json (downloaded from browser console)
and auto-updates GROUP_IDS in fb_reels_poster.py

USAGE:
    python import_groups.py
"""

import json
import re
from pathlib import Path

GROUP_IDS_FILE = "group_ids.json"
POSTER_SCRIPT  = "fb_reels_poster.py"

# Also checks Downloads folder automatically
DOWNLOADS = Path.home() / "Downloads" / "group_ids.json"


def main():
    # Find the file
    src = Path(GROUP_IDS_FILE)
    if not src.exists() and DOWNLOADS.exists():
        src = DOWNLOADS
        print(f"📁 Found group_ids.json in Downloads folder")

    if not src.exists():
        print(f"❌ group_ids.json not found!")
        print(f"   Run the browser console script first, then try again.")
        return

    # Load IDs
    data = json.loads(src.read_text())

    # Handle both formats: ["id1","id2"] or [{"id":"...","name":"..."}]
    if data and isinstance(data[0], dict):
        ids = [str(d["id"]) for d in data]
    else:
        ids = [str(d) for d in data]

    print(f"✅ Loaded {len(ids)} group IDs from {src}")

    # Update fb_reels_poster.py
    poster = Path(POSTER_SCRIPT)
    if not poster.exists():
        print(f"❌ {POSTER_SCRIPT} not found in current folder.")
        return

    content   = poster.read_text(encoding="utf-8")
    id_lines  = "\n".join(f'    "{gid}",' for gid in ids)
    new_block = f"GROUP_IDS = [\n{id_lines}\n]"
    updated   = re.sub(r'GROUP_IDS\s*=\s*\[.*?\]', new_block, content, flags=re.DOTALL)

    if updated != content:
        poster.write_text(updated, encoding="utf-8")
        print(f"✅ Updated GROUP_IDS in {POSTER_SCRIPT} with {len(ids)} groups!")
        print(f"\nYou can now run:")
        print(f"   python fb_reels_poster.py")
    else:
        print(f"⚠️  Could not find GROUP_IDS block in {POSTER_SCRIPT}")


if __name__ == "__main__":
    main()
