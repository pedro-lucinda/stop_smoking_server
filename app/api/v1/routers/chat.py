import logging
from typing import Generator
from uuid import uuid4
from datetime import date

from fastapi import APIRouter, Body, Depends, HTTPException, Path, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.auth0 import get_current_user
from app.api.v1.dependencies.db import get_async_db
from app.models.preference import Preference
from app.models.user import User
from app.schemas.chat import ChatIn, ThreadOut
from app.services.ai.agent import agent
from app.utils.ai import _event, _extract_text, _iter_tool_calls, _to_json, sse

logger = logging.getLogger(__name__)

router = APIRouter()

EVENT_TOKEN = "token"
EVENT_TOOL_CALL = "tool_call"
EVENT_TOOL_RESULT = "tool_result"
EVENT_ERROR = "error"

@router.post("/thread", response_model=ThreadOut, dependencies=[Depends(get_current_user)])
def create_thread() -> ThreadOut:
    """Create a new chat thread for the user."""
    thread_id = str(uuid4())
    logger.info(f"Created new chat thread: {thread_id}")
    return ThreadOut(thread_id=thread_id)


@router.post("/threads/{thread_id}/stream", dependencies=[Depends(get_current_user)])
async def chat_stream(
    thread_id: str = Path(..., min_length=1),
    payload: ChatIn = Body(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Streams assistant output and tool activity as Server-Sent Events.
    
    Events:
        - {"event":"tool_call","tool":str,"args":dict}
        - {"event":"token","text":str}
        - {"event":"tool_result","tool":str,"content":str}
        - {"event":"error","message":str}
    """
    # Check if agent is available
    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Chat service is currently unavailable"
        )
    
    # Get user's quit information for context
    user_context = {}
    try:
        pref_result = await db.execute(
            select(Preference).where(Preference.user_id == current_user.id)
        )
        preference = pref_result.scalar_one_or_none()
        
        if preference:
            days_since_quit = (date.today() - preference.quit_date).days
            user_context = {
                "user_id": str(current_user.id),
                "quit_date": preference.quit_date.isoformat(),
                "days_since_quit": days_since_quit,
                "quit_reason": preference.reason,
                "cigarettes_per_day": preference.cig_per_day or 0,
            }
            logger.info(f"Loaded user context for {current_user.id}: {days_since_quit} days smoke-free")
    except Exception as e:
        logger.warning(f"Could not load user context: {e}")

    cfg = {"configurable": {"thread_id": thread_id, "checkpoint_ns": "chat"}}

    def gen() -> Generator[str, None, None]:
        try:
            # Build structured initial state for the custom agent
            initial_state = {
                "messages": [{"role": "user", "content": payload.message}],
            }
            # Attach structured user context if available (do NOT reset conversation_context/tool_results)
            if user_context:
                initial_state.update({
                    "user_id": str(current_user.id),
                    "quit_date": user_context.get("quit_date"),
                    "days_since_quit": user_context.get("days_since_quit"),
                    "quit_reason": user_context.get("quit_reason"),
                    "cigarettes_per_day": user_context.get("cigarettes_per_day"),
                })

            stream = agent.stream(
                initial_state,
                config=cfg,
                stream_mode="messages",
            )

            for msg, meta in stream:
                node = meta.get("langgraph_node")

                if node == "agent":
                    # tool calls requested by the assistant
                    for name, args in _iter_tool_calls(msg):
                        if name:
                            yield _event(EVENT_TOOL_CALL, tool=name, args=args)

                    # assistant token chunks
                    text = _extract_text(msg)
                    if text:
                        yield _event(EVENT_TOKEN, text=text)
                    continue

                # tool node produced a result
                content = getattr(msg, "content", None)
                if content is not None:
                    normalized = content if isinstance(content, str) else _to_json(content)
                    yield _event(EVENT_TOOL_RESULT, tool=node, content=normalized)
                    
        except Exception as e:
            logger.error(f"Error in chat stream for thread {thread_id}: {e}")
            yield _event(EVENT_ERROR, message="An error occurred while processing your request. Please try again.")

    return sse(gen())


@router.get("/health")
async def chat_health_check():
    """Check if the chat service is available."""
    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Chat service is unavailable"
        )
    return {"status": "healthy", "agent_available": True}