import os
import json
import time
import logging
import requests
from datetime import datetime
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials
from googleapiclient.errors import HttpError


# ================= CONFIG =================

PROJECTS_DIR = "projects"

VIDEO_FOLDER = r"C:\Users\VCOM\Desktop\Kalyan_Penal_Scraper\ReelsOutput"

CATEGORY_ID = "22"

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

LOG_DIR = "logs"
HISTORY_FILE = os.path.join(LOG_DIR, "upload_history.json")


# 🔥 FIXED VIRAL TITLE
FIXED_TITLE = "₹500 se ₹1 Crore? India ka Oldest Lottery Satta Matka History EXPOSED"


MASTER_DESCRIPTION = """#Shorts

Aaj ka Satta Matka AI Prediction Video
Is video me aapko milta hai:
• Aaj ka Open Digit
• Close Digit
• Jodi
• Open Panna
• Close Panna
• Market wise full AI report

📲 App Download Kare:
https://tinyurl.com/sattamatkaAi-2

⚠️ DISCLAIMER:
Entertainment purpose only.

#SattaMatka #Matka #Satta #Shorts
"""


# ================= LOG =================

os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    filename=os.path.join(LOG_DIR, "upload.log"),
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# ================= HELPERS =================


def load_projects():
    projects = []
    for f in sorted(os.listdir(PROJECTS_DIR)):
        if f.endswith(".json"):
            with open(os.path.join(PROJECTS_DIR, f)) as fp:
                projects.append(json.load(fp))
    return projects


def get_access_token(project):
    r = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": project["client_id"],
            "client_secret": project["client_secret"],
            "refresh_token": project["refresh_token"],
            "grant_type": "refresh_token"
        }
    )
    r.raise_for_status()
    return r.json()["access_token"]


def build_youtube(project):

    token = get_access_token(project)

    creds = Credentials(
        token=token,
        refresh_token=project["refresh_token"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=project["client_id"],
        client_secret=project["client_secret"],
        scopes=SCOPES
    )

    return build("youtube", "v3", credentials=creds)


# 🔥 READ ALL VIDEOS FROM ALL SUBFOLDERS
def get_videos():

    videos = []

    for root, dirs, files in os.walk(VIDEO_FOLDER):
        for f in files:
            if f.lower().endswith(".mp4"):
                videos.append(os.path.join(root, f))

    return sorted(videos)


def load_history():
    if not os.path.exists(HISTORY_FILE):
        return {}
    return json.load(open(HISTORY_FILE))


def save_history(h):
    json.dump(h, open(HISTORY_FILE, "w"), indent=2)


def is_quota_error(e):
    return isinstance(e, HttpError) and (
        "quotaExceeded" in str(e) or
        "dailyLimitExceeded" in str(e)
    )


# ================= MAIN =================

def main():

    if not os.path.exists(VIDEO_FOLDER):
        raise RuntimeError("❌ Reels folder not found")

    projects = load_projects()
    videos = get_videos()
    history = load_history()

    exhausted_projects = set()

    print(f"\n🎬 Found {len(videos)} reels")

    for video in videos:

        filename = os.path.basename(video)

        # skip already uploaded
        if filename in history:
            continue

        uploaded = False

        for attempt in range(len(projects)):

            project_idx = attempt % len(projects)

            if project_idx in exhausted_projects:
                continue

            project = projects[project_idx]
            youtube = build_youtube(project)

            body = {
                "snippet": {
                    "title": FIXED_TITLE,
                    "description": MASTER_DESCRIPTION,
                    "categoryId": CATEGORY_ID
                },
                "status": {
                    "privacyStatus": "public",
                    "selfDeclaredMadeForKids": False
                }
            }

            media = MediaFileUpload(video, resumable=True)

            try:

                res = youtube.videos().insert(
                    part="snippet,status",
                    body=body,
                    media_body=media
                ).execute()

                history[filename] = {
                    "video_id": res["id"],
                    "uploaded_at": str(datetime.now()),
                    "project_used": project_idx
                }

                save_history(history)

                print("✅ Uploaded:", filename)

                uploaded = True
                break

            except Exception as e:

                if is_quota_error(e):
                    exhausted_projects.add(project_idx)
                    logging.warning(f"Quota exhausted project {project_idx}")
                    continue

                logging.error(f"{filename} failed: {e}")
                break

        if not uploaded:
            print("⚠️ All projects quota finished")
            break

        time.sleep(3)

    print("\n🎉 ALL REELS PROCESSED")


if __name__ == "__main__":
    main()