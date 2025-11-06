from langgraph.graph import StateGraph, START, END, MessagesState
from agents.intent_agent import intent_llm_agent, route_intent
from agents.change_pin_agent import change_pin_llm_agent
from agents.view_card_agent import view_card_llm_agent
from agents.create_card_agent import create_card_llm_agent
from agents.stop_card_agent import stop_card_llm_agent


def build_graph():
    builder = StateGraph(MessagesState)

    # register nodes
    builder.add_node("intent_agent", intent_llm_agent)
    builder.add_node("change_pin_agent", change_pin_llm_agent)
    builder.add_node("view_card_agent", view_card_llm_agent)
    builder.add_node("create_card_agent", create_card_llm_agent)
    builder.add_node("stop_card_agent", stop_card_llm_agent)

    # flow: start → intent agent
    builder.add_edge(START, "intent_agent")

    # conditional branching after intent detection
    builder.add_conditional_edges(
        "intent_agent",
        route_intent,
        {
            "change_pin": "change_pin_agent",
            "view_card": "view_card_agent",
            "create_card": "create_card_agent",
            "stop_card": "stop_card_agent",
            "end": END,
        },
    )

    # optional: let agents loop back if needed
    builder.add_edge("change_pin_agent", "intent_agent")
    builder.add_edge("view_card_agent", "intent_agent")
    builder.add_edge("create_card_agent", "intent_agent")
    builder.add_edge("stop_card_agent", "intent_agent")

    return builder
