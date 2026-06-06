from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from app.config import PanelistSettings
from app.schemas.chat import ChatMessage, ChatRequest, ChatResponse
from app.schemas.events import StreamEvent
from app.schemas.provider import (
    ProviderRequest,
    ProviderResponse,
    ProviderStreamChunk,
)
from app.storage.base import ConversationStore


class Panelist(ABC):
    """Abstract Panelist.

    Owns the *common* chat lifecycle so subclasses implement only
    provider-specific concerns:

        load history -> build provider request -> call provider
        -> normalize -> persist -> return

    Subclasses MUST NOT re-implement history loading, persistence, or the
    overall streaming flow (see PANELIST_SERVER.md sections 3 and 9).
    """

    def __init__(
        self,
        *,
        panelist_id: str,
        model_name: str,
        conversation_store: ConversationStore,
        settings: PanelistSettings,
    ) -> None:
        self.panelist_id = panelist_id
        self.model_name = model_name
        self.conversation_store = conversation_store
        self.settings = settings

    # ------------------------------------------------------------------
    # Common lifecycle (final — do not override in subclasses)
    # ------------------------------------------------------------------
    async def chat(self, request: ChatRequest) -> ChatResponse:
        messages = await self._build_conversation_context(request)
        provider_request = self._build_provider_request(
            request=request, messages=messages
        )
        provider_response = await self._call_provider(provider_request)
        response = self._normalize_provider_response(
            request=request, provider_response=provider_response
        )
        await self._persist_exchange(request=request, response=response)
        return response

    async def chat_stream(
        self, request: ChatRequest
    ) -> AsyncIterator[StreamEvent]:
        messages = await self._build_conversation_context(request)
        provider_request = self._build_provider_request(
            request=request, messages=messages
        )

        yield StreamEvent.make_start(
            conversation_id=request.conversation_id,
            panelist_id=self.panelist_id,
        )

        accumulated_text: list[str] = []
        async for chunk in self._stream_provider(provider_request):
            event = self._normalize_stream_chunk(request=request, chunk=chunk)
            if event.delta:
                accumulated_text.append(event.delta)
            yield event

        final_response = self._build_stream_final_response(
            request=request, text="".join(accumulated_text)
        )
        await self._persist_exchange(request=request, response=final_response)

        yield StreamEvent.make_completed(
            conversation_id=request.conversation_id,
            panelist_id=self.panelist_id,
            message_id=final_response.message_id,
        )

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------
    async def _build_conversation_context(
        self, request: ChatRequest
    ) -> list[ChatMessage]:
        history = await self.conversation_store.get_recent_messages(
            conversation_id=request.conversation_id,
            limit=self.settings.max_history_messages,
        )
        return [
            *history,
            ChatMessage(role="user", content=request.message),
        ]

    def _build_provider_request(
        self,
        *,
        request: ChatRequest,
        messages: list[ChatMessage],
    ) -> ProviderRequest:
        return ProviderRequest(
            panelist_id=self.panelist_id,
            model_name=self.model_name,
            messages=messages,
            temperature=request.temperature,
            max_output_tokens=(
                request.max_output_tokens
                or self.settings.default_max_output_tokens
            ),
            metadata={
                "conversation_id": request.conversation_id,
                "user_id": request.user_id,
            },
        )

    async def _persist_exchange(
        self,
        *,
        request: ChatRequest,
        response: ChatResponse,
    ) -> None:
        await self.conversation_store.append_message(
            conversation_id=request.conversation_id,
            user_id=request.user_id,
            role="user",
            content=request.message,
        )
        await self.conversation_store.append_message(
            conversation_id=request.conversation_id,
            user_id=request.user_id,
            role="assistant",
            content=response.content,
            provider=response.provider,
            model=response.model,
            message_id=response.message_id,
        )

    def _build_stream_final_response(
        self,
        *,
        request: ChatRequest,
        text: str,
    ) -> ChatResponse:
        return ChatResponse.create(
            conversation_id=request.conversation_id,
            panelist_id=self.panelist_id,
            provider=self.provider_name,
            model=self.model_name,
            content=text,
        )

    # ------------------------------------------------------------------
    # Provider-specific hooks (subclasses implement these)
    # ------------------------------------------------------------------
    @property
    @abstractmethod
    def provider_name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    async def _call_provider(
        self, request: ProviderRequest
    ) -> ProviderResponse:
        raise NotImplementedError

    @abstractmethod
    def _stream_provider(
        self, request: ProviderRequest
    ) -> AsyncIterator[ProviderStreamChunk]:
        raise NotImplementedError

    @abstractmethod
    def _normalize_provider_response(
        self,
        *,
        request: ChatRequest,
        provider_response: ProviderResponse,
    ) -> ChatResponse:
        raise NotImplementedError

    @abstractmethod
    def _normalize_stream_chunk(
        self,
        *,
        request: ChatRequest,
        chunk: ProviderStreamChunk,
    ) -> StreamEvent:
        raise NotImplementedError
