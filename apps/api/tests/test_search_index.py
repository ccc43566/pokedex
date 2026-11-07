import asyncio
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from test_names import name_families  # noqa: F401
from test_pokemon_api import seed_pikachu

from pokedex_api.models import LocalizedName, PokemonSearchIndex
from pokedex_api.services.names import matching_name_ids
from pokedex_api.services.search_index import (
    SearchCache,
    WorkerCaches,
    data_version,
    matching_ids,
    rebuild_indexes,
    search_index,
    worker,
)


@pytest.mark.parametrize("locale", ["zh-Hans", "en"])
@pytest.mark.usefixtures("name_families")
async def test_index_preserves_appearance_matching(session, locale):
    version = await rebuild_indexes(session)
    await session.commit()
    index = await search_index(session, locale, version)
    for query in [
        "皮卡",
        "Minior Orange Core",
        "Mega Female",
        "Mega Male",
        "Zygarde 50 Aura Break",
        "Galarian Zen Mode",
        "Own Tempo",
        "超能妙喵",
        "MEGA",
        "does-not-exist",
        "%",
        "Pa’u",
    ]:
        assert set(matching_ids(index, query)) == set(
            await matching_name_ids(session, query, locale)
        )


async def test_shared_revision_invalidates_workers_and_persisted_snapshot(
    client: AsyncClient,
    session: AsyncSession,
):
    await seed_pikachu(session)
    old_version = await rebuild_indexes(session)
    await session.commit()
    first = (await client.get("/api/v1/pokemon?q=皮卡")).json()
    assert first["dataVersion"] == old_version
    # An unrelated worker owns independent caches and sees the same DB version.
    second_worker = WorkerCaches()
    assert second_worker.results is not worker(session).results
    await session.execute(
        text(
            "UPDATE localized_name SET name='电气鼠' "
            "WHERE entity_type='pokemon-species' AND locale='zh-Hans' AND entity_id=25"
        )
    )
    await session.commit()
    new_version = await data_version(session)
    assert new_version != old_version
    assert await session.scalar(select(PokemonSearchIndex.version).limit(1)) == old_version
    # Both workers reject the old persisted snapshot, even before maintenance.
    assert (await client.get("/api/v1/pokemon?q=皮卡")).json()["total"] == 0
    new = (await client.get("/api/v1/pokemon?q=电气鼠")).json()
    assert new["items"][0]["displayName"] == "电气鼠"
    assert new["dataVersion"] == new_version
    snapshot = await second_worker.index.load(
        (new_version,),
        lambda: search_index(session, "zh-Hans", new_version),
    )
    assert matching_ids(snapshot, "电气鼠") == [25]
    assert (await client.get("/api/v1/pokemon/revision")).json()["version"] == new_version
    # Failed rebuild rolls back, leaving the old snapshot unusable, not current.
    await rebuild_indexes(session, force=True)
    await session.rollback()
    assert await session.scalar(select(PokemonSearchIndex.version).limit(1)) == old_version
    assert (await client.get("/api/v1/pokemon?q=电气鼠")).json()["total"] == 1


async def test_cache_coalesces_retries_bounds_and_expires():
    cache = SearchCache(capacity=2, ttl=0.02)
    release = asyncio.Event()
    calls = 0

    async def produce():
        nonlocal calls
        calls += 1
        await release.wait()
        return 25

    tasks = [asyncio.create_task(cache.load(("same",), produce)) for _ in range(5)]
    await asyncio.sleep(0)
    release.set()
    assert await asyncio.gather(*tasks) == [25] * 5
    assert calls == 1
    await cache.load(("second",), produce)
    await cache.load(("third",), produce)
    assert len(cache.values) == 2 and ("same",) not in cache.values
    await asyncio.sleep(0.03)
    await cache.load(("third",), produce)
    assert calls == 4
    failed = AsyncMock(side_effect=ValueError("failure"))
    for _ in range(2):
        with pytest.raises(ValueError):
            await cache.load(("bad",), failed)
    assert failed.await_count == 2
    assert not cache.locks


async def test_all_filters_pages_and_language_have_distinct_results(client, session):
    await seed_pikachu(session)
    for params, expected in [
        ({"q": "Pikachu"}, 1),
        ({"q": "皮卡"}, 1),
        ({"q": "25"}, 1),
        ({"q": "25.1"}, 0),
        ({"q": "25", "type": "fire"}, 0),
        ({"q": "25", "type": "electric", "generation": 1}, 1),
        ({"q": "25", "generation": 2}, 0),
        ({"q": "25", "isMega": "true"}, 0),
        ({"q": "25", "isGigantamax": "true"}, 0),
        ({"q": "25", "isLegendary": "true"}, 0),
        ({"q": "25", "isMythical": "true"}, 0),
    ]:
        for locale in ["zh-Hans", "en"]:
            result = (
                await client.get("/api/v1/pokemon", params={**params, "locale": locale})
            ).json()
            assert result["total"] == expected
            if expected:
                assert result["items"][0]["localizedName"] == (
                    "皮卡丘" if locale == "zh-Hans" else "Pikachu"
                )
    await session.execute(text("UPDATE media_asset SET local_path='changed.png'"))
    await session.commit()
    result = (await client.get("/api/v1/pokemon?q=25")).json()
    assert result["items"][0]["spriteUrl"].endswith("changed.png")


async def test_rollback_does_not_invalidate_committed_revision(session):
    await seed_pikachu(session)
    before = await data_version(session)
    session.add(
        LocalizedName(entity_type="pokemon-species", entity_id=25, locale="en", name="Mouse")
    )
    await session.flush()
    assert await data_version(session) != before
    await session.rollback()
    assert await data_version(session) == before


async def test_failed_rebuild_cannot_publish_a_partial_snapshot(session, monkeypatch):
    from pokedex_api.services import search_index as service

    await seed_pikachu(session)
    before = await rebuild_indexes(session)
    await session.commit()
    session.add(
        LocalizedName(entity_type="pokemon-species", entity_id=25, locale="en", name="Mouse")
    )
    await session.commit()
    original = service.build_index

    async def fail_second_locale(db, locale):
        if locale == "en":
            raise RuntimeError("interrupted rebuild")
        return await original(db, locale)

    with monkeypatch.context() as context:
        context.setattr(service, "build_index", fail_second_locale)
        with pytest.raises(RuntimeError, match="interrupted rebuild"):
            await rebuild_indexes(session, force=True)
        await session.rollback()
    versions = (await session.scalars(select(PokemonSearchIndex.version))).all()
    assert versions == [before, before]
    current = await data_version(session)
    assert current != before
    assert matching_ids(await search_index(session, "en", current), "Mouse") == [25]
