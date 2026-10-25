
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
from collections.abc import AsyncIterator, Iterable
from io import BytesIO
from pathlib import Path
from typing import Any, TypeVar, cast

from PIL import Image
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from pokedex_api.models import (
    Ability,
    Base,
    EvolutionChain,
    EvolutionNode,
    GenerationEntity,
    LocalizedName,
    LocalizedText,
    MediaAsset,
    PokedexEntity,
    Pokemon,
    PokemonAbility,
    PokemonForm,
    PokemonSpecies,
    PokemonStat,
    PokemonType,
    SourceRecord,
    StatEntity,
    SyncRun,
    TypeEntity,
)
from pokedex_api.sync.provider import SourceProvider
from pokedex_api.sync.version_sprites import mirror_versions

logger = logging.getLogger(__name__)

ModelT = TypeVar("ModelT", bound=Base)
SUPPORTED_LOCALES = {"zh-hans": "zh-Hans", "en": "en"}
CORE_ENDPOINTS = (
    "generation",
    "type",
    "stat",
    "ability",
    "pokedex",
    "pokemon-species",
    "pokemon",
    "pokemon-form",
    "evolution-chain",
)
ASSET_SPECS = (
    ("front-default", ("front_default",)),
    ("front-shiny", ("front_shiny",)),
    ("official-artwork", ("other", "official-artwork", "front_default")),
    ("home", ("other", "home", "front_default")),
)


def resource_id_from_url(url: str) -> int:
    match = re.search(r"/(\d+)/?$", url)
    if match is None:
        raise ValueError(f"Cannot extract a resource id from {url!r}")
    return int(match.group(1))


def normalize_locale(language: str) -> str | None:
    return SUPPORTED_LOCALES.get(language.lower().replace("_", "-"))


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("\f", " ")).strip()


def json_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def nested_value(payload: dict[str, Any], path: Iterable[str]) -> Any:
    current: Any = payload
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def localized_names(payload: dict[str, Any]) -> list[tuple[str, str]]:
    result: list[tuple[str, str]] = []
    for entry in payload.get("names", []):
        locale = normalize_locale(entry.get("language", {}).get("name", ""))
        name = entry.get("name")
        if locale and name:
            result.append((locale, str(name)))
    return result


def localized_entries(
    payload: dict[str, Any],
    key: str,
    *,
    text_field: str = "text",
    version_field: str | None = None,
) -> list[tuple[str, str | None, str]]:
    result: list[tuple[str, str | None, str]] = []
    for entry in payload.get(key, []):
        locale = normalize_locale(entry.get("language", {}).get("name", ""))
        value = entry.get(text_field)
        if not locale or not value:
            continue
        version = None
        if version_field and entry.get(version_field):
            version = entry[version_field].get("name")
        result.append((locale, version, clean_text(str(value))))
    return result


class PokeApiImporter:
    def __init__(
        self,
        session: AsyncSession,
        provider: SourceProvider,
        *,
        media_root: Path,
        download_media: bool = True,
    ) -> None:
        self.session = session
        self.provider = provider
        self.media_root = media_root
        self.download_media = download_media
        self.counts: dict[str, Any] = {}

    async def run(self, *, force: bool = False) -> dict[str, Any]:
        meta = await self.provider.get_meta()
        source_hash = str(meta.get("hash") or json_hash(meta))
        previous = await self.session.scalar(
            select(SyncRun)
            .where(SyncRun.status == "success", SyncRun.source_hash == source_hash)
            .order_by(SyncRun.finished_at.desc())
            .limit(1)
        )
        if previous is not None and not force:
            return {
                "status": "unchanged",
                "sourceHash": source_hash,
                "message": "PokeAPI deployment hash is unchanged",
            }

        sync_run = SyncRun(status="running", source_hash=source_hash)
        self.session.add(sync_run)
        await self.session.commit()
        sync_run_id = sync_run.id

        try:
            payloads = await self._fetch_core(payloads_only=False)
            await self._transform(payloads)
            if self.download_media:
                self.counts["media"] = await self._mirror_media(
                    payloads["pokemon"], payloads["pokemon-form"]
                )
                self.counts["versionSprites"] = await self._mirror_versions()
            sync_run.status = "success"
            sync_run.counts = self.counts
            from datetime import UTC, datetime

            sync_run.finished_at = datetime.now(UTC)
            await self.session.commit()
            return {
                "status": "success",
                "sourceHash": source_hash,
                "counts": self.counts,
            }
        except Exception as exc:
            await self.session.rollback()
            from datetime import UTC, datetime

            failed_run = await self.session.get(SyncRun, sync_run_id)
            if failed_run is not None:
                failed_run.status = "failed"
                failed_run.error = str(exc)
                failed_run.finished_at = datetime.now(UTC)
                await self.session.commit()
            raise

    async def run_media_only(self) -> dict[str, Any]:
        self.media_root.mkdir(parents=True, exist_ok=True)
        total = 0
        for owner_type, resource_type in (
            ("pokemon", "pokemon"),
            ("pokemon-form", "pokemon-form"),
        ):
            async for batch in self._source_payload_batches(resource_type, 30):
                total += await self._mirror_asset_payloads(batch, owner_type=owner_type)
        return {"status": "success", "media": total}

    async def _mirror_versions(self) -> dict[str, Any]:
        from pokedex_api.config import get_settings

        return await mirror_versions(
            database_url=get_settings().database_url,
            media_root=self.media_root,
        )

    async def _source_payload_batches(
        self,
        resource_type: str,
        batch_size: int,
    ) -> AsyncIterator[list[dict[str, Any]]]:
        offset = 0
        while True:
            payloads = list(
                (
                    await self.session.scalars(
                        select(SourceRecord.raw_payload)
                        .where(SourceRecord.resource_type == resource_type)
                        .order_by(SourceRecord.resource_id)
                        .offset(offset)
                        .limit(batch_size)
                    )
                ).all()
            )
            if not payloads:
                return
            yield payloads
            offset += len(payloads)

    async def _fetch_core(self, *, payloads_only: bool) -> dict[str, list[dict[str, Any]]]:
        payloads: dict[str, list[dict[str, Any]]] = {}
        for endpoint in CORE_ENDPOINTS:
            records: list[dict[str, Any]] = []
            summaries = await self.provider.list_resources(endpoint)
            self.counts[f"listed_{endpoint}"] = len(summaries)
            for index in range(0, len(summaries), 40):
                batch = summaries[index : index + 40]
                resources = await asyncio.gather(
                    *(self.provider.get_resource(item["url"]) for item in batch)
                )
                for summary, payload in zip(batch, resources, strict=True):
                    records.append(payload)
                    if not payloads_only:
                        await self._store_source(endpoint, summary, payload)
                await self.session.commit()
            payloads[endpoint] = records
            logger.info("Fetched %s %s records", len(records), endpoint)
        return payloads

    async def _store_source(
        self,
        resource_type: str,
        summary: dict[str, Any],
        payload: dict[str, Any],
    ) -> None:
        resource_id = resource_id_from_url(summary["url"])
        existing = await self.session.scalar(
            select(SourceRecord).where(
                SourceRecord.resource_type == resource_type,
                SourceRecord.resource_id == resource_id,
            )
        )
        values = {
            "name": summary.get("name") or payload.get("name"),
            "source_url": summary["url"],
            "source_hash": json_hash(payload),
            "raw_payload": payload,
        }
        if existing is None:
            self.session.add(
                SourceRecord(resource_type=resource_type, resource_id=resource_id, **values)
            )
        else:
            for key, value in values.items():
                setattr(existing, key, value)

    async def _transform(self, payloads: dict[str, list[dict[str, Any]]]) -> None:
        await self._import_generations(payloads["generation"])
        await self._import_types(payloads["type"])
        await self._import_stats(payloads["stat"])
        await self._import_abilities(payloads["ability"])
        await self._import_pokedexes(payloads["pokedex"])
        await self._import_species(payloads["pokemon-species"])
        await self._import_pokemon(payloads["pokemon"])
        await self._import_forms(payloads["pokemon-form"])
        await self._import_evolution_chains(payloads["evolution-chain"])

    async def _upsert_by_id(
        self,
        model: type[ModelT],
        object_id: int,
        **values: Any,
    ) -> ModelT:
        instance = await self.session.get(model, object_id)
        if instance is None:
            instance = cast(Any, model)(id=object_id, **values)
            self.session.add(instance)
        else:
            for key, value in values.items():
                setattr(instance, key, value)
        await self.session.flush()
        return cast(ModelT, instance)

    async def _replace_names(
        self,
        entity_type: str,
        entity_id: int,
        names: list[tuple[str, str]],
    ) -> None:
        await self.session.execute(
            delete(LocalizedName).where(
                LocalizedName.entity_type == entity_type,
                LocalizedName.entity_id == entity_id,
            )
        )
        self.session.add_all(
            LocalizedName(
                entity_type=entity_type,
                entity_id=entity_id,
                locale=locale,
                name=name,
                is_canonical=locale == "en",
            )
            for locale, name in names
        )

    async def _replace_texts(
        self,
        entity_type: str,
        entity_id: int,
        entries: list[tuple[str, str, str | None, str]],
    ) -> None:
        await self.session.execute(
            delete(LocalizedText).where(
                LocalizedText.entity_type == entity_type,
                LocalizedText.entity_id == entity_id,
            )
        )
        self.session.add_all(
            LocalizedText(
                entity_type=entity_type,
                entity_id=entity_id,
                locale=locale,
                text_kind=text_kind,
                version=version,
                text=text,
            )
            for locale, text_kind, version, text in entries
        )

    async def _import_generations(self, payloads: list[dict[str, Any]]) -> None:
        for payload in payloads:
            generation_id = int(payload["id"])
            await self._upsert_by_id(
                GenerationEntity,
                generation_id,
                name=payload["name"],
                main_region=(payload.get("main_region") or {}).get("name"),
                raw_payload=payload,
            )
            await self._replace_names("generation", generation_id, localized_names(payload))
        await self.session.commit()

    async def _import_types(self, payloads: list[dict[str, Any]]) -> None:
        for payload in payloads:
            type_id = int(payload["id"])
            await self._upsert_by_id(
                TypeEntity,
                type_id,
                name=payload["name"],
                damage_relations=payload.get("damage_relations") or {},
                past_damage_relations=payload.get("past_damage_relations") or [],
                raw_payload=payload,
            )
            await self._replace_names("type", type_id, localized_names(payload))
        await self.session.commit()

    async def _import_stats(self, payloads: list[dict[str, Any]]) -> None:
        for payload in payloads:
            stat_id = int(payload["id"])
            await self._upsert_by_id(
                StatEntity,
                stat_id,
                name=payload["name"],
                is_battle_only=bool(payload.get("is_battle_only")),
                raw_payload=payload,
            )
            await self._replace_names("stat", stat_id, localized_names(payload))
        await self.session.commit()

    async def _import_abilities(self, payloads: list[dict[str, Any]]) -> None:
        for payload in payloads:
            ability_id = int(payload["id"])
            generation_id = (
                resource_id_from_url(payload["generation"]["url"])
                if payload.get("generation")
                else None
            )
            await self._upsert_by_id(
                Ability,
                ability_id,
                name=payload["name"],
                generation_id=generation_id,
                is_main_series=bool(payload.get("is_main_series", True)),
                effect_entries=payload.get("effect_entries") or [],
                flavor_text_entries=payload.get("flavor_text_entries") or [],
                raw_payload=payload,
            )
            await self._replace_names("ability", ability_id, localized_names(payload))
        await self.session.commit()

    async def _import_pokedexes(self, payloads: list[dict[str, Any]]) -> None:
        for payload in payloads:
            pokedex_id = int(payload["id"])
            await self._upsert_by_id(
                PokedexEntity,
                pokedex_id,
                name=payload["name"],
                is_main_series=bool(payload.get("is_main_series")),
                region_name=(payload.get("region") or {}).get("name"),
                raw_payload=payload,
            )
            await self._replace_names("pokedex", pokedex_id, localized_names(payload))
        await self.session.commit()

    async def _import_species(self, payloads: list[dict[str, Any]]) -> None:
        for payload in payloads:
            species_id = int(payload["id"])
            generation_id = (
                resource_id_from_url(payload["generation"]["url"])
                if payload.get("generation")
                else None
            )
            evolution_chain_id = (
                resource_id_from_url(payload["evolution_chain"]["url"])
                if payload.get("evolution_chain")
                else None
            )
            await self._upsert_by_id(
                PokemonSpecies,
                species_id,
                name=payload["name"],
                generation_id=generation_id,
                evolution_chain_id=evolution_chain_id,
                color=(payload.get("color") or {}).get("name"),
                habitat=(payload.get("habitat") or {}).get("name"),
                shape=(payload.get("shape") or {}).get("name"),
                capture_rate=payload.get("capture_rate"),
                base_happiness=payload.get("base_happiness"),
                hatch_counter=payload.get("hatch_counter"),
                gender_rate=payload.get("gender_rate"),
                is_baby=bool(payload.get("is_baby")),
                is_legendary=bool(payload.get("is_legendary")),
                is_mythical=bool(payload.get("is_mythical")),
                raw_payload=payload,
            )
            await self._replace_names("pokemon-species", species_id, localized_names(payload))
            text_entries: list[tuple[str, str, str | None, str]] = [
                (locale, "flavor_text", version, text)
                for locale, version, text in localized_entries(
                    payload,
                    "flavor_text_entries",
                    text_field="flavor_text",
                    version_field="version",
                )
            ]
            text_entries.extend(
                (locale, "genus", None, text)
                for locale, _version, text in localized_entries(
                    payload, "genera", text_field="genus"
                )
            )
            await self._replace_texts("pokemon-species", species_id, text_entries)
        await self.session.commit()

    async def _named_id_map(self, model: type[ModelT]) -> dict[str, int]:
        rows = (await self.session.scalars(select(model))).all()
        return {
            str(cast(Any, row).name): int(cast(Any, row).id)
            for row in rows
            if hasattr(row, "name")
        }

    async def _import_pokemon(self, payloads: list[dict[str, Any]]) -> None:
        type_ids = await self._named_id_map(TypeEntity)
        ability_ids = await self._named_id_map(Ability)
        stat_ids = await self._named_id_map(StatEntity)
        for payload in payloads:
            pokemon_id = int(payload["id"])
            species_id = (
                resource_id_from_url(payload["species"]["url"])
                if payload.get("species")
                else None
            )
            await self._upsert_by_id(
                Pokemon,
                pokemon_id,
                name=payload["name"],
                species_id=species_id,
                height=payload.get("height"),
                weight=payload.get("weight"),
                base_experience=payload.get("base_experience"),
                order=payload.get("order"),
                is_default=bool(payload.get("is_default", True)),
                sprites=payload.get("sprites") or {},
                raw_payload=payload,
            )
            await self.session.execute(
                delete(PokemonType).where(PokemonType.pokemon_id == pokemon_id)
            )
            await self.session.execute(
                delete(PokemonAbility).where(PokemonAbility.pokemon_id == pokemon_id)
            )
            await self.session.execute(
                delete(PokemonStat).where(PokemonStat.pokemon_id == pokemon_id)
            )
            self.session.add_all(
                PokemonType(
                    pokemon_id=pokemon_id,
                    type_id=type_ids[entry["type"]["name"]],
                    slot=int(entry["slot"]),
                )
                for entry in payload.get("types", [])
                if entry["type"]["name"] in type_ids
            )
            self.session.add_all(
                PokemonAbility(
                    pokemon_id=pokemon_id,
                    ability_id=ability_ids[entry["ability"]["name"]],
                    slot=int(entry["slot"]),
                    is_hidden=bool(entry.get("is_hidden")),
                )
                for entry in payload.get("abilities", [])
                if entry["ability"]["name"] in ability_ids
            )
            self.session.add_all(
                PokemonStat(
                    pokemon_id=pokemon_id,
                    stat_id=stat_ids[entry["stat"]["name"]],
                    base_stat=int(entry["base_stat"]),
                    effort=int(entry.get("effort", 0)),
                )
                for entry in payload.get("stats", [])
                if entry["stat"]["name"] in stat_ids
            )
            if pokemon_id % 100 == 0:
                await self.session.flush()
        await self.session.commit()
        self.counts["pokemon"] = len(payloads)

    async def _import_forms(self, payloads: list[dict[str, Any]]) -> None:
        for payload in payloads:
            form_id = int(payload["id"])
            pokemon_id = (
                resource_id_from_url(payload["pokemon"]["url"]) if payload.get("pokemon") else None
            )
            version_group = (payload.get("version_group") or {}).get("name")
            await self._upsert_by_id(
                PokemonForm,
                form_id,
                name=payload["name"],
                pokemon_id=pokemon_id,
                form_name=payload.get("form_name"),
                is_default=bool(payload.get("is_default")),
                is_battle_only=bool(payload.get("is_battle_only")),
                is_mega=bool(payload.get("is_mega")),
                version_group=version_group,
                sprites=payload.get("sprites") or {},
                raw_payload=payload,
            )
            await self._replace_names("pokemon-form", form_id, localized_names(payload))
        await self.session.commit()
        self.counts["pokemon_form"] = len(payloads)

    async def _import_evolution_chains(self, payloads: list[dict[str, Any]]) -> None:
        for payload in payloads:
            chain_id = int(payload["id"])
            await self._upsert_by_id(
                EvolutionChain,
                chain_id,
                baby_trigger_item=(payload.get("baby_trigger_item") or {}).get("name"),
                raw_payload=payload,
            )
            await self.session.execute(
                delete(EvolutionNode).where(EvolutionNode.chain_id == chain_id)
            )
            await self.session.flush()

            async def walk(
                node: dict[str, Any],
                parent_id: int | None,
                stage: int,
                sort_order: int,
                bound_chain_id: int = chain_id,
            ) -> None:
                species_id = resource_id_from_url(node["species"]["url"])
                details = node.get("evolution_details") or [{}]
                condition = details[0] if details else {}
                evolution_node = EvolutionNode(
                    chain_id=bound_chain_id,
                    species_id=species_id,
                    parent_id=parent_id,
                    stage=stage,
                    sort_order=sort_order,
                    is_baby=bool(node.get("is_baby")),
                    condition=condition,
                )
                self.session.add(evolution_node)
                await self.session.flush()
                for child_order, child in enumerate(node.get("evolves_to", [])):
                    await walk(child, evolution_node.id, stage + 1, child_order)

            await walk(payload["chain"], None, 0, 0)
        await self.session.commit()
        self.counts["evolution_chain"] = len(payloads)

    async def _mirror_media(
        self,
        pokemon_payloads: list[dict[str, Any]],
        form_payloads: list[dict[str, Any]],
    ) -> int:
        self.media_root.mkdir(parents=True, exist_ok=True)
        count = 0
        count += await self._mirror_asset_payloads(
            pokemon_payloads,
            owner_type="pokemon",
        )
        count += await self._mirror_asset_payloads(
            form_payloads,
            owner_type="pokemon-form",
        )
        return count

    async def _mirror_asset_payloads(
        self,
        payloads: list[dict[str, Any]],
        *,
        owner_type: str,
    ) -> int:
        count = 0
        for index in range(0, len(payloads), 30):
            batch = payloads[index : index + 30]
            jobs = []
            for payload in batch:
                sprites = payload.get("sprites") or {}
                for kind, path in ASSET_SPECS:
                    source_url = nested_value(sprites, path)
                    if source_url:
                        jobs.append((payload, kind, str(source_url)))
            if not jobs:
                continue
            pending: list[int] = []
            pending_urls: list[str] = []
            local_paths: dict[int, Path] = {}
            skipped: set[int] = set()
            for job_index, (payload, kind, source_url) in enumerate(jobs):
                owner_id = int(payload["id"])
                existing = await self._find_media_asset(owner_id, owner_type, kind)
                if (
                    existing is not None
                    and existing.local_path
                    and existing.source_url == source_url
                    and (self.media_root / existing.local_path).is_file()
                ):
                    skipped.add(job_index)
                    continue
                local_path = self._existing_asset_path(
                    owner_id,
                    owner_type,
                    kind,
                    source_url,
                )
                if local_path is not None:
                    local_paths[job_index] = local_path
                else:
                    pending.append(job_index)
                    pending_urls.append(source_url)

            results = await asyncio.gather(
                *(self._download_asset(url) for url in pending_urls),
                return_exceptions=True,
            )
            downloads = dict(zip(pending, results, strict=True))
            for job_index, (payload, kind, source_url) in enumerate(jobs):
                if job_index in skipped:
                    continue
                local_path = local_paths.get(job_index)
                if local_path is not None:
                    data = await asyncio.to_thread(local_path.read_bytes)
                    content_type: str | None = (
                        "image/jpeg"
                        if local_path.suffix.lower() in {".jpg", ".jpeg"}
                        else "image/png"
                    )
                else:
                    result = downloads.get(job_index)
                    if isinstance(result, BaseException) or result is None:
                        logger.warning("Could not download %s: %s", source_url, result)
                        continue
                    data, content_type = result
                if await self._store_media(
                    payload,
                    owner_type=owner_type,
                    kind=kind,
                    source_url=source_url,
                    data=data,
                    content_type=content_type,
                    local_file=local_path,
                ):
                    count += 1
            await self.session.commit()
        return count

    async def _download_asset(self, url: str) -> tuple[bytes, str | None]:
        return await self.provider.download(url)

    async def _find_media_asset(
        self,
        owner_id: int,
        owner_type: str,
        kind: str,
    ) -> MediaAsset | None:
        filters = [MediaAsset.kind == kind]
        if owner_type == "pokemon":
            filters.append(MediaAsset.pokemon_id == owner_id)
            filters.append(MediaAsset.form_id.is_(None))
        else:
            filters.append(MediaAsset.form_id == owner_id)
        return await self.session.scalar(select(MediaAsset).where(*filters))

    def _existing_asset_path(
        self,
        owner_id: int,
        owner_type: str,
        kind: str,
        source_url: str,
    ) -> Path | None:
        extensions = (
            (".jpg", ".png")
            if source_url.lower().endswith((".jpg", ".jpeg"))
            else (".png", ".jpg")
        )
        for extension in extensions:
            path = self.media_root / owner_type / str(owner_id) / f"{kind}{extension}"
            if path.is_file():
                return path
        return None

    async def _store_media(
        self,
        payload: dict[str, Any],
        *,
        owner_type: str,
        kind: str,
        source_url: str,
        data: bytes,
        content_type: str | None,
        local_file: Path | None = None,
    ) -> bool:
        owner_id = int(payload["id"])
        existing = await self._find_media_asset(owner_id, owner_type, kind)
        checksum = hashlib.sha256(data).hexdigest()
        if existing and existing.checksum == checksum and existing.local_path:
            return False
        if local_file is not None:
            relative = local_file.relative_to(self.media_root)
        else:
            extension = ".png"
            if content_type and "jpeg" in content_type:
                extension = ".jpg"
            elif ".jpg" in source_url.lower() or ".jpeg" in source_url.lower():
                extension = ".jpg"
            relative = Path(owner_type) / str(owner_id) / f"{kind}{extension}"
            file_path = self.media_root / relative
            await asyncio.to_thread(file_path.parent.mkdir, parents=True, exist_ok=True)
            await asyncio.to_thread(file_path.write_bytes, data)
        width, height = self._image_dimensions(data)
        values = {
            "kind": kind,
            "source_url": source_url,
            "local_path": relative.as_posix(),
            "checksum": checksum,
            "width": width,
            "height": height,
        }
        if existing is None:
            self.session.add(
                MediaAsset(
                    pokemon_id=owner_id if owner_type == "pokemon" else None,
                    form_id=owner_id if owner_type == "pokemon-form" else None,
                    **values,
                )
            )
        else:
            for key, value in values.items():
                setattr(existing, key, value)
        await self.session.flush()
        return True

    @staticmethod
    def _image_dimensions(data: bytes) -> tuple[int | None, int | None]:
        try:
            with Image.open(BytesIO(data)) as image:
                return image.width, image.height
        except Exception:
            return None, None


async def iter_batches(
    items: list[dict[str, Any]], size: int
) -> AsyncIterator[list[dict[str, Any]]]:
    for index in range(0, len(items), size):
        yield items[index : index + size]
