import sys
import os


import json
import requests
from tools.openNotifications import get_notifications
from tools.Retriever_technical_objects import retrieve_and_query_llm
from tools.createNotification import post_notification
from langgraph.graph import StateGraph,START,END
from langgraph.prebuilt import ToolNode
from langgraph.graph.message import add_messages
from typing import Annotated
from langgraph.checkpoint.memory import MemorySaver
from tools.orderapi import get_order_by_number

from typing_extensions import TypedDict
from langgraph.prebuilt import tools_condition

from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Environment variables
HANA_HOST = os.getenv("HANA_HOST")
HANA_USER_DB = os.getenv("HANA_USER")
HANA_PASSWORD_VDB = os.getenv("HANA_PASSWORD")

AICORE_AUTH_URL = os.getenv("AICORE_AUTH_URL")
AICORE_CLIENT_ID = os.getenv("AICORE_CLIENT_ID")
AICORE_CLIENT_SECRET = os.getenv("AICORE_CLIENT_SECRET")
AICORE_BASE_URL = os.getenv("AICORE_BASE_URL")

# Step 1: Get Access Token from SAP BTP AI Core
params = {"grant_type": "client_credentials"}
resp = requests.post(
    f"{AICORE_AUTH_URL}/oauth/token",
    auth=(AICORE_CLIENT_ID, AICORE_CLIENT_SECRET),
    params=params
)
access_token = resp.json()["access_token"]

# Update env for GenAI Hub usage
os.environ.update({
    "AICORE_AUTH_URL": AICORE_AUTH_URL,
    "AICORE_CLIENT_ID": AICORE_CLIENT_ID,
    "AICORE_CLIENT_SECRET": AICORE_CLIENT_SECRET,
    "AICORE_RESOURCE_GROUP": os.getenv("AICORE_RESOURCE_GROUP", "default"),
    "AICORE_BASE_URL": AICORE_BASE_URL
})

from gen_ai_hub.proxy.native.openai import chat
from gen_ai_hub.proxy.langchain.openai import OpenAIEmbeddings, ChatOpenAI
from gen_ai_hub.proxy.core.proxy_clients import get_proxy_client

proxy_client = get_proxy_client('gen-ai-hub')
llm = ChatOpenAI(proxy_model_name='gpt-4o', proxy_client=proxy_client, temperature=0.0)




##Memory agent
memory=MemorySaver()

class State(TypedDict):
    # Messages have the type "list". The `add_messages` function
    # in the annotation defines how this state key should be updated
    # (in this case, it appends messages to the list, rather than overwriting them)
    messages:Annotated[list,add_messages]

##retriever tool for getting the techincal object
def retrieveTechnicalObjects(
    query: str,
    plant: str = "",
    functional_location: str = "",
    equipment: str = "",
    assembly: str = ""
) -> str:
    """
    Retrieve and recommend technical objects from SAP HANA based on the malfunction query and optional conditions.
    
    Args:
        query (str): Description of the malfunction (e.g. "Generator is not working")
        plant (str): Optional plant filter
        functional_location (str): Optional functional location ID
        equipment (str): Optional equipment ID
        assembly (str): Optional assembly ID
    
    Returns:
        str: JSON array of most relevant technical objects
    """
    condn = {
        "plant": plant,
        "functional_location": functional_location,
        "equipment": equipment,
        "assembly": assembly
    }
    return retrieve_and_query_llm(query, condn)



##notification tools
def openNotificatoins(TechnicalObjectLabel: str) -> str:
    """
    Tool function to get open notifications from SAP system based on TechnicalObjectLabel.
    Args:
        TechnicalObjectLabel (str): Label of the technical object
    Returns:
        str: Message with notification summary
    """
    message, data = get_notifications(TechnicalObjectLabel)
    return f"{message}\n\n{data if data else ''}"



## create Notification
def createNofication(
        NotificationText:str,
        NotificationType:str,
        MainWorkCenter:str,
        MaintenancePlanningPlant:str
        ) -> str: # It's good practice to add a return type hint
    """ Tool function to create the Notifications from SAP system based on NotificationText and NotificationType.
    
    Args:
        NotificationText (str): Description for creating Notification (e.g. "Generator is not working")
        NotificationType (str): NotificationType (e.g. "M1")
        MainWorkCenter (str): Optional MainWorkCenter ID (e.g "030001")
        MaintenancePlanningPlant (str): Optional MaintenancePlanningPlant ID (e.g "0001")
    
    Returns:
        str: JSON string of the created MaintenanceNotification or an error message.
    """
    # --- MODIFIED LOGIC ---
    # 1. Build the payload dictionary from the arguments.
    payload = {
        "NotificationText": NotificationText,
        "NotificationType": NotificationType,
        "MainWorkCenter": MainWorkCenter,
        "MaintenancePlanningPlant": MaintenancePlanningPlant
    }
    
    # 2. Call post_notification with the single payload dictionary.
    result = post_notification(payload)
    
    # 3. Return the result as a JSON string for the agent.
    return json.dumps(result)

## order details 
# def  getOrderDetails(oredernumber:int)->str:
    
#      """
#     Tool function to get order details from SAP system based on order number.
#     Args:
#         MaintenanceOrder (int): MaintenanceOrder number
#     Returns:
#         str: Message with order details summary
#     """
#      result=get_order_by_number(oredernumber)
#      return result
     
def getOrderDetails(order_number: int) -> str:
    """
    Tool: getOrderDetails

    Description:
        Retrieves maintenance order details from SAP based on the provided order number.

    Args:
        order_number (int): The maintenance order number (e.g., 200200)

    Returns:
        str: A structured message containing key order details or an error message if not found.
    """
    try:
        order_data = get_order_by_number(order_number)
        if isinstance(order_data, dict) and "MaintenanceOrder" in order_data:
            return (
                f"✅ Maintenance Order Details:\n"
                f"Order Number       : {order_data.get('MaintenanceOrder')}\n"
                f"Description        : {order_data.get('MaintenanceOrderDesc')}\n"
                f"Order Type         : {order_data.get('MaintenanceOrderType')}\n"
                f"Planning Plant     : {order_data.get('MaintenancePlanningPlant')}\n"
                f"Main Work Center   : {order_data.get('MainWorkCenter')}\n"
                f"Technical Object   : {order_data.get('TechnicalObject')}"
            )
        else:
            return f"❌ No valid data found for order number {order_number}."
    except Exception as e:
        return f"❌ Error while fetching order details: {str(e)}"


## Custom function
def multiply(a:int,b:int)->int:
    """Multiply a and b

    Args:
        a (int): first int
        b (int): second int

    Returns:
        int: output int
    """
    return a*b

tools=[multiply,openNotificatoins,retrieveTechnicalObjects,createNofication,getOrderDetails]
llm_with_tools=llm.bind_tools(tools)
# print(llm_with_tools)


##Node definition
def tool_calling_llm(state:State):
    response = llm_with_tools.invoke(state["messages"])
    return {"messages": state["messages"] + [response]}

##Graph
builder=StateGraph(State)
builder.add_node("supervisor",tool_calling_llm)
builder.add_node("tools",ToolNode(tools))


##Edges
builder.add_edge(START,"supervisor")
builder.add_conditional_edges("supervisor",tools_condition)
builder.add_edge("tools",END)


graph=builder.compile(checkpointer=memory)

png_image=graph.get_graph().draw_mermaid_png()
with open("flow1.png", "wb") as f:
    f.write(png_image)

# Conversational loop for terminal interaction
while True:
    user_input = input("You: ")
    if user_input.lower() == "quit":
        print("Exiting the chatbot. Goodbye!")
        break

    # Invoke the graph with user input
    config = {"configurable": {"thread_id": "5"}}
    result = graph.invoke({"messages": [user_input]}, config=config)

    # Print the chatbot's response
    for m in result['messages']:
        m.pretty_print()