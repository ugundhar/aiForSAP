import sys
import os


import json
import requests
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
chat_llm = ChatOpenAI(proxy_model_name='anthropic--claude-3.5-sonnet', proxy_client=proxy_client, temperature=0.0)

result=chat_llm.invoke("what is usa full form").content
print(result)

