import sys
import os
import json
import requests
from typing import Annotated
from typing_extensions import TypedDict

from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from dotenv import load_dotenv

# Import custom tools
from tools.openNotifications import get_notifications
from tools.Retriever_technical_objects import retrieve_and_query_llm

# Load environment variables
load_dotenv()

class Config:
    """Configuration class for environment variables"""
    
    def __init__(self):
        # SAP HANA Configuration
        self.HANA_HOST = os.getenv("HANA_HOST")
        self.HANA_USER_DB = os.getenv("HANA_USER")
        self.HANA_PASSWORD_VDB = os.getenv("HANA_PASSWORD")
        
        # SAP BTP AI Core Configuration
        self.AICORE_AUTH_URL = os.getenv("AICORE_AUTH_URL")
        self.AICORE_CLIENT_ID = os.getenv("AICORE_CLIENT_ID")
        self.AICORE_CLIENT_SECRET = os.getenv("AICORE_CLIENT_SECRET")
        self.AICORE_BASE_URL = os.getenv("AICORE_BASE_URL")
        self.AICORE_RESOURCE_GROUP = os.getenv("AICORE_RESOURCE_GROUP", "default")
        
        # Validate required environment variables
        self._validate_config()
    
    def _validate_config(self):
        """Validate that all required environment variables are set"""
        required_vars = [
            'HANA_HOST', 'HANA_USER_DB', 'HANA_PASSWORD_VDB',
            'AICORE_AUTH_URL', 'AICORE_CLIENT_ID', 'AICORE_CLIENT_SECRET', 'AICORE_BASE_URL'
        ]
        
        missing_vars = [var for var in required_vars if not getattr(self, var)]
        
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

class AICoreLLMClient:
    """Client for SAP BTP AI Core LLM services"""
    
    def __init__(self, config: Config):
        self.config = config
        self.access_token = None
        self.llm = None
        self._initialize_client()
    
    def _get_access_token(self) -> str:
        """Get access token from SAP BTP AI Core"""
        params = {"grant_type": "client_credentials"}
        resp = requests.post(
            f"{self.config.AICORE_AUTH_URL}/oauth/token",
            auth=(self.config.AICORE_CLIENT_ID, self.config.AICORE_CLIENT_SECRET),
            params=params
        )
        
        if resp.status_code != 200:
            raise Exception(f"Failed to get access token: {resp.text}")
        
        return resp.json()["access_token"]
    
    def _initialize_client(self):
        """Initialize the GenAI Hub client and LLM"""
        # Get access token
        self.access_token = self._get_access_token()
        
        # Update environment variables for GenAI Hub
        os.environ.update({
            "AICORE_AUTH_URL": self.config.AICORE_AUTH_URL,
            "AICORE_CLIENT_ID": self.config.AICORE_CLIENT_ID,
            "AICORE_CLIENT_SECRET": self.config.AICORE_CLIENT_SECRET,
            "AICORE_RESOURCE_GROUP": self.config.AICORE_RESOURCE_GROUP,
            "AICORE_BASE_URL": self.config.AICORE_BASE_URL
        })
        
        # Initialize GenAI Hub components
        from gen_ai_hub.proxy.langchain.openai import ChatOpenAI
        from gen_ai_hub.proxy.core.proxy_clients import get_proxy_client
        
        proxy_client = get_proxy_client('gen-ai-hub')
        self.llm = ChatOpenAI(
            proxy_model_name='gpt-4o', 
            proxy_client=proxy_client, 
            temperature=0.0
        )

class State(TypedDict):
    """State definition for LangGraph"""
    messages: Annotated[list, add_messages]

class ToolDefinitions:
    """Tool definitions for the LangGraph agent"""
    
    @staticmethod
    def retrieve_technical_objects(
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
        try:
            return retrieve_and_query_llm(query, condn)
        except Exception as e:
            return f"Error retrieving technical objects: {str(e)}"
    
    @staticmethod
    def open_notifications(technical_object_label: str) -> str:
        """
        Tool function to get open notifications from SAP system based on TechnicalObjectLabel.
        
        Args:
            technical_object_label (str): Label of the technical object
        
        Returns:
            str: Message with notification summary
        """
        try:
            message, data = get_notifications(technical_object_label)
            return f"{message}\n\n{data if data else ''}"
        except Exception as e:
            return f"Error retrieving notifications: {str(e)}"
    
    @staticmethod
    def multiply(a: int, b: int) -> int:
        """
        Multiply two integers (demo tool).
        
        Args:
            a (int): First integer
            b (int): Second integer
        
        Returns:
            int: Product of a and b
        """
        return a * b

class LangGraphAgent:
    """LangGraph agent for SAP AI Assistant"""
    
    def __init__(self, config: Config):
        self.config = config
        self.llm_client = AICoreLLMClient(config)
        self.memory = MemorySaver()
        self.graph = None
        self.tools = []
        self._initialize_graph()
    
    def _initialize_tools(self):
        """Initialize tools for the agent"""
        self.tools = [
            ToolDefinitions.multiply,
            ToolDefinitions.open_notifications,
            ToolDefinitions.retrieve_technical_objects
        ]
    
    def _tool_calling_llm(self, state: State):
        """LLM node with tool calling capability"""
        llm_with_tools = self.llm_client.llm.bind_tools(self.tools)
        response = llm_with_tools.invoke(state["messages"])
        return {"messages": state["messages"] + [response]}
    
    def _initialize_graph(self):
        """Initialize the LangGraph"""
        self._initialize_tools()
        
        # Create state graph
        builder = StateGraph(State)
        
        # Add nodes
        builder.add_node("supervisor", self._tool_calling_llm)
        builder.add_node("tools", ToolNode(self.tools))
        
        # Add edges
        builder.add_edge(START, "supervisor")
        builder.add_conditional_edges("supervisor", tools_condition)
        builder.add_edge("tools", "supervisor")
        
        # Compile graph with memory
        self.graph = builder.compile(checkpointer=self.memory)
    
    def invoke(self, messages: dict, config: dict = None) -> dict:
        """
        Invoke the LangGraph with messages
        
        Args:
            messages (dict): Messages in the format {"messages": [msg1, msg2, ...]}
            config (dict): Configuration including thread_id
        
        Returns:
            dict: Result from graph execution
        """
        if config is None:
            config = {"configurable": {"thread_id": "1"}}
        
        return self.graph.invoke(messages, config=config)
    
    def save_flow_diagram(self, filename: str = "flow1.png"):
        """Save the flow diagram as PNG"""
        try:
            png_image = self.graph.get_graph().draw_mermaid_png()
            with open(filename, "wb") as f:
                f.write(png_image)
            print(f"Flow diagram saved as {filename}")
        except Exception as e:
            print(f"Error saving flow diagram: {str(e)}")

# Initialize the backend components
try:
    config = Config()
    agent = LangGraphAgent(config)
    graph = agent.graph
    
    # Save flow diagram for UI
    agent.save_flow_diagram()
    
    print("Backend initialized successfully!")
    
except Exception as e:
    print(f"Error initializing backend: {str(e)}")
    # Create a dummy graph for development/testing
    graph = None
    config = None