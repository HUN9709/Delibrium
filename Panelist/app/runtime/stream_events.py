from __future__ import annotations

from app.schemas.events import StreamEvent


def format_sse(event: StreamEvent) -> str:
    """Render a StreamEvent as one SSE frame.

    The API route uses this so it never needs to know provider-specific chunk
    formats (see PANELIST_SERVER.md section 17).
    """
    data = event.model_dump_json(exclude_none=True)
    return f"event: {event.event}\ndata: {data}\n\n"
