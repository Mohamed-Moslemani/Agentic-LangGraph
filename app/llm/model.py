import os
from langchain_ollama import ChatOllama

def get_llm():

    model = os.getenv("LLM_MODEL", "gpt-oss:latest")
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

    return ChatOllama(
        model=model,
        base_url=base_url,
        temperature=0,
    )
