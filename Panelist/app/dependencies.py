from __future__ import annotations

from fastapi import Request

from app.config import PanelistSettings
from app.panelists.base import Panelist
from app.storage.base import ConversationStore

# Singletons live on app.state (created during the lifespan startup). These
# dependency functions just expose them to routes.


def get_settings_dep(request: Request) -> PanelistSettings:
    return request.app.state.settings


def get_conversation_store(request: Request) -> ConversationStore:
    return request.app.state.store


def get_panelist(request: Request) -> Panelist:
    return request.app.state.panelist
