from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.chat import ChatMessage


class ProviderRequest(BaseModel):
    """Normalized request handed to a provider implementation.

    Subclasses translate this into the provider-native API format. The base
    Panelist builds it so subclasses never reconstruct conversation context.
    """

    panelist_id: str
    model_name: str
    messages: list[ChatMessage]
    temperature: float | None = None
    max_output_tokens: int | None = None
    metadata: dict = Field(default_factory=dict)


class ProviderResponse(BaseModel):
    """Normalized non-streaming provider result."""

    text: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    provider_request_id: str | None = None
    raw: dict | str | None = None


class ProviderStreamChunk(BaseModel):
    """Normalized streaming chunk. One incremental piece of output text."""

    delta: str | None = None
    raw: dict | str | None = None
