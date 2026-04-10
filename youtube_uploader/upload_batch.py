import os
import json
import time
import logging
import requests
import re
from datetime import datetime, timedelta, timezone
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials
from googleapiclient.errors import HttpError

# ================= CONFIG =================

PROJECTS_DIR = "projects"
BASE_VIDEO_DIR = r"C:\Users\VCOM\Desktop\Kalyan_Penal_Scraper\video_output"

date_folders = [
    d for d in os.listdir(BASE_VIDEO_DIR)
    if os.path.isdir(os.path.join(BASE_VIDEO_DIR, d))
]

if not date_folders:
    raise RuntimeError("❌ No date folders found in video_output")

latest_folder = sorted(date_folders)[-1]
VIDEO_FOLDER = os.path.join(BASE_VIDEO_DIR, latest_folder)

print(f"📁 Using video folder: {VIDEO_FOLDER}")




CATEGORY_ID = "22"
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

LOG_DIR = "logs"
HISTORY_FILE = os.path.join(LOG_DIR, "upload_history.json")

MASTER_DESCRIPTION = """Aaj ka Satta Matka AI Prediction Video
Is video me aapko milta hai:
• Aaj ka Open Digit
• Close Digit
• Jodi
• Open Panna
• Close Panna
• Market wise full AI report (Kalyan, Rajdhani, Milan, aur sabhi markets)

Ye prediction SattaMatkaAI Engine se auto-generate hota hai jo historical data, patterns aur frequency analysis par based hai.
📲 Hamari App Download Kare (FREE)
👉 App Link: https://tinyurl.com/sattamatkaAi-2
App Kaise Download Kare:
1. Link par click kare
2. package installer select kare
3.Unknown device settings se enable kre
4. Daily AI predictions, premium charts, aur yesterday winners free me dekhe

⚠️ IMPORTANT DISCLAIMER

Ye video sirf entertainment aur informational purpose ke liye hai.
Hum kisi bhi tarah ki satta ya gambling ko promote nahi karte.
Prediction ke numbers data-based hain, guaranteed winning nahi dete.
Koi bhi financial loss ya misuse ke liye hum zimmedar nahi honge.

📌 About This Video

Is video me aapko milta hai full AI prediction chart jisme sabhi markets ka Open, Close, Jodi, Panna auto-animated format me show hota hai.
Daily new video generate hota hai hamare AI script se.

Video ko LIKE kare
• Comment me market name likhe
• Channel ko SUBSCRIBE kare daily AI prediction videos ke liye
• Hamari SattaMatkaAI app download jarur kare
👇 Follow for daily Satta Matka predictions & updates 👇

@SattaMatkaAI

Follow us on Instagram:
👉 https://www.instagram.com/sattamatkaai?igsh=MWhreDlqNWZ2cDNqcw==

Like our Facebook Page:
👉 https://www.facebook.com/share/1BYc2qHqtu/

Subscribe on YouTube:
👉 https://youtube.com/@sattamatkaai?si=8GG2IJnrEblBTNg-



#SattaMatka #Matka #Satta #KalyanMatka #Rajdhani #MilanDay #TimeBazaar #MainBazar #SrideviNight #MatkaPrediction #MatkaResults #SattaResults #MatkaGame #MatkaCommunity #MatkaCharts #MatkaTips #KalyanResult #RajdhaniNight #MilanNight #SattaKing #MatkaTricks #MatkaJodi #MatkaOpenClose #MatkaNumbers #SattaToday #SattaMatkaChart #MatkaLive #MatkaResultToday #MatkaGuessing #SattaMatka2025 #MatkaWinning #MatkaOnline #MatkaFix #MatkaBazaar #MatkaGuru #MatkaWorld #SattaMatkaPrediction #MatkaInfo #MatkaDaily #SattaFans
"""

# ========================================

os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    filename=os.path.join(LOG_DIR, "upload.log"),
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# ---------- HELPERS ----------

def extract_tags(description):
    tags = re.findall(r"#(\w+)", description)
    return list(dict.fromkeys(tags))[:15]

def generate_title(filename):
    name = os.path.splitext(filename)[0]
    parts = name.split("_")

    market = parts[0].capitalize()

    # Handle YYYYMMDD, Unix ms (13 digits), or Unix s (10 digits)
    date_obj = None
    for part in parts[1:]:
        if part.isdigit():
            if len(part) == 8:
                date_obj = datetime.strptime(part, "%Y%m%d")
                break
            elif len(part) == 13:
                date_obj = datetime.fromtimestamp(int(part) / 1000)
                break
            elif len(part) == 10:
                date_obj = datetime.fromtimestamp(int(part))
                break

    if not date_obj:
        date_obj = datetime.now()

    pretty_date = date_obj.strftime("%d %b %Y")
    return f"{market} Satta Matka AI Prediction | {pretty_date} 🔥"

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

def get_videos():
    return sorted([f for f in os.listdir(VIDEO_FOLDER) if f.endswith(".mp4")])

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

# ---------- MAIN ----------

def main():


    projects = load_projects()
    videos = get_videos()
    history = load_history()
    tags = extract_tags(MASTER_DESCRIPTION)

    if not os.path.exists(VIDEO_FOLDER):
        raise FileNotFoundError(f"❌ Video folder not found: {VIDEO_FOLDER}")
    

     

    exhausted_projects = set()
    

    for video in videos:
        if video in history:
            continue

        uploaded = False

        for attempt in range(len(projects)):
            project_idx = attempt % len(projects)

            if project_idx in exhausted_projects:
                continue

            project = projects[project_idx]
            youtube = build_youtube(project)

            title = generate_title(video)
            

            body = {
                "snippet": {
                    "title": title,
                    "description": MASTER_DESCRIPTION,
                    "tags": tags,
                    "categoryId": CATEGORY_ID
                },
                "status": {
                    "privacyStatus": "public"
                    
                }
            }

            media = MediaFileUpload(os.path.join(VIDEO_FOLDER, video), resumable=True)

            try:
                res = youtube.videos().insert(
                    part="snippet,status",
                    body=body,
                    media_body=media
                ).execute()

                history[video] = {
                    "video_id": res["id"],
                    "project_used": project_idx,
                    
                }
                save_history(history)

                print(f"✅ Uploaded & Published: {title}")
                
                uploaded = True
                break

            except Exception as e:
                if is_quota_error(e):
                    exhausted_projects.add(project_idx)
                    logging.warning(f"Quota exhausted for project {project_idx}")
                    continue
                else:
                    logging.error(f"{video} failed: {e}")
                    break

        if not uploaded:
            print("⚠️ All projects exhausted. Stopping.")
            break

        time.sleep(2)

    print("🎉 PROCESS COMPLETE")

if __name__ == "__main__":
    main()