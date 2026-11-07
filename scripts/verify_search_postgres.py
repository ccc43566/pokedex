"""Multi-worker invalidation check; only run in the disposable verification DB."""

import asyncio

from pokedex_api.db import SessionLocal, engine
from pokedex_api.services.pokemon import list_pokemon
from pokedex_api.services.search_index import data_version, rebuild_indexes
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


async def main() -> None:
    assert engine.url.database == "pokedex_search_check"
    second_engine = create_async_engine(engine.url)
    other_worker = async_sessionmaker(second_engine, expire_on_commit=False)
    original_name = None
    try:
        async with SessionLocal() as first, other_worker() as second:
            a = await list_pokemon(first, locale="zh-Hans", q="皮卡")
            b = await list_pokemon(second, locale="zh-Hans", q="皮卡")
            assert a.model_dump() == b.model_dump()
            original_version = await data_version(first)
        async with SessionLocal() as writer:
            original_name = await writer.scalar(
                text(
                    "SELECT name FROM localized_name WHERE entity_type='pokemon-species' "
                    "AND entity_id=25 AND locale='zh-Hans' ORDER BY id LIMIT 1"
                )
            )
            await writer.execute(
                text(
                    "UPDATE localized_name SET name='search-invalidation-check' "
                    "WHERE entity_type='pokemon-species' AND entity_id=25 AND locale='zh-Hans'"
                )
            )
            await writer.commit()
        for factory in (SessionLocal, other_worker):
            async with factory() as reader:
                assert await data_version(reader) != original_version
                fresh = await list_pokemon(
                    reader, locale="zh-Hans", q="search-invalidation-check"
                )
                assert fresh.total > 0
                assert all(
                    p.localized_name == "search-invalidation-check" for p in fresh.items
                )
        print(
            "PASS: two independent engines reject obsolete name/result snapshots after direct SQL commit"
        )
    finally:
        if original_name is not None:
            async with SessionLocal() as writer:
                await writer.execute(
                    text(
                        "UPDATE localized_name SET name=:name WHERE entity_type='pokemon-species' "
                        "AND entity_id=25 AND locale='zh-Hans'"
                    ),
                    {"name": original_name},
                )
                await writer.commit()
                await rebuild_indexes(writer, force=True)
                await writer.commit()
        await second_engine.dispose()
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
