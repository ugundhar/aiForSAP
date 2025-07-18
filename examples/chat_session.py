import sys
import os

# Dynamically add the project root directory to sys.path
current_file_path = os.path.abspath(__file__)
project_root = os.path.abspath(os.path.join(current_file_path, "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Now you can import from src
from typing import TypedDict, Annotated, List, Literal
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver


from langgraph.graph import StateGraph, END, MessagesState
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver

from src.llm.gpt_client import chat_llm
from tools.openNotifications import get_notifications



from typing import TypedDict, Annotated, List, Literal

## Definine state

class AgentState(MessagesState):
    next_agent:str #which agent should go next


## create the simple tools
# Create simple tools
@tool
def get_notification(query: str) -> str:
    """get Open notificatoins """
    # use get notification tool
    search = get_notifications(max_results=3)
    results = search.invoke(query)
    return str(results)

    #
# Define agent functions (simpler approach)
def get_open_notification_agent(state: AgentState):
    """get all the open notificatoin for information"""
    
    messages = state["messages"]
    
    # Add system message for context
    system_msg = SystemMessage(content="You are a getting open notificatoin agent. Use the get_notification tool to to get all the open notificaiton information for  the user's request.")
    
    # Call LLM with tools
    researcher_llm = chat_llm.bind_tools([get_notification])
    response = researcher_llm.invoke([system_msg] + messages)
    
    # Return the response and route to writer
    return {
        "messages": [response],
        "next_agent": "writer"
    }

    """notification agent that creates notificatoin"""
    
    messages = state["messages"]
    
    # Add system message
    system_msg = SystemMessage(content="You are a notificaiton creation agent.create the notification based on the user query")
    
    # Simple completion without tools
    response = chat_llm.invoke([system_msg] + messages)
    
    return {
        "messages": [response],
        "next_agent": "end"
    }
# Tool executor node
def execute_tools(state: AgentState):
    """Execute any pending tool calls"""
    messages = state["messages"]
    last_message = messages[-1]
    
    # Check if there are tool calls to execute
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        # Create tool node and execute
        tool_node = ToolNode([open_notification_agent, create_notification_agent])
        response = tool_node.invoke(state)
        return response
    
    # No tools to execute
    return state
# Build graph
workflow = StateGraph(AgentState)

# Add nodes
workflow.add_node("get open notifications", open_notification_agent)
workflow.add_node("create open notificatoins", create_notification_agent)

# Set flow
workflow.set_entry_point("get open notifications")
workflow.add_edge("get open notifications", "create open notificatoins")
workflow.add_edge("wcreate open notificatoins", END)

# Compile graph
final_workflow = workflow.compile()
png_data = final_workflow.get_graph().draw_mermaid_png()
with open("flow.png", "wb") as f:
    f.write(png_data)

response=final_workflow.invoke({"messages":"Reasearch about the usecase of agentic ai in business"})

print((response["messages"][-1]).content)



































# StateGraph,MessagesState,Literal,List,Annotated,

# BaseMessage,HumanMessage,AIMessage,SystemMessage