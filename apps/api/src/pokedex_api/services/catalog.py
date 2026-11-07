"""Display identities and species-wide choices; source IDs and stored assets stay intact."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from sqlalchemy import exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.selectable import Subquery

from pokedex_api.models import (
    LocalizedName,
    MediaAsset,
    Pokemon,
    PokemonForm,
    PokemonSpecies,
)
from pokedex_api.schemas import NamedResource, PokemonFormOption, VersionSpriteOwner
from pokedex_api.services.names import Names, load_names, readable_slug


def is_totem_record() -> Any:
    """Use upstream form_name tokens, never species/translated names or regional suffixes."""
    token = func.lower(func.coalesce(PokemonForm.form_name, ""))
    return exists(
        select(PokemonForm.id).where(
            PokemonForm.pokemon_id == Pokemon.id,
            or_(
                token == "totem",
                token.startswith("totem-"),
                token.endswith("-totem"),
                token.contains("-totem-"),
            ),
        )
    )


def dex_catalog() -> Subquery:
    """Rank the entire collection BEFORE applying any search, filter or page."""
    national = func.coalesce(Pokemon.species_id, Pokemon.id)
    order = (Pokemon.is_default.desc(), Pokemon.id)
    return (
        select(
            Pokemon.id.label("pokemon_id"),
            national.label("national"),
            (func.row_number().over(partition_by=national, order_by=order) - 1).label("variant"),
            func.count().over(partition_by=national).label("variant_count"),
            func.first_value(Pokemon.base_experience)
            .over(partition_by=national, order_by=order)
            .label("family_experience"),
        )
        .where(~is_totem_record())
        .subquery("dex_catalog")
    )


async def identities(
    session: AsyncSession,
    ids: list[int],
    locale: str,
    name_context: Names | None = None,
) -> dict[int, dict[str, Any]]:
    if not ids:
        return {}
    catalog = dex_catalog()
    rows = (
        await session.execute(
            select(
                Pokemon,
                PokemonSpecies,
                func.coalesce(Pokemon.species_id, Pokemon.id),
                catalog.c.variant,
                catalog.c.variant_count,
            )
            .outerjoin(catalog, catalog.c.pokemon_id == Pokemon.id)
            .outerjoin(PokemonSpecies, Pokemon.species_id == PokemonSpecies.id)
            .where(Pokemon.id.in_(ids))
        )
    ).all()
    species_ids = [row[0].species_id for row in rows if row[0].species_id is not None]
    context = name_context or await load_names(session, species_ids, locale)
    result: dict[int, dict[str, Any]] = {}
    for pokemon, _species, national, variant, _count in rows:
        preferred = context.forms[pokemon.id][0] if context.forms[pokemon.id] else None
        base_name = context.base.get(pokemon.species_id or pokemon.id, readable_slug(pokemon.name))
        label = context.label(pokemon, preferred) if pokemon.species_id in context.species else ""
        display = str(national) + (f".{variant}" if variant else "")
        result[pokemon.id] = {
            "species_id": pokemon.species_id,
            "national_dex_number": int(national),
            "variant_index": int(variant) if variant is not None else None,
            "is_listed": variant is not None,
            "display_number": display,
            "variant_label": label,
            "display_name": f"{base_name}（{label}）" if label else base_name,
        }
    return result


async def species_options(
    session: AsyncSession,
    pokemon: Pokemon,
    *,
    locale: str,
    media_public_path: str,
) -> list[PokemonFormOption]:
    variants = list(
        (
            await session.scalars(
                select(Pokemon)
                .where(
                    Pokemon.species_id == pokemon.species_id
                    if pokemon.species_id is not None
                    else Pokemon.id == pokemon.id
                )
                .order_by(Pokemon.is_default.desc(), Pokemon.id)
            )
        ).all()
    )
    ids = [row.id for row in variants]
    context = await load_names(session, [pokemon.species_id or pokemon.id], locale)
    labels = await identities(session, ids, locale, context)
    forms = context.forms
    assets: dict[tuple[str, int], dict[str, str]] = defaultdict(dict)
    form_ids = [form.id for group in forms.values() for form in group]
    for asset in (
        await session.scalars(
            select(MediaAsset).where(
                MediaAsset.pokemon_id.in_(ids) | MediaAsset.form_id.in_(form_ids)
            )
        )
    ).all():
        if not asset.local_path:
            continue
        key = (
            ("form", asset.form_id) if asset.form_id is not None else ("pokemon", asset.pokemon_id)
        )
        if key[1] is not None:
            assets[(key[0], int(key[1]))][asset.kind] = (
                f"{media_public_path.rstrip('/')}/{asset.local_path.lstrip('/')}"
            )
    type_names = {
        n.entity_id: n.name
        for n in (
            await session.scalars(
                select(LocalizedName).where(
                    LocalizedName.entity_type == "type", LocalizedName.locale == locale
                )
            )
        ).all()
    }
    options: list[PokemonFormOption] = []
    for variant in variants:
        identity = labels[variant.id]
        group = forms[variant.id]
        # The first/default form carries BOTH source identities; no duplicate base choice.
        for index, form in enumerate(group or [None]):
            default = index == 0
            label = context.label(variant, form)
            display_name = context.display(variant, form)
            sprite = assets[("form", form.id)].get("front-default") if form else None
            variant_assets = assets[("pokemon", variant.id)]
            if default:
                sprite = sprite or variant_assets.get("front-default")
            artwork = variant_assets.get("official-artwork") if default else sprite
            sources = (
                [VersionSpriteOwner(owner_type="pokemon", owner_id=variant.id, name=variant.name)]
                if default
                else []
            )
            if form is not None:
                sources.append(
                    VersionSpriteOwner(owner_type="form", owner_id=form.id, name=form.name)
                )
            types = []
            for entry in ((form.raw_payload or {}).get("types") or []) if form else []:
                value = entry["type"]
                type_id = int(value["url"].rstrip("/").split("/")[-1])
                types.append(
                    NamedResource(
                        id=type_id,
                        name=value["name"],
                        localized_name=type_names.get(type_id, value["name"]),
                    )
                )
            options.append(
                PokemonFormOption(
                    key=f"pokemon:{variant.id}"
                    if default
                    else f"form:{form.id if form else variant.id}",
                    pokemon_id=variant.id,
                    form_id=form.id if form else None,
                    name=form.name if form else variant.name,
                    label=display_name,
                    form_label=label,
                    display_number=identity["display_number"],
                    is_listed=identity["is_listed"],
                    is_default=default,
                    sprite_url=sprite,
                    artwork_url=artwork,
                    types=types,
                    sources=sources,
                )
            )
    return options
