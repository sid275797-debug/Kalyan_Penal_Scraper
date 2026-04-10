import os

# ================== CONFIG ==================

ROOT_FOLDER = r"C:\Users\VCOM\Desktop\Kalyan_Penal_Scraper\video_output"

VIDEO_EXTENSIONS = (".mp4", ".mov", ".mkv", ".avi")

# Premium market aliases (case-insensitive)
PREMIUM_ALIASES = [
    # KALYAN
    "kalyan",
    "kalyan_main",
    "kalyan_day",
    "kalyan_night",
    "kalyanmatka",

    # RAJDHANI
    "rajdhani",
    "rajdhani_day",
    "rajdhani_night",
    "rajdhanimatka",

    # MILAN
    "milan",
    "milan_day",
    "milan_night",
    "milanmatka",

    # TIME BAZAR
    "timebazar",
    "time_bazar",
    "time-bazar",
    "timebazar_main",
]

DRY_RUN = False  # Set True first if you want preview only

# ============================================


def is_premium_video(filename: str) -> bool:
    name = filename.lower()
    return any(alias in name for alias in PREMIUM_ALIASES)


def clean_premium_videos():
    deleted = 0
    scanned = 0

    for root, _, files in os.walk(ROOT_FOLDER):
        for file in files:
            if not file.lower().endswith(VIDEO_EXTENSIONS):
                continue

            scanned += 1
            full_path = os.path.join(root, file)

            if is_premium_video(file):
                if DRY_RUN:
                    print(f"[DRY-RUN] WOULD DELETE: {full_path}")
                else:
                    try:
                        os.remove(full_path)
                        print(f"DELETED: {full_path}")
                        deleted += 1
                    except Exception as e:
                        print(f"ERROR deleting {full_path}: {e}")

    print("\n======== SUMMARY ========")
    print(f"Scanned videos : {scanned}")
    print(f"Deleted videos : {deleted}")
    print("Dry run mode   :", DRY_RUN)
    print("=========================\n")


if __name__ == "__main__":
    clean_premium_videos()
