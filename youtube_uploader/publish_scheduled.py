import json
import os
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
import requests

PROJECTS_DIR = "projects"
HISTORY_FILE = os.path.join("logs", "upload_history.json")
SCOPES = ["https://www.googleapis.com/auth/youtube"]

def load_projects():
    projects = []
    for f in os.listdir(PROJECTS_DIR):
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

def main():
    history = json.load(open(HISTORY_FILE))
    projects = load_projects()

    youtube = build_youtube(projects[0])  # one project is enough

    count = 0

    for video, data in history.items():
        video_id = data["video_id"]

        youtube.videos().update(
            part="status",
            body={
                "id": video_id,
                "status": {
                    "privacyStatus": "public"
                }
            }
        ).execute()

        print(f"✅ Published: {video}")
        count += 1

    print(f"\n🎉 DONE — {count} videos published")

if __name__ == "__main__":
    main()
