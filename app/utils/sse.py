from typing import Generator
from fastapi.responses import StreamingResponse


def sse(gen: Generator[str, None, None]) -> StreamingResponse:
    def wrap():
        for chunk in gen:
            yield f"data: {chunk}\n\n"
        yield "event: end\ndata: [DONE]\n\n"

    return StreamingResponse(wrap(), media_type="text/event-stream")
