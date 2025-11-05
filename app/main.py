
from app.graph.build_graph import build_graph
from app.memory.checkpoint import get_checkpointer

def main():
    builder = build_graph()
    checkpointer = get_checkpointer()

    app = builder.compile(checkpointer=checkpointer)

    # Example user chat
    config = {"configurable": {"thread_id": "user_123"}}

    # User wants to change their PIN
    inputs = {
        "messages": [
            {"role": "user", "content": "I want to change the PIN of my card token XYZ for client 1001 to 1234"}
        ]
    }

    for event in app.stream(inputs, config=config, stream_mode="values"):
        print("STEP:", event)

    

if __name__ == "__main__":
    main()
