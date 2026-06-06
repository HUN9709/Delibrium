from __future__ import annotations

from pydantic import BaseModel


class ConversationCreateRequest(BaseModel):
    conversation_id: str | None = None
    user_id: str
    title: str | None = None


class Conversation(BaseModel):
    conversation_id: str
    user_id: str
    title: str | None = None
    created_at: str


class MessageOut(BaseModel):
    message_id: str
    role: str
    content: str
    provider: str | None = None
    model: str | None = None
    created_at: str


class ConversationListResponse(BaseModel):
    conversations: list[Conversation]


class ConversationMessagesResponse(BaseModel):
    conversation_id: str
    messages: list[MessageOut]
