from typing import Dict, Any

from langgraph.graph import MessagesState
from langgraph.prebuilt import ToolNode

from app.llm.model import get_llm
from app.tools.mcp_tools import (
    change_pin_tool,
    view_card_details_tool,
    create_card_tool,
    stop_card_tool,
)

# 1) Collect the tools
TOOLS = [
    change_pin_tool,
    view_card_details_tool,
    create_card_tool,
    stop_card_tool,
]

# 2) LLM bound to these tools (function calling)
LLM = get_llm().bind_tools(TOOLS)

# 3) Node: LLM agent
def card_llm_agent(state: MessagesState) -> Dict[str, Any]:
    """
    Core LLM node: takes messages, returns one more AI message
    that may or may not include tool_calls.
    """
    messages = state["messages"]
    ai_msg = LLM.invoke(messages)
    return {"messages": messages + [ai_msg]}

# 4) Tool node: actually runs the MCP tools for any tool_calls
tool_node = ToolNode(TOOLS)


def route_after_llm(state: MessagesState) -> str:
    """
    Decide whether to go to tools or end.
    If the last AI message has tool_calls, run the tools, else stop.
    """
    last = state["messages"][-1]
    # langchain's AIMessage has .tool_calls for function calling
    tool_calls = getattr(last, "tool_calls", None)
    if tool_calls:
        return "tools"
    return "end"
