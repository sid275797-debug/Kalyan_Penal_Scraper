import json
import requests
from google.oauth2 import service_account
from google.auth.transport.requests import Request

# ================= CONFIG =================

SERVICE_ACCOUNT_FILE = "Serviceaccount.json"
PROJECT_ID = "sattamatkaai-77102"   # confirm this is correct
FCM_ENDPOINT = f"https://fcm.googleapis.com/v1/projects/{PROJECT_ID}/messages:send"

SCOPES = ["https://www.googleapis.com/auth/firebase.messaging"]

# ========================================

def get_access_token():
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    credentials.refresh(Request())
    return credentials.token


def send_result_notification(market_name):
    access_token = get_access_token()

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json; UTF-8",
    }

    payload = {
        "message": {
            "topic": "daily",
            "notification": {
                "title": f"✅ Result Out – {market_name}",
                "body": "Today’s open & close result is now available."
            },
            "android": {
                "priority": "HIGH"
            }
        }
    }

    response = requests.post(
        FCM_ENDPOINT,
        headers=headers,
        data=json.dumps(payload)
    )

    if response.status_code == 200:
        print(f"✅ Notification sent for {market_name}")
    else:
        print("❌ Failed to send notification")
        print(response.status_code, response.text)


# ===== TEST RUN =====
if __name__ == "__main__":
    send_result_notification("Kalyan")
