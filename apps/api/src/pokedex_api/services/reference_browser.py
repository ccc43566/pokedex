"""Read-only, ID-preserving item/move catalog queries and bounded relations."""

from __future__ import annotations

import math
import re
from collections import defaultdict
from collections.abc import Sequence
from typing import Any, Literal

from fastapi import HTTPException
from sqlalchemy import case, exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from pokedex_api.config import get_settings
from pokedex_api.models import EvolutionChain, LocalizedName, Pokemon, SourceRecord
from pokedex_api.reference_models import (
    Berry,
    BerryFlavor,
    CatalogDictionary,
    CatalogDictionaryLink,
    CatalogMachine,
    EvolutionItemReference,
    Item,
    ItemAttribute,
    ItemGameIndex,
    ItemMedia,
    ItemPrice,
    Move,
    MovePastValue,
    MoveStatChange,
    PokemonHeldItem,
    PokemonMove,
)
from pokedex_api.reference_schemas import (
    CatalogLabel,
    ReferenceCard,
    ReferenceDetail,
    ReferencePage,
    RelationPage,
)
from pokedex_api.schemas import PokemonFormOption
from pokedex_api.services.catalog import identities, species_options
from pokedex_api.services.evolution import resource_id
from pokedex_api.services.reference_catalog import reference_texts

Kind = Literal["item", "move"]


async def names(
    session: AsyncSession, kind: str, ids: list[int], locale: str
) -> dict[int, tuple[str, str]]:
    if not ids:
        return {}
    rows = (
        await session.scalars(
            select(LocalizedName)
            .where(
                LocalizedName.entity_type == kind,
                LocalizedName.entity_id.in_(ids),
                LocalizedName.locale.in_([locale, "en"]),
            )
            .order_by(case((LocalizedName.locale == locale, 0), else_=1), LocalizedName.id)
        )
    ).all()
    result: dict[int, tuple[str, str]] = {}
    for row in rows:
        result.setdefault(row.entity_id, (row.name, row.locale))
    return result


class Dictionaries:
    """Translate internal dictionary FKs to original upstream IDs at the API boundary."""

    def __init__(self) -> None:
        self.labels: dict[int, CatalogLabel] = {}
        self.by_key: dict[tuple[str, int], CatalogLabel] = {}
        self.links: dict[int, dict[str, int]] = defaultdict(dict)

    @classmethod
    async def load(cls, session: AsyncSession, locale: str) -> Dictionaries:
        result = cls()
        rows = (await session.scalars(select(CatalogDictionary))).all()
        for kind in {row.resource_type for row in rows}:
            group = [row for row in rows if row.resource_type == kind]
            translated = await names(session, kind, [row.resource_id for row in group], locale)
            for row in group:
                text, language = translated.get(row.resource_id, (row.name, "identifier"))
                label = CatalogLabel(
                    id=row.resource_id,
                    name=row.name,
                    localized_name=text,
                    name_locale=language,
                    resource_type=kind,
                )
                result.labels[row.id] = label
                result.by_key[kind, row.resource_id] = label
        for link in (await session.scalars(select(CatalogDictionaryLink))).all():
            result.links[link.dictionary_id][link.path] = link.target_id
        for key, label in result.labels.items():
            generation = result.get(result.links[key].get("$.generation"))
            if generation:
                label.generation_id = generation.id
            if label.resource_type == "version-group":
                versions = [
                    result.get(target)
                    for path, target in result.links[key].items()
                    if path.startswith("$.versions[")
                ]
                readable = [v.localized_name for v in versions if v]
                if readable:
                    label.localized_name = " / ".join(readable)
                    label.name_locale = locale
        return result

    def get(self, key: int | None) -> CatalogLabel | None:
        return self.labels.get(key) if key is not None else None

    def values(self, kind: str) -> list[CatalogLabel]:
        return sorted(
            [v for v in self.labels.values() if v.resource_type == kind], key=lambda v: v.id
        )

    def context(self, value: str | None) -> CatalogLabel | None:
        if value and ":" in value:
            kind, key = value.split(":", 1)
            if key.isdigit():
                return self.by_key.get((kind.replace("_", "-"), int(key)))
            return next(
                (
                    v
                    for v in self.labels.values()
                    if v.resource_type == kind.replace("_", "-") and v.name == key
                ),
                None,
            )
        return None


async def filters(session: AsyncSession, kind: Kind, locale: str) -> dict[str, Any]:
    dictionaries = await Dictionaries.load(session, locale)
    kinds = (
        ["item-category", "item-pocket", "version-group"]
        if kind == "item"
        else ["type", "move-damage-class", "generation", "move-learn-method", "version-group"]
    )
    result: dict[str, Any] = {k: dictionaries.values(k) for k in kinds}
    if kind == "item":
        result["categoryPockets"] = {
            str(label.id): pocket.id
            for key, label in dictionaries.labels.items()
            if label.resource_type == "item-category"
            and (pocket := dictionaries.get(dictionaries.links[key].get("$.pocket")))
        }
        result["version"] = dictionaries.values("version")
    return result


async def resolve(session: AsyncSession, kind: Kind, key: str) -> Item | Move:
    model: Any = Item if kind == "item" else Move
    query = select(model).where(model.id == int(key) if key.isdigit() else model.name == key)
    rows = (await session.scalars(query)).all()
    if not rows:
        raise HTTPException(404, f"{kind} not found")
    if len(rows) != 1:
        raise HTTPException(
            409,
            {"message": "Ambiguous identifier; use an explicit ID", "ids": [r.id for r in rows]},
        )
    record: Item | Move = rows[0]
    return record


async def cards(
    session: AsyncSession,
    kind: Kind,
    rows: Sequence[Item | Move],
    locale: str,
    dictionaries: Dictionaries,
) -> list[ReferenceCard]:
    translated = await names(session, kind, [r.id for r in rows], locale)
    media = (
        {
            r.item_id: r
            for r in (
                await session.scalars(
                    select(ItemMedia).where(ItemMedia.item_id.in_([r.id for r in rows]))
                )
            ).all()
        }
        if kind == "item" and rows
        else {}
    )
    result = []
    for row in rows:
        text, language = translated.get(row.id, (row.name, "identifier"))
        card = ReferenceCard(
            id=row.id, name=row.name, localized_name=text, name_locale=language, resource_type=kind
        )
        if isinstance(row, Item):
            card.category = dictionaries.get(row.category_id)
            card.pocket = (
                dictionaries.get(dictionaries.links[row.category_id].get("$.pocket"))
                if row.category_id
                else None
            )
            image = media.get(row.id)
            card.image_status = image.status if image else "pending"
            if image and image.status == "downloaded" and image.local_path:
                base = get_settings().media_public_path.rstrip("/")
                card.image_url = f"{base}/{image.local_path.lstrip('/')}"
        else:
            card.type = dictionaries.get(row.type_id)
            card.damage_class = dictionaries.get(row.damage_class_id)
            card.generation = dictionaries.get(row.generation_id)
            card.power, card.accuracy, card.pp, card.priority = (
                row.power,
                row.accuracy,
                row.pp,
                row.priority,
            )
        result.append(card)
    return result


async def browse(
    session: AsyncSession,
    kind: Kind,
    locale: str,
    *,
    q: str = "",
    page: int = 1,
    page_size: int = 60,
    sort: str = "id",
    category: int | None = None,
    pocket: int | None = None,
    type_id: int | None = None,
    damage_class: int | None = None,
    generation: int | None = None,
) -> ReferencePage:
    dictionaries = await Dictionaries.load(session, locale)
    model: Any = Item if kind == "item" else Move
    conditions: list[Any] = []
    query = q.strip()
    if query.isdigit():
        conditions.append(model.id == int(query))
    elif query:
        # Escape wildcards: a user search is a literal substring, not SQL pattern syntax.
        pattern = "%" + query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        conditions.append(
            or_(
                model.name.ilike(pattern, escape="\\"),
                exists(
                    select(LocalizedName.id).where(
                        LocalizedName.entity_type == kind,
                        LocalizedName.entity_id == model.id,
                        LocalizedName.name.ilike(pattern, escape="\\"),
                    )
                ),
            )
        )

    def dictionary_ids(resource: str, upstream: int) -> list[int]:
        return [
            key
            for key, value in dictionaries.labels.items()
            if value.resource_type == resource and value.id == upstream
        ]

    if kind == "item":
        if category is not None:
            conditions.append(Item.category_id.in_(dictionary_ids("item-category", category)))
        if pocket is not None:
            pockets = dictionary_ids("item-pocket", pocket)
            categories = [
                key for key, links in dictionaries.links.items() if links.get("$.pocket") in pockets
            ]
            conditions.append(Item.category_id.in_(categories))
    else:
        for value, field, resource in [
            (type_id, Move.type_id, "type"),
            (damage_class, Move.damage_class_id, "move-damage-class"),
            (generation, Move.generation_id, "generation"),
        ]:
            if value is not None:
                conditions.append(field.in_(dictionary_ids(resource, value)))
    total = await session.scalar(select(func.count()).select_from(model).where(*conditions)) or 0
    order: list[Any] = [model.id]
    if sort == "id_desc":
        order = [model.id.desc()]
    elif sort == "name":
        preferred = (
            select(LocalizedName.name)
            .where(
                LocalizedName.entity_type == kind,
                LocalizedName.entity_id == model.id,
                LocalizedName.locale.in_([locale, "en"]),
            )
            .order_by(case((LocalizedName.locale == locale, 0), else_=1), LocalizedName.id)
            .limit(1)
            .scalar_subquery()
        )
        order = [func.coalesce(preferred, model.name), model.id]
    elif kind == "move" and sort in {"power_desc", "priority_desc"}:
        field = Move.power if sort == "power_desc" else Move.priority
        order = [field.desc().nulls_last(), model.id]
    rows = list(
        (
            await session.scalars(
                select(model)
                .where(*conditions)
                .order_by(*order)
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        ).all()
    )
    return ReferencePage(
        items=await cards(session, kind, rows, locale, dictionaries),
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size),
    )


def price_value(value: int | None, payload: dict[str, Any], key: str) -> dict[str, Any]:
    # Only an EXPLICIT null means unavailable. Absent key is unknown; zero is a value.
    return {
        "value": value,
        "status": "value"
        if value is not None
        else ("unavailable" if key in payload and payload[key] is None else "unknown"),
    }


async def detail(
    session: AsyncSession,
    kind: Kind,
    key: str,
    locale: str,
) -> ReferenceDetail:
    record = await resolve(session, kind, key)
    dictionaries = await Dictionaries.load(session, locale)
    card = (await cards(session, kind, [record], locale, dictionaries))[0]
    texts = await reference_texts(session, kind, record.id, locale)
    source = (
        await session.execute(
            select(
                SourceRecord.source_url, SourceRecord.source_hash, SourceRecord.fetched_at
            ).where(SourceRecord.id == record.source_record_id)
        )
    ).one()
    result = ReferenceDetail(
        record=card,
        texts=[
            {
                "kind": t.text_kind,
                "version": t.version,
                "context": dictionaries.context(t.version),
                "locale": t.locale,
                "text": t.text,
            }
            for t in texts
        ],
        source={
            "url": source.source_url,
            "hash": source.source_hash,
            "fetchedAt": source.fetched_at,
            "provider": "PokéAPI",
        },
    )
    d = dictionaries.get
    if isinstance(record, Item):
        attributes = (
            await session.scalars(
                select(ItemAttribute.attribute_id).where(ItemAttribute.item_id == record.id)
            )
        ).all()
        indices = (
            await session.scalars(
                select(ItemGameIndex)
                .where(ItemGameIndex.item_id == record.id)
                .order_by(ItemGameIndex.ordinal)
            )
        ).all()
        prices = (
            await session.scalars(
                select(ItemPrice).where(ItemPrice.item_id == record.id).order_by(ItemPrice.ordinal)
            )
        ).all()
        result.fields = {
            # Legacy cost has no version/currency context: deliberately NOT a purchase price.
            "legacyCost": record.cost,
            "flingPower": record.fling_power,
            "flingEffect": d(record.fling_effect_id),
            "attributes": [d(a) for a in attributes],
            "gameIndices": [
                {"generation": d(i.generation_id), "index": i.game_index} for i in indices
            ],
            "prices": [
                {
                    "versionGroup": d(p.version_group_id),
                    "currency": d(p.currency_id),
                    "purchase": price_value(p.purchase_price, p.raw_payload, "purchase_price"),
                    "sell": price_value(p.sell_price, p.raw_payload, "sell_price"),
                }
                for p in prices
            ],
            "imageSource": record.sprites.get("default"),
        }
        berry = await session.scalar(select(Berry).where(Berry.item_id == record.id))
        if berry:
            flavors = (
                await session.scalars(select(BerryFlavor).where(BerryFlavor.berry_id == berry.id))
            ).all()
            result.fields["berry"] = {
                "id": berry.id,
                "itemId": berry.item_id,
                "firmness": d(berry.firmness_id),
                "naturalGiftType": d(berry.natural_gift_type_id),
                "growthTime": berry.growth_time,
                "maxHarvest": berry.max_harvest,
                "naturalGiftPower": berry.natural_gift_power,
                "size": berry.size,
                "smoothness": berry.smoothness,
                "soilDryness": berry.soil_dryness,
                "flavors": [{"flavor": d(f.flavor_id), "potency": f.potency} for f in flavors],
            }
        relations = {
            "holders": (PokemonHeldItem, PokemonHeldItem.item_id),
            "machines": (CatalogMachine, CatalogMachine.item_id),
            "evolutions": (EvolutionItemReference, EvolutionItemReference.item_id),
        }
    else:
        changes = (
            await session.scalars(
                select(MoveStatChange)
                .where(MoveStatChange.move_id == record.id)
                .order_by(MoveStatChange.ordinal)
            )
        ).all()
        past = (
            await session.scalars(
                select(MovePastValue)
                .where(MovePastValue.move_id == record.id)
                .order_by(MovePastValue.ordinal)
            )
        ).all()
        result.fields = {
            "target": d(record.target_id),
            "effectChance": record.effect_chance,
            "category": d(record.category_id),
            "ailment": d(record.ailment_id),
            "meta": {
                k: v
                for k, v in (record.meta or {}).items()
                if v is None or isinstance(v, int | float | bool | str)
            },
            "statChanges": [{"stat": d(c.stat_id), "change": c.change} for c in changes],
            "pastValues": [
                {
                    "versionGroup": d(p.version_group_id),
                    "type": d(p.type_id),
                    "power": p.power,
                    "accuracy": p.accuracy,
                    "pp": p.pp,
                    "effectChance": p.effect_chance,
                }
                for p in past
            ],
            "contestType": d(record.contest_type_id),
        }
        relations = {
            "learners": (PokemonMove, PokemonMove.move_id),
            "machines": (CatalogMachine, CatalogMachine.move_id),
        }
    for name, (model, foreign_key) in relations.items():
        result.relation_counts[name] = (
            await session.scalar(
                select(func.count()).select_from(model).where(foreign_key == record.id)
            )
            or 0
        )
    return result


def evolution_reference_nodes(
    payload: dict[str, Any],
    path: str,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None, dict[str, Any]]:
    """Parse only stored, whitelisted structural paths, never eval JSONPath/code."""
    node = payload.get("chain")
    if not isinstance(node, dict):
        return None, None, {}
    if path == "$.baby_trigger_item":
        return None, node, {}
    match = re.fullmatch(
        r"\$\.chain((?:\.evolves_to\[\d+\])+)\.evolution_details\[(\d+)\]\.(?:item|held_item)",
        path,
    )
    if not match:
        return None, None, {}
    parent = None
    try:
        for index in re.findall(r"\[(\d+)\]", match[1]):
            parent = node
            node = node["evolves_to"][int(index)]
        method = node["evolution_details"][int(match[2])]
    except (IndexError, KeyError, TypeError):
        return None, None, {}
    return parent, node, method if isinstance(method, dict) else {}


async def evolution_uses(
    session: AsyncSession,
    rows: Sequence[EvolutionItemReference],
    locale: str,
) -> list[dict[str, Any]]:
    chains = {
        c.id: c.raw_payload
        for c in (
            await session.scalars(
                select(EvolutionChain).where(EvolutionChain.id.in_([r.chain_id for r in rows]))
            )
        ).all()
    }
    cache: dict[tuple[int, int | None, bool], dict[str, Any]] = {}
    choices_by_species: dict[int, list[PokemonFormOption]] = {}
    default_ids: dict[int, int | None] = {}

    async def vertex(node: dict[str, Any] | None, form: Any) -> dict[str, Any] | None:
        sid = resource_id(node.get("species"), "pokemon-species") if node else None
        if sid is None:
            return None
        fid = resource_id(form, "pokemon-form")
        key = (sid, fid, form is not None)
        if key in cache:
            return cache[key]
        translated = await names(session, "pokemon-species", [sid], locale)
        result: dict[str, Any] = {
            "speciesId": sid,
            "displayName": translated.get(sid, (f"Pokémon species #{sid}", ""))[0],
        }
        if sid not in choices_by_species:
            pokemon = await session.scalar(
                select(Pokemon)
                .where(Pokemon.species_id == sid, Pokemon.is_default.is_(True))
                .order_by(Pokemon.id)
            )
            default_ids[sid] = pokemon.id if pokemon else None
            choices_by_species[sid] = (
                await species_options(
                    session,
                    pokemon,
                    locale=locale,
                    media_public_path=get_settings().media_public_path,
                )
                if pokemon
                else []
            )
        choices = choices_by_species[sid]
        if choices:
            option = (
                next((o for o in choices if o.form_id == fid), None)
                if fid
                else (
                    next(
                        (o for o in choices if o.pokemon_id == default_ids[sid] and o.is_default),
                        None,
                    )
                    if form is None
                    else None
                )
            )
            if option:
                result.update(
                    {
                        "pokemonId": option.pokemon_id,
                        "displayName": option.label,
                        "displayNumber": option.display_number,
                        "formKey": None if option.is_default else option.key,
                    }
                )
        cache[key] = result
        return result

    result = []
    for row in rows:
        source, target, method = evolution_reference_nodes(chains.get(row.chain_id, {}), row.path)
        result.append(
            {
                "id": row.id,
                "chainId": row.chain_id,
                "path": row.path,
                "role": row.role,
                "source": await vertex(source, method.get("required_pokemon_form")),
                "target": await vertex(target, method.get("evolved_pokemon_form")),
            }
        )
    return result


async def relations(
    session: AsyncSession,
    kind: Kind,
    key: str,
    relation: str,
    locale: str,
    *,
    page: int = 1,
    page_size: int = 24,
    version_group: int | None = None,
    method: int | None = None,
    version: int | None = None,
) -> RelationPage:
    record = await resolve(session, kind, key)
    dictionaries = await Dictionaries.load(session, locale)
    allowed: dict[str, Any] = {"machines": CatalogMachine}
    allowed.update(
        {"holders": PokemonHeldItem, "evolutions": EvolutionItemReference}
        if kind == "item"
        else {"learners": PokemonMove}
    )
    model = allowed.get(relation)
    if model is None:
        raise HTTPException(404, "Unknown relation")
    foreign = model.item_id if kind == "item" else model.move_id
    conditions = [foreign == record.id]
    for resource, value, column in [
        ("version-group", version_group, getattr(model, "version_group_id", None)),
        ("move-learn-method", method, getattr(model, "learn_method_id", None)),
        ("version", version, getattr(model, "version_id", None)),
    ]:
        if value is not None and column is not None:
            keys = [
                k
                for k, v in dictionaries.labels.items()
                if v.resource_type == resource and v.id == value
            ]
            conditions.append(column.in_(keys))
    total = await session.scalar(select(func.count()).select_from(model).where(*conditions)) or 0
    order = (
        [
            model.pokemon_id,
            model.version_group_id,
            model.learn_method_id,
            model.level_learned_at,
            model.move_ordinal,
            model.detail_ordinal,
        ]
        if relation == "learners"
        else (
            [model.pokemon_id, model.version_id, model.item_ordinal, model.detail_ordinal]
            if relation == "holders"
            else [model.id]
        )
    )
    rows = (
        await session.scalars(
            select(model)
            .where(*conditions)
            .order_by(*order)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()
    items: list[dict[str, Any]] = []
    d = dictionaries.get
    if relation in {"learners", "holders"}:
        labels = await identities(session, list({r.pokemon_id for r in rows}), locale)
        for row in rows:
            identity = labels.get(row.pokemon_id, {})
            common = {
                "pokemonId": row.pokemon_id,
                "displayName": identity.get("display_name"),
                "displayNumber": identity.get("display_number"),
                "sourceOrdinal": [
                    row.move_ordinal if relation == "learners" else row.item_ordinal,
                    row.detail_ordinal,
                ],
            }
            if relation == "learners":
                common.update(
                    {
                        "versionGroup": d(row.version_group_id),
                        "method": d(row.learn_method_id),
                        "level": row.level_learned_at,
                        "order": row.learn_order,
                    }
                )
            else:
                common.update({"version": d(row.version_id), "rarity": row.rarity})
            items.append(common)
    elif relation == "machines":
        item_names = await names(session, "item", [r.item_id for r in rows], locale)
        move_names = await names(session, "move", [r.move_id for r in rows], locale)
        item_slugs = dict(
            (
                await session.execute(
                    select(Item.id, Item.name).where(Item.id.in_([r.item_id for r in rows]))
                )
            ).all()
        )
        move_slugs = dict(
            (
                await session.execute(
                    select(Move.id, Move.name).where(Move.id.in_([r.move_id for r in rows]))
                )
            ).all()
        )
        for row in rows:
            items.append(
                {
                    "id": row.id,
                    "itemId": row.item_id,
                    "moveId": row.move_id,
                    "itemName": item_names.get(row.item_id, (item_slugs[row.item_id], ""))[0],
                    "moveName": move_names.get(row.move_id, (move_slugs[row.move_id], ""))[0],
                    "versionGroup": d(row.version_group_id),
                }
            )
    else:
        items = await evolution_uses(session, rows, locale)
    return RelationPage(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size),
    )
