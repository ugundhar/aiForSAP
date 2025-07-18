import re
import streamlit as st
from src.llm.gpt_client import chat_llm
from tools.openNotifications import get_notifications
from tools.NotificationAPI import post_notification
from langchain_core.messages import SystemMessage

SYSTEM_PROMPT = SystemMessage(
    content="""You are a versatile AI assistant capable of handling general queries and interacting with specialized tools.
    
    For general queries:
    - Provide concise, accurate, and helpful responses.
    - Use your knowledge base to answer questions directly.

    For queries related to Notifications:
    - Prompt the user to provide the required Technical Object Label.
    - Use the Notification tool to fetch and display relevant data.
    - Ensure the response is formatted in clean Markdown  in json format for clarity.

    Always aim to provide clear and actionable information to the user."""
)

def handle_query(user_query):
    """
    Intelligent supervisor to decide which tool to call based on the user's query.
    """
    # Define tool mappings
    tool_mappings = {
        "create notification": post_notification,
        "see notifications": get_notifications
    }

    # Iterate through tool mappings to find the right tool
    for keyword, tool in tool_mappings.items():
        if re.search(keyword, user_query, re.IGNORECASE):
            st.write(f"Agent: Detected intent to {keyword}.")
            if tool == get_notifications:
                st.write("Agent: Please provide your Technical Object Label.")
                tech_obj_label = st.text_input("Enter Technical Object Label:")
                if tech_obj_label:
                    st.write("Calling get_notifications tool...")
                    result = tool(tech_obj_label)
                    if isinstance(result, tuple):
                        message, response = result
                        st.write("Response:")
                        st.write(message)
                        if response:
                            st.write(response)
                    else:
                        st.write(result)
            else:
                tool()
            return

    # Default to LLM for general queries
    st.write("Forwarding query to LLM...")
    response = chat_llm.invoke(user_query).content
    st.write("Response:")
    st.write(response)
