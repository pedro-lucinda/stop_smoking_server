from langchain.chat_models import init_chat_model
from langgraph.prebuilt import create_react_agent

from app.services.ai.checkpointer import build_checkpointer
from app.services.ai.tools import TOOLS

# Singleton agent with persisted memory (module scope)
_model = init_chat_model("gpt-4.1", model_provider="openai")
_checkpointer = build_checkpointer()
agent = create_react_agent(_model, TOOLS, checkpointer=_checkpointer)

