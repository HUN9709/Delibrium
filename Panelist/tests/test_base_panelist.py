from __future__ import annotations

from app.schemas.chat import ChatRequest
from app.schemas.events import (
    EVENT_MESSAGE_COMPLETED,
    EVENT_MESSAGE_DELTA,
    EVENT_MESSAGE_START,
)


def _request(message: str, conversation_id: str = "conv-1") -> ChatRequest:
    return ChatRequest(
        conversation_id=conversation_id,
        user_id="user-1",
        message=message,
    )


async def test_chat_returns_normalized_response(fake_panelist):
    response = await fake_panelist.chat(_request("hello"))

    assert response.provider == "fake"
    assert response.model == "fake-1"
    assert response.status == "completed"
    assert "echo: hello" in response.content
    assert response.message_id.startswith("msg-")


async def test_chat_persists_user_and_assistant(fake_panelist, store):
    response = await fake_panelist.chat(_request("hello"))

    messages = await store.get_messages(conversation_id="conv-1")
    assert [m.role for m in messages] == ["user", "assistant"]
    assert messages[0].content == "hello"
    # The persisted assistant message id matches the returned response id.
    assert messages[1].message_id == response.message_id
    assert messages[1].provider == "fake"


async def test_history_is_loaded_into_context(fake_panelist, store):
    await fake_panelist.chat(_request("first"))
    await fake_panelist.chat(_request("second"))

    messages = await store.get_messages(conversation_id="conv-1")
    # Two exchanges => four stored messages, in order.
    assert [m.role for m in messages] == [
        "user",
        "assistant",
        "user",
        "assistant",
    ]
    assert messages[2].content == "second"


async def test_chat_stream_emits_start_deltas_completed(fake_panelist):
    events = [event async for event in fake_panelist.chat_stream(_request("stream me"))]

    assert events[0].event == EVENT_MESSAGE_START
    assert events[-1].event == EVENT_MESSAGE_COMPLETED
    assert events[-1].message_id is not None

    deltas = [e.delta for e in events if e.event == EVENT_MESSAGE_DELTA]
    assert "".join(deltas) == "[fake:fake-1] echo: stream me"


async def test_chat_stream_persists_exchange(fake_panelist, store):
    async for _ in fake_panelist.chat_stream(_request("persisted")):
        pass

    messages = await store.get_messages(conversation_id="conv-1")
    assert [m.role for m in messages] == ["user", "assistant"]
    assert "echo: persisted" in messages[1].content
