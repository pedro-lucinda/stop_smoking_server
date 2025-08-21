import json
from typing import Any, Generator, Iterable, Optional

from fastapi.responses import StreamingResponse


def sse(gen: Generator[str, None, None]) -> StreamingResponse:
    def wrap():
        for chunk in gen:
            yield f"data: {chunk}\n\n"
        yield "event: end\ndata: [DONE]\n\n"

    return StreamingResponse(wrap(), media_type="text/event-stream")


def _to_json(obj: Any) -> str:
    """Safe JSON dump with unicode preserved."""
    return json.dumps(obj, ensure_ascii=False, default=str)


def _event(name: str, **data: Any) -> str:
    """Uniform event envelope."""
    return _to_json({"event": name, **data})


def _extract_text(msg: Any) -> Optional[str]:
    """Return assistant text chunk if available."""
    text_fn = getattr(msg, "text", None)
    return text_fn() if callable(text_fn) else None


def _iter_tool_calls(msg: Any) -> Iterable[tuple[Optional[str], dict]]:
    """
    Yield (name, args) pairs for tool calls.
    Handles dict-like and object-like tool call shapes.
    """
    tool_calls = getattr(msg, "tool_calls", None) or []
    for tc in tool_calls:
        if isinstance(tc, dict):
            name = tc.get("name")
            args = tc.get("args") or {}
        else:
            name = getattr(tc, "name", None)
            args = getattr(tc, "args", None) or {}
        yield name, args

