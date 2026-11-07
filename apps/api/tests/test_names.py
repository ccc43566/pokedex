import json
from pathlib import Path
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from pokedex_api.models import (
    Ability,
    LocalizedName,
    Pokemon,
    PokemonAbility,
    PokemonForm,
    PokemonSpecies,
)
from pokedex_api.services.names import form_label


@pytest.fixture
async def name_families(session: AsyncSession) -> dict[str, Any]:
    data: dict[str, Any] = json.loads(
        (Path(__file__).parent / "fixtures/name-families.json").read_text(encoding="utf-8")
    )
    for s in data["species"]:
        session.add(PokemonSpecies(id=s["id"], name=s["name"], raw_payload={"names": s["names"]}))
        for n in s["names"]:
            raw_locale = n["language"]["name"]
            if raw_locale.lower() in {"en", "zh-hans"}:
                session.add(
                    LocalizedName(
                        entity_type="pokemon-species",
                        entity_id=s["id"],
                        locale="zh-Hans" if raw_locale.lower() == "zh-hans" else "en",
                        name=n["name"],
                    )
                )
    ability_ids = {
        name: i + 1
        for i, name in enumerate(sorted({a for p in data["pokemon"] for a in p["abilities"]}))
    }
    for name, aid in ability_ids.items():
        session.add(Ability(id=aid, name=name))
    for p in data["pokemon"]:
        session.add(Pokemon(**{k: v for k, v in p.items() if k != "abilities"}))
        for slot, name in enumerate(p["abilities"], 1):
            session.add(PokemonAbility(pokemon_id=p["id"], ability_id=ability_ids[name], slot=slot))
    for f in data["forms"]:
        session.add(PokemonForm(**{k: v for k, v in f.items() if k != "raw"}, raw_payload=f["raw"]))
    await session.commit()
    return data


@pytest.mark.parametrize(
    ("pid", "expected"),
    [
        (678, "超能妙喵（Male）"),
        (10025, "超能妙喵（Female）"),
        (10314, "超能妙喵（Mega Male）"),
        (10326, "超能妙喵（Mega Female）"),
        (718, "基格尔德（50% Forme · Aura Break）"),
        (10118, "基格尔德（10% Forme · Power Construct）"),
        (10119, "基格尔德（50% Forme · Power Construct）"),
        (10181, "基格尔德（10% Forme · Aura Break）"),
        (10017, "达摩狒狒（Zen Mode）"),
        (10178, "达摩狒狒（Galarian Zen Mode）"),
        (744, "岩狗狗"),
        (10151, "岩狗狗（Own Tempo）"),
    ],
)
async def test_labels_shared_by_cards_detail_options_and_search(
    client: AsyncClient,
    name_families: dict[str, Any],
    pid: int,
    expected: str,
) -> None:
    detail = (await client.get(f"/api/v1/pokemon/{pid}")).json()
    assert detail["displayName"] == expected
    default = next(o for o in detail["formOptions"] if o["pokemonId"] == pid and o["isDefault"])
    assert default["label"] == expected
    record = next(p for p in name_families["pokemon"] if p["id"] == pid)
    listing = (
        await client.get("/api/v1/pokemon", params={"q": record["name"], "pageSize": 100})
    ).json()
    card = next(p for p in listing["items"] if p["id"] == pid)
    assert card["displayName"] == expected
    assert card["displayNumber"] == detail["displayNumber"]
    assert (await client.get(f"/api/v1/pokemon/{record['name']}")).json()["id"] == pid


async def test_all_minior_colours_are_distinct_without_changing_records(
    client: AsyncClient,
    name_families: dict[str, Any],
) -> None:
    listing = (await client.get("/api/v1/pokemon?q=774&pageSize=100")).json()
    assert listing["total"] == 14
    assert [p["displayNumber"] for p in listing["items"]] == [
        "774",
        *[f"774.{i}" for i in range(1, 14)],
    ]
    colours = ["Red", "Orange", "Yellow", "Green", "Blue", "Indigo", "Violet"]
    assert [p["variantLabel"] for p in listing["items"]] == [
        *[f"Meteor · {c} Core" for c in colours],
        *[f"{c} Core" for c in colours],
    ]
    for query, expected in [
        ("Minior Orange Core", {10130, 10137}),
        ("Mega Female", {10326}),
        ("Mega Male", {10314}),
        ("Zygarde 50 Aura Break", {718}),
        ("Galarian Zen Mode", {10178}),
        ("Own Tempo", {10151}),
    ]:
        found = (await client.get("/api/v1/pokemon", params={"q": query, "pageSize": 100})).json()
        assert {p["id"] for p in found["items"]} == expected


@pytest.mark.parametrize(
    ("identifier", "seed", "expected"),
    [
        ("galar-mega-female", "Mega Form", "Galarian Mega Female"),
        ("hisui-zen", "Zen Mode", "Hisuian Zen Mode"),
        ("mega-female", "Mega Female", "Mega Female"),
        ("alola-cap", "Alola Cap", "Alola Cap"),
        ("starter", "Partner", "Partner"),
    ],
)
def test_qualifier_completion_is_generic_and_does_not_repeat_information(
    identifier: str,
    seed: str,
    expected: str,
) -> None:
    form = PokemonForm(
        name=f"example-{identifier}",
        form_name=identifier,
        raw_payload={"form_names": [{"name": seed, "language": {"name": "en"}}]},
    )
    assert form_label(form, "Example", identifier, species_slug="example") == expected


@pytest.mark.parametrize(
    ("pid", "key", "expected"),
    [
        (592, "form:10552", "轻飘飘（Female）"),
        (593, "form:10553", "胖嘟嘟（Female）"),
        (668, "form:10551", "火炎狮（Female）"),
        (666, "form:10162", "彩粉蝶（Poké Ball Pattern）"),
        (201, "form:10026", "未知图腾（!）"),
        (493, "form:10057", "阿尔宙斯（??? Type）"),
    ],
)
async def test_cosmetic_forms_override_owner_appearance_without_duplicate_qualifiers(
    client: AsyncClient,
    name_families: dict[str, Any],
    pid: int,
    key: str,
    expected: str,
) -> None:
    detail = (await client.get(f"/api/v1/pokemon/{pid}", params={"form": key})).json()
    choice = next(o for o in detail["formOptions"] if o["key"] == key)
    assert choice["label"] == expected
    current = next(n for n in detail["evolutionGraph"]["nodes"] if n["isCurrent"])
    assert current["label"] == expected
