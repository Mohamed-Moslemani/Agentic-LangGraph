import os
from langchain_ollama import ChatOllama

def get_llm():
    """
    Central LLM for the card assistant.
    Uses Ollama local model (default: gpt-oss:latest).
    Requires OLLAMA_BASE_URL in environment (e.g. http://localhost:11434).
    """
    model = os.getenv("LLM_MODEL", "gpt-oss:latest")
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

    return ChatOllama(
        model=model,
        base_url=base_url,
        temperature=0,
    )
