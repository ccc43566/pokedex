"""Round-trip the additive search migration in the disposable database only."""

import asyncio
import subprocess
import sys

from pokedex_api.db import SessionLocal, engine
from pokedex_api.search_schema import SOURCE_TABLES
from pokedex_api.services.search_index import rebuild_indexes
from sqlalchemy import text


async def counts():
    async with SessionLocal() as session:
        return {
            table: await session.scalar(text(f'SELECT count(*) FROM "{table}"'))
            for table in SOURCE_TABLES
        }


async def main():
    assert engine.url.database == "pokedex_search_check"
    before = await counts()
    for command in [("downgrade", "0006_item_media"), ("upgrade", "head")]:
        await asyncio.to_thread(
            subprocess.run, [sys.executable, "-m", "alembic", *command], check=True
        )
    assert await counts() == before
    async with SessionLocal() as session:
        await rebuild_indexes(session)
        await session.commit()
        assert (
            await session.scalar(text("SELECT count(*) FROM pokemon_search_index")) == 2
        )
    print(
        "PASS: search migration downgrade/upgrade preserves all source counts and rebuilds both locales"
    )
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
