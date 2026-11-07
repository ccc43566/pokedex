from __future__ import annotations

import math
import re
from collections import defaultdict
from typing import Any

from sqlalchemy import ColumnElement, Select, and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from pokedex_api.models import (
    Ability,
    GenerationEntity,
    LocalizedName,
    LocalizedText,
    MediaAsset,
    Pokemon,
    PokemonAbility,
    PokemonForm,
    PokemonSpecies,
    PokemonStat,
    PokemonType,
    StatEntity,
    TypeEntity,
)
from pokedex_api.schemas import (
    AbilityDetail,
    AbilityValue,
    GenerationSummary,
    MediaAssetOut,
    NamedResource,
    PaginatedPokemon,
    PokemonDetail,
    PokemonFormValue,
    PokemonListItem,
    SearchSuggestion,
    StatValue,
    TypeDetail,
    TypeSummary,
)
from pokedex_api.services.catalog import dex_catalog, identities, is_totem_record, species_options
from pokedex_api.services.detail_facts import egg_groups, stat_changes
from pokedex_api.services.evolution import evolution_graph, legacy_tree
from pokedex_api.services.search_index import data_version, matching_ids, search_index, worker

SUPPORTED_LOCALES = ("zh-Hans", "en")


def normalize_locale(locale: str) -> str:
    return "zh-Hans" if locale.lower().replace("_", "-").startswith("zh") else "en"


async def localized_name_map(
    session: AsyncSession,
    entity_type: str,
    entity_ids: list[int],
    locale: str,
) -> dict[int, str]:
    if not entity_ids:
        return {}
    rows = (
        await session.execute(
            select(LocalizedName.entity_id, LocalizedName.locale, LocalizedName.name).where(
                LocalizedName.entity_type == entity_type,
                LocalizedName.entity_id.in_(entity_ids),
                LocalizedName.locale.in_(SUPPORTED_LOCALES),
            )
        )
    ).all()
    values: dict[int, dict[str, str]] = defaultdict(dict)
    for entity_id, row_locale, name in rows:
        values[entity_id][row_locale] = name

    result: dict[int, str] = {}
    for entity_id, localized in values.items():
        result[entity_id] = localized.get(locale) or localized.get("en") or ""
    return result


def _pick_text(entries: list[dict[str, Any]], locale: str, key: str = "text") -> str | None:
    exact = [
        entry
        for entry in entries
        if entry.get("language", {}).get("name", "").lower() == locale.lower()
    ]
    english = [
        entry for entry in entries if entry.get("language", {}).get("name", "").lower() == "en"
    ]
    for entry in [*exact, *english]:
        value = entry.get(key)
        if value:
            return str(value)
    return None


def _asset_url(local_path: str | None, source_url: str, media_public_path: str) -> str:
    if local_path:
        return f"{media_public_path.rstrip('/')}/{local_path.lstrip('/')}"
    return source_url


def _remote_sprite(pokemon: Pokemon, key: str) -> str | None:
    sprites = pokemon.sprites or {}
    other = sprites.get("other") or {}
    if key == "official-artwork":
        return (other.get("official-artwork") or {}).get("front_default")
    if key == "home":
        return (other.get("home") or {}).get("front_default")
    if key == "front-shiny":
        return sprites.get("front_shiny")
    return sprites.get("front_default")


async def media_map(
    session: AsyncSession,
    pokemon_ids: list[int],
    media_public_path: str,
) -> dict[int, dict[str, str]]:
    if not pokemon_ids:
        return {}
    assets = (
        await session.scalars(
            select(MediaAsset).where(
                MediaAsset.pokemon_id.in_(pokemon_ids),
                MediaAsset.form_id.is_(None),
            )
        )
    ).all()
    result: dict[int, dict[str, str]] = defaultdict(dict)
    for asset in assets:
        if asset.pokemon_id is None:
            continue
        result[asset.pokemon_id][asset.kind] = _asset_url(
            asset.local_path, asset.source_url, media_public_path
        )
    return result


def _sprite_from_maps(
    pokemon: Pokemon,
    media: dict[int, dict[str, str]],
    kind: str,
) -> str | None:
    return media.get(pokemon.id, {}).get(kind) or _remote_sprite(pokemon, kind)


def _sort_expression(sort: str, catalog: Any) -> tuple[Any, ...]:
    segments = (catalog.c.national, catalog.c.variant, Pokemon.id)
    if sort == "base_experience":
        return (catalog.c.family_experience.desc().nullslast(), *segments)
    if sort == "name":
        return (PokemonSpecies.name, *segments)
    if sort == "newest":
        return (catalog.c.national.desc(), catalog.c.variant, Pokemon.id)
    return segments


def _pokemon_filtered_query(
    *,
    q: str | None,
    use_fts: bool,
    type_name: str | None,
    generation: int | None,
    is_legendary: bool | None,
    is_mythical: bool | None,
    display_name_ids: list[int] | None = None,
    is_mega: bool | None = None,
    is_gigantamax: bool | None = None,
) -> Select[Any]:
    stmt = (
        select(Pokemon.id)
        .join(PokemonSpecies, Pokemon.species_id == PokemonSpecies.id)
        .where(~is_totem_record())
    )
    if q:
        pattern = f"%{q.strip()}%"
        search_conditions: list[ColumnElement[bool]] = [
            Pokemon.name.ilike(pattern),
            LocalizedName.name.ilike(pattern),
        ]
        if display_name_ids:
            search_conditions.append(Pokemon.id.in_(display_name_ids))
        if q.strip().isdigit():
            number = int(q.strip())
            search_conditions.extend([Pokemon.id == number, Pokemon.species_id == number])
        elif match := re.fullmatch(r"(\d+)\.(\d+)", q.strip()):
            catalog = dex_catalog()
            search_conditions.append(
                Pokemon.id.in_(
                    select(catalog.c.pokemon_id).where(
                        catalog.c.national == int(match[1]), catalog.c.variant == int(match[2])
                    )
                )
            )
        search_conditions.append(
            Pokemon.id.in_(
                select(PokemonForm.pokemon_id)
                .join(
                    LocalizedName,
                    and_(
                        LocalizedName.entity_type == "pokemon-form",
                        LocalizedName.entity_id == PokemonForm.id,
                    ),
                )
                .where(LocalizedName.name.ilike(pattern))
            )
        )
        if use_fts:
            search_conditions.append(
                func.to_tsvector("english", LocalizedName.name).op("@@")(
                    func.plainto_tsquery("english", q.strip())
                )
            )
        stmt = stmt.outerjoin(
            LocalizedName,
            and_(
                LocalizedName.entity_type == "pokemon-species",
                LocalizedName.entity_id == PokemonSpecies.id,
            ),
        ).where(or_(*search_conditions))
    if type_name:
        stmt = (
            stmt.join(PokemonType, PokemonType.pokemon_id == Pokemon.id)
            .join(TypeEntity, TypeEntity.id == PokemonType.type_id)
            .where(TypeEntity.name == type_name.lower())
        )
    if generation is not None:
        stmt = stmt.where(PokemonSpecies.generation_id == generation)
    if is_legendary is not None:
        stmt = stmt.where(PokemonSpecies.is_legendary == is_legendary)
    if is_mythical is not None:
        stmt = stmt.where(PokemonSpecies.is_mythical == is_mythical)
    # Forms are selected BEFORE counting and pagination. Two selected form tags
    # form a union; type/search/species filters still intersect that union.
    mega = (
        select(PokemonForm.id)
        .where(PokemonForm.pokemon_id == Pokemon.id, PokemonForm.is_mega.is_(True))
        .exists()
    )
    token = func.lower(func.coalesce(PokemonForm.form_name, ""))
    gigantamax = (
        select(PokemonForm.id)
        .where(
            PokemonForm.pokemon_id == Pokemon.id,
            or_(
                token == "gmax",
                token.startswith("gmax-"),
                token.endswith("-gmax"),
                token.contains("-gmax-"),
            ),
        )
        .exists()
    )
    selected_forms: list[ColumnElement[bool]] = []
    if is_mega:
        selected_forms.append(mega)
    if is_gigantamax:
        selected_forms.append(gigantamax)
    if selected_forms:
        stmt = stmt.where(or_(*selected_forms))
    if is_mega is False:
        stmt = stmt.where(~mega)
    if is_gigantamax is False:
        stmt = stmt.where(~gigantamax)
    return stmt.distinct()


async def list_pokemon(
    session: AsyncSession,
    *,
    locale: str,
    q: str | None = None,
    type_name: str | None = None,
    generation: int | None = None,
    is_legendary: bool | None = None,
    is_mythical: bool | None = None,
    is_mega: bool | None = None,
    is_gigantamax: bool | None = None,
    page: int = 1,
    page_size: int = 24,
    sort: str = "id",
    media_public_path: str = "/media",
) -> PaginatedPokemon:
    from fastapi import HTTPException

    locale = normalize_locale(locale)
    q = (q.strip() or None) if q else None
    params = dict(locale=locale, q=q, type_name=type_name, generation=generation,
                  is_legendary=is_legendary, is_mythical=is_mythical,
                  is_mega=is_mega, is_gigantamax=is_gigantamax,
                  page=page, page_size=page_size, sort=sort, media_public_path=media_public_path)
    for _ in range(3):
        version = await data_version(session)
        key = (version, *params.values())

        async def build(version: str = version) -> PaginatedPokemon:
            result = await _list_pokemon(
                session, locale=locale, q=q, type_name=type_name, generation=generation,
                is_legendary=is_legendary, is_mythical=is_mythical, is_mega=is_mega,
                is_gigantamax=is_gigantamax, page=page, page_size=page_size,
                sort=sort, media_public_path=media_public_path, version=version,
            )
            return result.model_copy(update={"data_version": version})

        result = await worker(session).results.load(key, build)
        if await data_version(session) == version:
            return result.model_copy(deep=True)
    raise HTTPException(
        503, "Pokémon data is updating; retry shortly", headers={"Retry-After": "1"}
    )


async def _list_pokemon(
    session: AsyncSession,
    *,
    locale: str,
    q: str | None = None,
    type_name: str | None = None,
    generation: int | None = None,
    is_legendary: bool | None = None,
    is_mythical: bool | None = None,
    is_mega: bool | None = None,
    is_gigantamax: bool | None = None,
    page: int = 1,
    page_size: int = 24,
    sort: str = "id",
    media_public_path: str = "/media",
    version: str,
) -> PaginatedPokemon:
    locale = normalize_locale(locale)
    index = await search_index(session, locale, version)
    display_name_ids = (
        matching_ids(index, q)
        if q and not re.fullmatch(r"\d+(?:\.\d+)?", q.strip())
        else []
    )
    base = _pokemon_filtered_query(
        q=q,
        use_fts=session.get_bind().dialect.name == "postgresql",
        type_name=type_name,
        generation=generation,
        is_legendary=is_legendary,
        is_mythical=is_mythical,
        is_mega=is_mega,
        is_gigantamax=is_gigantamax,
        display_name_ids=display_name_ids,
    )
    total = int(await session.scalar(select(func.count()).select_from(base.subquery())) or 0)
    total_pages = max(1, math.ceil(total / page_size))
    page = min(max(1, page), total_pages)
    catalog = dex_catalog()
    raw_ids = (
        await session.scalars(
            select(Pokemon.id)
            .join(catalog, catalog.c.pokemon_id == Pokemon.id)
            .join(PokemonSpecies, Pokemon.species_id == PokemonSpecies.id)
            .where(Pokemon.id.in_(base))
            .order_by(*_sort_expression(sort, catalog))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()
    ids: list[int] = [int(row[0]) if isinstance(row, tuple) else int(row) for row in raw_ids]
    if not ids:
        return PaginatedPokemon(
            items=[],
            page=page,
            page_size=page_size,
            total=total,
            total_pages=total_pages,
            has_next=False,
            has_previous=page > 1,
        )

    pokemon_rows = list((await session.scalars(select(Pokemon).where(Pokemon.id.in_(ids)))).all())
    pokemon_by_id = {item.id: item for item in pokemon_rows}
    species_ids = [item.species_id for item in pokemon_rows if item.species_id is not None]
    species_rows = list(
        (
            await session.scalars(select(PokemonSpecies).where(PokemonSpecies.id.in_(species_ids)))
        ).all()
    )
    species_by_id = {item.id: item for item in species_rows}
    localized = await localized_name_map(session, "pokemon-species", species_ids, locale)

    type_rows = (
        await session.execute(
            select(
                PokemonType.pokemon_id,
                TypeEntity.id,
                TypeEntity.name,
                PokemonType.slot,
            )
            .join(TypeEntity, TypeEntity.id == PokemonType.type_id)
            .where(PokemonType.pokemon_id.in_(ids))
            .order_by(PokemonType.slot)
        )
    ).all()
    type_names = await localized_name_map(
        session, "type", list({row[1] for row in type_rows}), locale
    )
    types_by_pokemon: dict[int, list[NamedResource]] = defaultdict(list)
    for pokemon_id, type_id, name, _slot in type_rows:
        types_by_pokemon[pokemon_id].append(
            NamedResource(id=type_id, name=name, localized_name=type_names.get(type_id, name))
        )

    media = await media_map(session, ids, media_public_path)
    display = {pid: index["identities"][str(pid)] for pid in ids}
    items: list[PokemonListItem] = []
    for pokemon_id in ids:
        pokemon = pokemon_by_id[pokemon_id]
        species = species_by_id.get(pokemon.species_id) if pokemon.species_id else None
        fallback = species.name if species else pokemon.name
        items.append(
            PokemonListItem(
                id=pokemon.id,
                name=pokemon.name,
                localized_name=localized.get(pokemon.species_id or 0, fallback),
                **display[pokemon.id],
                sprite_url=_sprite_from_maps(pokemon, media, "front-default")
                or _sprite_from_maps(pokemon, media, "official-artwork"),
                artwork_url=_sprite_from_maps(pokemon, media, "official-artwork"),
                types=types_by_pokemon.get(pokemon.id, []),
                generation_id=species.generation_id if species else None,
                is_legendary=species.is_legendary if species else False,
                is_mythical=species.is_mythical if species else False,
            )
        )

    return PaginatedPokemon(
        items=items,
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_previous=page > 1,
    )


async def get_pokemon(
    session: AsyncSession,
    id_or_name: str,
    *,
    locale: str,
    media_public_path: str = "/media",
    form_key: str | None = None,
) -> PokemonDetail | None:
    locale = normalize_locale(locale)
    conditions = [Pokemon.name == id_or_name.lower()]
    if id_or_name.isdigit():
        conditions.append(Pokemon.id == int(id_or_name))
    pokemon = await session.scalar(select(Pokemon).where(or_(*conditions)))
    if pokemon is None:
        return None

    species = (
        await session.get(PokemonSpecies, pokemon.species_id)
        if pokemon.species_id is not None
        else None
    )
    localized = await localized_name_map(
        session,
        "pokemon-species",
        [species.id] if species else [],
        locale,
    )

    type_rows = (
        await session.execute(
            select(TypeEntity.id, TypeEntity.name, PokemonType.slot)
            .join(PokemonType, PokemonType.type_id == TypeEntity.id)
            .where(PokemonType.pokemon_id == pokemon.id)
            .order_by(PokemonType.slot)
        )
    ).all()
    type_names = await localized_name_map(session, "type", [row[0] for row in type_rows], locale)
    types = [
        NamedResource(id=type_id, name=name, localized_name=type_names.get(type_id, name))
        for type_id, name, _slot in type_rows
    ]

    ability_rows = (
        await session.execute(
            select(
                Ability.id,
                Ability.name,
                Ability.effect_entries,
                PokemonAbility.slot,
                PokemonAbility.is_hidden,
            )
            .join(PokemonAbility, PokemonAbility.ability_id == Ability.id)
            .where(PokemonAbility.pokemon_id == pokemon.id)
            .order_by(PokemonAbility.slot)
        )
    ).all()
    ability_names = await localized_name_map(
        session, "ability", [row[0] for row in ability_rows], locale
    )
    abilities = [
        AbilityValue(
            id=ability_id,
            name=name,
            localized_name=ability_names.get(ability_id, name),
            effect=_pick_text(effect_entries or [], locale, "effect"),
            short_effect=_pick_text(effect_entries or [], locale, "short_effect"),
            is_hidden=is_hidden,
            slot=slot,
        )
        for ability_id, name, effect_entries, slot, is_hidden in ability_rows
    ]

    stat_rows = (
        await session.execute(
            select(StatEntity.id, StatEntity.name, PokemonStat.base_stat, PokemonStat.effort)
            .join(PokemonStat, PokemonStat.stat_id == StatEntity.id)
            .where(PokemonStat.pokemon_id == pokemon.id)
            .order_by(StatEntity.id)
        )
    ).all()
    stat_names = await localized_name_map(session, "stat", [row[0] for row in stat_rows], locale)
    stats = [
        StatValue(
            name=name,
            localized_name=stat_names.get(stat_id, name),
            base_stat=base_stat,
            effort=effort,
        )
        for stat_id, name, base_stat, effort in stat_rows
    ]

    form_rows = list(
        (
            await session.scalars(
                select(PokemonForm)
                .where(PokemonForm.pokemon_id == pokemon.id)
                .order_by(PokemonForm.id)
            )
        ).all()
    )
    form_names = await localized_name_map(
        session, "pokemon-form", [form.id for form in form_rows], locale
    )
    forms = [
        PokemonFormValue(
            id=form.id,
            name=form.name,
            form_name=form_names.get(form.id) or form.form_name,
            is_default=form.is_default,
            is_battle_only=form.is_battle_only,
            is_mega=form.is_mega,
            sprite_url=(form.sprites or {}).get("front_default"),
        )
        for form in form_rows
    ]

    media = await media_map(session, [pokemon.id], media_public_path)
    media_rows = list(
        (
            await session.scalars(
                select(MediaAsset)
                .where(MediaAsset.pokemon_id == pokemon.id)
                .order_by(MediaAsset.kind)
            )
        ).all()
    )
    media_items = [
        MediaAssetOut(
            kind=asset.kind,
            url=_asset_url(asset.local_path, asset.source_url, media_public_path),
            width=asset.width,
            height=asset.height,
        )
        for asset in media_rows
    ]

    description = None
    genus = None
    if species:
        text_rows = (
            await session.scalars(
                select(LocalizedText).where(
                    LocalizedText.entity_type == "pokemon-species",
                    LocalizedText.entity_id == species.id,
                    LocalizedText.locale.in_(SUPPORTED_LOCALES),
                )
            )
        ).all()
        descriptions = [row for row in text_rows if row.text_kind == "flavor_text"]
        descriptions.sort(key=lambda row: (row.locale != locale, -row.id))
        description = descriptions[0].text if descriptions else None
        genus_text = [row for row in text_rows if row.text_kind == "genus"]
        genus_text.sort(key=lambda row: row.locale != locale)
        genus = genus_text[0].text if genus_text else None

    fallback_name = species.name if species else pokemon.name
    display = await identities(session, [pokemon.id], locale)
    options = await species_options(
        session,
        pokemon,
        locale=locale,
        media_public_path=media_public_path,
    )
    current = next(
        (o for o in options if o.pokemon_id == pokemon.id and o.key == form_key),
        next(o for o in options if o.pokemon_id == pokemon.id and o.is_default),
    )
    graph = await evolution_graph(
        session, pokemon, current, locale=locale, media_public_path=media_public_path
    )
    all_stats = list((await session.scalars(select(StatEntity))).all())
    all_stat_names = await localized_name_map(session, "stat", [s.id for s in all_stats], locale)
    history_names = {s.name: all_stat_names.get(s.id, s.name) for s in all_stats}
    if history_names.get("special", "special") == "special":
        history_names["special"] = "特殊" if locale == "zh-Hans" else "Special"
    return PokemonDetail(
        id=pokemon.id,
        name=pokemon.name,
        localized_name=localized.get(species.id if species else 0, fallback_name),
        **display[pokemon.id],
        sprite_url=_sprite_from_maps(pokemon, media, "front-default"),
        artwork_url=_sprite_from_maps(pokemon, media, "official-artwork"),
        types=types,
        generation_id=species.generation_id if species else None,
        is_legendary=species.is_legendary if species else False,
        is_mythical=species.is_mythical if species else False,
        height=pokemon.height,
        weight=pokemon.weight,
        base_experience=pokemon.base_experience,
        order=pokemon.order,
        is_default=pokemon.is_default,
        description=description,
        genus=genus,
        abilities=abilities,
        stats=stats,
        base_stat_total=sum(
            stat.base_stat
            for stat in stats
            if stat.name
            in {"hp", "attack", "defense", "special-attack", "special-defense", "speed"}
        ),
        egg_groups=egg_groups(species.raw_payload or {}, locale) if species else [],
        gender_rate=species.gender_rate if species else None,
        stat_changes=stat_changes(pokemon.raw_payload or {}, stats, history_names),
        stat_history_available="past_stats" in (pokemon.raw_payload or {}),
        forms=forms,
        form_options=options,
        evolution_chain=legacy_tree(graph),
        evolution_graph=graph,
        media=media_items,
    )


async def list_types(session: AsyncSession, *, locale: str) -> list[TypeSummary]:
    locale = normalize_locale(locale)
    types = list((await session.scalars(select(TypeEntity).order_by(TypeEntity.id))).all())
    localized = await localized_name_map(session, "type", [item.id for item in types], locale)
    return [
        TypeSummary(id=item.id, name=item.name, localized_name=localized.get(item.id, item.name))
        for item in types
    ]


async def get_type(
    session: AsyncSession,
    id_or_name: str,
    *,
    locale: str,
) -> TypeDetail | None:
    locale = normalize_locale(locale)
    conditions = [TypeEntity.name == id_or_name.lower()]
    if id_or_name.isdigit():
        conditions.append(TypeEntity.id == int(id_or_name))
    item = await session.scalar(select(TypeEntity).where(or_(*conditions)))
    if item is None:
        return None
    localized = await localized_name_map(session, "type", [item.id], locale)
    raw_relations = item.damage_relations or {}
    relation_names: dict[str, str] = {}
    relation_ids = {
        int(relation["url"].rstrip("/").split("/")[-1])
        for values in raw_relations.values()
        for relation in values
        if relation.get("url")
    }
    if relation_ids:
        relation_types = list(
            (await session.scalars(select(TypeEntity).where(TypeEntity.id.in_(relation_ids)))).all()
        )
        localized_relations = await localized_name_map(
            session, "type", [relation.id for relation in relation_types], locale
        )
        relation_names = {
            relation.name: localized_relations.get(relation.id, relation.name)
            for relation in relation_types
        }
    relations = {
        key: [
            NamedResource(
                id=int(relation["url"].rstrip("/").split("/")[-1]),
                name=relation["name"],
                localized_name=relation_names.get(relation["name"], relation["name"]),
            )
            for relation in values
        ]
        for key, values in raw_relations.items()
    }
    return TypeDetail(
        id=item.id,
        name=item.name,
        localized_name=localized.get(item.id, item.name),
        damage_relations=relations,
        past_damage_relations=item.past_damage_relations or [],
    )


async def get_ability(
    session: AsyncSession,
    id_or_name: str,
    *,
    locale: str,
) -> AbilityDetail | None:
    locale = normalize_locale(locale)
    conditions = [Ability.name == id_or_name.lower()]
    if id_or_name.isdigit():
        conditions.append(Ability.id == int(id_or_name))
    item = await session.scalar(select(Ability).where(or_(*conditions)))
    if item is None:
        return None
    localized = await localized_name_map(session, "ability", [item.id], locale)
    return AbilityDetail(
        id=item.id,
        name=item.name,
        localized_name=localized.get(item.id, item.name),
        generation_id=item.generation_id,
        is_main_series=item.is_main_series,
        effect=_pick_text(item.effect_entries or [], locale, "effect"),
        short_effect=_pick_text(item.effect_entries or [], locale, "short_effect"),
        flavor_text=_pick_text(item.flavor_text_entries or [], locale, "flavor_text"),
    )


async def list_generations(session: AsyncSession, *, locale: str) -> list[GenerationSummary]:
    locale = normalize_locale(locale)
    generations = list(
        (await session.scalars(select(GenerationEntity).order_by(GenerationEntity.id))).all()
    )
    localized = await localized_name_map(
        session, "generation", [item.id for item in generations], locale
    )
    counts = dict(
        (
            await session.execute(
                select(PokemonSpecies.generation_id, func.count(PokemonSpecies.id))
                .where(PokemonSpecies.generation_id.is_not(None))
                .group_by(PokemonSpecies.generation_id)
            )
        ).all()
    )
    return [
        GenerationSummary(
            id=item.id,
            name=item.name,
            localized_name=localized.get(item.id, item.name),
            main_region=item.main_region,
            species_count=int(counts.get(item.id, 0)),
        )
        for item in generations
    ]


async def search_suggestions(
    session: AsyncSession,
    *,
    q: str,
    locale: str,
    limit: int = 8,
    media_public_path: str = "/media",
) -> list[SearchSuggestion]:
    page = await list_pokemon(
        session,
        locale=locale,
        q=q,
        page=1,
        page_size=limit,
        media_public_path=media_public_path,
    )
    return [
        SearchSuggestion(
            id=item.id,
            name=item.name,
            localized_name=item.localized_name,
            sprite_url=item.sprite_url,
        )
        for item in page.items
    ]
