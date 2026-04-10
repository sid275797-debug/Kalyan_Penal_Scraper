import os
import json
import logging
import requests
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials
from datetime import datetime


# ---------------- CONFIG ----------------

PROJECT_JSON = os.path.join("projects", "project_1.json")

MERGED_VIDEO_PATH = r"C:\Users\VCOM\Desktop\Kalyan_Penal_Scraper\merged_videos\final_merged.mp4"


TODAY = datetime.now().strftime("%d %b %Y")  # e.g. 27 Dec 2025
TITLE = f"Aaj ka Satta Matka AI Prediction | {TODAY}"





DESCRIPTION = """  Aaj ka Satta Matka AI Prediction Video
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
TAGS = [
    "Satta Matka", "Matka", "Kalyan", "Rajdhani", "Milan",
    "Satta Prediction", "Matka AI"
]

CATEGORY_ID = "22"
PRIVACY_STATUS = "public"

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

# ----------------------------------------

os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    filename="logs/upload.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def load_project():
    with open(PROJECT_JSON, "r") as f:
        return json.load(f)

def get_access_token(client_id, client_secret, refresh_token):
    token_url = "https://oauth2.googleapis.com/token"
    payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token"
    }

    response = requests.post(token_url, data=payload)
    response.raise_for_status()
    return response.json()["access_token"]


def upload_video(youtube, video_path):
    request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": TITLE,
                "description": DESCRIPTION,
                "tags": TAGS,
                "categoryId": CATEGORY_ID
            },
            "status": {
                "privacyStatus": PRIVACY_STATUS
            }
        },
        media_body=MediaFileUpload(video_path, resumable=True)
    )

    return request.execute()

def main():
    try:
        project = load_project()

        access_token = get_access_token(
            project["client_id"],
            project["client_secret"],
            project["refresh_token"]
        )

        creds = Credentials(
            token=access_token,
            refresh_token=project["refresh_token"],
            token_uri="https://oauth2.googleapis.com/token",
            client_id=project["client_id"],
            client_secret=project["client_secret"],
            scopes=SCOPES
        )

        youtube = build("youtube", "v3", credentials=creds)

        video_path = MERGED_VIDEO_PATH
        if not os.path.exists(video_path):
            raise Exception("Merged video not found")


        logging.info(f"Uploading video: {video_path}")
        response = upload_video(youtube, video_path)

        video_id = response["id"]
        logging.info(f"Upload successful. Video ID: {video_id}")

        print("✅ Upload successful")
        print("Video ID:", video_id)

    except Exception as e:
        logging.error(str(e))
        print("❌ Upload failed:", e)

if __name__ == "__main__":
    main()
