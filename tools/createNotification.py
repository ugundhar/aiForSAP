import requests
from requests.auth import HTTPBasicAuth
import json
from dotenv import load_dotenv
import os
# Load .env file
load_dotenv()

username = os.getenv("USER_NAME") # <-- Replace with your SAP username
password = os.getenv("PASSWORD")  # <-- Replace with your SAP password

sap_client = '910'
base_url = 'https://ldai1qm7.wdf.sap.corp:44320'
odata_url = f'/sap/opu/odata/sap/API_MAINTNOTIFICATION/MaintenanceNotification?sap-client={sap_client}'
full_url = base_url + odata_url

requests.packages.urllib3.disable_warnings()

def fetch_csrf_token():
    headers = {
        'Accept': 'application/json',
        'x-csrf-token': 'Fetch'
    }
    response = requests.get(full_url, headers=headers, auth=HTTPBasicAuth(username, password), verify=False)
    if response.status_code != 200:
        print(f"Failed to fetch CSRF token: {response.status_code}")
        print(response.text)
        return None, None
    token = response.headers.get('x-csrf-token')
    cookies = response.cookies
    return token, cookies

def post_notification(payload: dict):
    token, cookies = fetch_csrf_token()
    if not token:
        return {"error": "Failed to fetch CSRF token"}

    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'x-csrf-token': token
    }

    response = requests.post(
        base_url + f'/sap/opu/odata/sap/API_MAINTNOTIFICATION/MaintenanceNotification',
        headers=headers,
        cookies=cookies,
        auth=HTTPBasicAuth(username, password),
        data=json.dumps(payload),
        verify=False
    )

    if response.status_code in [200, 201]:
        response_data = response.json()
        notification = response_data.get("d", {})
        notification_number = notification.get("MaintenanceNotification")
        notification_text = notification.get("NotificationText")
        notification_type = notification.get("NotificationType")
        NotifProcessingPhase = notification.get("NotifProcessingPhase")



        result={

            "Notification Number":notification_number,
            "Notification Tex": notification_text,
            "NotificationType":notification_type,
            "NotifProcessingPhase":NotifProcessingPhase

        }

        # Print the success message (this will appear in console)
        # print("✅ Notification created successfully.")
        # print(f"Notification Number: {notification_number}")
        # print(f"Notification Text: {notification_text}")
        # print(f"Notification Type: {notification_type}")
        # print(f"NotifProcessingPhase: {NotifProcessingPhase}")
        
        # Return the full response for the agent to process
        return result
    else:
        error_message = f"POST failed with status code {response.status_code}"
        print(f"❌ {error_message}")
        print(response.text)
        return {"error": error_message, "details": response.text}

if __name__ == "__main__":
    post_notification()

