from __future__ import annotations

from collections.abc import AsyncIterator

from app.panelists.base import Panelist
from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.events import StreamEvent
from app.schemas.provider import (
    ProviderRequest,
    ProviderResponse,
    ProviderStreamChunk,
)


def _last_user_message(request: ProviderRequest) -> str:
    for message in reversed(request.messages):
        if message.role == "user":
            return message.content
    return ""


def _reply_text(model_name: str, user_message: str) -> str:
    return f"[fake:{model_name}] echo: {user_message}"


class FakePanelist(Panelist):
    """Provider-independent Panelist used for the Milestone 1 skeleton and tests.

    It echoes the latest user message. No real LLM provider is involved, which
    keeps the base lifecycle and SSE plumbing testable before any SDK exists.
    """

    @property
    def provider_name(self) -> str:
        return "fake"

    async def _call_provider(
        self, request: ProviderRequest
    ) -> ProviderResponse:
        user_message = _last_user_message(request)
        text = _reply_text(request.model_name, user_message)
        return ProviderResponse(
            text=text,
            input_tokens=len(user_message.split()),
            output_tokens=len(text.split()),
            provider_request_id="fake-request",
            raw={"echo": user_message},
        )

    async def _stream_provider(
        self, request: ProviderRequest
    ) -> AsyncIterator[ProviderStreamChunk]:
        user_message = _last_user_message(request)
        text = _reply_text(request.model_name, user_message)
        tokens = text.split(" ")
        for index, token in enumerate(tokens):
            # Re-attach the spaces we split on, except after the final token.
            delta = token if index == len(tokens) - 1 else f"{token} "
            yield ProviderStreamChunk(delta=delta)

    def _normalize_provider_response(
        self,
        *,
        request: ChatRequest,
        provider_response: ProviderResponse,
    ) -> ChatResponse:
        return ChatResponse.create(
            conversation_id=request.conversation_id,
            panelist_id=self.panelist_id,
            provider=self.provider_name,
            model=self.model_name,
            content=provider_response.text,
            input_tokens=provider_response.input_tokens,
            output_tokens=provider_response.output_tokens,
            provider_request_id=provider_response.provider_request_id,
        )

    def _normalize_stream_chunk(
        self,
        *,
        request: ChatRequest,
        chunk: ProviderStreamChunk,
    ) -> StreamEvent:
        return StreamEvent.make_delta(
            conversation_id=request.conversation_id,
            panelist_id=self.panelist_id,
            delta=chunk.delta or "",
        )
