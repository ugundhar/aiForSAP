import json
import os
from hdbcli import dbapi
from dotenv import load_dotenv
from gen_ai_hub.proxy.langchain.openai import OpenAIEmbeddings, ChatOpenAI
from langchain.prompts import PromptTemplate

# Load environment variables
load_dotenv()

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

# Initialize embedding and LLM models
embedding_model = OpenAIEmbeddings(proxy_model_name='text-embedding-ada-002')
chat_llm = ChatOpenAI(proxy_model_name='gpt-4o', temperature=0.0, top_p=0.9)

# Define prompt template
promptTemplate_fstring = """
Display all the retrieved 4 results from the database and select the most relevant technical objects based on the query.

Return the answer as a JSON array of objects.
Important:

Use double quotes for all keys and string values.
Do not include any extra text, explanation, or formatting—only output the JSON array.
Each object must include all of the following fields (even if some values are empty):
"Assembly"
"AssemblyName"
"Equipment"
"EquipmentName"
"FunctionalLocation"
"FunctionalLocationName"
"Plant"
"MaintenanceOrderDesc"
For each result, fill the fields as follows:

If Type = "Functional Location":
"FunctionalLocation": <ID>
"FunctionalLocationName": <NAME>
"Equipment": ""
"EquipmentName": ""
"Assembly": ""
"AssemblyName": ""
"Plant": <PLANT>
"MaintenanceOrderDesc": <query>

If Type = "Equipment":
"Equipment": <ID>
"EquipmentName": <NAME>
"FunctionalLocation": <PARENTID>
"FunctionalLocationName": ""
"Plant": <PLANT>
"Assembly": ""
"AssemblyName": ""
"MaintenanceOrderDesc": <query>

If Type = "Material":
"Assembly": <ID>
"AssemblyName": <NAME>
"Equipment": <PARENTID>
"EquipmentName": ""
"FunctionalLocation": ""
"FunctionalLocationName": ""
"Plant": <PLANT>
"MaintenanceOrderDesc": <query>

Context:
{context}
Question:
{query}

"""
promptTemplate = PromptTemplate.from_template(promptTemplate_fstring)

# Perform vector search
cursor = connection.cursor()

def get_embedding(input_text):
    return embedding_model.embed_query(input_text)

def format_results(results):
    formatted_results = []
    for result in results:
        formatted_results.append({
            "ID": result[0],
            "Type": result[1],
            "Name": result[2],
            "Parent ID": result[3],
            "Parent Type": result[4],
            "Plant": result[5],
            "Relevance Score": round(result[6] * 100, 2)
        })
    return formatted_results

def run_vector_search(query: str, condn: dict, metric="COSINE_SIMILARITY", k=4):
    tab = 'TECHNICAL_OBJECTS'
    sort = 'ASC' if metric == 'L2DISTANCE' else 'DESC'
    query_vector = get_embedding(query)

    # Build WHERE clause dynamically
    where_conditions = []
    if condn.get('plant'):
        where_conditions.append(f"PLANT = '{condn['plant']}'")

    id_conditions = []
    if condn.get('functional_location'):
        id_conditions.append(f"ID = '{condn['functional_location']}'")
    if condn.get('equipment'):
        id_conditions.append(f"ID = '{condn['equipment']}'")
    if condn.get('assembly'):
        id_conditions.append(f"ID = '{condn['assembly']}'")

    plant_clause = " AND ".join(where_conditions) if where_conditions else ""
    id_clause = " OR ".join(id_conditions) if id_conditions else ""

    where_clause = f"WHERE {plant_clause} AND ({id_clause})" if plant_clause and id_clause else f"WHERE {plant_clause}" if plant_clause else f"WHERE {id_clause}" if id_clause else ""

    sql = f'''
    SELECT TOP {k} ID, TYPE, NAME, PARENTID, PARENTTYPE, PLANT,
    COSINE_SIMILARITY(TO_REAL_VECTOR('{query_vector}'), "VECTOR_STR") AS similarity_score
    FROM "{tab}"
    {where_clause}
    ORDER BY similarity_score {sort}
    '''
    
    print(f"Executing SQL: {sql}")

    cursor.execute(sql)
    hdf = cursor.fetchall()
    print(f"Retrieved {len(hdf)} results from the database.")
    print(f"Results: {hdf[:k]}")
    return format_results(hdf[:k])

def retrieve_and_query_llm(query: str, condn: dict, metric='COSINE_SIMILARITY', k=4):
    context = run_vector_search(query, condn, metric, k)
    prompt = promptTemplate.format(query=query, context=' '.join(str(context)))
    response = chat_llm.invoke(prompt).content
    
    return response

# query = "Generator is not working"
# response = retrieve_and_query_llm(query=query, condn={}, k=4)
# print(response)