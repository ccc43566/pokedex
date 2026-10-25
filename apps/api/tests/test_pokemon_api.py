from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from pokedex_api.models import (
    GenerationEntity,
    LocalizedName,
    LocalizedText,
    MediaAsset,
    Pokemon,
    PokemonSpecies,
    PokemonStat,
    PokemonType,
    StatEntity,
    TypeEntity,
)


async def seed_pikachu(session: AsyncSession) -> None:
    session.add_all(
        [
            GenerationEntity(id=1, name="generation-i", main_region="kanto", raw_payload={}),
            TypeEntity(
                id=13,
                name="electric",
                damage_relations={"double_damage_to": [{"name": "water", "url": "x/3/"}]},
                past_damage_relations=[],
                raw_payload={},
            ),
            StatEntity(id=1, name="hp", is_battle_only=False, raw_payload={}),
            PokemonSpecies(
                id=25,
                name="pikachu",
                generation_id=1,
                evolution_chain_id=10,
                is_legendary=False,
                is_mythical=False,
                raw_payload={},
            ),
            Pokemon(
                id=25,
                name="pikachu",
                species_id=25,
                height=4,
                weight=60,
                base_experience=112,
                order=25,
                is_default=True,
                sprites={"front_default": "https://example.test/pikachu.png"},
                raw_payload={},
            ),
        ]
    )
    await session.flush()
    session.add_all(
        [
            LocalizedName(
                entity_type="pokemon-species",
                entity_id=25,
                locale="zh-Hans",
                name="皮卡丘",
                is_canonical=False,
            ),
            LocalizedName(
                entity_type="pokemon-species",
                entity_id=25,
                locale="en",
                name="Pikachu",
                is_canonical=True,
            ),
            LocalizedName(
                entity_type="type",
                entity_id=13,
                locale="zh-Hans",
                name="电",
                is_canonical=False,
            ),
            LocalizedText(
                entity_type="pokemon-species",
                entity_id=25,
                locale="zh-Hans",
                text_kind="flavor_text",
                text="会把电储存在脸颊的电力袋里。",
            ),
            PokemonType(pokemon_id=25, type_id=13, slot=1),
            PokemonStat(pokemon_id=25, stat_id=1, base_stat=35, effort=0),
            MediaAsset(
                pokemon_id=25,
                form_id=None,
                kind="front-default",
                source_url="https://example.test/pikachu.png",
                local_path="pokemon/25/front-default.png",
                checksum="abc",
                width=96,
                height=96,
            ),
        ]
    )
    await session.commit()


async def test_pokemon_list_and_detail(client: AsyncClient, session: AsyncSession) -> None:
    await seed_pikachu(session)

    listing = await client.get("/api/v1/pokemon?locale=zh-Hans&q=皮卡")
    assert listing.status_code == 200
    payload = listing.json()
    assert payload["total"] == 1
    assert payload["items"][0]["localizedName"] == "皮卡丘"
    assert payload["items"][0]["types"][0]["localizedName"] == "电"

    detail = await client.get("/api/v1/pokemon/25?locale=zh-Hans")
    assert detail.status_code == 200
    detail_payload = detail.json()
    assert detail_payload["localizedName"] == "皮卡丘"
    assert detail_payload["description"] == "会把电储存在脸颊的电力袋里。"
    assert detail_payload["spriteUrl"] == "/media/pokemon/25/front-default.png"


async def test_type_and_suggestion_endpoints(
    client: AsyncClient, session: AsyncSession
) -> None:
    await seed_pikachu(session)
    types = await client.get("/api/v1/types?locale=zh-Hans")
    assert types.status_code == 200
    assert types.json()[0]["localizedName"] == "电"

    suggestions = await client.get("/api/v1/search/suggest?locale=zh-Hans&q=皮卡")
    assert suggestions.status_code == 200
    assert suggestions.json()[0]["localizedName"] == "皮卡丘"
