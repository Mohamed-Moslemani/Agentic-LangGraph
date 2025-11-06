from typing import Dict, Any
from langgraph.graph import MessagesState
try:
    from langgraph.prebuilt import ToolNode
except ImportError:
    from langgraph.prebuilt.tool import ToolNode  

from llm.model import get_llm
from tools.mcp_tools import create_card_tool

TOOLS = [create_card_tool]
LLM = get_llm().bind_tools(TOOLS)

def create_card_llm_agent(state: MessagesState) -> Dict[str, Any]:
    """
    Agent responsible for card creation requests.
    """
    messages = state["messages"]
    ai_msg = LLM.invoke(messages)
    return {"messages": messages + [ai_msg]}

tool_node = ToolNode(TOOLS)

def route_after_llm(state: MessagesState) -> str:
    last = state["messages"][-1]
    tool_calls = getattr(last, "tool_calls", None)
    if tool_calls:
        return "tools"
    return "end"
