import logging
import os
from typing import Optional

from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel

from app.core.config import settings
from app.prompts.chat import SYSTEM_POLICY
from app.services.ai.checkpointer import build_checkpointer
from app.services.ai.tools import TOOLS

logger = logging.getLogger(__name__)

# Import custom agent (required)
from app.services.ai.custom_agent import create_custom_agent


def create_chat_model() -> BaseChatModel:
    """Create and configure the chat model with proper error handling."""
    api_key = settings.openai_api_key
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not configured")
    os.environ.setdefault("OPENAI_API_KEY", api_key)

    model = init_chat_model(
        "gpt-4o-mini",
        model_provider="openai",
        temperature=0.7,
        max_tokens=2000,
    )
    logger.info("Chat model initialized successfully")
    return model


def _safe_build_checkpointer():
    """Try to build persistent checkpointer; fall back to None on failure."""
    try:
        return build_checkpointer()
    except Exception as e:
        logger.warning(
            "Checkpointer setup failed; continuing without persistence. Error: %s", e
        )
        return None


def create_agent() -> Optional[object]:
    """Create the custom LangGraph agent (only)."""
    try:
        logger.info("Creating chat model...")
        model = create_chat_model()

        logger.info("Building checkpointer...")
        checkpointer = _safe_build_checkpointer()

        logger.info("Creating custom LangGraph agent...")
        agent = create_custom_agent(model, TOOLS, checkpointer)
        logger.info("Custom agent created successfully")
        return agent

    except Exception as e:
        logger.error(f"Failed to create custom agent: {e}")
        logger.exception("Full traceback:")
        return None


# Singleton agent with persisted memory (module scope)
agent = create_agent()

if agent is None:
    logger.warning("Custom agent initialization failed - chat functionality will be disabled")

