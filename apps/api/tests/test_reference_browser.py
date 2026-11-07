from __future__ import annotations

from typing import Any

import pytest
import respx
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from test_catalog import seed_family
from test_reference_data import BASE, importer, mock_api, payloads

from pokedex_api.models import LocalizedName, LocalizedText, SourceRecord
from pokedex_api.reference_models import (
    CatalogDictionary,
    CatalogMachine,
    Item,
    ItemMedia,
    Move,
    PokemonHeldItem,
    PokemonMove,
)
from pokedex_api.services.reference_browser import evolution_reference_nodes, price_value
from pokedex_api.sync.provider import PokeApiProvider


@pytest.fixture
async def catalog(session: AsyncSession) -> None:
    with respx.mock as routes:
        data = payloads()
        data["move", 1]["flavor_text_entries"][0]["version_group"]["name"] = "red-blue"
        mock_api(routes, data)
        async with PokeApiProvider(BASE, "test", concurrency=1) as provider:
            assert (await importer(session, provider).run(skip_links=True))["status"] == "success"
            await importer(session, provider).run(
                skip_links=True, only={("move-learn-method", 1), ("version", 1)}
            )
    for number in (723, 2279):
        source = SourceRecord(
            resource_type="item",
            resource_id=number,
            name="roseli-berry",
            source_url=f"{BASE}/item/{number}/",
            source_hash="d" * 64,
            raw_payload={"keep": "untouched"},
        )
        session.add(source)
        await session.flush()
        session.add(
            Item(
                id=number,
                name="roseli-berry",
                source_record_id=source.id,
                sprites={"default": "same.png"},
            )
        )
        session.add(
            LocalizedName(entity_type="item", entity_id=number, locale="en", name="Roseli Berry")
        )
        session.add(
            ItemMedia(
                item_id=number,
                source_url="same.png",
                status="downloaded",
                local_path="shared.png",
                checksum="f" * 64,
            )
        )
    session.add_all(
        [
            LocalizedText(
                entity_type="move",
                entity_id=1,
                locale="en",
                text_kind="flavor",
                version="version_group:yellow",
                text="Historical English",
            ),
            LocalizedText(
                entity_type="move",
                entity_id=1,
                locale="zh-Hans",
                text_kind="flavor",
                version="version_group:yellow",
                text="历史中文",
            ),
        ]
    )
    await session.commit()


async def test_search_paging_duplicate_identifiers_and_id_resolution(
    client: AsyncClient,
    catalog: None,
) -> None:
    listing = (await client.get("/api/v1/items?q=Roseli&page_size=1")).json()
    assert listing["total"] == 2 and listing["totalPages"] == 2
    first = listing["items"][0]
    assert first["id"] == 723 and first["localizedName"] == "Roseli Berry"
    assert first["nameLocale"] == "en"
    second = (await client.get("/api/v1/items?q=roseli-berry&page=2&page_size=1")).json()
    assert second["items"][0]["id"] == 2279
    assert second["items"][0]["imageUrl"] == first["imageUrl"] == "/media/shared.png"
    assert (await client.get("/api/v1/items/roseli-berry")).status_code == 409
    for number in (723, 2279):
        assert (await client.get(f"/api/v1/items/{number}")).json()["record"]["id"] == number
    assert (await client.get("/api/v1/items?q=2279")).json()["total"] == 1
    assert (await client.get("/api/v1/items?q=樱子果")).json()["items"][0]["id"] == 1
    assert (await client.get("/api/v1/items?q=%25")).json()["total"] == 0
    assert (await client.get("/api/v1/items?page_size=101")).status_code == 422
    assert (await client.get("/api/v1/items/999999")).status_code == 404


async def test_official_category_and_pocket_use_upstream_ids(
    client: AsyncClient,
    catalog: None,
    session: AsyncSession,
) -> None:
    # Internal dictionary PKs need not equal upstream IDs.
    dictionary = await session.scalar(
        select(CatalogDictionary).where(CatalogDictionary.resource_type == "item-pocket")
    )
    assert dictionary and dictionary.id != dictionary.resource_id
    filters = (await client.get("/api/v1/items/filters")).json()
    assert filters["categoryPockets"] == {"1": 1}
    assert (await client.get("/api/v1/items?pocket=1&category=1")).json()["total"] == 1
    assert (await client.get("/api/v1/items?pocket=999")).json()["total"] == 0


async def test_item_prices_berry_source_and_media_never_use_pokemon_id(
    client: AsyncClient,
    catalog: None,
    session: AsyncSession,
) -> None:
    from pokedex_api.models import MediaAsset, Pokemon

    session.add(Pokemon(id=1, name="wrong-pokemon", raw_payload={}))
    session.add(
        MediaAsset(
            pokemon_id=1, kind="front-default", source_url="wrong.png", local_path="wrong.png"
        )
    )
    await session.commit()
    detail = (await client.get("/api/v1/items/1")).json()
    assert detail["record"]["imageUrl"] is None
    assert detail["fields"]["berry"]["itemId"] == 1
    prices = detail["fields"]["prices"]
    assert prices[0]["purchase"] == {"value": None, "status": "unavailable"}
    assert prices[0]["sell"] == {"value": 0, "status": "value"}
    assert prices[1]["purchase"] == {"value": 300, "status": "value"}
    assert prices[0]["versionGroup"]["id"] != prices[1]["versionGroup"]["id"]
    assert detail["fields"]["legacyCost"] == 80  # not substituted for missing version prices
    assert "rawPayload" not in detail and "hash" in detail["source"]
    missing = (await client.get("/api/v1/items/723")).json()
    assert missing["fields"]["prices"] == []
    assert price_value(None, {}, "purchase_price") == {"value": None, "status": "unknown"}


async def test_move_nulls_zero_history_contexts_and_filters(
    client: AsyncClient,
    catalog: None,
    session: AsyncSession,
) -> None:
    move = await session.get(Move, 2)
    assert move
    move.power, move.accuracy, move.pp = None, None, 0
    await session.commit()
    response = (await client.get("/api/v1/moves?type=1&damage_class=1")).json()
    assert response["total"] == 1 and response["items"][0]["localizedName"] == "拍击"
    detail = (await client.get("/api/v1/moves/2")).json()
    assert detail["record"]["power"] is None and detail["record"]["accuracy"] is None
    assert detail["record"]["pp"] == 0
    detail = (await client.get("/api/v1/moves/1")).json()
    assert detail["fields"]["pastValues"][0]["power"] == 35
    assert detail["fields"]["pastValues"][0]["accuracy"] is None
    assert [t["text"] for t in detail["texts"]] == ["Old text", "历史中文"]
    assert {t["context"]["id"] for t in detail["texts"]} == {1, 2}
    english = (await client.get("/api/v1/moves/1?locale=en")).json()
    assert english["record"]["localizedName"] == "Pound"
    assert "Historical English" in [t["text"] for t in english["texts"]]


async def test_relations_preserve_independent_forms_versions_rarity_and_machine_ids(
    client: AsyncClient,
    catalog: None,
    session: AsyncSession,
) -> None:
    family = await seed_family(session, variants=2)
    dictionaries = {
        (d.resource_type, d.resource_id): d.id
        for d in (await session.scalars(select(CatalogDictionary))).all()
    }
    for index, pid in enumerate(family):
        for vg in (1, 2):
            session.add(
                PokemonMove(
                    pokemon_id=pid,
                    move_ordinal=0,
                    detail_ordinal=vg,
                    move_id=1,
                    version_group_id=dictionaries["version-group", vg],
                    learn_method_id=dictionaries["move-learn-method", 1],
                    level_learned_at=7 + index,
                    learn_order=0,
                    raw_payload={},
                )
            )
    session.add(
        PokemonHeldItem(
            pokemon_id=family[1],
            item_ordinal=0,
            detail_ordinal=0,
            item_id=1,
            version_id=dictionaries["version", 1],
            rarity=37,
            raw_payload={},
        )
    )
    for mid, vg in [(8, 1), (9, 2)]:
        session.add(
            CatalogMachine(
                id=mid,
                item_id=1,
                move_id=1,
                source_record_id=(await session.get(Move, 1)).source_record_id,
                version_group_id=dictionaries["version-group", vg],
            )
        )
    await session.commit()
    page = (
        await client.get("/api/v1/moves/1/learners?version_group=2&method=1&page_size=1")
    ).json()
    assert page["total"] == 2 and page["totalPages"] == 2
    row = (
        await client.get("/api/v1/moves/1/learners?version_group=2&method=1&page_size=1&page=2")
    ).json()["items"][0]
    assert row["pokemonId"] == family[1] and row["displayNumber"] == "892.1"
    assert row["level"] == 8 and row["order"] == 0 and row["versionGroup"]["id"] == 2
    holder = (await client.get("/api/v1/items/1/holders?version=1")).json()["items"][0]
    assert holder["pokemonId"] == family[1] and holder["rarity"] == 37
    machines = (await client.get("/api/v1/items/1/machines")).json()["items"]
    assert [r["id"] for r in machines] == [8, 9]
    assert [r["versionGroup"]["id"] for r in machines] == [1, 2]
    assert (await client.get("/api/v1/items/1/learners")).status_code == 404


def test_evolution_reference_path_is_structural_and_retains_actual_method() -> None:
    target = {"evolves_to": [], "evolution_details": [{"required_pokemon_form": {"url": "x"}}]}
    source = {"evolves_to": [target]}
    payload: dict[str, Any] = {"chain": source}
    parent, child, method = evolution_reference_nodes(
        payload, "$.chain.evolves_to[0].evolution_details[0].held_item"
    )
    assert parent is source and child is target and method == target["evolution_details"][0]
    for path in ("$.chain.evolves_to[99].evolution_details[0].item", "__import__('os')"):
        assert evolution_reference_nodes(payload, path) == (None, None, {})


async def test_item_evolution_links_keep_cosmetic_form_keys_and_reject_invalid_form_refs(
    client: AsyncClient,
    catalog: None,
    session: AsyncSession,
) -> None:
    from test_reference_data import ref

    from pokedex_api.models import EvolutionChain, PokemonForm
    from pokedex_api.reference_models import EvolutionItemReference

    family = await seed_family(session, variants=2)
    session.add(
        PokemonForm(
            id=55555,
            pokemon_id=family[1],
            name="urshifu-test-appearance",
            form_name="test-appearance",
            is_default=False,
            raw_payload={"form_names": [{"language": {"name": "en"}, "name": "Test Appearance"}]},
        )
    )
    children = [
        {
            "species": ref("pokemon-species", 892),
            "evolution_details": [{"item": ref("item", 1), "evolved_pokemon_form": form}],
            "evolves_to": [],
        }
        for form in (ref("pokemon-form", 55555), ref("move", 1))
    ]
    session.add(
        EvolutionChain(
            id=999,
            raw_payload={"chain": {"species": ref("pokemon-species", 893), "evolves_to": children}},
        )
    )
    for i in range(2):
        session.add(
            EvolutionItemReference(
                chain_id=999,
                item_id=1,
                role="item",
                path=f"$.chain.evolves_to[{i}].evolution_details[0].item",
                raw_reference={},
            )
        )
    await session.commit()
    rows = (await client.get("/api/v1/items/1/evolutions")).json()["items"]
    assert rows[0]["source"]["pokemonId"] == 893
    assert rows[0]["target"]["pokemonId"] == family[1]
    assert rows[0]["target"]["formKey"] == "form:55555"
    assert rows[0]["target"]["displayNumber"] == "892.1"
    assert "pokemonId" not in rows[1]["target"]
