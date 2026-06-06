from __future__ import annotations

import os

import anthropic
import httpx
import pytest

from app.config import PanelistSettings
from app.panelists.claude import (
    ClaudePanelist,
    split_system,
    translate_anthropic_error,
)
from app.runtime.errors import (
    INTERNAL_ERROR,
    PROVIDER_TIMEOUT,
    PanelistError,
)
from app.schemas.chat import ChatMessage, ChatRequest
from app.schemas.events import EVENT_MESSAGE_COMPLETED, EVENT_MESSAGE_DELTA
from app.storage.sqlite_store import SQLiteConversationStore

MEMORY_URL = "sqlite+aiosqlite:///:memory:"


# --------------------------------------------------------------------------
# Fake Anthropic async client (mocks the SDK surface we depend on)
# --------------------------------------------------------------------------
class _Block:
    def __init__(self, text: str) -> None:
        self.type = "text"
        self.text = text


class _Usage:
    def __init__(self, input_tokens: int, output_tokens: int) -> None:
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens


class _Message:
    def __init__(self, text: str, input_tokens: int, output_tokens: int) -> None:
        self.id = "msg_claude_test"
        self.content = [_Block(text)]
        self.usage = _Usage(input_tokens, output_tokens)


async def _aiter(items):
    for item in items:
        yield item


class _FakeStreamManager:
    def __init__(self, texts: list[str]) -> None:
        self._texts = texts

    async def __aenter__(self) -> "_FakeStreamManager":
        return self

    async def __aexit__(self, *_exc) -> bool:
        return False

    @property
    def text_stream(self):
        return _aiter(self._texts)


class _FakeMessages:
    def __init__(self, message=None, stream_texts=None, error=None) -> None:
        self._message = message
        self._stream_texts = stream_texts or []
        self._error = error
        self.captured_kwargs: dict | None = None

    async def create(self, **kwargs):
        self.captured_kwargs = kwargs
        if self._error is not None:
            raise self._error
        return self._message

    def stream(self, **kwargs):
        self.captured_kwargs = kwargs
        if self._error is not None:
            raise self._error
        return _FakeStreamManager(self._stream_texts)


class _FakeClient:
    def __init__(self, message=None, stream_texts=None, error=None) -> None:
        self.messages = _FakeMessages(
            message=message, stream_texts=stream_texts, error=error
        )


def _settings() -> PanelistSettings:
    return PanelistSettings(
        panelist_id="claude-panelist",
        panelist_type="claude",
        provider="anthropic",
        model_name="claude-test-model",
        database_url=MEMORY_URL,
        anthropic_api_key="test-key",
    )


async def _make_panelist(client) -> ClaudePanelist:
    store = SQLiteConversationStore(MEMORY_URL)
    await store.init()
    return ClaudePanelist(
        panelist_id="claude-panelist",
        model_name="claude-test-model",
        conversation_store=store,
        settings=_settings(),
        client=client,
    )


def _request(message: str) -> ChatRequest:
    return ChatRequest(
        conversation_id="conv-claude",
        user_id="user-1",
        message=message,
    )


# --------------------------------------------------------------------------
# Pure helpers
# --------------------------------------------------------------------------
def test_split_system_separates_system_and_converts():
    messages = [
        ChatMessage(role="system", content="be neutral"),
        ChatMessage(role="user", content="hi"),
        ChatMessage(role="assistant", content="hello"),
        ChatMessage(role="system", content="stay concise"),
    ]
    system, converted = split_system(messages)
    assert system == "be neutral\n\nstay concise"
    assert converted == [
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "hello"},
    ]


def test_split_system_no_system_returns_none():
    system, converted = split_system([ChatMessage(role="user", content="hi")])
    assert system is None
    assert converted == [{"role": "user", "content": "hi"}]


def test_translate_error_timeout():
    exc = anthropic.APITimeoutError(request=httpx.Request("POST", "http://x"))
    translated = translate_anthropic_error(exc)
    assert isinstance(translated, PanelistError)
    assert translated.code == PROVIDER_TIMEOUT
    assert translated.retryable is True


def test_translate_error_generic():
    translated = translate_anthropic_error(ValueError("boom"))
    assert translated.code == INTERNAL_ERROR


# --------------------------------------------------------------------------
# Non-streaming
# --------------------------------------------------------------------------
async def test_chat_normalizes_anthropic_message():
    client = _FakeClient(message=_Message("Delibrium explained.", 11, 7))
    panelist = await _make_panelist(client)

    response = await panelist.chat(_request("explain"))

    assert response.provider == "anthropic"
    assert response.model == "claude-test-model"
    assert response.content == "Delibrium explained."
    assert response.input_tokens == 11
    assert response.output_tokens == 7
    assert response.provider_request_id == "msg_claude_test"

    # System param omitted when there is no system message; required fields set.
    kwargs = client.messages.captured_kwargs
    assert kwargs["model"] == "claude-test-model"
    assert "max_tokens" in kwargs
    assert "system" not in kwargs
    assert kwargs["messages"][-1] == {"role": "user", "content": "explain"}


async def test_chat_translates_provider_error():
    err = anthropic.APITimeoutError(request=httpx.Request("POST", "http://x"))
    panelist = await _make_panelist(_FakeClient(error=err))

    with pytest.raises(PanelistError) as exc_info:
        await panelist.chat(_request("explain"))
    assert exc_info.value.code == PROVIDER_TIMEOUT


# --------------------------------------------------------------------------
# Streaming
# --------------------------------------------------------------------------
async def test_chat_stream_accumulates_text():
    client = _FakeClient(stream_texts=["Deli", "brium", " rocks"])
    panelist = await _make_panelist(client)

    events = [e async for e in panelist.chat_stream(_request("stream"))]

    deltas = [e.delta for e in events if e.event == EVENT_MESSAGE_DELTA]
    assert "".join(deltas) == "Delibrium rocks"
    assert events[-1].event == EVENT_MESSAGE_COMPLETED


async def test_chat_stream_persists_assistant_message():
    client = _FakeClient(stream_texts=["hello ", "world"])
    panelist = await _make_panelist(client)

    async for _ in panelist.chat_stream(_request("stream")):
        pass

    messages = await panelist.conversation_store.get_messages(
        conversation_id="conv-claude"
    )
    assert [m.role for m in messages] == ["user", "assistant"]
    assert messages[1].content == "hello world"
    assert messages[1].provider == "anthropic"


# --------------------------------------------------------------------------
# Opt-in integration test (real API; skipped without a key)
# --------------------------------------------------------------------------
@pytest.mark.skipif(
    not os.getenv("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not set; skipping live Anthropic call.",
)
async def test_live_anthropic_chat():
    model = os.getenv("ANTHROPIC_MODEL_NAME", "claude-sonnet-4-6")
    settings = PanelistSettings(
        panelist_id="claude-panelist",
        panelist_type="claude",
        provider="anthropic",
        model_name=model,
        database_url=MEMORY_URL,
        anthropic_api_key=os.environ["ANTHROPIC_API_KEY"],
        default_max_output_tokens=64,
    )
    store = SQLiteConversationStore(MEMORY_URL)
    await store.init()
    panelist = ClaudePanelist(
        panelist_id="claude-panelist",
        model_name=model,
        conversation_store=store,
        settings=settings,
    )
    response = await panelist.chat(
        ChatRequest(
            conversation_id="live",
            user_id="live",
            message="Reply with the single word: ok",
        )
    )
    assert response.content.strip()
    assert response.provider == "anthropic"
