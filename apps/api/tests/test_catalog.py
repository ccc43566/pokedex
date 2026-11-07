from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from pokedex_api.models import (
    LocalizedName,
    MediaAsset,
    Pokemon,
    PokemonForm,
    PokemonSpecies,
    VersionSprite,
)


async def seed_family(session: AsyncSession, *, variants: int = 4) -> list[int]:
    session.add(
        PokemonSpecies(
            id=892,
            name="urshifu",
            raw_payload={
                "names": [
                    {"name": "Urshifu", "language": {"name": "en"}},
                ]
            },
        )
    )
    session.add_all(
        [
            LocalizedName(
                entity_type="pokemon-species", entity_id=892, locale="zh-Hans", name="武道熊师"
            ),
            LocalizedName(
                entity_type="pokemon-species", entity_id=892, locale="en", name="Urshifu"
            ),
            PokemonSpecies(id=893, name="zarude", raw_payload={}),
            Pokemon(id=893, name="zarude", species_id=893, is_default=True, raw_payload={}),
        ]
    )
    ids = [892] + list(range(10191, 10191 + variants - 1))
    for index, pokemon_id in enumerate(ids):
        slug = "urshifu-single-strike" if index == 0 else f"urshifu-variant-{index}"
        label = "Single Strike Style" if index == 0 else f"Variant {index}"
        session.add(
            Pokemon(
                id=pokemon_id,
                name=slug,
                species_id=892,
                is_default=index == 0,
                base_experience=index + 100,
                raw_payload={},
            )
        )
        session.add(
            PokemonForm(
                id=pokemon_id + 20000,
                pokemon_id=pokemon_id,
                name=slug,
                is_default=True,
                form_name=slug,
                raw_payload={"form_names": [{"name": label, "language": {"name": "en"}}]},
            )
        )
        session.add(
            MediaAsset(
                pokemon_id=pokemon_id,
                kind="front-default",
                source_url=f"https://source.test/{pokemon_id}.png",
                local_path=f"version-sprites/{pokemon_id}.png",
                checksum=str(pokemon_id),
            )
        )
        session.add(
            VersionSprite(
                owner_type="pokemon",
                owner_id=pokemon_id,
                generation="generation-viii",
                game="sword-shield",
                kind="front_default",
                status="downloaded",
                source_url=f"https://source.test/{pokemon_id}.png",
                local_path=f"version-sprites/{pokemon_id}.png",
            )
        )
    await session.commit()
    return ids


async def test_display_segments_are_stable_across_pages_filters_and_internal_links(
    client: AsyncClient,
    session: AsyncSession,
) -> None:
    ids = await seed_family(session, variants=12)
    listing = (await client.get("/api/v1/pokemon?pageSize=100")).json()
    assert [p["id"] for p in listing["items"]] == [*ids, 893]
    assert [p["displayNumber"] for p in listing["items"][:12]] == [
        "892",
        *[f"892.{index}" for index in range(1, 12)],
    ]
    # .10 stays a separate integer segment, after .9, including across page boundaries.
    second_page = (await client.get("/api/v1/pokemon?page=2&pageSize=10")).json()
    assert second_page["items"][0]["displayNumber"] == "892.10"
    found = (await client.get("/api/v1/pokemon?q=892.10")).json()
    assert found["total"] == 1
    assert found["items"][0]["id"] == ids[10]
    assert found["items"][0]["variantIndex"] == 10
    filtered = (await client.get("/api/v1/pokemon?q=variant-10")).json()
    assert filtered["items"][0]["displayNumber"] == "892.10"
    old_link = await client.get(f"/api/v1/pokemon/{ids[10]}")
    assert old_link.status_code == 200
    assert old_link.json()["displayNumber"] == "892.10"
    assert (await client.get("/api/v1/pokemon/urshifu-single-strike")).status_code == 200
    for sort in ["name", "newest", "base_experience"]:
        items = (await client.get(f"/api/v1/pokemon?sort={sort}&pageSize=100")).json()["items"]
        family = [p for p in items if p["speciesId"] == 892]
        assert [p["id"] for p in family] == ids


async def test_family_options_merge_default_sources_and_include_cosmetics(
    client: AsyncClient,
    session: AsyncSession,
) -> None:
    ids = await seed_family(session)
    session.add(
        PokemonForm(
            id=40000,
            pokemon_id=ids[0],
            name="urshifu-special-look",
            form_name="special-look",
            is_default=False,
            raw_payload={},
        )
    )
    session.add(
        MediaAsset(
            form_id=40000,
            kind="front-default",
            source_url="https://source.test/look.png",
            local_path="version-sprites/existing-look.png",
            checksum="existing",
        )
    )
    await session.commit()
    default = (await client.get("/api/v1/pokemon/892")).json()
    alternate = (await client.get(f"/api/v1/pokemon/{ids[1]}")).json()
    assert default["formOptions"] == alternate["formOptions"]
    assert len(default["formOptions"]) == 5  # four variants + one cosmetic, not 4+4+1
    merged = default["formOptions"][0]
    assert merged["key"] == "pokemon:892"
    assert {r["ownerType"] for r in merged["sources"]} == {"pokemon", "form"}
    cosmetic = default["formOptions"][1]
    assert cosmetic["pokemonId"] == 892
    assert cosmetic["key"] == "form:40000"
    assert cosmetic["spriteUrl"] == "/media/version-sprites/existing-look.png"
    assert cosmetic["artworkUrl"] == cosmetic["spriteUrl"]
    listing = (await client.get("/api/v1/pokemon?q=892")).json()
    assert listing["total"] == 4  # cosmetic appearance never becomes a card
    gallery = (await client.get(f"/api/v1/pokemon/{ids[1]}/version-sprites")).json()
    assert {r["ownerId"] for r in gallery["owners"] if r["ownerType"] == "pokemon"} == set(ids)
    assert {r["ownerId"] for r in gallery["sprites"]} == set(ids)


async def test_single_default_has_one_choice_and_english_labels_are_readable(
    client: AsyncClient,
    session: AsyncSession,
) -> None:
    await seed_family(session, variants=1)
    single = (await client.get("/api/v1/pokemon/892")).json()
    assert len(single["formOptions"]) == 1
    assert single["displayName"] == "武道熊师（Single Strike）"
    assert single["id"] == 892


async def test_totems_do_not_consume_numbers_counts_or_search_results(
    client: AsyncClient,
    session: AsyncSession,
) -> None:
    ids = await seed_family(session, variants=12)
    # Insert a hidden record BETWEEN visible IDs; labeling alone must not hide a record.
    session.add(Pokemon(id=10000, name="urshifu-hidden", species_id=892, is_default=False))
    session.add(
        PokemonForm(
            id=50000,
            pokemon_id=10000,
            name="urshifu-hidden",
            form_name="totem-alola",
            is_default=True,
        )
    )
    # An ordinary regional form sharing the Alola suffix remains visible.
    session.add(Pokemon(id=10001, name="urshifu-alola", species_id=892, is_default=False))
    session.add(
        PokemonForm(
            id=50001, pokemon_id=10001, name="urshifu-alola", form_name="alola", is_default=True
        )
    )
    await session.commit()
    listing = (await client.get("/api/v1/pokemon?q=892&pageSize=100")).json()
    assert listing["total"] == 13
    assert [p["id"] for p in listing["items"]] == [ids[0], 10001, *ids[1:]]
    assert [p["displayNumber"] for p in listing["items"]] == [
        "892",
        *[f"892.{i}" for i in range(1, 13)],
    ]
    assert (await client.get("/api/v1/pokemon?q=hidden")).json()["total"] == 0
    assert (await client.get("/api/v1/pokemon?q=10000")).json()["total"] == 0
    assert (await client.get("/api/v1/search/suggest?q=hidden")).json() == []
    hidden = (await client.get("/api/v1/pokemon/10000")).json()
    assert hidden["isListed"] is False
    assert hidden["variantIndex"] is None
    assert hidden["displayNumber"] == "892"
    assert len(hidden["formOptions"]) == 14
    for query in ["q=892.10", "q=variant-9", "q=10199"]:
        found = (await client.get(f"/api/v1/pokemon?{query}")).json()
        assert found["items"][0]["displayNumber"] == "892.10"
    page = (await client.get("/api/v1/pokemon?q=892&pageSize=10&page=2")).json()
    assert page["items"][0]["displayNumber"] == "892.10"


async def test_prototype_never_gains_default_label(
    client: AsyncClient, session: AsyncSession
) -> None:
    await seed_family(session)
    detail = (await client.get("/api/v1/pokemon/893")).json()
    assert detail["displayName"] == "Zarude"
    assert detail["formOptions"][0]["label"] == "Zarude"
    assert detail["formOptions"][0]["formLabel"] == ""
