from collections import deque
from uuid import uuid4
import json
from fastapi import APIRouter, Body, Depends, Path
from app.api.v1.dependencies.auth0 import get_current_user
from app.schemas.chat import ChatIn, ThreadOut
from app.services.ai.agent import agent
from app.utils.ai import _event, _extract_text, _iter_tool_calls, sse

router = APIRouter()

EVENT_TOKEN = "token"
EVENT_TOOL_CALL = "tool_call"
EVENT_TOOL_RESULT = "tool_result"

def _jsonable(x):
    try:
        return json.loads(json.dumps(x, default=str, ensure_ascii=False))
    except Exception:
        return str(x)

@router.post("/thread", response_model=ThreadOut, dependencies=[Depends(get_current_user)])
def create_thread() -> ThreadOut:
    return ThreadOut(thread_id=str(uuid4()))

@router.post("/threads/{thread_id}/stream", dependencies=[Depends(get_current_user)])
def chat_stream(
    thread_id: str = Path(..., min_length=1),
    payload: ChatIn = Body(...),
):
    cfg = {"configurable": {"thread_id": thread_id}}

    def gen():
        # Global FIFO of pending tool-call IDs and their real tool names
        pending_ids: deque[str] = deque()
        name_by_id: dict[str, str] = {}

        stream = agent.stream(
            {"messages": [{"role": "user", "content": payload.message}]},
            config=cfg,
            stream_mode="messages",
        )

        for msg, meta in stream:
            node = meta.get("langgraph_node")

            if node == "agent":
                # Announce only REAL tool calls. If assistant calls the router "tools",
                # rewrite to the routed tool name from args (e.g., {"tool_name": "tavily_search", ...}).
                for name, args in _iter_tool_calls(msg):
                    routed = None
                    if name == "tools" and isinstance(args, dict):
                        routed = args.get("tool_name") or args.get("name")  # common patterns
                    tool_name = (routed or name or "").strip()
                    if not tool_name:
                        continue  # skip empty names

                    call_id = str(uuid4())
                    pending_ids.append(call_id)
                    name_by_id[call_id] = tool_name

                    yield _event(
                        EVENT_TOOL_CALL,
                        id=call_id,
                        tool=tool_name,
                        args=_jsonable(args),
                    )

                # Assistant tokens
                text = _extract_text(msg)
                if text:
                    yield _event(EVENT_TOKEN, text=text)
                continue

            # Tool node executed (often "tools"). Pair result to the oldest pending call.
            if pending_ids:
                call_id = pending_ids.popleft()
                tool_name = name_by_id.get(call_id, "tool")
                content = getattr(msg, "content", None)
                yield _event(
                    EVENT_TOOL_RESULT,
                    id=call_id,            # reuse the REAL call id
                    tool=tool_name,        # expose the REAL tool name
                    content=_jsonable(content),
                )
            # else: no pending call -> drop orphan result

    return sse(gen())
