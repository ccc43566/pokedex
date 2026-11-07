"""Bounded, restartable data-only import; no Pokemon fetches or media downloads."""

from __future__ import annotations

import asyncio
import logging
from collections import Counter
from collections.abc import Iterator
from typing import Any
from urllib.parse import urlparse

import httpx
from sqlalchemy import delete, insert, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from pokedex_api.models import (
    EvolutionChain,
    LocalizedName,
    LocalizedText,
    Pokemon,
    SourceRecord,
    SyncRun,
    utcnow,
)
from pokedex_api.reference_models import (
    Berry,
    BerryFlavor,
    CatalogDictionary,
    CatalogDictionaryLink,
    CatalogDiscoveryPage,
    CatalogMachine,
    CatalogReferenceIssue,
    CatalogSyncEntry,
    EvolutionItemReference,
    Item,
    ItemAttribute,
    ItemGameIndex,
    ItemPrice,
    Move,
    MovePastValue,
    MoveStatChange,
    PokemonHeldItem,
    PokemonMove,
)
from pokedex_api.sync.importer import clean_text, json_hash
from pokedex_api.sync.provider import PokeApiProvider

logger = logging.getLogger(__name__)
PRIMARY = ("move", "item", "berry")
EVOLUTION_DICTIONARIES = ("evolution-trigger", "evolution-variable")
DICTIONARIES = frozenset(
    {
        "type",
        "generation",
        "stat",
        "version",
        "version-group",
        "move-damage-class",
        "move-target",
        "move-category",
        "move-ailment",
        "move-learn-method",
        "item-category",
        "item-pocket",
        "item-attribute",
        "item-fling-effect",
        "berry-firmness",
        "berry-flavor",
        "contest-type",
        "contest-effect",
        "super-contest-effect",
        "currency",
        *EVOLUTION_DICTIONARIES,
    }
)
ALLOWED = DICTIONARIES | set(PRIMARY) | {"machine"}
LOCALES = {"en": "en", "zh-hans": "zh-Hans", "zh-hant": "zh-Hant"}


def reference(value: Any) -> tuple[str, int] | None:
    if not isinstance(value, dict) or not isinstance(value.get("url"), str):
        return None
    parts = urlparse(value["url"]).path.rstrip("/").split("/")
    if len(parts) < 2 or not parts[-1].removeprefix("-").isdigit():
        return None
    return parts[-2], int(parts[-1])


def references(value: Any, path: str = "$") -> Iterator[tuple[str, dict[str, Any]]]:
    if isinstance(value, dict):
        if "url" in value:
            yield path, value
        else:
            for key, child in value.items():
                yield from references(child, f"{path}.{key}")
    elif isinstance(value, list):
        for ordinal, child in enumerate(value):
            yield from references(child, f"{path}[{ordinal}]")


def localized_rows(
    kind: str, entity_id: int, payload: dict[str, Any]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    names: list[dict[str, Any]] = []
    texts: list[dict[str, Any]] = []
    for entry in payload.get("names", []):
        locale = LOCALES.get(entry.get("language", {}).get("name"))
        if locale and entry.get("name"):
            row = dict(
                entity_type=kind,
                entity_id=entity_id,
                locale=locale,
                name=entry["name"],
                is_canonical=True,
            )
            if row not in names:
                names.append(row)

    def add_entries(data: dict[str, Any], *, change_version: str | None = None) -> None:
        for array, fields in (
            ("effect_entries", (("effect", "effect"), ("short_effect", "short_effect"))),
            ("flavor_text_entries", (("flavor_text", "flavor"), ("text", "flavor"))),
            ("descriptions", (("description", "description"),)),
        ):
            for entry in data.get(array, []):
                locale = LOCALES.get(entry.get("language", {}).get("name"))
                if not locale:
                    continue
                version = change_version
                for version_kind in ("version", "version_group", "generation"):
                    if entry.get(version_kind):
                        version = f"{version_kind}:{entry[version_kind]['name']}"
                        break
                for field, text_kind in fields:
                    if entry.get(field):
                        row = dict(
                            entity_type=kind,
                            entity_id=entity_id,
                            locale=locale,
                            text_kind=("past_" if change_version else "") + text_kind,
                            version=version,
                            text=clean_text(entry[field]),
                        )
                        if row not in texts:
                            texts.append(row)

    add_entries(payload)
    for change in payload.get("effect_changes", []):
        vg = change.get("version_group", {}).get("name")
        add_entries(change, change_version=f"version_group:{vg}" if vg else "unspecified")
    for past in payload.get("past_values", []):
        vg = past.get("version_group", {}).get("name")
        add_entries(past, change_version=f"version_group:{vg}" if vg else "unspecified")
    return names, texts


class ReferenceImporter:
    def __init__(
        self,
        factory: async_sessionmaker[AsyncSession],
        provider: PokeApiProvider,
        *,
        concurrency: int = 4,
    ) -> None:
        self.factory = factory
        self.provider = provider
        self.concurrency = concurrency
        self.run_id = 0
        self.counts: Counter[str] = Counter()
        self.dict_ids: dict[tuple[str, int], int] = {}
        self.entity_ids: dict[str, set[int]] = {}
        self.issues: list[dict[str, Any]] = []
        self.queued: set[tuple[str, int]] = set()
        self.scope = "reference-data"

    async def issue(
        self,
        session: AsyncSession,
        owner_type: str,
        owner_id: int,
        path: str,
        value: Any,
        reason: str,
    ) -> None:
        target = value.get("url") if isinstance(value, dict) else None
        key = json_hash(
            dict(owner_type=owner_type, owner_id=owner_id, path=path, target=target, reason=reason)
        )
        row = await session.get(CatalogReferenceIssue, key)
        if row is None:
            row = CatalogReferenceIssue(
                fingerprint=key,
                owner_type=owner_type,
                owner_id=owner_id,
                path=path,
                target_url=target,
                reason=reason,
            )
            session.add(row)
        row.resolved = False
        row.updated_at = utcnow()
        self.issues.append(
            dict(
                owner_type=owner_type,
                owner_id=owner_id,
                path=path,
                target_url=target,
                reason=reason,
            )
        )

    async def discover(self, kind: str, *, limit: int | None) -> dict[str, Any]:
        url: str | None = (
            f"{self.provider.base_url}/{kind}/?limit={self.provider.page_size}&offset=0"
        )
        pages: set[str] = set()
        summaries: dict[int, dict[str, Any]] = {}
        expected: int | None = None
        while url:
            if url in pages:
                raise ValueError(f"Pagination cycle for {kind}: {url}")
            pages.add(url)
            payload = await self.provider.get_resource(url)
            if expected is None:
                expected = int(payload["count"])
            elif int(payload["count"]) != expected:
                raise ValueError(f"List changed during discovery: {kind}; rerun discovery")
            async with self.factory() as session:
                page = await session.scalar(
                    select(CatalogDiscoveryPage).where(
                        CatalogDiscoveryPage.run_id == self.run_id,
                        CatalogDiscoveryPage.resource_type == kind,
                        CatalogDiscoveryPage.page_url == url,
                    )
                )
                if page is None:
                    page = CatalogDiscoveryPage(
                        run_id=self.run_id, resource_type=kind, page_url=url
                    )
                    session.add(page)
                page.raw_payload, page.source_hash = payload, json_hash(payload)
                page.fetched_at = utcnow()
                await session.commit()
            for summary in payload["results"]:
                ref = reference(summary)
                if ref is None or ref[0] != kind:
                    raise ValueError(f"Invalid {kind} list member: {summary}")
                if ref[1] in summaries:
                    raise ValueError(f"Repeated {kind} list member: {ref[1]}")
                summaries[ref[1]] = summary
            url = payload.get("next")
            if url and not url.startswith(self.provider.base_url + "/"):
                raise ValueError("Pagination URL outside configured provider")
        if len(summaries) != expected:
            raise ValueError(f"Incomplete {kind} list: {len(summaries)} != {expected}")
        selected = sorted(summaries)[:limit] if limit is not None else sorted(summaries)
        async with self.factory() as session:
            await session.execute(
                update(CatalogReferenceIssue)
                .where(
                    CatalogReferenceIssue.owner_type == "discovery",
                    CatalogReferenceIssue.path == kind,
                )
                .values(resolved=True)
            )
            await session.execute(
                delete(CatalogDiscoveryPage).where(
                    CatalogDiscoveryPage.run_id == self.run_id,
                    CatalogDiscoveryPage.resource_type == kind,
                    CatalogDiscoveryPage.page_url.not_in(pages),
                )
            )
            for resource_id in selected:
                await self.enqueue(session, kind, resource_id, summaries[resource_id]["url"])
            old_ids = set(
                (
                    await session.scalars(
                        select(CatalogSyncEntry.resource_id).where(
                            CatalogSyncEntry.resource_type == kind
                        )
                    )
                ).all()
            )
            for missing in old_ids - summaries.keys():
                await self.issue(
                    session,
                    "discovery",
                    missing,
                    kind,
                    None,
                    "Local resource absent from current list; retained, not deleted",
                )
            await session.commit()
        result = dict(
            expected=expected,
            discovered=len(summaries),
            pages=len(pages),
            selected=len(selected),
            absent_locally_known=sorted(old_ids - summaries.keys()),
        )
        logger.info("Discovery %s: %s", kind, result)
        return result

    async def enqueue(self, session: AsyncSession, kind: str, resource_id: int, url: str) -> None:
        if kind not in ALLOWED:
            raise ValueError(f"Out-of-scope resource {kind}")
        if (kind, resource_id) in self.queued:
            return
        self.queued.add((kind, resource_id))
        statement = (
            (pg_insert if session.get_bind().dialect.name == "postgresql" else sqlite_insert)(
                CatalogSyncEntry
            )
            .values(
                resource_type=kind,
                resource_id=resource_id,
                source_url=url,
                status="pending",
                attempts=0,
            )
            .on_conflict_do_nothing()
        )
        await session.execute(statement)

    async def seed_local_dependencies(self) -> None:
        async with self.factory() as session:
            # No remote Pokemon requests. Only dictionary references from retained JSON.
            for model in (Pokemon, EvolutionChain):
                last = 0
                while True:
                    rows = (
                        await session.execute(
                            select(model.id, model.raw_payload)
                            .where(model.id > last)
                            .order_by(model.id)
                            .limit(20)
                        )
                    ).all()
                    if not rows:
                        break
                    for owner_id, payload in rows:
                        last = owner_id
                        await self.seed_payload(session, model, owner_id, payload)
                    await session.commit()

    async def seed_payload(
        self, session: AsyncSession, model: Any, owner_id: int, payload: dict[str, Any]
    ) -> None:
        for _path, value in references(payload):
            ref = reference(value)
            if ref and ref[0] in DICTIONARIES:
                await self.enqueue(session, *ref, value["url"])
        if model is Pokemon:
            for key in ("moves", "held_items"):
                if not isinstance(payload.get(key), list):
                    await self.issue(
                        session,
                        "pokemon",
                        owner_id,
                        f"$.{key}",
                        None,
                        "Required source array missing; original retained",
                    )

    async def fetch_one(self, kind: str, resource_id: int, *, refresh: bool) -> bool:
        async with self.factory() as session:
            entry = await session.get(CatalogSyncEntry, (kind, resource_id))
            assert entry is not None
            source = await session.scalar(
                select(SourceRecord).where(
                    SourceRecord.resource_type == kind, SourceRecord.resource_id == resource_id
                )
            )
            # Preserve original dictionaries/sources byte-for-byte when already available.
            if (
                source is not None
                and (not refresh or kind in {"type", "generation", "stat"})
                and entry.status not in {"failed", "missing"}
            ):
                if entry.status not in {"success", "partial"}:
                    entry.status = "fetched"
                self.counts[f"cached:{kind}"] += 1
            else:
                entry.attempts += 1
                entry.run_id = self.run_id
                await session.commit()
                try:
                    payload = await self.provider.get_resource(entry.source_url)
                    if int(payload["id"]) != resource_id:
                        raise ValueError("Response ID does not match discovered ID")
                    if source is None:
                        source = SourceRecord(resource_type=kind, resource_id=resource_id)
                        session.add(source)
                    source.name = payload.get("name")
                    source.source_url = entry.source_url
                    source.source_hash = json_hash(payload)
                    source.raw_payload, source.fetched_at = payload, utcnow()
                    entry.status, entry.error, entry.fetched_at = "fetched", None, utcnow()
                    await session.commit()  # durable raw payload before transformation
                    self.counts[f"fetched:{kind}"] += 1
                except Exception as exc:
                    await session.rollback()
                    entry = await session.get(CatalogSyncEntry, (kind, resource_id))
                    assert entry is not None
                    entry.status = (
                        "missing"
                        if isinstance(exc, httpx.HTTPStatusError)
                        and exc.response.status_code == 404
                        else "failed"
                    )
                    entry.error = f"{type(exc).__name__}: {exc}"
                    await session.commit()
                    self.counts[f"failed:{kind}"] += 1
                    logger.warning("%s/%s: %s", kind, resource_id, entry.error)
                    return False
            assert source is not None
            for _path, value in references(source.raw_payload):
                ref = reference(value)
                if ref and (ref[0] in DICTIONARIES or ref[0] == "machine"):
                    await self.enqueue(session, *ref, value["url"])
            await session.commit()
            return True

    async def fetch(
        self,
        *,
        refresh: bool,
        only: set[tuple[str, int]] | None = None,
        retry_failed: bool = False,
        stop_after: int | None = None,
        allowed_kinds: set[str] | None = None,
    ) -> bool:
        visited: set[tuple[str, int]] = set()
        while True:
            async with self.factory() as session:
                entries = (
                    await session.execute(
                        select(
                            CatalogSyncEntry.resource_type,
                            CatalogSyncEntry.resource_id,
                            CatalogSyncEntry.status,
                        ).where(CatalogSyncEntry.resource_type.in_(ALLOWED))
                    )
                ).all()
            pending = [
                (kind, resource_id)
                for kind, resource_id, status in entries
                if (kind, resource_id) not in visited
                and (allowed_kinds is None or kind in allowed_kinds)
                and (
                    only is None
                    or (kind, resource_id) in only
                    or (kind not in PRIMARY and status != "success")
                )
                and (not retry_failed or status in {"failed", "missing", "pending", "partial"})
            ]
            if not pending:
                return True
            for offset in range(0, len(pending), self.concurrency):
                batch = pending[offset : offset + self.concurrency]
                if stop_after is not None:
                    batch = batch[: max(0, stop_after - len(visited))]
                    if not batch:
                        return False
                await asyncio.gather(*(self.fetch_one(*ref, refresh=refresh) for ref in batch))
                visited.update(batch)
                if len(visited) % 40 < self.concurrency:
                    logger.info(
                        "Fetch checkpoint: processed=%s counts=%s", len(visited), dict(self.counts)
                    )
                await self.checkpoint()

    async def checkpoint(self, **extra: Any) -> None:
        async with self.factory() as session:
            run = await session.get(SyncRun, self.run_id)
            assert run is not None
            run.counts = {
                **run.counts,
                "scope": self.scope,
                "progress": dict(self.counts),
                **extra,
            }
            await session.commit()

    def dictionary(self, value: Any) -> int | None:
        ref = reference(value)
        return self.dict_ids.get(ref) if ref else None

    async def required(
        self,
        session: AsyncSession,
        kind: str,
        resource_id: int,
        path: str,
        value: Any,
        *,
        target: str | None = None,
        nullable: bool = False,
    ) -> int | None:
        if value is None and nullable:
            return None
        ref = reference(value)
        result = None
        if ref:
            if target:
                if ref[0] == target and ref[1] in self.entity_ids.get(target, set()):
                    result = ref[1]
            else:
                result = self.dict_ids.get(ref)
        if result is None:
            await self.issue(
                session,
                kind,
                resource_id,
                path,
                value,
                "Unresolved or malformed resource reference",
            )
        return result

    async def replace_localized(
        self, session: AsyncSession, kind: str, resource_id: int, payload: dict[str, Any]
    ) -> None:
        # Existing type/generation/stat text is shared with the live site: do not rewrite it.
        if kind in {"type", "generation", "stat"}:
            return
        names, texts = localized_rows(kind, resource_id, payload)
        for model, rows in ((LocalizedName, names), (LocalizedText, texts)):
            await session.execute(
                delete(model).where(model.entity_type == kind, model.entity_id == resource_id)
            )
            if rows:
                await session.execute(insert(model), rows)

    async def prepare_dictionaries(self) -> None:
        async with self.factory() as session:
            sources = (
                await session.scalars(
                    select(SourceRecord).where(SourceRecord.resource_type.in_(DICTIONARIES))
                )
            ).all()
            for source in sources:
                dictionary = await session.scalar(
                    select(CatalogDictionary).where(
                        CatalogDictionary.resource_type == source.resource_type,
                        CatalogDictionary.resource_id == source.resource_id,
                    )
                )
                if dictionary is None:
                    dictionary = CatalogDictionary(
                        resource_type=source.resource_type, resource_id=source.resource_id
                    )
                    session.add(dictionary)
                dictionary.name = source.name or f"{source.resource_type}-{source.resource_id}"
                dictionary.source_record_id, dictionary.sort_order = (
                    source.id,
                    source.raw_payload.get("order"),
                )
            await session.commit()
            self.dict_ids = {
                (row.resource_type, row.resource_id): row.id
                for row in (await session.scalars(select(CatalogDictionary))).all()
            }
        for source in sources:
            async with self.factory() as session:
                dictionary_id = self.dict_ids[(source.resource_type, source.resource_id)]
                entry = await session.get(
                    CatalogSyncEntry, (source.resource_type, source.resource_id)
                )
                if (
                    entry is not None
                    and entry.status == "success"
                    and entry.normalized_hash == source.source_hash
                ):
                    self.counts[f"unchanged:{source.resource_type}"] += 1
                    continue
                issues_before = len(self.issues)
                await session.execute(
                    update(CatalogReferenceIssue)
                    .where(
                        CatalogReferenceIssue.owner_type == source.resource_type,
                        CatalogReferenceIssue.owner_id == source.resource_id,
                    )
                    .values(resolved=True)
                )
                await session.execute(
                    delete(CatalogDictionaryLink).where(
                        CatalogDictionaryLink.dictionary_id == dictionary_id
                    )
                )
                for path, value in references(source.raw_payload):
                    ref = reference(value)
                    if ref and ref[0] in DICTIONARIES:
                        target = self.dict_ids.get(ref)
                        if target:
                            session.add(
                                CatalogDictionaryLink(
                                    dictionary_id=dictionary_id, path=path, target_id=target
                                )
                            )
                        else:
                            await self.issue(
                                session,
                                source.resource_type,
                                source.resource_id,
                                path,
                                value,
                                "Dictionary target unavailable",
                            )
                await self.replace_localized(
                    session, source.resource_type, source.resource_id, source.raw_payload
                )
                if entry is not None and entry.status not in {"failed", "missing"}:
                    entry.status = "success" if len(self.issues) == issues_before else "partial"
                    entry.normalized_hash = source.source_hash
                await session.commit()

    async def normalize_one(self, kind: str, source_id: int) -> None:
        async with self.factory() as session:
            source = await session.get(SourceRecord, source_id)
            assert source is not None
            resource_id, p = source.resource_id, source.raw_payload
            normalization_hash = (
                json_hash({"source_hash": source.source_hash, "transform": "item-prices-v1"})
                if kind == "item"
                else source.source_hash
            )
            entry = await session.get(CatalogSyncEntry, (kind, resource_id))
            if entry and entry.normalized_hash == normalization_hash and entry.status == "success":
                self.counts[f"unchanged:{kind}"] += 1
                return
            if entry and entry.status in {"failed", "missing"}:
                return
            await session.execute(
                update(CatalogReferenceIssue)
                .where(
                    CatalogReferenceIssue.owner_type == kind,
                    CatalogReferenceIssue.owner_id == resource_id,
                )
                .values(resolved=True)
            )
            issues_before = len(self.issues)

            async def d(key: str, data: dict[str, Any] | None = None) -> int | None:
                return await self.required(
                    session,
                    kind,
                    resource_id,
                    key,
                    (data if data is not None else p).get(key),
                    nullable=True,
                )

            model: Any = {"move": Move, "item": Item, "berry": Berry, "machine": CatalogMachine}[
                kind
            ]
            row = await session.get(model, resource_id)
            fields: dict[str, Any] = dict(source_record_id=source.id)
            if kind != "machine":
                fields["name"] = p["name"]
            children: list[tuple[Any, Any, list[dict[str, Any]]]] = []
            if kind == "move":
                fields.update(
                    {
                        key: p.get(key)
                        for key in ("power", "accuracy", "pp", "priority", "effect_chance", "meta")
                    }
                )
                for key in (
                    "type",
                    "generation",
                    "damage_class",
                    "target",
                    "contest_type",
                    "contest_effect",
                    "super_contest_effect",
                ):
                    fields[f"{key}_id"] = await d(key)
                fields["category_id"] = await d("category", p.get("meta") or {})
                fields["ailment_id"] = await d("ailment", p.get("meta") or {})
                changes = []
                for ordinal, change in enumerate(p.get("stat_changes", [])):
                    stat = await self.required(
                        session,
                        kind,
                        resource_id,
                        f"stat_changes[{ordinal}].stat",
                        change.get("stat"),
                    )
                    if stat:
                        changes.append(
                            dict(
                                move_id=resource_id,
                                ordinal=ordinal,
                                stat_id=stat,
                                change=change["change"],
                            )
                        )
                children.append((MoveStatChange, MoveStatChange.move_id, changes))
                history = []
                for ordinal, past in enumerate(p.get("past_values", [])):
                    history.append(
                        dict(
                            move_id=resource_id,
                            ordinal=ordinal,
                            version_group_id=await d("version_group", past),
                            type_id=await d("type", past),
                            raw_payload=past,
                            **{
                                key: past.get(key)
                                for key in ("power", "accuracy", "pp", "effect_chance")
                            },
                        )
                    )
                children.append((MovePastValue, MovePastValue.move_id, history))
            elif kind == "item":
                fields.update(
                    cost=p.get("cost"),
                    fling_power=p.get("fling_power"),
                    category_id=await d("category"),
                    fling_effect_id=await d("fling_effect"),
                    sprites=p.get("sprites") or {},
                )
                attributes: list[dict[str, int]] = []
                for ordinal, attribute in enumerate(p.get("attributes", [])):
                    attribute_id = await self.required(
                        session, kind, resource_id, f"attributes[{ordinal}]", attribute
                    )
                    if attribute_id and attribute_id not in {a["attribute_id"] for a in attributes}:
                        attributes.append(dict(item_id=resource_id, attribute_id=attribute_id))
                children.append((ItemAttribute, ItemAttribute.item_id, attributes))
                indices = []
                for ordinal, game_index in enumerate(p.get("game_indices", [])):
                    generation_id = await self.required(
                        session,
                        kind,
                        resource_id,
                        f"game_indices[{ordinal}].generation",
                        game_index.get("generation"),
                    )
                    if generation_id:
                        indices.append(
                            dict(
                                item_id=resource_id,
                                ordinal=ordinal,
                                generation_id=generation_id,
                                game_index=game_index["game_index"],
                            )
                        )
                children.append((ItemGameIndex, ItemGameIndex.item_id, indices))
                prices = []
                for ordinal, price in enumerate(p.get("prices", [])):
                    currency = await self.required(
                        session,
                        kind,
                        resource_id,
                        f"prices[{ordinal}].currency",
                        price.get("currency"),
                    )
                    version_group = await self.required(
                        session,
                        kind,
                        resource_id,
                        f"prices[{ordinal}].version_group",
                        price.get("version_group"),
                    )
                    if currency and version_group:
                        prices.append(
                            dict(
                                item_id=resource_id,
                                ordinal=ordinal,
                                currency_id=currency,
                                version_group_id=version_group,
                                purchase_price=price.get("purchase_price"),
                                sell_price=price.get("sell_price"),
                                raw_payload=price,
                            )
                        )
                children.append((ItemPrice, ItemPrice.item_id, prices))
            elif kind == "berry":
                item_id = await self.required(
                    session, kind, resource_id, "item", p.get("item"), target="item"
                )
                if item_id is None:
                    if entry:
                        entry.status = "partial"
                    await session.commit()
                    return
                fields.update(
                    item_id=item_id,
                    firmness_id=await d("firmness"),
                    natural_gift_type_id=await d("natural_gift_type"),
                    **{
                        key: p.get(key)
                        for key in (
                            "growth_time",
                            "max_harvest",
                            "natural_gift_power",
                            "size",
                            "smoothness",
                            "soil_dryness",
                        )
                    },
                )
                flavors = []
                for ordinal, flavor in enumerate(p.get("flavors", [])):
                    flavor_id = await self.required(
                        session,
                        kind,
                        resource_id,
                        f"flavors[{ordinal}].flavor",
                        flavor.get("flavor"),
                    )
                    if flavor_id:
                        flavors.append(
                            dict(
                                berry_id=resource_id, flavor_id=flavor_id, potency=flavor["potency"]
                            )
                        )
                children.append((BerryFlavor, BerryFlavor.berry_id, flavors))
            else:
                for key in ("item", "move"):
                    fields[f"{key}_id"] = await self.required(
                        session, kind, resource_id, key, p.get(key), target=key
                    )
                fields["version_group_id"] = await d("version_group")
                if any(value is None for value in fields.values()):
                    if entry:
                        entry.status = "partial"
                    await session.commit()
                    return
            if row is None:
                row = model(id=resource_id, **fields)
                session.add(row)
            else:
                for key, value in fields.items():
                    setattr(row, key, value)
            await session.flush()
            for child_model, parent_column, values in children:
                await session.execute(delete(child_model).where(parent_column == resource_id))
                if values:
                    await session.execute(insert(child_model), values)
            await self.replace_localized(session, kind, resource_id, p)
            if entry:
                entry.status = "success" if len(self.issues) == issues_before else "partial"
                entry.normalized_hash = normalization_hash
                entry.error = None
            await session.commit()
            self.counts[f"normalized:{kind}"] += 1

    async def normalize(self) -> None:
        await self.prepare_dictionaries()
        for kind, model in (
            ("move", Move),
            ("item", Item),
            ("berry", Berry),
            ("machine", CatalogMachine),
        ):
            async with self.factory() as session:
                ids = (
                    await session.scalars(
                        select(SourceRecord.id)
                        .where(SourceRecord.resource_type == kind)
                        .order_by(SourceRecord.resource_id)
                    )
                ).all()
            for source_id in ids:
                try:
                    await self.normalize_one(kind, source_id)
                except Exception as exc:
                    async with self.factory() as session:
                        source = await session.get(SourceRecord, source_id)
                        assert source is not None
                        entry = await session.get(CatalogSyncEntry, (kind, source.resource_id))
                        assert entry is not None
                        entry.status, entry.error = "partial", f"{type(exc).__name__}: {exc}"
                        await session.commit()
                    logger.exception("Normalization failed: %s source %s", kind, source_id)
            async with self.factory() as session:
                self.entity_ids[kind] = set((await session.scalars(select(model.id))).all())
            logger.info("Normalized %s: %s", kind, len(self.entity_ids[kind]))
            await self.checkpoint()

    async def link_pokemon(self, pokemon_id: int, payload: dict[str, Any]) -> None:
        digest = json_hash(payload)
        async with self.factory() as session:
            state = await session.get(CatalogSyncEntry, ("local-pokemon-links", pokemon_id))
            if state and state.normalized_hash == digest and state.status == "success":
                self.counts["unchanged:pokemon-links"] += 1
                return
            if state is None:
                state = CatalogSyncEntry(
                    resource_type="local-pokemon-links",
                    resource_id=pokemon_id,
                    source_url=f"local:pokemon/{pokemon_id}",
                    status="pending",
                    attempts=0,
                )
                session.add(state)
            state.attempts += 1
            state.run_id = self.run_id
            await session.execute(
                update(CatalogReferenceIssue)
                .where(
                    CatalogReferenceIssue.owner_type == "pokemon",
                    CatalogReferenceIssue.owner_id == pokemon_id,
                )
                .values(resolved=True)
            )
            before = len(self.issues)
            for key in ("moves", "held_items"):
                if not isinstance(payload.get(key), list):
                    await self.issue(
                        session,
                        "pokemon",
                        pokemon_id,
                        key,
                        None,
                        "Required source array missing; previous links retained",
                    )
            if len(self.issues) != before:
                state.status = "partial"
                await session.commit()
                return
            moves, held = [], []
            for mo, move in enumerate(payload["moves"]):
                path = f"$.moves[{mo}]"
                move_id = await self.required(
                    session, "pokemon", pokemon_id, f"{path}.move", move.get("move"), target="move"
                )
                details = move.get("version_group_details")
                if not isinstance(details, list) or not details:
                    await self.issue(
                        session,
                        "pokemon",
                        pokemon_id,
                        path,
                        move.get("move"),
                        "Move has no learning details",
                    )
                    continue
                for ordinal, detail in enumerate(details):
                    vg = await self.required(
                        session,
                        "pokemon",
                        pokemon_id,
                        f"{path}[{ordinal}].version_group",
                        detail.get("version_group"),
                    )
                    method = await self.required(
                        session,
                        "pokemon",
                        pokemon_id,
                        f"{path}[{ordinal}].move_learn_method",
                        detail.get("move_learn_method"),
                    )
                    if (
                        move_id
                        and vg
                        and method
                        and isinstance(detail.get("level_learned_at"), int)
                    ):
                        moves.append(
                            dict(
                                pokemon_id=pokemon_id,
                                move_ordinal=mo,
                                detail_ordinal=ordinal,
                                move_id=move_id,
                                version_group_id=vg,
                                learn_method_id=method,
                                level_learned_at=detail["level_learned_at"],
                                learn_order=detail.get("order"),
                                raw_payload=detail,
                            )
                        )
                    elif move_id and vg and method:
                        await self.issue(
                            session,
                            "pokemon",
                            pokemon_id,
                            path,
                            None,
                            "Missing or invalid level_learned_at",
                        )
            for io, item in enumerate(payload["held_items"]):
                path = f"$.held_items[{io}]"
                item_id = await self.required(
                    session, "pokemon", pokemon_id, f"{path}.item", item.get("item"), target="item"
                )
                details = item.get("version_details")
                if not isinstance(details, list) or not details:
                    await self.issue(
                        session,
                        "pokemon",
                        pokemon_id,
                        path,
                        item.get("item"),
                        "Held item has no version details",
                    )
                    continue
                for ordinal, detail in enumerate(details):
                    version = await self.required(
                        session,
                        "pokemon",
                        pokemon_id,
                        f"{path}[{ordinal}].version",
                        detail.get("version"),
                    )
                    if item_id and version and isinstance(detail.get("rarity"), int):
                        held.append(
                            dict(
                                pokemon_id=pokemon_id,
                                item_ordinal=io,
                                detail_ordinal=ordinal,
                                item_id=item_id,
                                version_id=version,
                                rarity=detail["rarity"],
                                raw_payload=detail,
                            )
                        )
                    elif item_id and version:
                        await self.issue(
                            session, "pokemon", pokemon_id, path, None, "Missing or invalid rarity"
                        )
            for model, values in ((PokemonMove, moves), (PokemonHeldItem, held)):
                await session.execute(delete(model).where(model.pokemon_id == pokemon_id))
                for start in range(0, len(values), 1000):
                    await session.execute(insert(model), values[start : start + 1000])
            state.status = "success" if len(self.issues) == before else "partial"
            state.normalized_hash = digest
            await session.commit()
            self.counts["linked:pokemon"] += 1
            self.counts["linked:learning-rows"] += len(moves)
            self.counts["linked:held-rows"] += len(held)

    async def link_local(self) -> None:
        # Keyset pagination avoids keeping 1,351 large raw Pokemon payloads in memory.
        last = 0
        while True:
            async with self.factory() as session:
                rows = (
                    await session.execute(
                        select(Pokemon.id, Pokemon.raw_payload)
                        .where(Pokemon.id > last)
                        .order_by(Pokemon.id)
                        .limit(20)
                    )
                ).all()
            if not rows:
                break
            for pokemon_id, payload in rows:
                await self.link_pokemon(pokemon_id, payload)
                last = pokemon_id
            logger.info("Local Pokemon checkpoint id=%s counts=%s", last, dict(self.counts))
            await self.checkpoint()
        async with self.factory() as session:
            rows = (
                await session.execute(select(EvolutionChain.id, EvolutionChain.raw_payload))
            ).all()
            await session.execute(
                update(CatalogReferenceIssue)
                .where(CatalogReferenceIssue.owner_type == "evolution-chain")
                .values(resolved=True)
            )
            for chain_id, payload in rows:
                digest = json_hash(payload)
                state = await session.get(CatalogSyncEntry, ("local-evolution-links", chain_id))
                if state and state.status == "success" and state.normalized_hash == digest:
                    self.counts["unchanged:evolution-links"] += 1
                    continue
                before = len(self.issues)
                if state is None:
                    state = CatalogSyncEntry(
                        resource_type="local-evolution-links",
                        resource_id=chain_id,
                        source_url=f"local:evolution-chain/{chain_id}",
                        status="pending",
                        attempts=0,
                    )
                    session.add(state)
                state.attempts += 1
                state.run_id = self.run_id
                await session.execute(
                    delete(EvolutionItemReference).where(
                        EvolutionItemReference.chain_id == chain_id
                    )
                )
                for path, value in references(payload):
                    ref = reference(value)
                    if (ref and ref[0] == "item") or path.endswith(
                        (".item", ".held_item", ".baby_trigger_item")
                    ):
                        item_id = await self.required(
                            session, "evolution-chain", chain_id, path, value, target="item"
                        )
                        if item_id:
                            session.add(
                                EvolutionItemReference(
                                    chain_id=chain_id,
                                    path=path,
                                    role=path.rsplit(".", 1)[-1],
                                    item_id=item_id,
                                    raw_reference=value,
                                )
                            )
                state.status = "success" if len(self.issues) == before else "partial"
                state.normalized_hash = digest
            await session.commit()

    async def run(
        self,
        *,
        limit: int | None = None,
        refresh: bool = False,
        skip_links: bool = False,
        only: set[tuple[str, int]] | None = None,
        retry_failed: bool = False,
        resume_run: int | None = None,
        stop_after: int | None = None,
        dictionary_only: bool = False,
    ) -> dict[str, Any]:
        self.scope = "evolution-dictionaries" if dictionary_only else "reference-data"
        async with self.factory() as session:
            run = await session.get(SyncRun, resume_run) if resume_run else None
            if run is not None and run.counts.get("scope") != self.scope:
                raise ValueError("Cannot resume an unrelated sync run")
            if resume_run and run is None:
                raise ValueError("Resume run not found")
            if run is None:
                run = SyncRun(status="running", counts={"scope": self.scope})
                session.add(run)
            run.status, run.finished_at = "running", None
            await session.commit()
            self.run_id = run.id
            self.queued = set(
                (
                    await session.execute(
                        select(CatalogSyncEntry.resource_type, CatalogSyncEntry.resource_id)
                    )
                ).all()
            )
        try:
            discovery = {}
            if only:
                async with self.factory() as session:
                    for kind, resource_id in only:
                        await self.enqueue(
                            session,
                            kind,
                            resource_id,
                            f"{self.provider.base_url}/{kind}/{resource_id}/",
                        )
                    await session.commit()
            elif not retry_failed:
                for kind in EVOLUTION_DICTIONARIES if dictionary_only else PRIMARY:
                    discovery[kind] = await self.discover(kind, limit=limit)
            await self.checkpoint(discovery=discovery)
            if not skip_links and not dictionary_only:
                await self.seed_local_dependencies()
            complete = await self.fetch(
                refresh=refresh,
                only=only,
                retry_failed=retry_failed,
                stop_after=stop_after,
                allowed_kinds=(
                    set(EVOLUTION_DICTIONARIES) | {"version-group", "generation"}
                    if dictionary_only
                    else None
                ),
            )
            if not complete:
                status = "interrupted"
            else:
                if dictionary_only:
                    await self.prepare_dictionaries()
                else:
                    await self.normalize()
                    if not skip_links:
                        await self.link_local()
                async with self.factory() as session:
                    states = (await session.scalars(select(CatalogSyncEntry.status))).all()
                    issues = (
                        await session.scalars(
                            select(CatalogReferenceIssue.fingerprint).where(
                                CatalogReferenceIssue.resolved.is_(False)
                            )
                        )
                    ).all()
                status = "partial" if any(s != "success" for s in states) or issues else "success"
            await self.checkpoint()
            async with self.factory() as session:
                run = await session.get(SyncRun, self.run_id)
                assert run is not None
                run.status, run.finished_at = status, utcnow()
                await session.commit()
                return dict(run_id=self.run_id, status=status, counts=run.counts)
        except BaseException as exc:
            async with self.factory() as session:
                run = await session.get(SyncRun, self.run_id)
                assert run is not None
                run.status = (
                    "interrupted"
                    if isinstance(exc, (KeyboardInterrupt, asyncio.CancelledError))
                    else "failed"
                )
                run.error, run.finished_at = f"{type(exc).__name__}: {exc}", utcnow()
                await session.commit()
            raise
