
import langgraph
import langgraph.prebuilt
print("LangGraph path:", langgraph)
print("Prebuilt path:", langgraph.prebuilt.__file__)
print("Has ToolNode:", "ToolNode" in dir(langgraph.prebuilt))
