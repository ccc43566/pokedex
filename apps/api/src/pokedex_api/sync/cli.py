
from __future__ import annotations

import argparse
import asyncio
import json
import logging
from typing import Any

from pokedex_api.config import get_settings
from pokedex_api.db import SessionLocal
from pokedex_api.sync.importer import PokeApiImporter
from pokedex_api.sync.provider import PokeApiProvider

logger = logging.getLogger(__name__)


async def run_sync(
    *,
    force: bool,
    download_media: bool = True,
    media_only: bool = False,
    versions_only: bool = False,
) -> dict[str, Any]:
    settings = get_settings()
    settings.media_root.mkdir(parents=True, exist_ok=True)
    if versions_only:
        from pathlib import Path

        from pokedex_api.sync.version_sprites import mirror_versions

        return await mirror_versions(
            database_url=settings.database_url,
            media_root=Path(settings.media_root),
        )
    async with SessionLocal() as session:
        async with PokeApiProvider(
            settings.pokeapi_base_url,
            settings.pokeapi_user_agent,
            concurrency=settings.sync_concurrency,
            page_size=settings.sync_page_size,
        ) as provider:
            importer = PokeApiImporter(
                session,
                provider,
                media_root=settings.media_root,
                download_media=download_media,
            )
            if media_only:
                result = await importer.run_media_only()
                from pokedex_api.sync.version_sprites import mirror_versions

                result["versionSprites"] = await mirror_versions(
                    database_url=settings.database_url,
                    media_root=settings.media_root,
                )
                return result
            return await importer.run(force=force)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Mirror core PokeAPI resources into PostgreSQL")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Run even if the PokeAPI hash is unchanged",
    )
    media_options = parser.add_mutually_exclusive_group()
    media_options.add_argument(
        "--skip-media",
        action="store_true",
        help="Do not download the curated Pokemon image set",
    )
    media_options.add_argument(
        "--media-only",
        action="store_true",
        help="Only mirror media using raw Pokemon records already stored in PostgreSQL",
    )
    media_options.add_argument(
        "--versions-only",
        action="store_true",
        help="Only mirror sprites.versions from Pokémon and forms already in PostgreSQL",
    )
    parser.add_argument("--log-level", default="INFO")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    result = asyncio.run(
        run_sync(
            force=args.force,
            download_media=not args.skip_media,
            media_only=args.media_only,
            versions_only=args.versions_only,
        )
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
