from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import anthropic

from app.config import PanelistSettings
from app.panelists.base import Panelist
from app.runtime.errors import (
    INTERNAL_ERROR,
    PROVIDER_AUTHENTICATION_ERROR,
    PROVIDER_INVALID_REQUEST,
    PROVIDER_RATE_LIMIT,
    PROVIDER_TIMEOUT,
    PROVIDER_UNAVAILABLE,
    PanelistError,
)
from app.schemas.chat import ChatMessage, ChatRequest, ChatResponse
from app.schemas.events import StreamEvent
from app.schemas.provider import (
    ProviderRequest,
    ProviderResponse,
    ProviderStreamChunk,
)
from app.storage.base import ConversationStore


def split_system(
    messages: list[ChatMessage],
) -> tuple[str | None, list[dict[str, str]]]:
    """Split out system text and convert the rest to Anthropic message dicts.

    The Anthropic Messages API takes system content as a top-level ``system``
    parameter, not as a message with ``role == "system"``.
    """
    system_parts: list[str] = []
    converted: list[dict[str, str]] = []
    for message in messages:
        if message.role == "system":
            system_parts.append(message.content)
        elif message.role in ("user", "assistant"):
            converted.append({"role": message.role, "content": message.content})
        # "tool" messages are not used until tool-calling milestones.
    system = "\n\n".join(system_parts) if system_parts else None
    return system, converted


def translate_anthropic_error(exc: Exception) -> PanelistError:
    """Map Anthropic SDK exceptions onto the common error model.

    Order matters: the specific 4xx subclasses must be checked before the
    generic ``APIStatusError`` base.
    """
    if isinstance(exc, PanelistError):
        return exc
    if isinstance(exc, anthropic.APITimeoutError):
        return PanelistError(
            PROVIDER_TIMEOUT, "The provider request timed out.", retryable=True
        )
    if isinstance(exc, anthropic.RateLimitError):
        return PanelistError(
            PROVIDER_RATE_LIMIT,
            "The configured provider rate limit was reached.",
            retryable=True,
        )
    if isinstance(exc, anthropic.AuthenticationError):
        return PanelistError(
            PROVIDER_AUTHENTICATION_ERROR, "Provider authentication failed."
        )
    if isinstance(exc, anthropic.BadRequestError):
        return PanelistError(
            PROVIDER_INVALID_REQUEST, "The provider rejected the request."
        )
    if isinstance(exc, anthropic.APIConnectionError):
        return PanelistError(
            PROVIDER_UNAVAILABLE,
            "Could not reach the provider.",
            retryable=True,
        )
    if isinstance(exc, anthropic.APIStatusError):
        return PanelistError(PROVIDER_UNAVAILABLE, "The provider returned an error.")
    return PanelistError(INTERNAL_ERROR, "An unexpected error occurred.")


def _extract_text(message: Any) -> str:
    parts: list[str] = []
    for block in getattr(message, "content", []) or []:
        if getattr(block, "type", None) == "text":
            parts.append(block.text)
    return "".join(parts)


class ClaudePanelist(Panelist):
    """Anthropic-backed Panelist.

    Provider-specific concerns only: SDK init, message conversion, the actual
    API calls, response/usage extraction, and error translation. The common
    chat lifecycle stays in the base class.
    """

    def __init__(
        self,
        *,
        panelist_id: str,
        model_name: str,
        conversation_store: ConversationStore,
        settings: PanelistSettings,
        client: anthropic.AsyncAnthropic | None = None,
    ) -> None:
        super().__init__(
            panelist_id=panelist_id,
            model_name=model_name,
            conversation_store=conversation_store,
            settings=settings,
        )
        # `client` injection keeps the SDK mockable in tests.
        self._client = client or anthropic.AsyncAnthropic(
            api_key=settings.anthropic_api_key
        )
        self._timeout = settings.llm_timeout_seconds

    @property
    def provider_name(self) -> str:
        return "anthropic"

    def _build_kwargs(self, request: ProviderRequest) -> dict[str, Any]:
        system, messages = split_system(request.messages)
        kwargs: dict[str, Any] = {
            "model": request.model_name,
            "max_tokens": request.max_output_tokens,
            "messages": messages,
            "timeout": self._timeout,
        }
        if system is not None:
            kwargs["system"] = system
        if request.temperature is not None:
            kwargs["temperature"] = request.temperature
        return kwargs

    async def _call_provider(
        self, request: ProviderRequest
    ) -> ProviderResponse:
        try:
            message = await self._client.messages.create(
                **self._build_kwargs(request)
            )
        except Exception as exc:  # noqa: BLE001 - normalized below
            raise translate_anthropic_error(exc) from exc

        usage = getattr(message, "usage", None)
        raw = message.model_dump() if hasattr(message, "model_dump") else None
        return ProviderResponse(
            text=_extract_text(message),
            input_tokens=getattr(usage, "input_tokens", None),
            output_tokens=getattr(usage, "output_tokens", None),
            provider_request_id=getattr(message, "id", None),
            raw=raw,
        )

    async def _stream_provider(
        self, request: ProviderRequest
    ) -> AsyncIterator[ProviderStreamChunk]:
        try:
            async with self._client.messages.stream(
                **self._build_kwargs(request)
            ) as stream:
                async for text in stream.text_stream:
                    yield ProviderStreamChunk(delta=text)
        except Exception as exc:  # noqa: BLE001 - normalized below
            raise translate_anthropic_error(exc) from exc

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
