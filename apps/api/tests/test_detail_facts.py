from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from pokedex_api.models import Pokemon, PokemonSpecies
from pokedex_api.schemas import StatValue
from pokedex_api.services.detail_facts import egg_groups, stat_changes
from tests.test_pokemon_api import seed_pikachu


def past(generation: int, **values: int) -> dict:
    return {
        "generation": {"url": f"https://pokeapi.co/api/v2/generation/{generation}/"},
        "stats": [{"stat": {"name": name}, "base_stat": value} for name, value in values.items()],
    }


def test_sparse_history_uses_next_value_per_stat_and_generation_boundary():
    stats = [
        StatValue(name=name, localized_name=name, base_stat=value, effort=0)
        for name, value in [("defense", 60), ("special-attack", 55), ("special-defense", 50)]
    ]
    payload = {
        "past_stats": [
            past(7, defense=50),
            past(1, special=50),
            past(5, defense=30, **{"special-defense": 40}),
        ]
    }
    changes = stat_changes(payload, stats, {})
    assert [(c.generation_id, c.name, c.old_value, c.new_value) for c in changes] == [
        (2, "special-attack", 50, 55),
        (2, "special-defense", 50, 40),
        (6, "defense", 30, 50),
        (6, "special-defense", 40, 50),
        (8, "defense", 50, 60),
    ]
    assert all(c.is_split for c in changes[:2])


def test_missing_history_and_unchanged_stats():
    stats = [StatValue(name="hp", localized_name="HP", base_stat=35, effort=0)]
    assert stat_changes({}, stats, {}) == []
    assert stat_changes({"past_stats": [past(5, hp=35)]}, stats, {}) == []
    assert egg_groups({}, "en") == []
    assert (
        egg_groups({"egg_groups": [{"name": "ground", "url": "x/5/"}]}, "zh-Hans")[0].localized_name
        == "陆上"
    )


async def test_detail_exposes_species_facts_and_stats(client: AsyncClient, session: AsyncSession):
    await seed_pikachu(session)
    species = await session.get(PokemonSpecies, 25)
    pokemon = await session.get(Pokemon, 25)
    assert species and pokemon
    species.gender_rate = 4
    species.raw_payload = {"egg_groups": [{"name": "fairy", "url": "x/6/"}]}
    pokemon.raw_payload = {"past_stats": [past(5, hp=30)]}
    await session.commit()
    response = await client.get("/api/v1/pokemon/25?locale=zh-Hans")
    assert response.status_code == 200
    detail = response.json()
    assert detail["baseStatTotal"] == 35
    assert detail["genderRate"] == 4
    assert detail["eggGroups"][0]["localizedName"] == "妖精"
    assert detail["statHistoryAvailable"] is True
    assert detail["statChanges"][0]["generationId"] == 6
    assert detail["statChanges"][0]["newValue"] == 35
