"""Rebuild search snapshots without fetching or modifying source Pokémon data."""
import asyncio

from pokedex_api.db import SessionLocal, engine
from pokedex_api.services.search_index import rebuild_indexes


async def rebuild() -> None:
    try:
        async with SessionLocal() as session:
            version = await rebuild_indexes(session, force=True)
            await session.commit()
            print(f"Pokémon search indexes ready: {version}")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(rebuild())
