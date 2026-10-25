from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from pokedex_api.config import get_settings


def create_engine(database_url: str | None = None) -> AsyncEngine:
    return create_async_engine(
        database_url or get_settings().database_url,
        pool_pre_ping=True,
        future=True,
    )


engine = create_engine()
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session
