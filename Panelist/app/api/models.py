from __future__ import annotations

from fastapi import APIRouter, Depends

from app.config import PanelistSettings
from app.dependencies import get_settings_dep

router = APIRouter(prefix="/v1/models", tags=["models"])


@router.get("/current")
async def current_model(
    settings: PanelistSettings = Depends(get_settings_dep),
) -> dict:
    return {
        "panelist_id": settings.panelist_id,
        "panelist_type": settings.panelist_type,
        "provider": settings.provider,
        "model": settings.model_name,
    }
