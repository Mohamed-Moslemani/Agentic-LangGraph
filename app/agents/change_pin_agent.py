from typing import Dict, Any
from langgraph.graph import MessagesState
from langgraph.prebuilt import ToolNode

from llm.model import get_llm
from tools.mcp_tools import change_pin_tool

TOOLS = [change_pin_tool]
LLM = get_llm().bind_tools(TOOLS)

def change_pin_llm_agent(state: MessagesState) -> Dict[str, Any]:
    """
    Agent that handles PIN change requests.
    """
    messages = state["messages"]
    ai_msg = LLM.invoke(messages)
    return {"messages": messages + [ai_msg]}

tool_node = ToolNode(TOOLS)

def route_after_llm(state: MessagesState) -> str:
    """
    Go to tools if the LLM called one, otherwise end.
    """
    last = state["messages"][-1]
    tool_calls = getattr(last, "tool_calls", None)
    if tool_calls:
        return "tools"
    return "end"
