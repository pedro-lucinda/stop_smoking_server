import json
from typing import Generator
from uuid import uuid4

from fastapi import APIRouter, Body, Depends, Path

from app.api.v1.dependencies.auth0 import get_current_user
from app.schemas.chat import ChatIn, ThreadOut
from app.services.ai.agent import agent
from app.utils.ai import _event, _extract_text, _iter_tool_calls, _to_json, sse
from app.prompts.chat import SYSTEM_POLICY

router = APIRouter()

EVENT_TOKEN = "token"
EVENT_TOOL_CALL = "tool_call"
EVENT_TOOL_RESULT = "tool_result"

@router.post("/thread", response_model=ThreadOut, dependencies=[Depends(get_current_user)])
def create_thread() -> ThreadOut:
    return ThreadOut(thread_id=str(uuid4()))


@router.post("/threads/{thread_id}/stream", dependencies=[Depends(get_current_user)])
def chat_stream(
    thread_id: str = Path(..., min_length=1),
    payload: ChatIn = Body(...),
):
    """
    Streams assistant output and tool activity as Server-Sent Events.

    Events:
      - {"event":"tool_call","name":str,"args":dict}
      - {"event":"token","text":str}
      - {"event":"tool_result","name":str,"content":str}
    """
    cfg = {"configurable": {"thread_id": thread_id}}

    def gen() -> Generator[str, None, None]:
        stream = agent.stream(
            {"messages": [
                 {"role": "system", "content": SYSTEM_POLICY},
                {"role": "user", "content": payload.message}]},
            config=cfg,
            stream_mode="messages",
        )

        for msg, meta in stream:
            node = meta.get("langgraph_node")

            if node == "agent":
                # tool calls requested by the assistant
                for name, args in _iter_tool_calls(msg):
                    if name:
                        yield _event(EVENT_TOOL_CALL, name=name, args=args)

                # assistant token chunks
                text = _extract_text(msg)
                if text:
                    yield _event(EVENT_TOKEN, text=text)
                continue

            # tool node produced a result
            content = getattr(msg, "content", None)
            if content is not None:
                # normalize to string; avoid double-encoding
                normalized = content if isinstance(content, str) else _to_json(content)
                yield _event(EVENT_TOOL_RESULT, name=node, content=normalized)

    return sse(gen())