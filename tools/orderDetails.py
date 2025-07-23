import requests
from requests.auth import HTTPBasicAuth
import json
from dotenv import load_dotenv
import os

# Load .env file
load_dotenv()

# Load credentials from environment
username = os.getenv("USER_NAME")  # Your SAP username
password = os.getenv("PASSWORD")   # Your SAP password

# Configuration
sap_client = '910'
base_url = 'https://ldai1qm7.wdf.sap.corp:44320'

# Disable SSL warnings for test systems
requests.packages.urllib3.disable_warnings()

def get_order_by_number(order_number: str):
    order_url = f"{base_url}/sap/opu/odata/sap/API_MAINTENANCEORDER/MaintenanceOrder('{order_number}')?sap-client={sap_client}"
    
    headers = {
        'Accept': 'application/json'
    }
    
    response = requests.get(order_url, headers=headers, auth=HTTPBasicAuth(username, password), verify=False)

    if response.status_code == 200:
        data = response.json()
        order_data = data.get("d", {})
        print("✅ Maintenance Order Details:")
        print(f"Order Number       : {order_data.get('MaintenanceOrder')}")
        print(f"Description        : {order_data.get('MaintenanceOrderDesc')}")
        print(f"Order Type         : {order_data.get('MaintenanceOrderType')}")
        print(f"Planning Plant     : {order_data.get('MaintenancePlanningPlant')}")
        print(f"Main Work Center   : {order_data.get('MainWorkCenter')}")
        print(f"Technical Object   : {order_data.get('TechnicalObject')}")
        print(json.dumps(order_data, indent=4))
        return data
    else:
        print(f"❌ Failed to retrieve order {order_number}. Status Code: {response.status_code}")
        print(response.text)

# Example usage
if __name__ == "__main__":
    order_number = input("Enter Maintenance Order Number (e.g., 200200): ").strip()
    get_order_by_number(order_number)
