from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api import chat, conversations, health, models
from app.config import get_settings
from app.observability.logging import configure_logging, get_logger
from app.panelists.factory import PanelistFactory
from app.runtime.errors import PanelistError, http_status_for
from app.storage.sqlite_store import SQLiteConversationStore

logger = get_logger("panelist.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    settings = get_settings()

    store = SQLiteConversationStore(settings.database_url)
    await store.init()

    # Fails fast at startup for an unsupported PANELIST_TYPE.
    panelist = PanelistFactory.create(
        panelist_type=settings.panelist_type,
        settings=settings,
        conversation_store=store,
    )

    app.state.settings = settings
    app.state.store = store
    app.state.panelist = panelist

    logger.info(
        "Panelist server ready: id=%s type=%s provider=%s model=%s",
        settings.panelist_id,
        settings.panelist_type,
        settings.provider,
        settings.model_name,
    )
    try:
        yield
    finally:
        await store.close()


def create_app() -> FastAPI:
    app = FastAPI(title="Delibrium Panelist Server", lifespan=lifespan)

    @app.exception_handler(PanelistError)
    async def _panelist_error_handler(
        _request: Request, exc: PanelistError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=http_status_for(exc.code),
            content=exc.to_payload(),
        )

    app.include_router(health.router)
    app.include_router(chat.router)
    app.include_router(conversations.router)
    app.include_router(models.router)
    return app


app = create_app()
