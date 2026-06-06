from __future__ import annotations

from datetime import datetime, timezone

# SQLite schema for short-term conversation history (Milestone 1).
# Long-term memory (Mem0) is intentionally NOT part of this store.
SCHEMA = """
CREATE TABLE IF NOT EXISTS conversations (
    conversation_id TEXT PRIMARY KEY,
    user_id         TEXT NOT NULL,
    title           TEXT,
    created_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id      TEXT NOT NULL UNIQUE,
    conversation_id TEXT NOT NULL,
    user_id         TEXT NOT NULL,
    role            TEXT NOT NULL,
    content         TEXT NOT NULL,
    provider        TEXT,
    model           TEXT,
    created_at      TEXT NOT NULL,
    FOREIGN KEY (conversation_id) REFERENCES conversations (conversation_id)
);

CREATE INDEX IF NOT EXISTS idx_messages_conversation
    ON messages (conversation_id, id);
"""


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
