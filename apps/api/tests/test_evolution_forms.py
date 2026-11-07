import json
from pathlib import Path
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from pokedex_api.models import EvolutionChain, MediaAsset, Pokemon, PokemonForm, PokemonSpecies


@pytest.fixture
async def family_data(session: AsyncSession) -> dict[str, Any]:
    data: dict[str, Any] = json.loads(
        (Path(__file__).parent / "fixtures/form-evolutions.json").read_text(encoding="utf-8")
    )
    for s in data["species"]:
        session.add(PokemonSpecies(id=s["id"], name=s["name"], evolution_chain_id=s["chain_id"]))
    for chain in data["chains"]:
        session.add(EvolutionChain(id=chain["id"], raw_payload=chain))
    for p in data["pokemon"]:
        session.add(Pokemon(**p))
        session.add(
            MediaAsset(
                pokemon_id=p["id"],
                kind="official-artwork",
                source_url=f"https://example.test/{p['id']}.png",
                local_path=f"existing/{p['id']}.png",
            )
        )
    for form in data["forms"]:
        session.add(PokemonForm(**form))
    await session.commit()
    return data


def edges(graph: dict[str, Any]) -> set[tuple[str, str]]:
    return {(e["source"], e["target"]) for e in graph["edges"]}


async def graph(client: AsyncClient, identifier: str | int, form: str = "") -> dict[str, Any]:
    response = await client.get(f"/api/v1/pokemon/{identifier}", params={"form": form})
    assert response.status_code == 200
    return response.json()["evolutionGraph"]


async def test_regions_match_source_and_target_not_the_entire_chain(
    client: AsyncClient,
    family_data: dict[str, Any],
) -> None:
    ordinary = await graph(client, 52)
    alola = await graph(client, "meowth-alola")
    galar = await graph(client, "meowth-galar")
    assert edges(ordinary) == {("pokemon:52", "pokemon:53")}
    assert edges(alola) == {("pokemon:10107", "pokemon:10108")}
    assert edges(galar) == {("pokemon:10161", "pokemon:863")}
    assert alola["edges"][0]["methods"][0]["min_happiness"] == 160
    assert galar["edges"][0]["methods"][0]["min_level"] == 28
    raichu = await graph(client, "raichu-alola")
    assert edges(raichu) == {("pokemon:172", "pokemon:25"), ("pokemon:25", "pokemon:10100")}
    assert {n["label"] for n in raichu["nodes"]} == {"Pichu", "Pikachu", "Raichu（Alolan）"}
    assert raichu["edges"][-1]["methods"][0]["region"]["name"] == "alola"


async def test_paths_keep_every_condition_and_real_sibling_edges(
    client: AsyncClient,
    family_data: dict[str, Any],
) -> None:
    eevee = await graph(client, 133)
    assert len(eevee["edges"]) == 8
    assert {e["source"] for e in eevee["edges"]} == {"pokemon:133"}
    leafeon = next(e for e in eevee["edges"] if e["target"] == "pokemon:470")
    assert len(leafeon["methods"]) == 6
    original = next(c for c in family_data["chains"] if c["id"] == 67)
    raw = next(n for n in original["chain"]["evolves_to"] if n["species"]["name"] == "leafeon")
    assert leafeon["methods"] == raw["evolution_details"]
    qwilfish = await graph(client, "qwilfish-hisui")
    assert len(qwilfish["edges"][0]["methods"]) == 3
    assert not (await graph(client, 211))["edges"]
    urshifu = await graph(client, "urshifu-rapid-strike")
    assert edges(urshifu) == {("pokemon:891", "pokemon:10191")}
    assert len(urshifu["edges"][0]["methods"]) == 2


async def test_cosmetic_form_urls_and_three_stages_are_exact(
    client: AsyncClient,
    family_data: dict[str, Any],
) -> None:
    burmy = await graph(client, 412, "form:10034")
    assert edges(burmy) == {("form:10034", "pokemon:10004"), ("form:10034", "pokemon:414")}
    butterfly = await graph(client, 666, "form:10087")
    assert edges(butterfly) == {("form:10271", "form:10290"), ("form:10290", "form:10087")}
    for node in butterfly["nodes"]:
        assert node["query"] == {"form": node["key"]}
    alcremie = await graph(client, 869, "form:10449")
    assert len(alcremie["edges"]) == 1
    assert alcremie["edges"][0]["target"] == "form:10449"
    assert alcremie["edges"][0]["methods"][0]["condition_expression"]["expression"]
    assert alcremie["nodes"][-1]["spriteUrl"] is None  # never substitute another form's art


async def test_unmapped_special_forms_are_isolated_and_missing_refs_fail_closed(
    client: AsyncClient,
    session: AsyncSession,
    family_data: dict[str, Any],
) -> None:
    for identifier, form in [
        (10093, ""),
        ("meowth-gmax", ""),
        ("urshifu-rapid-strike-gmax", ""),
        (172, "form:10065"),
    ]:
        special = await graph(client, identifier, form)
        assert len(special["nodes"]) == 1
        assert not special["edges"]
        assert special["warnings"]
    chain = await session.get(EvolutionChain, 22)
    assert chain is not None
    raw = json.loads(json.dumps(chain.raw_payload))
    raw["chain"]["evolves_to"][0]["evolution_details"][1]["evolved_pokemon_form"]["url"] = (
        "https://pokeapi.co/api/v2/pokemon-form/999999/"
    )
    chain.raw_payload = raw
    await session.commit()
    incomplete = await graph(client, "meowth-alola")
    assert not incomplete["edges"]
    assert any("引用缺失" in warning for warning in incomplete["warnings"])
