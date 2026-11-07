
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from pokedex_api.api.v1.router import router as v1_router
from pokedex_api.config import Settings, get_settings
from pokedex_api.db import SessionLocal, get_session
from pokedex_api.schemas import HealthResponse


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    settings.media_root.mkdir(parents=True, exist_ok=True)
    # A failed rebuild leaves source data usable; requests rebuild the current
    # revision in memory and never reuse a stale persisted snapshot.
    import logging

    from pokedex_api.services.search_index import rebuild_indexes

    try:
        async with SessionLocal() as session:
            await rebuild_indexes(session)
            await session.commit()
    except Exception:
        logging.getLogger(__name__).exception(
            "Search warmup failed; check migrations and run python -m pokedex_api.sync.search_index"
        )
    yield


settings = get_settings()
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)
app.include_router(v1_router, prefix="/api/v1")


@app.get("/api/v1/health", response_model=HealthResponse, tags=["system"])
async def health(
    session: Annotated[AsyncSession, Depends(get_session)],
    config: Annotated[Settings, Depends(get_settings)],
) -> HealthResponse:
    try:
        await session.execute(text("SELECT 1"))
        database = "ok"
    except Exception:
        database = "unavailable"
    return HealthResponse(status="ok", database=database, version=config.app_version)


Path(settings.media_root).mkdir(parents=True, exist_ok=True)
app.mount(
    settings.media_public_path,
    StaticFiles(directory=str(settings.media_root), check_dir=False),
    name="media",
)
