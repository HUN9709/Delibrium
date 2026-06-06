from __future__ import annotations

from abc import ABC, abstractmethod

from app.schemas.chat import ChatMessage
from app.schemas.conversation import Conversation, MessageOut


class ConversationStore(ABC):
    """Short-term conversation history abstraction.

    The base Panelist depends ONLY on this interface, never on a concrete
    backend. Milestone 1 ships an async SQLite implementation; PostgreSQL can
    be added later behind the same interface.
    """

    @abstractmethod
    async def init(self) -> None:
        """Open resources and create schema if needed."""

    @abstractmethod
    async def close(self) -> None:
        """Release resources."""

    @abstractmethod
    async def create_conversation(
        self,
        *,
        conversation_id: str,
        user_id: str,
        title: str | None = None,
    ) -> Conversation:
        ...

    @abstractmethod
    async def get_conversation(self, *, conversation_id: str) -> Conversation | None:
        ...

    @abstractmethod
    async def get_recent_messages(
        self,
        *,
        conversation_id: str,
        limit: int,
    ) -> list[ChatMessage]:
        """Return up to `limit` most recent messages in chronological order."""

    @abstractmethod
    async def get_messages(self, *, conversation_id: str) -> list[MessageOut]:
        """Return the full message history for the API."""

    @abstractmethod
    async def append_message(
        self,
        *,
        conversation_id: str,
        user_id: str,
        role: str,
        content: str,
        provider: str | None = None,
        model: str | None = None,
        message_id: str | None = None,
    ) -> MessageOut:
        ...

    @abstractmethod
    async def list_conversations(self, *, user_id: str | None = None) -> list[Conversation]:
        ...

    @abstractmethod
    async def delete_conversation(self, *, conversation_id: str) -> bool:
        ...
