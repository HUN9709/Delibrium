from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import StreamingResponse

from app.dependencies import get_panelist
from app.panelists.base import Panelist
from app.runtime.errors import PanelistError, http_status_for
from app.runtime.stream_events import format_sse
from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.events import StreamEvent

router = APIRouter(prefix="/v1", tags=["chat"])


def _wants_stream(chat_request: ChatRequest, accept: str | None) -> bool:
    if chat_request.stream:
        return True
    return bool(accept and "text/event-stream" in accept.lower())


async def _sse_stream(
    panelist: Panelist, chat_request: ChatRequest
) -> AsyncIterator[str]:
    try:
        async for event in panelist.chat_stream(chat_request):
            yield format_sse(event)
    except PanelistError as exc:
        error_event = StreamEvent.make_error(
            conversation_id=chat_request.conversation_id,
            panelist_id=panelist.panelist_id,
            error=exc.message,
        )
        yield format_sse(error_event)


@router.post("/chat")
async def chat(
    chat_request: ChatRequest,
    request: Request,
    panelist: Panelist = Depends(get_panelist),
    accept: str | None = Header(default=None),
):
    if _wants_stream(chat_request, accept):
        return StreamingResponse(
            _sse_stream(panelist, chat_request),
            media_type="text/event-stream",
        )

    try:
        response: ChatResponse = await panelist.chat(chat_request)
    except PanelistError as exc:
        from fastapi.responses import JSONResponse

        return JSONResponse(
            status_code=http_status_for(exc.code),
            content=exc.to_payload(),
        )
    return response


@router.post("/chat/stream")
async def chat_stream(
    chat_request: ChatRequest,
    panelist: Panelist = Depends(get_panelist),
) -> StreamingResponse:
    return StreamingResponse(
        _sse_stream(panelist, chat_request),
        media_type="text/event-stream",
    )
