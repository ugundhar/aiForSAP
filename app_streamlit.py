import streamlit as st
import time
import json
import uuid
from typing import List, Dict, Any
import traceback
from datetime import datetime

# Import backend components
from backend import graph, config as default_config

# Page configuration
st.set_page_config(
    page_title="SAP AI Assistant",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for ChatGPT-style interface
st.markdown("""
<style>
    .chat-container {
        max-width: 800px;
        margin: 0 auto;
        padding: 20px;
    }
    
    .user-message {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 12px 16px;
        border-radius: 18px 18px 4px 18px;
        margin: 8px 0 8px 60px;
        word-wrap: break-word;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .assistant-message {
        background: #f1f3f4;
        color: #333;
        padding: 12px 16px;
        border-radius: 18px 18px 18px 4px;
        margin: 8px 60px 8px 0;
        word-wrap: break-word;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .thinking-indicator {
        background: #f1f3f4;
        padding: 12px 16px;
        border-radius: 18px;
        margin: 8px 60px 8px 0;
        font-style: italic;
        color: #666;
        animation: pulse 1.5s infinite;
    }
    
    @keyframes pulse {
        0% { opacity: 0.6; }
        50% { opacity: 1; }
        100% { opacity: 0.6; }
    }
    
    .tool-call {
        background: #e8f4f8;
        border-left: 4px solid #1f77b4;
        padding: 10px;
        margin: 8px 0;
        border-radius: 4px;
        font-family: 'Courier New', monospace;
        font-size: 0.9em;
    }
    
    .error-message {
        background: #ffebee;
        color: #c62828;
        border-left: 4px solid #f44336;
        padding: 12px;
        margin: 8px 0;
        border-radius: 4px;
    }
    
    .session-info {
        background: #f8f9fa;
        padding: 12px;
        border-radius: 8px;
        margin: 10px 0;
        border: 1px solid #dee2e6;
    }
    
    .stButton > button {
        width: 100%;
        border-radius: 8px;
        border: none;
        padding: 8px 16px;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)

def initialize_session_state():
    """Initialize session state variables"""
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    
    if 'thread_id' not in st.session_state:
        st.session_state.thread_id = str(uuid.uuid4())
    
    if 'is_thinking' not in st.session_state:
        st.session_state.is_thinking = False

def clear_chat():
    """Clear chat history and reset session"""
    st.session_state.messages = []
    st.session_state.thread_id = str(uuid.uuid4())
    st.session_state.is_thinking = False
    st.rerun()

def format_message_content(content: Any) -> str:
    """Format message content for display"""
    if isinstance(content, dict):
        return f"```json\n{json.dumps(content, indent=2)}\n```"
    elif isinstance(content, list):
        return f"```json\n{json.dumps(content, indent=2)}\n```"
    else:
        return str(content)

def display_message(message: Dict[str, Any], is_user: bool = False):
    """Display a single message with proper styling"""
    if is_user:
        st.markdown(f'<div class="user-message">{message["content"]}</div>', 
                   unsafe_allow_html=True)
    else:
        # Handle different message types
        if message.get("type") == "ai":
            content = format_message_content(message.get("content", ""))
            st.markdown(f'<div class="assistant-message">{content}</div>', 
                       unsafe_allow_html=True)
        elif message.get("type") == "tool":
            # Display tool calls in a special format
            tool_name = message.get("name", "Unknown Tool")
            tool_content = message.get("content", "")
            st.markdown(f'<div class="tool-call"><strong>🔧 {tool_name}</strong><br>{tool_content}</div>', 
                       unsafe_allow_html=True)
        else:
            # Default message display
            content = format_message_content(message.get("content", ""))
            st.markdown(f'<div class="assistant-message">{content}</div>', 
                       unsafe_allow_html=True)

def display_thinking_indicator():
    """Display thinking indicator"""
    st.markdown('<div class="thinking-indicator">🤔 Assistant is thinking...</div>', 
               unsafe_allow_html=True)

def process_graph_response(messages: List[str]) -> List[Dict[str, Any]]:
    """Process messages from LangGraph response"""
    processed_messages = []
    
    for msg in messages:
        try:
            # Handle different message types from LangGraph
            if hasattr(msg, 'content'):
                processed_messages.append({
                    "content": msg.content,
                    "type": getattr(msg, 'type', 'ai'),
                    "name": getattr(msg, 'name', None),
                    "timestamp": datetime.now().isoformat()
                })
            else:
                processed_messages.append({
                    "content": str(msg),
                    "type": "ai",
                    "timestamp": datetime.now().isoformat()
                })
        except Exception as e:
            st.error(f"Error processing message: {str(e)}")
            continue
    
    return processed_messages

def invoke_graph(user_input: str) -> List[Dict[str, Any]]:
    """Invoke the LangGraph with user input"""
    try:
        # Prepare messages for graph
        graph_messages = [user_input]
        
        # Add conversation history for context
        for msg in st.session_state.messages:
            if msg.get("is_user"):
                graph_messages.append(msg["content"])
            else:
                graph_messages.append(msg["content"])
        
        # Configure graph with thread ID
        config = {"configurable": {"thread_id": st.session_state.thread_id}}
        
        # Invoke graph
        result = graph.invoke({"messages": graph_messages}, config=config)
        
        # Process and return messages
        return process_graph_response(result.get("messages", []))
        
    except Exception as e:
        st.error(f"Graph invocation failed: {str(e)}")
        st.error("Please check your backend configuration and try again.")
        print(f"Graph error: {traceback.format_exc()}")
        return []

def render_sidebar():
    """Render sidebar with controls and information"""
    with st.sidebar:
        st.title("🤖 SAP AI Assistant")
        st.markdown("---")
        
        # Clear chat button
        if st.button("🗑️ Clear Chat", use_container_width=True):
            clear_chat()
        
        st.markdown("---")
        
        # Session information
        st.markdown("### 📊 Session Info")
        st.markdown(f"""
        <div class="session-info">
            <strong>Thread ID:</strong> {st.session_state.thread_id[:8]}...<br>
            <strong>Messages:</strong> {len(st.session_state.messages)}<br>
            <strong>Status:</strong> {'🤔 Thinking' if st.session_state.is_thinking else '✅ Ready'}
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Available tools
        st.markdown("### 🔧 Available Tools")
        tools_info = [
            {
                "name": "retrieveTechnicalObjects",
                "description": "Retrieve and recommend technical objects from SAP HANA based on malfunction queries",
                "icon": "🔍"
            },
            {
                "name": "openNotifications",
                "description": "Get open notifications from SAP system based on technical object labels",
                "icon": "📢"
            },
            {
                "name": "multiply",
                "description": "Multiply two integers (demo tool)",
                "icon": "✖️"
            }
        ]
        
        for tool in tools_info:
            st.markdown(f"""
            **{tool['icon']} {tool['name']}**  
            {tool['description']}
            """)
        
        st.markdown("---")
        
        # About section
        st.markdown("### ℹ️ About")
        st.markdown("""
        **SAP BTP AI Core Integration**
        
        This assistant is powered by:
        - **LangGraph** for multi-agent orchestration
        - **SAP BTP AI Core** for LLM access
        - **GenAI Hub** for model management
        - **SAP HANA** for technical object retrieval
        
        The assistant can help with:
        - Technical object recommendations
        - Notification management
        - Maintenance troubleshooting
        """)
        
        # Flow diagram (if available)
        try:
            st.markdown("### 📊 Agent Flow")
            st.image("flow1.png", caption="LangGraph Flow Diagram", use_column_width=True)
        except:
            st.markdown("*Flow diagram not available*")

def main():
    """Main application function"""
    initialize_session_state()
    
    # Render sidebar
    render_sidebar()
    
    # Main chat interface
    st.title("💬 SAP AI Assistant")
    st.markdown("Ask me about technical objects, notifications, or maintenance issues!")
    
    # Chat container
    chat_container = st.container()
    
    with chat_container:
        # Display chat history
        for message in st.session_state.messages:
            display_message(message, is_user=message.get("is_user", False))
        
        # Display thinking indicator if processing
        if st.session_state.is_thinking:
            display_thinking_indicator()
    
    # Chat input
    user_input = st.chat_input("Type your message here...", key="chat_input")
    
    if user_input:
        # Add user message to history
        user_message = {
            "content": user_input,
            "is_user": True,
            "timestamp": datetime.now().isoformat()
        }
        st.session_state.messages.append(user_message)
        
        # Set thinking state
        st.session_state.is_thinking = True
        st.rerun()
    
    # Process user input if thinking
    if st.session_state.is_thinking and st.session_state.messages:
        last_message = st.session_state.messages[-1]
        
        if last_message.get("is_user"):
            # Get response from graph
            response_messages = invoke_graph(last_message["content"])
            
            # Add response messages to history
            for response_msg in response_messages:
                if response_msg.get("content"):  # Only add non-empty responses
                    st.session_state.messages.append(response_msg)
            
            # If no response, add a default message
            if not response_messages:
                st.session_state.messages.append({
                    "content": "I'm sorry, I encountered an issue processing your request. Please try again.",
                    "type": "ai",
                    "timestamp": datetime.now().isoformat()
                })
            
            # Clear thinking state
            st.session_state.is_thinking = False
            st.rerun()

if __name__ == "__main__":
    main()