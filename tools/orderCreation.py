
# import requests
# from requests.auth import HTTPBasicAuth
# import json

# # Configuration
# username = 'MYU'  # <-- Replace with your SAP username
# password = '@7Ugundharchaudhary'  # <-- Replace with your SAP password
# sap_client = '910'
# base_url = 'https://ldciqm7.wdf.sap.corp:44320'
# odata_url = f'/sap/opu/odata/sap/API_MAINTENANCEORDER/MaintenanceOrder?sap-client={sap_client}'
# full_url = base_url + odata_url

# # Disable SSL warnings for test systems
# requests.packages.urllib3.disable_warnings()

# def fetch_csrf_token():
#     headers = {
#         'Accept': 'application/json',
#         'x-csrf-token': 'Fetch'
#     }
#     response = requests.get(full_url, headers=headers, auth=HTTPBasicAuth(username, password), verify=False)
#     if response.status_code != 200:
#         print(f"Failed to fetch CSRF token: {response.status_code}")
#         print(response.text)
#         return None, None
#     token = response.headers.get('x-csrf-token')
#     cookies = response.cookies
#     return token, cookies

# def get_notifications():
#     headers = {
#         'Accept': 'application/json'
#     }
#     response = requests.get(full_url, headers=headers, auth=HTTPBasicAuth(username, password), verify=False)
#     if response.status_code == 200:
#         data = response.json()
#         print(json.dumps(data, indent=4))
#     else:
#         print(f"GET failed with status code {response.status_code}")
#         print(response.text)

# def create_order():
#     token, cookies = fetch_csrf_token()
#     if not token:
#         return

#     headers = {
#         'Content-Type': 'application/json',
#         'Accept': 'application/json',
#         'x-csrf-token': token
#     }

#     payload = {
  
#   "MaintenanceOrderType": "PM01",
#   "MaintenanceOrderDesc": "ORDER FOR AGENTIC AI CASE",
#   "MainWorkCenter": "030001",
#   "MaintenancePlanningPlant": "0001"

  
# }

#     response = requests.post(
#         base_url + f'/sap/opu/odata/sap/API_MAINTENANCEORDER/MaintenanceOrder?sap-client={sap_client}',
#         headers=headers,
#         cookies=cookies,
#         auth=HTTPBasicAuth(username, password),
#         data=json.dumps(payload),
#         verify=False
#     )
#     response_data= response.json()
#     order = response_data.get("d", {})
#     MaintenanceOrder_number = order.get("MaintenanceOrder")
#     MaintenanceOrderDesc = order.get("MaintenanceOrderDesc")
#     MaintenanceOrderType = order.get("MaintenanceOrderType")
#     MainWorkCenter = order.get("MainWorkCenter")



#     if response.status_code in [200, 201]:
#         print("✅ Order created successfully.")
#         print(f"Notification Number:{MaintenanceOrder_number}")
#         print(f"Notification Text: {MaintenanceOrderDesc}")
#         print(f"Notification Type:{MaintenanceOrderType}")
#         print(f"notiProcessingPhase:{MainWorkCenter}")
        
#         print(json.dumps(response.json(), indent=4))
#         return response_data
#     else:
#         print(f"❌ POST failed with status code {response.status_code}")
#         print(response.text)

# if __name__ == "__main__":
#     choice = input("Enter 'get' to fetch notifications or 'post' to create one: ").strip().lower()
#     if choice == 'get':
#         get_notifications()
#     elif choice == 'post':
#         create_order()
#     else:
#         print("Invalid choice. Please enter 'get' or 'post'.")



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
odata_url = f'/sap/opu/odata/sap/API_MAINTENANCEORDER/MaintenanceOrder?sap-client={sap_client}'
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

def create_order(payload: dict):
    token, cookies = fetch_csrf_token()
    if not token:
        return {"error": "Failed to fetch CSRF token"}

    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'x-csrf-token': token
    }

    response = requests.post(
        full_url,
        headers=headers,
        cookies=cookies,
        auth=HTTPBasicAuth(username, password),
        data=json.dumps(payload),
        verify=False
    )

    if response.status_code in [200, 201]:
        response_data = response.json()
        # notification = response_data.get("d", {})
        # notification_number = notification.get("MaintenanceNotification")
        # notification_text = notification.get("NotificationText")
        # notification_type = notification.get("NotificationType")
        # NotifProcessingPhase = notification.get("NotifProcessingPhase")


        

        # Print the success message (this will appear in console)
        # print("✅ Notification created successfully.")
        # print(f"Notification Number: {notification_number}")
        # print(f"Notification Text: {notification_text}")
        # print(f"Notification Type: {notification_type}")
        # print(f"NotifProcessingPhase: {NotifProcessingPhase}")
        
        # Return the full response for the agent to process
        return response_data
    else:
        error_message = f"POST failed with status code {response.status_code}"
        print(f"❌ {error_message}")
        print(response.text)
        return {"error": error_message, "details": response.text}

if __name__ == "__main__":
    print("hello")

