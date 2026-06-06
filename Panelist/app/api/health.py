from __future__ import annotations

from fastapi import APIRouter, Depends

from app.config import PanelistSettings
from app.dependencies import get_settings_dep

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(settings: PanelistSettings = Depends(get_settings_dep)) -> dict:
    return {
        "status": "ok",
        "panelist_id": settings.panelist_id,
        "provider": settings.provider,
        "model": settings.model_name,
    }
