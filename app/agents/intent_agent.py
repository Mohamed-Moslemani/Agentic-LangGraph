from typing import Dict, Any
from langgraph.graph import MessagesState
from llm.model import get_llm

# Initialize model
LLM = get_llm()

def intent_llm_agent(state: MessagesState) -> Dict[str, Any]:

    messages = state["messages"]
    user_input = messages[-1].content

    # Ask the model to classify intent
    prompt = (
        f"Classify the user request into one of the following intents:\n"
        f" - change_pin\n - view_card\n - create_card\n - stop_card\n - end\n\n"
        f"User message: {user_input}\n"
        f"Answer ONLY with one of these labels."
    )
    ai_msg = LLM.invoke(prompt)

    intent = ai_msg.content.strip().lower()
    state["intent"] = intent
    return {"messages": messages + [ai_msg], "intent": intent}


def route_intent(state: MessagesState) -> str:
    """
    Routes based on the detected intent.
    """
    intent = state.get("intent", "")
    if "pin" in intent:
        return "change_pin"
    if "view" in intent or "details" in intent:
        return "view_card"
    if "create" in intent or "issue" in intent:
        return "create_card"
    if "stop" in intent or "block" in intent or "delete" in intent:
        return "stop_card"
    return "end"
