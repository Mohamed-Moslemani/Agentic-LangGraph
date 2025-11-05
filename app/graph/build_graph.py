from langgraph.graph import StateGraph, START, END, MessagesState
from app.agents.card_agent import card_llm_agent, tool_node, route_after_llm


def build_graph():
    builder = StateGraph(MessagesState)

    # Nodes
    builder.add_node("card_agent", card_llm_agent)
    builder.add_node("tools", tool_node)

    # Start at LLM
    builder.add_edge(START, "card_agent")

    # Decide whether to call tools or end
    builder.add_conditional_edges(
        "card_agent",
        route_after_llm,
        {
            "tools": "tools",
            "end": END,
        },
    )

    # After tools run, go back to the LLM
    builder.add_edge("tools", "card_agent")

    return builder
