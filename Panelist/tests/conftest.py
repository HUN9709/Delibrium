from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import PanelistSettings, get_settings
from app.main import create_app
from app.panelists.fake import FakePanelist
from app.storage.sqlite_store import SQLiteConversationStore

MEMORY_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
def settings() -> PanelistSettings:
    return PanelistSettings(
        panelist_id="fake-panelist",
        panelist_type="fake",
        provider="fake",
        model_name="fake-1",
        database_url=MEMORY_URL,
        max_history_messages=30,
    )


@pytest.fixture
async def store():
    s = SQLiteConversationStore(MEMORY_URL)
    await s.init()
    try:
        yield s
    finally:
        await s.close()


@pytest.fixture
async def fake_panelist(store, settings) -> FakePanelist:
    return FakePanelist(
        panelist_id=settings.panelist_id,
        model_name=settings.model_name,
        conversation_store=store,
        settings=settings,
    )


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", MEMORY_URL)
    monkeypatch.setenv("PANELIST_TYPE", "fake")
    monkeypatch.setenv("PANELIST_ID", "fake-panelist")
    monkeypatch.setenv("PROVIDER", "fake")
    monkeypatch.setenv("MODEL_NAME", "fake-1")
    get_settings.cache_clear()
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client
    get_settings.cache_clear()
