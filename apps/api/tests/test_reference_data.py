from __future__ import annotations

import copy
from typing import Any
from unittest.mock import patch

import httpx
import pytest
import respx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from tenacity import wait_none

from pokedex_api.models import EvolutionChain, LocalizedName, Pokemon, SourceRecord
from pokedex_api.reference_models import (
    Berry,
    CatalogDiscoveryPage,
    CatalogReferenceIssue,
    CatalogSyncEntry,
    EvolutionItemReference,
    Item,
    ItemPrice,
    Move,
    PokemonHeldItem,
    PokemonMove,
)
from pokedex_api.services.reference_catalog import reference_name, reference_texts
from pokedex_api.sync.provider import PokeApiProvider
from pokedex_api.sync.reference_data import ReferenceImporter, localized_rows

BASE = "https://example.test/api/v2"


def ref(kind: str, number: int) -> dict[str, Any]:
    return dict(name=f"{kind}-{number}", url=f"{BASE}/{kind}/{number}/")


def names(en: str, zh: str | None = None) -> list[dict[str, Any]]:
    result = [dict(name=en, language=dict(name="en"))]
    if zh:
        result.append(dict(name=zh, language=dict(name="zh-hans")))
    return result


def payloads() -> dict[tuple[str, int], dict[str, Any]]:
    return {
        ("move", 1): dict(
            id=1,
            name="pound",
            names=names("Pound", "拍击"),
            power=40,
            accuracy=100,
            pp=35,
            priority=0,
            meta={"ailment": ref("move-ailment", -1)},
            type=ref("type", 1),
            damage_class=ref("move-damage-class", 1),
            target=ref("move-target", 1),
            past_values=[dict(version_group=ref("version-group", 1), power=35)],
            flavor_text_entries=[
                dict(
                    flavor_text="Old text",
                    language=dict(name="en"),
                    version_group=ref("version-group", 1),
                )
            ],
        ),
        ("move", 2): dict(
            id=2, name="chop", names=names("Chop"), power=50, accuracy=100, pp=25, priority=0
        ),
        ("item", 1): dict(
            id=1,
            name="cheri-berry",
            names=names("Cheri Berry", "樱子果"),
            cost=80,
            category=ref("item-category", 1),
            sprites=dict(default="x.png"),
            prices=[
                dict(
                    currency=ref("currency", 1),
                    version_group=ref("version-group", 1),
                    purchase_price=None,
                    sell_price=0,
                ),
                dict(
                    currency=ref("currency", 1),
                    version_group=ref("version-group", 2),
                    purchase_price=300,
                    sell_price=150,
                ),
            ],
        ),
        ("berry", 1): dict(
            id=1, name="cheri", item=ref("item", 1), growth_time=3, natural_gift_type=ref("type", 1)
        ),
        ("item-category", 1): dict(
            id=1, name="berries", names=names("Berries"), pocket=ref("item-pocket", 1)
        ),
        ("item-pocket", 1): dict(id=1, name="berries", names=names("Berries")),
        ("type", 1): dict(id=1, name="normal"),
        ("move-damage-class", 1): dict(id=1, name="physical"),
        ("move-target", 1): dict(id=1, name="selected-pokemon"),
        ("move-ailment", -1): dict(id=-1, name="unknown"),
        ("version-group", 1): dict(id=1, name="red-blue"),
        ("version-group", 2): dict(id=2, name="yellow"),
        ("currency", 1): dict(id=1, name="poke-dollar"),
        ("version", 1): dict(id=1, name="red", version_group=ref("version-group", 1)),
        ("move-learn-method", 1): dict(id=1, name="level-up"),
    }


def mock_api(route: respx.MockRouter, data: dict[tuple[str, int], dict[str, Any]]) -> list[str]:
    visited: list[str] = []

    def respond(request: httpx.Request) -> httpx.Response:
        visited.append(str(request.url))
        kind = request.url.path.rstrip("/").split("/")[-1]
        if request.url.params:
            ids = sorted(number for (k, number) in data if k == kind)
            offset = int(request.url.params.get("offset", "0"))
            limit = int(request.url.params["limit"])
            next_url = (
                f"{BASE}/{kind}/?limit={limit}&offset={offset + limit}"
                if offset + limit < len(ids)
                else None
            )
            return httpx.Response(
                200,
                json=dict(
                    count=len(ids),
                    next=next_url,
                    results=[ref(kind, n) for n in ids[offset : offset + limit]],
                ),
            )
        parts = request.url.path.rstrip("/").split("/")
        key = parts[-2], int(parts[-1])
        return httpx.Response(200, json=data[key]) if key in data else httpx.Response(404)

    route.get(url__startswith=BASE).mock(side_effect=respond)
    return visited


def importer(session: AsyncSession, provider: PokeApiProvider) -> ReferenceImporter:
    assert session.bind is not None
    return ReferenceImporter(
        async_sessionmaker(session.bind, expire_on_commit=False), provider, concurrency=1
    )


@pytest.mark.asyncio
async def test_complete_pagination_scope_and_idempotence(session: AsyncSession) -> None:
    with respx.mock as routes:
        visited = mock_api(routes, payloads())
        async with PokeApiProvider(BASE, "test", concurrency=1, page_size=1) as provider:
            first = await importer(session, provider).run(skip_links=True)
            assert first["status"] == "success"
            assert first["counts"]["discovery"]["move"]["pages"] == 2
            assert await session.scalar(select(func.count()).select_from(Move)) == 2
            assert await session.scalar(select(func.count()).select_from(Item)) == 1
            assert await session.scalar(select(func.count()).select_from(Berry)) == 1
            original = list(visited)
            assert (await importer(session, provider).run(skip_links=True))["status"] == "success"
            assert all("?" in url for url in visited[len(original) :])  # lists only, no refetch
            assert not any("pokemon/" in u or "x.png" in u for u in visited)
    assert await session.scalar(select(func.count()).select_from(Move)) == 2
    prices = (await session.scalars(select(ItemPrice).order_by(ItemPrice.ordinal))).all()
    assert len(prices) == 2
    assert prices[0].purchase_price is None and prices[0].sell_price == 0
    assert prices[1].purchase_price == 300 and prices[1].sell_price == 150
    assert (
        await session.scalar(
            select(func.count())
            .select_from(LocalizedName)
            .where(LocalizedName.entity_type == "move")
        )
        == 3
    )
    assert await reference_name(session, "move", 2) == "Chop"
    assert await reference_name(session, "berry", 1) == "樱子果"
    assert (await reference_texts(session, "move", 1))[0].text == "Old text"
    assert await session.scalar(select(func.count()).select_from(CatalogDiscoveryPage)) == 8
    assert await session.scalar(
        select(SourceRecord.source_hash).where(
            SourceRecord.resource_type == "move", SourceRecord.resource_id == 1
        )
    )


@pytest.mark.asyncio
async def test_interruption_resume_and_individual_retry(session: AsyncSession) -> None:
    data = payloads()
    with respx.mock as routes:
        mock_api(routes, data)
        async with PokeApiProvider(BASE, "test", concurrency=1, page_size=1) as provider:
            first = await importer(session, provider).run(skip_links=True, stop_after=1)
            assert first["status"] == "interrupted"
            assert await session.scalar(select(func.count()).select_from(SourceRecord)) == 1
            second = await importer(session, provider).run(
                skip_links=True, resume_run=first["run_id"]
            )
            assert second["status"] == "success"
            # A source failure is durable and cannot delete an existing normalized resource.
            data[("move", 2)]["id"] = 999
            failure = await importer(session, provider).run(
                skip_links=True, only={("move", 2)}, refresh=True
            )
            assert failure["status"] == "partial"
            assert await session.get(Move, 2)
            state = await session.get(CatalogSyncEntry, ("move", 2))
            assert state and state.status == "failed" and "Response ID" in (state.error or "")
            data[("move", 2)]["id"] = 2
            assert (await importer(session, provider).run(skip_links=True, retry_failed=True))[
                "status"
            ] == "success"
    assert await session.scalar(select(func.count()).select_from(Move)) == 2


@pytest.mark.asyncio
async def test_per_record_learning_held_rarity_and_unresolved(session: AsyncSession) -> None:
    detail = dict(
        level_learned_at=7,
        order=3,
        move_learn_method=ref("move-learn-method", 1),
        version_group=ref("version-group", 1),
    )
    raw = dict(
        moves=[dict(move=ref("move", 1), version_group_details=[detail])],
        held_items=[
            dict(item=ref("item", 1), version_details=[dict(rarity=37, version=ref("version", 1))])
        ],
    )
    session.add_all(
        [
            Pokemon(id=1, name="first", raw_payload=raw),
            Pokemon(id=10001, name="variant", raw_payload=copy.deepcopy(raw)),
        ]
    )
    await session.commit()
    session.add(
        EvolutionChain(
            id=1,
            raw_payload=dict(
                baby_trigger_item=ref("item", 1),
                chain=dict(
                    evolution_details=[dict(item=ref("item", 1)), dict(held_item=ref("item", 1))]
                ),
            ),
        )
    )
    await session.commit()
    with respx.mock as routes:
        mock_api(routes, payloads())
        async with PokeApiProvider(BASE, "test", concurrency=1, page_size=2) as provider:
            result = await importer(session, provider).run()
            assert result["status"] == "success"
            assert await session.scalar(select(func.count()).select_from(PokemonMove)) == 2
            held = (await session.scalars(select(PokemonHeldItem))).all()
            assert [r.rarity for r in held] == [37, 37]
            learned = await session.get(PokemonMove, (10001, 0, 0))
            assert learned and learned.learn_order == 3 and learned.level_learned_at == 7
            evolution_rows = (
                await session.scalars(
                    select(EvolutionItemReference).order_by(EvolutionItemReference.id)
                )
            ).all()
            assert {r.role for r in evolution_rows} == {"item", "held_item", "baby_trigger_item"}
            evolution_ids = [r.id for r in evolution_rows]
            assert (await importer(session, provider).run())["status"] == "success"
            assert (
                await session.scalars(
                    select(EvolutionItemReference.id).order_by(EvolutionItemReference.id)
                )
            ).all() == evolution_ids
            variant = await session.get(Pokemon, 10001)
            assert variant
            variant.raw_payload = dict(
                moves=[dict(move=ref("move", 999), version_group_details=[detail])], held_items=[]
            )
            await session.commit()
            result = await importer(session, provider).run()
            assert result["status"] == "partial"
    issues = (
        await session.scalars(
            select(CatalogReferenceIssue).where(CatalogReferenceIssue.resolved.is_(False))
        )
    ).all()
    assert (
        len(issues) == 1 and issues[0].owner_id == 10001 and "999" in (issues[0].target_url or "")
    )


@pytest.mark.asyncio
async def test_bad_pagination_is_rejected(session: AsyncSession) -> None:
    with respx.mock as routes:
        routes.get(f"{BASE}/move/?limit=1&offset=0").respond(
            200,
            json={
                "count": 2,
                "next": None,
                "results": [ref("move", 1)],
            },
        )
        async with PokeApiProvider(BASE, "test", page_size=1) as provider:
            with pytest.raises(ValueError, match="Incomplete"):
                await importer(session, provider).run(skip_links=True)


async def test_evolution_dictionary_scope_never_fetches_main_resources(
    session: AsyncSession,
) -> None:
    data = payloads()
    data[("evolution-trigger", 1)] = dict(id=1, name="level-up", names=names("Level up"))
    data[("evolution-variable", 1)] = dict(
        id=1,
        name="encryption-constant",
        symbol="EC",
        data_type="uint32",
        source="pokemon",
        version_group=ref("version-group", 1),
    )
    with respx.mock as routes:
        visited = mock_api(routes, data)
        async with PokeApiProvider(BASE, "test", concurrency=1, page_size=1) as provider:
            result = await importer(session, provider).run(dictionary_only=True)
            assert (
                result["status"] == "success"
                and result["counts"]["scope"] == "evolution-dictionaries"
            )
            assert (await importer(session, provider).run(dictionary_only=True))[
                "status"
            ] == "success"
    assert not any(
        f"/{kind}/" in u for kind in ["move", "item", "berry", "pokemon"] for u in visited
    )
    assert await session.scalar(select(func.count()).select_from(Move)) == 0


@pytest.mark.asyncio
async def test_distinct_upstream_ids_can_share_identifier(session: AsyncSession) -> None:
    data = payloads()
    data[("item", 2)] = {**copy.deepcopy(data[("item", 1)]), "id": 2}
    data[("item", 2)]["names"] = []
    with respx.mock as routes:
        mock_api(routes, data)
        async with PokeApiProvider(BASE, "test", concurrency=1) as provider:
            assert (await importer(session, provider).run(skip_links=True))["status"] == "success"
            assert (await importer(session, provider).run(skip_links=True))["status"] == "success"
    assert (
        await session.scalars(select(Item.id).where(Item.name == "cheri-berry").order_by(Item.id))
    ).all() == [1, 2]
    assert await reference_name(session, "item", 2) == "cheri-berry"


@pytest.mark.asyncio
async def test_transient_retry_and_remote_missing_preserve_local(session: AsyncSession) -> None:
    data = payloads()
    with respx.mock as routes:
        mock_api(routes, data)
        async with PokeApiProvider(BASE, "test", concurrency=1) as provider:
            assert (await importer(session, provider).run(skip_links=True))["status"] == "success"
    with respx.mock as routes, patch.object(PokeApiProvider._get.retry, "wait", wait_none()):
        route = routes.get(f"{BASE}/move/2/").mock(
            side_effect=[
                httpx.Response(503),
                httpx.Response(200, json=data[("move", 2)]),
            ]
        )
        async with PokeApiProvider(BASE, "test", concurrency=1) as provider:
            assert (
                await importer(session, provider).run(
                    skip_links=True, only={("move", 2)}, refresh=True
                )
            )["status"] == "success"
        assert route.call_count == 2
    with respx.mock as routes, patch.object(PokeApiProvider._get.retry, "wait", wait_none()):
        routes.get(f"{BASE}/move/2/").respond(404)
        async with PokeApiProvider(BASE, "test", concurrency=1) as provider:
            assert (
                await importer(session, provider).run(
                    skip_links=True, only={("move", 2)}, refresh=True
                )
            )["status"] == "partial"
        assert await session.get(Move, 2)
        state = await session.get(CatalogSyncEntry, ("move", 2))
        assert state and state.status == "missing" and state.error


def test_localized_history_preserves_context_and_no_translation() -> None:
    names_, texts = localized_rows(
        "move",
        1,
        dict(
            names=names("English only"),
            flavor_text_entries=[
                dict(
                    flavor_text="Old",
                    language=dict(name="en"),
                    version_group=ref("version-group", 1),
                ),
                dict(
                    flavor_text="New",
                    language=dict(name="en"),
                    version_group=ref("version-group", 2),
                ),
            ],
            effect_changes=[
                dict(
                    version_group=ref("version-group", 1),
                    effect_entries=[dict(effect="Former effect", language=dict(name="en"))],
                )
            ],
        ),
    )
    assert [n["locale"] for n in names_] == ["en"]
    assert len(texts) == 3 and len({t["version"] for t in texts}) == 2
    assert texts[-1]["text_kind"] == "past_effect"
