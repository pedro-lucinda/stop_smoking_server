import json
from uuid import uuid4

from fastapi import APIRouter, Body, Depends, Path

from app.api.v1.dependencies.auth0 import get_current_user
from app.schemas.chat import ChatIn, ThreadOut
from app.services.ai.agent import agent
from app.utils.sse import sse

router = APIRouter()


@router.post(
    "/thread", response_model=ThreadOut, dependencies=[Depends(get_current_user)]
)
def create_thread():
    return ThreadOut(thread_id=str(uuid4()))


@router.post("/threads/{thread_id}/stream", dependencies=[Depends(get_current_user)])
def chat_stream(
    thread_id: str = Path(..., min_length=1),
    payload: ChatIn = Body(...),
):
    cfg = {"configurable": {"thread_id": thread_id}}

    def gen():
        for msg, meta in agent.stream(
            {"messages": [{"role": "user", "content": payload.message}]},
            config=cfg,
            stream_mode="messages",
        ):
            node = meta.get("langgraph_node")

            if node == "agent":
                # 1) tool calls requested by the assistant
                tcs = getattr(msg, "tool_calls", None)
                if tcs:
                    for tc in tcs:
                        name = (
                            tc.get("name")
                            if isinstance(tc, dict)
                            else getattr(tc, "name", None)
                        )
                        args = (
                            tc.get("args")
                            if isinstance(tc, dict)
                            else getattr(tc, "args", {}) or {}
                        )
                        yield json.dumps(
                            {"event": "tool_call", "name": name, "args": args}
                        )
                # 2) assistant token chunks
                text_fn = getattr(msg, "text", None)
                if callable(text_fn):
                    chunk = text_fn()
                    if chunk:
                        yield json.dumps({"event": "token", "text": chunk})
            else:
                # 3) tool result message from the tool node (node == tool name)
                content = getattr(msg, "content", None)
                if content:
                    # normalize non-str payloads
                    out = content if isinstance(content, str) else json.dumps(content)
                    yield json.dumps(
                        {"event": "tool_result", "name": node, "content": out}
                    )

    return sse(gen())
