from __future__ import annotations

from pydantic import BaseModel

# SSE event names (see PANELIST_SERVER.md section 10.4 / 17).
EVENT_MESSAGE_START = "message_start"
EVENT_MESSAGE_DELTA = "message_delta"
EVENT_MESSAGE_COMPLETED = "message_completed"
EVENT_ERROR = "error"


class StreamEvent(BaseModel):
    event: str
    conversation_id: str
    panelist_id: str
    delta: str | None = None
    message_id: str | None = None
    error: str | None = None

    # NOTE: constructors are prefixed `make_` because `delta` and `error` are
    # also field names; in Pydantic v2 a field name would shadow a classmethod.
    @classmethod
    def make_start(cls, *, conversation_id: str, panelist_id: str) -> "StreamEvent":
        return cls(
            event=EVENT_MESSAGE_START,
            conversation_id=conversation_id,
            panelist_id=panelist_id,
        )

    @classmethod
    def make_delta(
        cls, *, conversation_id: str, panelist_id: str, delta: str
    ) -> "StreamEvent":
        return cls(
            event=EVENT_MESSAGE_DELTA,
            conversation_id=conversation_id,
            panelist_id=panelist_id,
            delta=delta,
        )

    @classmethod
    def make_completed(
        cls, *, conversation_id: str, panelist_id: str, message_id: str
    ) -> "StreamEvent":
        return cls(
            event=EVENT_MESSAGE_COMPLETED,
            conversation_id=conversation_id,
            panelist_id=panelist_id,
            message_id=message_id,
        )

    @classmethod
    def make_error(
        cls, *, conversation_id: str, panelist_id: str, error: str
    ) -> "StreamEvent":
        return cls(
            event=EVENT_ERROR,
            conversation_id=conversation_id,
            panelist_id=panelist_id,
            error=error,
        )
