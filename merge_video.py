import os
import subprocess

# ===== PATHS =====
BASE_VIDEO_DIR = r"C:\Users\VCOM\Desktop\Kalyan_Penal_Scraper\video_output"
OUTPUT_DIR = r"C:\Users\VCOM\Desktop\Kalyan_Penal_Scraper\merged_videos"
OUTPUT_VIDEO = os.path.join(OUTPUT_DIR, "final_merged.mp4")

os.makedirs(OUTPUT_DIR, exist_ok=True)

# 1️⃣ Find latest date folder
date_folders = [
    d for d in os.listdir(BASE_VIDEO_DIR)
    if os.path.isdir(os.path.join(BASE_VIDEO_DIR, d))
]

if not date_folders:
    raise RuntimeError("❌ No date folders found")

latest_folder = sorted(date_folders)[-1]
LATEST_PATH = os.path.join(BASE_VIDEO_DIR, latest_folder)

print(f"📁 Using latest folder: {LATEST_PATH}")

# 2️⃣ Collect videos from latest folder only
videos = sorted([
    f for f in os.listdir(LATEST_PATH)
    if f.lower().endswith((".mp4", ".mov", ".mkv"))
])

if not videos:
    raise RuntimeError("❌ No videos found in latest folder")

# 3️⃣ Create concat list
list_file = os.path.join(LATEST_PATH, "files.txt")
with open(list_file, "w", encoding="utf-8") as f:
    for v in videos:
        f.write(f"file '{os.path.join(LATEST_PATH, v)}'\n")

# 4️⃣ Merge videos (fast, no re-encode)
cmd = [
    "ffmpeg", "-y",
    "-f", "concat",
    "-safe", "0",
    "-i", list_file,
    "-c", "copy",
    OUTPUT_VIDEO
]

subprocess.run(cmd, check=True)

print("✅ MERGED VIDEO CREATED:")
print(OUTPUT_VIDEO)
