from __future__ import annotations

import pytest

from app.config import PanelistSettings
from app.panelists.claude import ClaudePanelist
from app.panelists.factory import PanelistFactory
from app.panelists.fake import FakePanelist
from app.storage.sqlite_store import SQLiteConversationStore


@pytest.fixture
def uninitialized_store() -> SQLiteConversationStore:
    # The factory only constructs; it never touches the store.
    return SQLiteConversationStore("sqlite+aiosqlite:///:memory:")


def test_create_fake_panelist(settings, uninitialized_store):
    panelist = PanelistFactory.create(
        panelist_type="fake",
        settings=settings,
        conversation_store=uninitialized_store,
    )
    assert isinstance(panelist, FakePanelist)
    assert panelist.provider_name == "fake"


def test_create_claude_panelist(uninitialized_store):
    claude_settings = PanelistSettings(
        panelist_id="claude-panelist",
        panelist_type="claude",
        provider="anthropic",
        model_name="claude-test-model",
        anthropic_api_key="test-key",  # construction only; no network call
    )
    panelist = PanelistFactory.create(
        panelist_type="claude",
        settings=claude_settings,
        conversation_store=uninitialized_store,
    )
    assert isinstance(panelist, ClaudePanelist)
    assert panelist.provider_name == "anthropic"


@pytest.mark.parametrize("panelist_type", ["gpt", "gemini"])
def test_known_but_unimplemented_types_raise(
    panelist_type, settings, uninitialized_store
):
    with pytest.raises(NotImplementedError):
        PanelistFactory.create(
            panelist_type=panelist_type,
            settings=settings,
            conversation_store=uninitialized_store,
        )


def test_unknown_type_raises_value_error(settings, uninitialized_store):
    with pytest.raises(ValueError):
        PanelistFactory.create(
            panelist_type="mystery",
            settings=settings,
            conversation_store=uninitialized_store,
        )
