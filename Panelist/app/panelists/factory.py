from __future__ import annotations

from app.config import PanelistSettings
from app.panelists.base import Panelist
from app.panelists.claude import ClaudePanelist
from app.panelists.fake import FakePanelist
from app.storage.base import ConversationStore

# Provider-backed panelists arrive in later milestones (PANELIST_SERVER.md
# sections 6-8). They are named here so the factory can give a precise error
# instead of a generic "unsupported type".
_NOT_YET_IMPLEMENTED = {
    "gpt": "Milestone 3",
    "gemini": "Milestone 4",
}


class PanelistFactory:
    """Creates the single Panelist instance this server process runs.

    Keeps provider branching in one place instead of scattering ``if
    panelist_type == ...`` across the codebase.
    """

    @staticmethod
    def create(
        *,
        panelist_type: str,
        settings: PanelistSettings,
        conversation_store: ConversationStore,
    ) -> Panelist:
        if panelist_type == "fake":
            return FakePanelist(
                panelist_id=settings.panelist_id,
                model_name=settings.model_name,
                conversation_store=conversation_store,
                settings=settings,
            )

        if panelist_type == "claude":
            return ClaudePanelist(
                panelist_id=settings.panelist_id,
                model_name=settings.model_name,
                conversation_store=conversation_store,
                settings=settings,
            )

        if panelist_type in _NOT_YET_IMPLEMENTED:
            milestone = _NOT_YET_IMPLEMENTED[panelist_type]
            raise NotImplementedError(
                f"Panelist type '{panelist_type}' is not implemented yet "
                f"(planned for {milestone})."
            )

        raise ValueError(f"Unsupported panelist type: {panelist_type}")
