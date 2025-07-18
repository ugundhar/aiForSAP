import json
import requests
import os
import csv
from hdbcli import dbapi
from dotenv import load_dotenv
from gen_ai_hub.proxy.langchain.openai import OpenAIEmbeddings, ChatOpenAI
from gen_ai_hub.proxy.core.proxy_clients import get_proxy_client
from langchain.text_splitter import CharacterTextSplitter
from langchain_community.document_loaders import CSVLoader  # Updated import path for CSVLoader

# Load environment variables
load_dotenv()

# Extract authentication details
AICORE_AUTH_URL = os.getenv("AICORE_AUTH_URL")
AICORE_CLIENT_ID = os.getenv("AICORE_CLIENT_ID")
AICORE_CLIENT_SECRET = os.getenv("AICORE_CLIENT_SECRET")
AICORE_BASE_URL = os.getenv("AICORE_BASE_URL")

# Get BTP Token
params = {"grant_type": "client_credentials"}
resp = requests.post(
    f"{AICORE_AUTH_URL}/oauth/token",
    auth=(AICORE_CLIENT_ID, AICORE_CLIENT_SECRET),
    params=params
)
if resp.status_code != 200:
    raise requests.exceptions.RequestException(f"Failed to retrieve token: {resp.status_code} {resp.text}")
access_token = resp.json()["access_token"]

# Set environment variables for downstream use
os.environ.update({
    "AICORE_BASE_URL": AICORE_BASE_URL,
    "AICORE_AUTH_URL": AICORE_AUTH_URL,
    "AICORE_CLIENT_ID": AICORE_CLIENT_ID,
    "AICORE_CLIENT_SECRET": AICORE_CLIENT_SECRET,
    "AICORE_RESOURCE_GROUP": os.getenv("AICORE_RESOURCE_GROUP", "default")
})

# Initialize embedding and LLM models
embedding_model = OpenAIEmbeddings(proxy_model_name='text-embedding-ada-002')
proxy_client = get_proxy_client('gen-ai-hub')
chat_llm = ChatOpenAI(proxy_model_name='gpt-35-turbo', proxy_client=proxy_client, temperature=0.0)

# Connect to SAP HANA
HANA_HOST = os.getenv("HANA_HOST")
HANA_USER = os.getenv("HANA_USER")
HANA_PASSWORD = os.getenv("HANA_PASSWORD")
connection = dbapi.connect(
    address=HANA_HOST,
    port=443,
    user=HANA_USER,
    password=HANA_PASSWORD,
    encrypt='true',
    autocommit='true'
)

# Load technical objects from CSV
csv_file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'technicalObject.csv'))

if not os.path.exists(csv_file_path):
    raise FileNotFoundError(f"CSV file not found at: {csv_file_path}")

data = []
with open(csv_file_path, encoding='utf-8') as csvfile:
    csv_reader = csv.reader(csvfile)
    for row in csv_reader:
        data.append(row)

# Prepare data with embeddings
def get_embedding(input_text):
    return embedding_model.embed_query(input_text)

prepared_data = []
for row in data[1:]:  # Skip the header row
    text = f"ID: {row[0]}\nTYPE: {row[1]}\nNAME: {row[2]}\nPARENTID: {row[3]}\nPARENTTYPE: {row[4]}\nPLANT: {row[5]}"
    embedding = get_embedding(text)
    embedding_str = "[" + ",".join(map(str, embedding)) + "]"
    prepared_data.append(row + [embedding_str])

# Update table creation to use REAL_VECTOR for VECTOR_STR
create_table_sql = '''
CREATE TABLE TECHNICAL_OBJECTS (
    ID NVARCHAR(255),
    TYPE NVARCHAR(255),
    NAME NVARCHAR(255),
    PARENTID NVARCHAR(255),
    PARENTTYPE NVARCHAR(255),
    PLANT NVARCHAR(255),
    VECTOR_STR REAL_VECTOR
);
'''

# Drop existing table if it exists
cursor = connection.cursor()

drop_table_sql = "DROP TABLE TECHNICAL_OBJECTS"
cursor.execute(drop_table_sql)
print("Table TECHNICAL_OBJECTS dropped successfully.")

# Check if the table exists and drop it
check_table_sql = "SELECT TABLE_NAME FROM TABLES WHERE TABLE_NAME = 'TECHNICAL_OBJECTS'"
cursor.execute(check_table_sql)
if cursor.fetchone():
    drop_table_sql = "DROP TABLE TECHNICAL_OBJECTS"
    cursor.execute(drop_table_sql)
    print("Table TECHNICAL_OBJECTS dropped successfully.")

# Create new table
cursor.execute(create_table_sql)
print("New table TECHNICAL_OBJECTS with REAL_VECTOR column created successfully.")

# Insert data into SAP HANA
sql_insert = 'INSERT INTO TECHNICAL_OBJECTS(ID, TYPE, NAME, PARENTID, PARENTTYPE, PLANT, VECTOR_STR) VALUES (?,?,?,?,?,?,TO_REAL_VECTOR(?))'
cursor.executemany(sql_insert, prepared_data)
cursor.close()
connection.close()
print("Embeddings stored successfully.")
