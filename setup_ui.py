# import streamlit as st
# import sys
# import os
# import json
# import requests
# import time
# from datetime import datetime
# from typing import Dict, List, Any, Optional
# import io
# import contextlib
# import re

# # Import your existing modules
# try:
#     from tools.openNotifications import get_notifications
#     from tools.Retriever_technical_objects import retrieve_and_query_llm
#     from tools.createNotification import post_notification
#     from langgraph.graph import StateGraph, START, END
#     from langgraph.prebuilt import ToolNode
#     from langgraph.graph.message import add_messages
#     from typing import Annotated
#     from langgraph.checkpoint.memory import MemorySaver
#     from typing_extensions import TypedDict
#     from langgraph.prebuilt import tools_condition
#     from dotenv import load_dotenv
#     from gen_ai_hub.proxy.native.openai import chat
#     from gen_ai_hub.proxy.langchain.openai import OpenAIEmbeddings, ChatOpenAI
#     from gen_ai_hub.proxy.core.proxy_clients import get_proxy_client
# except ImportError as e:
#     st.error(f"Missing dependencies: {e}")
#     st.stop()

# # Load environment variables
# load_dotenv()

# # Page configuration
# st.set_page_config(
#     page_title="SAP Maintenance Assistant",
#     page_icon="🔧",
#     layout="wide",
#     initial_sidebar_state="expanded"
# )

# # Custom CSS for modern chat interface
# st.markdown("""
# <style>
#     .main-header {
#         text-align: center;
#         padding: 1rem 0;
#         background: linear-gradient(90deg, #1f4e79 0%, #2d5aa0 100%);
#         color: white;
#         margin: -1rem -1rem 2rem -1rem;
#         border-radius: 0 0 10px 10px;
#     }
    
#     .chat-container {
#         max-height: 500px;
#         overflow-y: auto;
#         padding: 1rem;
#         border: 1px solid #e0e0e0;
#         border-radius: 10px;
#         margin-bottom: 1rem;
#         background: #fafafa;
#     }
    
#     .user-message {
#         background: #007acc;
#         color: white;
#         padding: 0.75rem 1rem;
#         border-radius: 15px 15px 5px 15px;
#         margin: 0.5rem 0 0.5rem auto;
#         max-width: 80%;
#         word-wrap: break-word;
#     }
    
#     .assistant-message {
#         background: white;
#         color: #333;
#         padding: 0.75rem 1rem;
#         border-radius: 15px 15px 15px 5px;
#         margin: 0.5rem auto 0.5rem 0;
#         max-width: 80%;
#         border: 1px solid #e0e0e0;
#         word-wrap: break-word;
#     }
    
#     .system-message {
#         background: #f0f8ff;
#         color: #555;
#         padding: 0.5rem 1rem;
#         border-radius: 10px;
#         margin: 0.5rem 0;
#         border-left: 4px solid #007acc;
#         font-style: italic;
#     }
    
#     .thinking-process {
#         background: #fff3cd;
#         border: 1px solid #ffeaa7;
#         border-radius: 8px;
#         padding: 0.75rem;
#         margin: 0.5rem 0;
#     }
    
#     .processing-step {
#         display: flex;
#         align-items: center;
#         margin: 0.25rem 0;
#     }
    
#     .spinner {
#         width: 16px;
#         height: 16px;
#         border: 2px solid #f3f3f3;
#         border-top: 2px solid #007acc;
#         border-radius: 50%;
#         animation: spin 1s linear infinite;
#         margin-right: 0.5rem;
#     }
    
#     @keyframes spin {
#         0% { transform: rotate(0deg); }
#         100% { transform: rotate(360deg); }
#     }
    
#     .metric-card {
#         background: white;
#         padding: 1rem;
#         border-radius: 8px;
#         border: 1px solid #e0e0e0;
#         text-align: center;
#     }
    
#     .status-indicator {
#         width: 12px;
#         height: 12px;
#         border-radius: 50%;
#         display: inline-block;
#         margin-right: 0.5rem;
#     }
    
#     .status-online { background-color: #28a745; }
#     .status-offline { background-color: #dc3545; }
# </style>
# """, unsafe_allow_html=True)

# # Initialize session state
# def init_session_state():
#     """Initialize session state variables"""
#     if 'messages' not in st.session_state:
#         st.session_state.messages = []
#     if 'conversation_history' not in st.session_state:
#         st.session_state.conversation_history = []
#     if 'system_initialized' not in st.session_state:
#         st.session_state.system_initialized = False
#     if 'graph' not in st.session_state:
#         st.session_state.graph = None
#     if 'processing_steps' not in st.session_state:
#         st.session_state.processing_steps = []

# class State(TypedDict):
#     messages: Annotated[list, add_messages]

# def initialize_system():
#     """Initialize the SAP system connection and LangGraph"""
#     try:
#         with st.spinner("🔄 Initializing SAP AI Core connection..."):
#             # Environment variables
#             HANA_HOST = os.getenv("HANA_HOST")
#             HANA_USER_DB = os.getenv("HANA_USER")
#             HANA_PASSWORD_VDB = os.getenv("HANA_PASSWORD")
            
#             AICORE_AUTH_URL = os.getenv("AICORE_AUTH_URL")
#             AICORE_CLIENT_ID = os.getenv("AICORE_CLIENT_ID")
#             AICORE_CLIENT_SECRET = os.getenv("AICORE_CLIENT_SECRET")
#             AICORE_BASE_URL = os.getenv("AICORE_BASE_URL")
            
#             if not all([AICORE_AUTH_URL, AICORE_CLIENT_ID, AICORE_CLIENT_SECRET, AICORE_BASE_URL]):
#                 st.error("❌ Missing required environment variables for SAP AI Core")
#                 return None
            
#             # Get Access Token from SAP BTP AI Core
#             params = {"grant_type": "client_credentials"}
#             resp = requests.post(
#                 f"{AICORE_AUTH_URL}/oauth/token",
#                 auth=(AICORE_CLIENT_ID, AICORE_CLIENT_SECRET),
#                 params=params
#             )
            
#             if resp.status_code != 200:
#                 st.error(f"❌ Failed to authenticate with SAP AI Core: {resp.status_code}")
#                 return None
                
#             access_token = resp.json()["access_token"]
            
#             # Update environment
#             os.environ.update({
#                 "AICORE_AUTH_URL": AICORE_AUTH_URL,
#                 "AICORE_CLIENT_ID": AICORE_CLIENT_ID,
#                 "AICORE_CLIENT_SECRET": AICORE_CLIENT_SECRET,
#                 "AICORE_RESOURCE_GROUP": os.getenv("AICORE_RESOURCE_GROUP", "default"),
#                 "AICORE_BASE_URL": AICORE_BASE_URL
#             })
            
#             # Initialize GenAI Hub components
#             proxy_client = get_proxy_client('gen-ai-hub')
#             llm = ChatOpenAI(proxy_model_name='gpt-4o', proxy_client=proxy_client, temperature=0.0)
            
#             # Define tools
#             def retrieveTechnicalObjects(
#                 query: str,
#                 plant: str = "",
#                 functional_location: str = "",
#                 equipment: str = "",
#                 assembly: str = ""
#             ) -> str:
#                 """Retrieve and recommend technical objects from SAP HANA based on the malfunction query and optional conditions."""
#                 condn = {
#                     "plant": plant,
#                     "functional_location": functional_location,
#                     "equipment": equipment,
#                     "assembly": assembly
#                 }
#                 return retrieve_and_query_llm(query, condn)

#             def openNotifications(TechnicalObjectLabel: str) -> str:
#                 """Tool function to get open notifications from SAP system based on TechnicalObjectLabel."""
#                 message, data = get_notifications(TechnicalObjectLabel)
#                 return f"{message}\n\n{data if data else ''}"

#             def createNotification(
#                 NotificationText: str,
#                 NotificationType: str,
#                 MainWorkCenter: str,
#                 MaintenancePlanningPlant: str
#             ) -> str:
#                 """Tool function to create the Notifications from SAP system."""
#                 payload = {
#                     "NotificationText": NotificationText,
#                     "NotificationType": NotificationType,
#                     "MainWorkCenter": MainWorkCenter,
#                     "MaintenancePlanningPlant": MaintenancePlanningPlant
#                 }
#                 result = post_notification(payload)
#                 return json.dumps(result)

#             def multiply(a: int, b: int) -> int:
#                 """Multiply a and b (utility function)"""
#                 return a * b

#             tools = [multiply, openNotifications, retrieveTechnicalObjects, createNotification]
#             llm_with_tools = llm.bind_tools(tools)
            
#             # Memory agent
#             memory = MemorySaver()
            
#             def tool_calling_llm(state: State):
#                 response = llm_with_tools.invoke(state["messages"])
#                 return {"messages": state["messages"] + [response]}
            
#             # Build graph
#             builder = StateGraph(State)
#             builder.add_node("supervisor", tool_calling_llm)
#             builder.add_node("tools", ToolNode(tools))
            
#             builder.add_edge(START, "supervisor")
#             builder.add_conditional_edges("supervisor", tools_condition)
#             builder.add_edge("tools", END)
            
#             graph = builder.compile(checkpointer=memory)
            
#             st.session_state.graph = graph
#             st.session_state.system_initialized = True
#             st.success("✅ SAP Maintenance Assistant initialized successfully!")
#             return graph
            
#     except Exception as e:
#         st.error(f"❌ System initialization failed: {str(e)}")
#         return None

# def add_processing_step(step: str, is_complete: bool = False):
#     """Add a processing step to the current operation"""
#     st.session_state.processing_steps.append({
#         'step': step,
#         'complete': is_complete,
#         'timestamp': datetime.now()
#     })

# def clear_processing_steps():
#     """Clear all processing steps"""
#     st.session_state.processing_steps = []

# def display_processing_steps():
#     """Display current processing steps"""
#     if st.session_state.processing_steps:
#         with st.expander("🔄 Processing Steps", expanded=True):
#             for step_info in st.session_state.processing_steps:
#                 if step_info['complete']:
#                     st.markdown(f"✅ {step_info['step']}")
#                 else:
#                     st.markdown(f"""
#                     <div class="processing-step">
#                         <div class="spinner"></div>
#                         {step_info['step']}
#                     </div>
#                     """, unsafe_allow_html=True)

# import io
# import contextlib

# def process_message(user_input: str) -> str:
#     """Process user message through the LangGraph system with pretty-printed response."""
#     if not st.session_state.system_initialized or not st.session_state.graph:
#         return "❌ System not initialized. Please check your configuration."
    
#     try:
#         clear_processing_steps()
#         add_processing_step("Analyzing user query...")
        
#         # Configuration for LangGraph
#         config = {"configurable": {"thread_id": "streamlit_session"}}
        
#         add_processing_step("Invoking AI assistant...")
        
#         # Invoke LangGraph with the user input
#         result = st.session_state.graph.invoke({"messages": [user_input]}, config=config)
        
#         add_processing_step("Processing response...", True)

#         # Extract and pretty print the last message
#         if result and 'messages' in result and result['messages']:
#             last_message = result['messages'][-1]
            
#             # Use pretty_print() if available
#             with io.StringIO() as buf, contextlib.redirect_stdout(buf):
#                 try:
#                     last_message.pretty_print()  # captures the pretty output
#                     response = buf.getvalue()
#                 except Exception:
#                     response = getattr(last_message, "content", str(last_message))
#         else:
#             response = "🤖 I received your message but couldn't generate a proper response."

#         add_processing_step("Response ready!", True)
#         return response

#     except Exception as e:
#         add_processing_step(f"Error: {str(e)}", True)
#         return f"❌ Error processing your request: {str(e)}"


# def strip_html_tags(text: str) -> str:
#     """Remove HTML tags from the given text."""
#     return re.sub(r'<[^>]+>', '', text)

# def display_chat_history():
#     """Display the chat history in a clean, markdown-friendly way."""
#     for message in st.session_state.conversation_history:
#         if message["role"] == "user":
#             st.markdown(f"""
#             <div class="user-message">
#                 <strong>You:</strong> {message["content"]}
#             </div>
#             """, unsafe_allow_html=True)
#         else:
#             # Use markdown rendering for assistant message to avoid broken HTML
#             clean_content = message["content"].strip()

#             # Optional: uncomment below to strip all HTML if pretty_print ever outputs it
#             # clean_content = strip_html_tags(clean_content)

#             # Render using markdown block
#             st.markdown(f"**🔧 Assistant:**\n\n{clean_content}", unsafe_allow_html=False)

# def main():
#     """Main Streamlit application"""
#     init_session_state()
    
#     # Header
#     st.markdown("""
#     <div class="main-header">
#         <h1>🔧 SAP Maintenance Assistant</h1>
#         <p>AI-powered maintenance notification and technical object management</p>
#     </div>
#     """, unsafe_allow_html=True)
    
#     # Sidebar
#     with st.sidebar:
#         st.header("📊 Dashboard")
        
#         # System status
#         if st.session_state.system_initialized:
#             st.markdown('<span class="status-indicator status-online"></span>**System Status:** Online', unsafe_allow_html=True)
#         else:
#             st.markdown('<span class="status-indicator status-offline"></span>**System Status:** Offline', unsafe_allow_html=True)
        
#         st.markdown("---")
        
#         # Chat statistics
#         col1, col2 = st.columns(2)
#         with col1:
#             st.markdown(f"""
#             <div class="metric-card">
#                 <h3>{len(st.session_state.conversation_history)}</h3>
#                 <p>Total Messages</p>
#             </div>
#             """, unsafe_allow_html=True)
        
#         with col2:
#             user_messages = len([m for m in st.session_state.conversation_history if m["role"] == "user"])
#             st.markdown(f"""
#             <div class="metric-card">
#                 <h3>{user_messages}</h3>
#                 <p>User Queries</p>
#             </div>
#             """, unsafe_allow_html=True)
        
#         st.markdown("---")
        
#         # Control buttons
#         if st.button("🗑️ Clear Chat", use_container_width=True):
#             st.session_state.conversation_history = []
#             clear_processing_steps()
#             st.rerun()
        
#         if st.button("🔄 Reinitialize System", use_container_width=True):
#             st.session_state.system_initialized = False
#             st.session_state.graph = None
#             st.rerun()
        
#         st.markdown("---")
        
#         # About section
#         with st.expander("ℹ️ About"):
#             st.markdown("""
#             **SAP Maintenance Assistant** is an AI-powered tool that helps with:
            
#             - 🔍 Retrieving technical objects
#             - 📋 Managing maintenance notifications
#             - 🛠️ Equipment troubleshooting
#             - 📊 System monitoring
            
#             Built with LangGraph and SAP AI Core integration.
#             """)
    
#     # Main content area
#     col1, col2 = st.columns([3, 1])
    
#     with col1:
#         st.subheader("💬 Chat Interface")
        
#         # Initialize system if not already done
#         if not st.session_state.system_initialized:
#             if st.button("🚀 Initialize SAP Connection", type="primary", use_container_width=True):
#                 initialize_system()
#                 st.rerun()
#         else:
#             # Chat container
#             chat_container = st.container()
#             with chat_container:
#                 display_chat_history()
            
#             # Processing steps (only show if there are any)
#             if st.session_state.processing_steps:
#                 display_processing_steps()
            
#             # Chat input
#             user_input = st.chat_input("Ask about maintenance, technical objects, or notifications...")
            
#             if user_input:
#                 # Add user message to history
#                 st.session_state.conversation_history.append({
#                     "role": "user", 
#                     "content": user_input,
#                     "timestamp": datetime.now()
#                 })
                
#                 # Process the message
#                 with st.spinner("🤖 Processing your request..."):
#                     response = process_message(user_input)
                
#                 # Add assistant response to history
#                 st.session_state.conversation_history.append({
#                     "role": "assistant", 
#                     "content": response,
#                     "timestamp": datetime.now()
#                 })
                
#                 # Clear processing steps after completion
#                 time.sleep(1)  # Brief pause to show completion
#                 clear_processing_steps()
                
#                 # Rerun to update the display
#                 st.rerun()


# if __name__ == "__main__":
#     main()


import streamlit as st
import sys
import os
import json
import requests
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
import io
import contextlib
import re

# NEW: Additional imports for the JSON viewer component
import uuid
import streamlit.components.v1 as components

# Import your existing modules
try:
    from tools.openNotifications import get_notifications
    from tools.Retriever_technical_objects import retrieve_and_query_llm
    from tools.createNotification import post_notification
    from langgraph.graph import StateGraph, START, END
    from langgraph.prebuilt import ToolNode
    from langgraph.graph.message import add_messages
    from typing import Annotated
    from langgraph.checkpoint.memory import MemorySaver
    from typing_extensions import TypedDict
    from langgraph.prebuilt import tools_condition
    from dotenv import load_dotenv
    from gen_ai_hub.proxy.native.openai import chat
    from gen_ai_hub.proxy.langchain.openai import OpenAIEmbeddings, ChatOpenAI
    from gen_ai_hub.proxy.core.proxy_clients import get_proxy_client
except ImportError as e:
    st.error(f"Missing dependencies: {e}")
    st.stop()

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="SAP Maintenance Assistant",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for modern chat interface
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 1rem 0;
        background: linear-gradient(90deg, #1f4e79 0%, #2d5aa0 100%);
        color: white;
        margin: -1rem -1rem 2rem -1rem;
        border-radius: 0 0 10px 10px;
    }
    .chat-container {
        max-height: 500px;
        overflow-y: auto;
        padding: 1rem;
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        margin-bottom: 1rem;
        background: #fafafa;
    }
    .user-message {
        background: #007acc;
        color: white;
        padding: 0.75rem 1rem;
        border-radius: 15px 15px 5px 15px;
        margin: 0.5rem 0 0.5rem auto;
        max-width: 80%;
        word-wrap: break-word;
    }
    .assistant-message {
        background: white;
        color: #333;
        padding: 0.75rem 1rem;
        border-radius: 15px 15px 15px 5px;
        margin: 0.5rem auto 0.5rem 0;
        max-width: 80%;
        border: 1px solid #e0e0e0;
        word-wrap: break-word;
    }
    .system-message {
        background: #f0f8ff;
        color: #555;
        padding: 0.5rem 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        border-left: 4px solid #007acc;
        font-style: italic;
    }
    .thinking-process {
        background: #fff3cd;
        border: 1px solid #ffeaa7;
        border-radius: 8px;
        padding: 0.75rem;
        margin: 0.5rem 0;
    }
    .processing-step {
        display: flex;
        align-items: center;
        margin: 0.25rem 0;
    }
    .spinner {
        width: 16px;
        height: 16px;
        border: 2px solid #f3f3f3;
        border-top: 2px solid #007acc;
        border-radius: 50%;
        animation: spin 1s linear infinite;
        margin-right: 0.5rem;
    }
    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid #e0e0e0;
        text-align: center;
    }
    .status-indicator {
        width: 12px;
        height: 12px;
        border-radius: 50%;
        display: inline-block;
        margin-right: 0.5rem;
    }
    .status-online { background-color: #28a745; }
    .status-offline { background-color: #dc3545; }
</style>
""", unsafe_allow_html=True)

# <<< --- NEW CODE START --- >>>

def is_json(myjson: str) -> bool:
    """Checks if a string is valid JSON."""
    try:
        json.loads(myjson)
    except (ValueError, TypeError, json.JSONDecodeError):
        return False
    return True

def st_display_json(json_data: Any):
    """
    Displays a JSON object or string in a formatted, copyable block.
    
    Args:
        json_data: A JSON string or a Python object (dict, list).
    """
    if isinstance(json_data, str):
        try:
            data = json.loads(json_data)
        except json.JSONDecodeError:
            st.code(json_data, language='text')
            return
    else:
        data = json_data

    json_string = json.dumps(data, indent=2, ensure_ascii=False)
    unique_id = uuid.uuid4().hex
    code_id = f"json-code-{unique_id}"
    button_id = f"copy-button-{unique_id}"

    html_content = f"""
    <div style="position: relative; border: 1px solid #333; border-radius: 8px; background-color: #0e1117;">
        <button id="{button_id}" title="Copy JSON to clipboard" style="position: absolute; top: 8px; right: 8px; background: #263849; color: #fff; border: 1px solid #445869; border-radius: 5px; cursor: pointer; padding: 4px 8px; font-size: 12px;">
            📋 Copy
        </button>
        <pre style="padding: 1.5rem 1rem 1rem 1rem; margin: 0; white-space: pre-wrap; word-wrap: break-word; color: #fff;"><code id="{code_id}">{json_string}</code></pre>
    </div>
    <script>
    document.getElementById("{button_id}").addEventListener("click", function() {{
        const textToCopy = document.getElementById("{code_id}").innerText;
        navigator.clipboard.writeText(textToCopy).then(() => {{
            const button = document.getElementById("{button_id}");
            button.innerText = "✅ Copied!";
            setTimeout(() => {{ button.innerText = "📋 Copy"; }}, 2000);
        }}, (err) => {{
            console.error("Failed to copy: ", err);
        }});
    }});
    </script>
    """
    components.html(html_content, height=300, scrolling=True)

# <<< --- NEW CODE END --- >>>

# Initialize session state
def init_session_state():
    """Initialize session state variables"""
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    if 'conversation_history' not in st.session_state:
        st.session_state.conversation_history = []
    if 'system_initialized' not in st.session_state:
        st.session_state.system_initialized = False
    if 'graph' not in st.session_state:
        st.session_state.graph = None
    if 'processing_steps' not in st.session_state:
        st.session_state.processing_steps = []

class State(TypedDict):
    messages: Annotated[list, add_messages]

def initialize_system():
    """Initialize the SAP system connection and LangGraph"""
    try:
        with st.spinner("🔄 Initializing SAP AI Core connection..."):
            # Environment variables
            HANA_HOST = os.getenv("HANA_HOST")
            HANA_USER_DB = os.getenv("HANA_USER")
            HANA_PASSWORD_VDB = os.getenv("HANA_PASSWORD")
            
            AICORE_AUTH_URL = os.getenv("AICORE_AUTH_URL")
            AICORE_CLIENT_ID = os.getenv("AICORE_CLIENT_ID")
            AICORE_CLIENT_SECRET = os.getenv("AICORE_CLIENT_SECRET")
            AICORE_BASE_URL = os.getenv("AICORE_BASE_URL")
            
            if not all([AICORE_AUTH_URL, AICORE_CLIENT_ID, AICORE_CLIENT_SECRET, AICORE_BASE_URL]):
                st.error("❌ Missing required environment variables for SAP AI Core")
                return None
            
            # Get Access Token from SAP BTP AI Core
            params = {"grant_type": "client_credentials"}
            resp = requests.post(
                f"{AICORE_AUTH_URL}/oauth/token",
                auth=(AICORE_CLIENT_ID, AICORE_CLIENT_SECRET),
                params=params
            )
            
            if resp.status_code != 200:
                st.error(f"❌ Failed to authenticate with SAP AI Core: {resp.status_code}")
                return None
                
            access_token = resp.json()["access_token"]
            
            # Update environment
            os.environ.update({
                "AICORE_AUTH_URL": AICORE_AUTH_URL,
                "AICORE_CLIENT_ID": AICORE_CLIENT_ID,
                "AICORE_CLIENT_SECRET": AICORE_CLIENT_SECRET,
                "AICORE_RESOURCE_GROUP": os.getenv("AICORE_RESOURCE_GROUP", "default"),
                "AICORE_BASE_URL": AICORE_BASE_URL
            })
            
            # Initialize GenAI Hub components
            proxy_client = get_proxy_client('gen-ai-hub')
            llm = ChatOpenAI(proxy_model_name='gpt-4o', proxy_client=proxy_client, temperature=0.0)
            
            # Define tools
            def retrieveTechnicalObjects(
                query: str,
                plant: str = "",
                functional_location: str = "",
                equipment: str = "",
                assembly: str = ""
            ) -> str:
                """Retrieve and recommend technical objects from SAP HANA based on the malfunction query and optional conditions."""
                condn = {
                    "plant": plant,
                    "functional_location": functional_location,
                    "equipment": equipment,
                    "assembly": assembly
                }
                return retrieve_and_query_llm(query, condn)

            def openNotifications(TechnicalObjectLabel: str) -> str:
                """Tool function to get open notifications from SAP system based on TechnicalObjectLabel."""
                message, data = get_notifications(TechnicalObjectLabel)
                return f"{message}\n\n{data if data else ''}"

            def createNotification(
                NotificationText: str,
                NotificationType: str,
                MainWorkCenter: str,
                MaintenancePlanningPlant: str
            ) -> str:
                """Tool function to create the Notifications from SAP system."""
                payload = {
                    "NotificationText": NotificationText,
                    "NotificationType": NotificationType,
                    "MainWorkCenter": MainWorkCenter,
                    "MaintenancePlanningPlant": MaintenancePlanningPlant
                }
                result = post_notification(payload)
                return json.dumps(result)

            def multiply(a: int, b: int) -> int:
                """Multiply a and b (utility function)"""
                return a * b

            tools = [multiply, openNotifications, retrieveTechnicalObjects, createNotification]
            llm_with_tools = llm.bind_tools(tools)
            
            # Memory agent
            memory = MemorySaver()
            
            def tool_calling_llm(state: State):
                response = llm_with_tools.invoke(state["messages"])
                return {"messages": state["messages"] + [response]}
            
            # Build graph
            builder = StateGraph(State)
            builder.add_node("supervisor", tool_calling_llm)
            builder.add_node("tools", ToolNode(tools))
            
            builder.add_edge(START, "supervisor")
            builder.add_conditional_edges("supervisor", tools_condition)
            builder.add_edge("tools", END)
            
            graph = builder.compile(checkpointer=memory)
            
            st.session_state.graph = graph
            st.session_state.system_initialized = True
            st.success("✅ SAP Maintenance Assistant initialized successfully!")
            return graph
            
    except Exception as e:
        st.error(f"❌ System initialization failed: {str(e)}")
        return None

def add_processing_step(step: str, is_complete: bool = False):
    """Add a processing step to the current operation"""
    st.session_state.processing_steps.append({
        'step': step,
        'complete': is_complete,
        'timestamp': datetime.now()
    })

def clear_processing_steps():
    """Clear all processing steps"""
    st.session_state.processing_steps = []

def display_processing_steps():
    """Display current processing steps"""
    if st.session_state.processing_steps:
        with st.expander("🔄 Processing Steps", expanded=True):
            for step_info in st.session_state.processing_steps:
                if step_info['complete']:
                    st.markdown(f"✅ {step_info['step']}")
                else:
                    st.markdown(f"""
                    <div class="processing-step">
                        <div class="spinner"></div>
                        {step_info['step']}
                    </div>
                    """, unsafe_allow_html=True)

def process_message(user_input: str) -> str:
    """Process user message through the LangGraph system with pretty-printed response."""
    if not st.session_state.system_initialized or not st.session_state.graph:
        return "❌ System not initialized. Please check your configuration."
    
    try:
        clear_processing_steps()
        add_processing_step("Analyzing user query...")
        
        config = {"configurable": {"thread_id": "streamlit_session"}}
        
        add_processing_step("Invoking AI assistant...")
        
        result = st.session_state.graph.invoke({"messages": [user_input]}, config=config)
        
        add_processing_step("Processing response...", True)

        if result and 'messages' in result and result['messages']:
            last_message = result['messages'][-1]
            
            with io.StringIO() as buf, contextlib.redirect_stdout(buf):
                try:
                    last_message.pretty_print()
                    response = buf.getvalue()
                except Exception:
                    response = getattr(last_message, "content", str(last_message))
        else:
            response = "🤖 I received your message but couldn't generate a proper response."

        add_processing_step("Response ready!", True)
        return response

    except Exception as e:
        add_processing_step(f"Error: {str(e)}", True)
        return f"❌ Error processing your request: {str(e)}"

def strip_html_tags(text: str) -> str:
    """Remove HTML tags from the given text."""
    return re.sub(r'<[^>]+>', '', text)

# <<< --- MODIFIED FUNCTION START --- >>>

def display_chat_history():
    """Display the chat history, rendering JSON content with a special viewer."""
    for message in st.session_state.conversation_history:
        if message["role"] == "user":
            st.markdown(f"""
            <div class="user-message">
                <strong>You:</strong> {message["content"]}
            </div>
            """, unsafe_allow_html=True)
        else:  # Assistant message
            clean_content = message["content"].strip()
            
            # Use regex to find a JSON object or array within the response string.
            json_match = re.search(r'(\[.*\]|\{.*\})', clean_content, re.DOTALL)
            
            if json_match and is_json(json_match.group(1)):
                json_string = json_match.group(1)
                st.markdown("**🔧 Assistant (Tool Output):**")
                st_display_json(json_string)  # Use our new component
            else:
                # Fallback for non-JSON or plain text messages
                st.markdown(f"**🔧 Assistant:**\n{clean_content}", unsafe_allow_html=False)

# <<< --- MODIFIED FUNCTION END --- >>>

def main():
    """Main Streamlit application"""
    init_session_state()
    
    st.markdown("""
    <div class="main-header">
        <h1>🔧 SAP Maintenance Assistant</h1>
        <p>AI-powered maintenance notification and technical object management</p>
    </div>
    """, unsafe_allow_html=True)
    
    with st.sidebar:
        st.header("📊 Dashboard")
        
        if st.session_state.system_initialized:
            st.markdown('<span class="status-indicator status-online"></span>**System Status:** Online', unsafe_allow_html=True)
        else:
            st.markdown('<span class="status-indicator status-offline"></span>**System Status:** Offline', unsafe_allow_html=True)
        
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <h3>{len(st.session_state.conversation_history)}</h3>
                <p>Total Messages</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            user_messages = len([m for m in st.session_state.conversation_history if m["role"] == "user"])
            st.markdown(f"""
            <div class="metric-card">
                <h3>{user_messages}</h3>
                <p>User Queries</p>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        if st.button("🗑️ Clear Chat", use_container_width=True):
            st.session_state.conversation_history = []
            clear_processing_steps()
            st.rerun()
        
        if st.button("🔄 Reinitialize System", use_container_width=True):
            st.session_state.system_initialized = False
            st.session_state.graph = None
            st.rerun()
        
        st.markdown("---")
        
        with st.expander("ℹ️ About"):
            st.markdown("""
            **SAP Maintenance Assistant** is an AI-powered tool that helps with:
            - 🔍 Retrieving technical objects
            - 📋 Managing maintenance notifications
            - 🛠️ Equipment troubleshooting
            - 📊 System monitoring
            
            Built with LangGraph and SAP AI Core integration.
            """)
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.subheader("💬 Chat Interface")
        
        if not st.session_state.system_initialized:
            if st.button("🚀 Initialize SAP Connection", type="primary", use_container_width=True):
                initialize_system()
                st.rerun()
        else:
            chat_container = st.container()
            with chat_container:
                display_chat_history()
            
            if st.session_state.processing_steps:
                display_processing_steps()
            
            user_input = st.chat_input("Ask about maintenance, technical objects, or notifications...")
            
            if user_input:
                st.session_state.conversation_history.append({
                    "role": "user", 
                    "content": user_input,
                    "timestamp": datetime.now()
                })
                
                with st.spinner("🤖 Processing your request..."):
                    response = process_message(user_input)
                
                st.session_state.conversation_history.append({
                    "role": "assistant", 
                    "content": response,
                    "timestamp": datetime.now()
                })
                
                time.sleep(1)
                clear_processing_steps()
                st.rerun()

if __name__ == "__main__":
    main()