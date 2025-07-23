import sys
import os



import app_streamlit as st
from src.llm.gpt_client import chat_llm
from src.llm.supervisor import handle_query

# Initialize Streamlit app
st.title("Chatbot Application")
st.write("Ask your questions below:")

# Input field for user question
user_question = st.text_input("Your Question:")

if user_question:
    # Use supervisor to handle the query
    response = handle_query(user_question)
    if response:
        st.write("Response:")
        st.write(response)
