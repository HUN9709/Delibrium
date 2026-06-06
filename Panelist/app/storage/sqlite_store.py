from __future__ import annotations

import uuid

import aiosqlite

from app.runtime.errors import CONVERSATION_STORE_ERROR, PanelistError
from app.schemas.chat import ChatMessage
from app.schemas.conversation import Conversation, MessageOut
from app.storage.base import ConversationStore
from app.storage.models import SCHEMA, now_iso


def _sqlite_path(database_url: str) -> str:
    """Extract a filesystem path (or ':memory:') from a SQLAlchemy-style URL."""
    for prefix in ("sqlite+aiosqlite:///", "sqlite:///"):
        if database_url.startswith(prefix):
            return database_url[len(prefix):]
    return database_url


class SQLiteConversationStore(ConversationStore):
    """Async SQLite store using a single shared connection.

    aiosqlite serializes operations on one connection, so a single shared
    connection is safe for Milestone 1 and lets ':memory:' databases persist
    for the lifetime of the store (useful in tests).
    """

    def __init__(self, database_url: str) -> None:
        self._path = _sqlite_path(database_url)
        self._conn: aiosqlite.Connection | None = None

    async def init(self) -> None:
        self._conn = await aiosqlite.connect(self._path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.executescript(SCHEMA)
        await self._conn.commit()

    async def close(self) -> None:
        if self._conn is not None:
            await self._conn.close()
            self._conn = None

    @property
    def _db(self) -> aiosqlite.Connection:
        if self._conn is None:
            raise PanelistError(
                CONVERSATION_STORE_ERROR,
                "Conversation store is not initialized.",
            )
        return self._conn

    async def create_conversation(
        self,
        *,
        conversation_id: str,
        user_id: str,
        title: str | None = None,
    ) -> Conversation:
        created_at = now_iso()
        await self._db.execute(
            "INSERT OR IGNORE INTO conversations "
            "(conversation_id, user_id, title, created_at) VALUES (?, ?, ?, ?)",
            (conversation_id, user_id, title, created_at),
        )
        await self._db.commit()
        existing = await self.get_conversation(conversation_id=conversation_id)
        if existing is None:  # pragma: no cover - defensive
            raise PanelistError(
                CONVERSATION_STORE_ERROR, "Failed to create conversation."
            )
        return existing

    async def get_conversation(self, *, conversation_id: str) -> Conversation | None:
        async with self._db.execute(
            "SELECT conversation_id, user_id, title, created_at "
            "FROM conversations WHERE conversation_id = ?",
            (conversation_id,),
        ) as cursor:
            row = await cursor.fetchone()
        if row is None:
            return None
        return Conversation(
            conversation_id=row["conversation_id"],
            user_id=row["user_id"],
            title=row["title"],
            created_at=row["created_at"],
        )

    async def _ensure_conversation(self, *, conversation_id: str, user_id: str) -> None:
        await self._db.execute(
            "INSERT OR IGNORE INTO conversations "
            "(conversation_id, user_id, title, created_at) VALUES (?, ?, ?, ?)",
            (conversation_id, user_id, None, now_iso()),
        )

    async def get_recent_messages(
        self,
        *,
        conversation_id: str,
        limit: int,
    ) -> list[ChatMessage]:
        async with self._db.execute(
            "SELECT role, content FROM messages WHERE conversation_id = ? "
            "ORDER BY id DESC LIMIT ?",
            (conversation_id, limit),
        ) as cursor:
            rows = await cursor.fetchall()
        # Rows came back newest-first; reverse to chronological order.
        return [ChatMessage(role=row["role"], content=row["content"]) for row in reversed(rows)]

    async def get_messages(self, *, conversation_id: str) -> list[MessageOut]:
        async with self._db.execute(
            "SELECT message_id, role, content, provider, model, created_at "
            "FROM messages WHERE conversation_id = ? ORDER BY id ASC",
            (conversation_id,),
        ) as cursor:
            rows = await cursor.fetchall()
        return [
            MessageOut(
                message_id=row["message_id"],
                role=row["role"],
                content=row["content"],
                provider=row["provider"],
                model=row["model"],
                created_at=row["created_at"],
            )
            for row in rows
        ]

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
        await self._ensure_conversation(
            conversation_id=conversation_id, user_id=user_id
        )
        msg_id = message_id or f"msg-{uuid.uuid4().hex}"
        created_at = now_iso()
        await self._db.execute(
            "INSERT INTO messages "
            "(message_id, conversation_id, user_id, role, content, provider, model, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (msg_id, conversation_id, user_id, role, content, provider, model, created_at),
        )
        await self._db.commit()
        return MessageOut(
            message_id=msg_id,
            role=role,
            content=content,
            provider=provider,
            model=model,
            created_at=created_at,
        )

    async def list_conversations(
        self, *, user_id: str | None = None
    ) -> list[Conversation]:
        if user_id is None:
            query = (
                "SELECT conversation_id, user_id, title, created_at "
                "FROM conversations ORDER BY created_at DESC"
            )
            params: tuple = ()
        else:
            query = (
                "SELECT conversation_id, user_id, title, created_at "
                "FROM conversations WHERE user_id = ? ORDER BY created_at DESC"
            )
            params = (user_id,)
        async with self._db.execute(query, params) as cursor:
            rows = await cursor.fetchall()
        return [
            Conversation(
                conversation_id=row["conversation_id"],
                user_id=row["user_id"],
                title=row["title"],
                created_at=row["created_at"],
            )
            for row in rows
        ]

    async def delete_conversation(self, *, conversation_id: str) -> bool:
        await self._db.execute(
            "DELETE FROM messages WHERE conversation_id = ?", (conversation_id,)
        )
        cursor = await self._db.execute(
            "DELETE FROM conversations WHERE conversation_id = ?", (conversation_id,)
        )
        await self._db.commit()
        return cursor.rowcount > 0
