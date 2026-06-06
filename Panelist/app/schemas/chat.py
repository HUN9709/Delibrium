from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, Field

Role = Literal["system", "user", "assistant", "tool"]


class ChatMessage(BaseModel):
    """A single turn in a conversation. Provider-independent."""

    role: Role
    content: str


class ChatRequest(BaseModel):
    conversation_id: str
    user_id: str
    message: str
    stream: bool = False
    temperature: float | None = None
    max_output_tokens: int | None = None


class ChatResponse(BaseModel):
    conversation_id: str
    message_id: str
    panelist_id: str
    provider: str
    model: str
    content: str
    status: str = "completed"
    input_tokens: int | None = None
    output_tokens: int | None = None
    provider_request_id: str | None = None

    @classmethod
    def create(
        cls,
        *,
        conversation_id: str,
        panelist_id: str,
        provider: str,
        model: str,
        content: str,
        status: str = "completed",
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        provider_request_id: str | None = None,
    ) -> "ChatResponse":
        return cls(
            conversation_id=conversation_id,
            message_id=f"msg-{uuid.uuid4().hex}",
            panelist_id=panelist_id,
            provider=provider,
            model=model,
            content=content,
            status=status,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            provider_request_id=provider_request_id,
        )
