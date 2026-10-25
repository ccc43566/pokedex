
from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pokedex_api.models import MediaAsset, SourceRecord
from pokedex_api.services.pokemon import get_pokemon
from pokedex_api.sync.importer import PokeApiImporter


class FakeProvider:
    def __init__(self) -> None:
        base = "https://example.test/api/v2"
        self.payloads: dict[str, dict[str, Any]] = {
            f"{base}/generation/1/": {
                "id": 1,
                "name": "generation-i",
                "main_region": {"name": "kanto"},
                "names": [{"name": "Generation I", "language": {"name": "en"}}],
            },
            f"{base}/type/1/": {
                "id": 1,
                "name": "grass",
                "damage_relations": {"double_damage_to": []},
                "past_damage_relations": [],
                "names": [{"name": "Grass", "language": {"name": "en"}}],
            },
            f"{base}/stat/1/": {
                "id": 1,
                "name": "hp",
                "is_battle_only": False,
                "names": [{"name": "HP", "language": {"name": "en"}}],
            },
            f"{base}/ability/1/": {
                "id": 1,
                "name": "overgrow",
                "generation": {"name": "generation-i", "url": f"{base}/generation/1/"},
                "is_main_series": True,
                "effect_entries": [
                    {
                        "effect": "Powers up Grass moves.",
                        "short_effect": "Powers up Grass moves.",
                        "language": {"name": "en"},
                    }
                ],
                "flavor_text_entries": [],
                "names": [{"name": "Overgrow", "language": {"name": "en"}}],
            },
            f"{base}/pokedex/1/": {
                "id": 1,
                "name": "kanto",
                "is_main_series": True,
                "region": {"name": "kanto"},
                "names": [{"name": "Kanto", "language": {"name": "en"}}],
            },
            f"{base}/pokemon-species/1/": {
                "id": 1,
                "name": "bulbasaur",
                "generation": {"name": "generation-i", "url": f"{base}/generation/1/"},
                "evolution_chain": {"url": f"{base}/evolution-chain/1/"},
                "color": {"name": "green"},
                "habitat": {"name": "grassland"},
                "shape": {"name": "quadruped"},
                "capture_rate": 45,
                "base_happiness": 50,
                "hatch_counter": 20,
                "gender_rate": 1,
                "is_baby": False,
                "is_legendary": False,
                "is_mythical": False,
                "names": [
                    {"name": "Bulbasaur", "language": {"name": "en"}},
                    {"name": "妙蛙种子", "language": {"name": "zh-Hans"}},
                ],
                "flavor_text_entries": [
                    {
                        "flavor_text": "A strange seed was planted on its back.",
                        "language": {"name": "en"},
                        "version": {"name": "red"},
                    }
                ],
                "genera": [{"genus": "Seed Pokemon", "language": {"name": "en"}}],
            },
            f"{base}/pokemon-species/2/": {
                "id": 2,
                "name": "ivysaur",
                "generation": {"name": "generation-i", "url": f"{base}/generation/1/"},
                "evolution_chain": {"url": f"{base}/evolution-chain/1/"},
                "names": [{"name": "Ivysaur", "language": {"name": "en"}}],
                "flavor_text_entries": [],
                "genera": [],
            },
            f"{base}/pokemon/1/": {
                "id": 1,
                "name": "bulbasaur",
                "species": {"name": "bulbasaur", "url": f"{base}/pokemon-species/1/"},
                "height": 7,
                "weight": 69,
                "base_experience": 64,
                "order": 1,
                "is_default": True,
                "types": [{"slot": 1, "type": {"name": "grass"}}],
                "abilities": [{"slot": 1, "is_hidden": False, "ability": {"name": "overgrow"}}],
                "stats": [{"base_stat": 45, "effort": 0, "stat": {"name": "hp"}}],
                "sprites": {"front_default": "https://example.test/1.png", "other": {}},
            },
            f"{base}/pokemon/2/": {
                "id": 2,
                "name": "ivysaur",
                "species": {"name": "ivysaur", "url": f"{base}/pokemon-species/2/"},
                "height": 10,
                "weight": 130,
                "base_experience": 142,
                "order": 2,
                "is_default": True,
                "types": [{"slot": 1, "type": {"name": "grass"}}],
                "abilities": [{"slot": 1, "is_hidden": False, "ability": {"name": "overgrow"}}],
                "stats": [{"base_stat": 60, "effort": 0, "stat": {"name": "hp"}}],
                "sprites": {"front_default": "https://example.test/2.png", "other": {}},
            },
            f"{base}/pokemon-form/1/": {
                "id": 1,
                "name": "bulbasaur",
                "pokemon": {"name": "bulbasaur", "url": f"{base}/pokemon/1/"},
                "form_name": "",
                "is_default": True,
                "is_battle_only": False,
                "is_mega": False,
                "version_group": {"name": "red-blue"},
                "sprites": {"front_default": "https://example.test/form-1.png"},
                "names": [{"name": "Bulbasaur", "language": {"name": "en"}}],
            },
            f"{base}/evolution-chain/1/": {
                "id": 1,
                "baby_trigger_item": None,
                "chain": {
                    "species": {"name": "bulbasaur", "url": f"{base}/pokemon-species/1/"},
                    "is_baby": False,
                    "evolution_details": [],
                    "evolves_to": [
                        {
                            "species": {"name": "ivysaur", "url": f"{base}/pokemon-species/2/"},
                            "is_baby": False,
                            "evolution_details": [
                                {"min_level": 16, "trigger": {"name": "level-up"}}
                            ],
                            "evolves_to": [],
                        }
                    ],
                },
            },
        }
        self.lists = {
            "generation": [f"{base}/generation/1/"],
            "type": [f"{base}/type/1/"],
            "stat": [f"{base}/stat/1/"],
            "ability": [f"{base}/ability/1/"],
            "pokedex": [f"{base}/pokedex/1/"],
            "pokemon-species": [f"{base}/pokemon-species/1/", f"{base}/pokemon-species/2/"],
            "pokemon": [f"{base}/pokemon/1/", f"{base}/pokemon/2/"],
            "pokemon-form": [f"{base}/pokemon-form/1/"],
            "evolution-chain": [f"{base}/evolution-chain/1/"],
        }

    async def get_meta(self) -> dict[str, Any]:
        return {"hash": "test-hash", "tag": None}

    async def list_resources(self, endpoint: str) -> list[dict[str, Any]]:
        return [
            {"name": self.payloads[url].get("name"), "url": url}
            for url in self.lists[endpoint]
        ]

    async def get_resource(self, url: str) -> dict[str, Any]:
        return self.payloads[url]

    async def download(self, url: str) -> tuple[bytes, str | None]:
        raise AssertionError("media download should be disabled in this test")


async def test_importer_first_run_and_idempotency(
    session: AsyncSession,
    tmp_path: Path,
) -> None:
    provider = FakeProvider()
    importer = PokeApiImporter(
        session,
        provider,
        media_root=tmp_path,
        download_media=False,
    )

    first = await importer.run(force=False)
    assert first["status"] == "success"
    assert first["counts"]["pokemon"] == 2

    detail = await get_pokemon(session, "1", locale="zh-Hans")
    assert detail is not None
    assert detail.localized_name == "妙蛙种子"
    assert detail.types[0].name == "grass"
    assert detail.stats[0].base_stat == 45
    assert detail.evolution_chain[0].children[0].name == "ivysaur"

    second = await importer.run(force=False)
    assert second["status"] == "unchanged"


async def test_media_only_registers_existing_files_without_download(
    session: AsyncSession,
    tmp_path: Path,
) -> None:
    png = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk"
        "+A8AAQUBAScY42YAAAAASUVORK5CYII="
    )
    media_root = tmp_path / "media"
    asset_path = media_root / "pokemon" / "1" / "front-default.png"
    asset_path.parent.mkdir(parents=True)
    asset_path.write_bytes(png)
    session.add(
        SourceRecord(
            resource_type="pokemon",
            resource_id=1,
            name="bulbasaur",
            source_url="https://example.test/api/v2/pokemon/1/",
            source_hash="source-hash",
            raw_payload={
                "id": 1,
                "name": "bulbasaur",
                "sprites": {
                    "front_default": "https://example.test/1.png",
                    "other": {},
                },
            },
        )
    )
    await session.commit()

    importer = PokeApiImporter(
        session,
        FakeProvider(),
        media_root=media_root,
        download_media=False,
    )
    result = await importer.run_media_only()

    assert result == {"status": "success", "media": 1}
    asset = await session.scalar(select(MediaAsset))
    assert asset is not None
    assert asset.local_path == "pokemon/1/front-default.png"
    assert asset.source_url == "https://example.test/1.png"
    assert asset.width == 1
    assert asset.height == 1
