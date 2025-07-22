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

# Disable SSL warnings for test systems
requests.packages.urllib3.disable_warnings()

def get_notifications(tech_obj_label):
    """" get open notification user will give the  TechnicalObjectLabel based on that get the notificatoins"""
    select_fields = (
        "TechnicalObjectLabel,MaintenanceNotification,MaintNotifInternalID,"
        "MaintenancePlanningPlant,MaintenancePlannerGroup,TechObjIsEquipOrFuncnlLocDesc,"
        "TechnicalObjectDescription,PlantName,MaintenancePlant,CreatedByUser,"
        "EAMProcessPhaseCodeDesc,MaintenancePlantName"
    )
    filter_query = f"$filter=TechnicalObjectLabel eq '{tech_obj_label}' and (NotifProcessingPhase eq '1' or NotifProcessingPhase eq '2' or NotifProcessingPhase eq '3')"
    odata_url = f'/sap/opu/odata/sap/API_MAINTNOTIFICATION/MaintenanceNotification?$select={select_fields}&{filter_query}&sap-client={sap_client}'
    full_url = base_url + odata_url

    headers = {
        'Accept': 'application/json'
    }
    response = requests.get(full_url, headers=headers, auth=HTTPBasicAuth(username, password), verify=False)
    
    if response.status_code == 200:
        data = response.json()
        notifications = data.get("d", {}).get("results", [])
        count = len(notifications)
        message = f"{count} open notifications are present for the given Technical Object Label."
        return message, json.dumps(notifications, indent=4)
    else:
        return f"GET failed with status code {response.status_code}\n{response.text}", None

if __name__ == "__main__":
    tech_obj_label = input("Enter Technical Object Label: ").strip()
    result = get_notifications(tech_obj_label)
    print(result)



