"""Run with python -m pokedex_api.sync.reference_cli (independent of the core sync)."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from pokedex_api.config import get_settings
from pokedex_api.sync.provider import PokeApiProvider
from pokedex_api.sync.reference_data import ALLOWED, ReferenceImporter


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Data-only move/item/berry targeted import")
    result.add_argument("--concurrency", type=int, default=4, choices=range(1, 9))
    result.add_argument("--page-size", type=int, default=100)
    result.add_argument("--limit", type=int, help="Pilot: first N IDs per complete resource list")
    result.add_argument("--skip-links", action="store_true", help="Pilot: skip local Pokemon links")
    result.add_argument("--refresh", action="store_true", help="Refetch cached scoped resources")
    result.add_argument("--retry-failed", action="store_true", help="Retry failed/missing entries")
    result.add_argument("--only", action="append", default=[], metavar="RESOURCE:ID")
    result.add_argument("--resume-run", type=int)
    result.add_argument(
        "--evolution-dictionaries",
        action="store_true",
        help="Only discover and mirror evolution-trigger/evolution-variable",
    )
    result.add_argument(
        "--stop-after-fetch",
        type=int,
        help="Gracefully interrupt after N records for checkpoint verification",
    )
    result.add_argument("--report", type=Path)
    return result


async def run(args: argparse.Namespace) -> dict[str, Any]:
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    only = set()
    for entry in args.only:
        kind, number = entry.rsplit(":", 1)
        if kind not in ALLOWED or not number.removeprefix("-").isdigit():
            raise ValueError(f"Invalid scoped target: {entry}")
        only.add((kind, int(number)))
    try:
        async with engine.connect() as lock:
            if lock.dialect.name == "postgresql":
                acquired = await lock.scalar(text("SELECT pg_try_advisory_lock(20261029, 1)"))
                if not acquired:
                    raise RuntimeError("Another reference-data import is running")
            try:
                async with PokeApiProvider(
                    settings.pokeapi_base_url,
                    settings.pokeapi_user_agent,
                    concurrency=args.concurrency,
                    page_size=args.page_size,
                    timeout=30,
                ) as provider:
                    importer = ReferenceImporter(
                        async_sessionmaker(engine, expire_on_commit=False),
                        provider,
                        concurrency=args.concurrency,
                    )
                    return await importer.run(
                        limit=args.limit,
                        refresh=args.refresh,
                        skip_links=args.skip_links,
                        only=only or None,
                        retry_failed=args.retry_failed,
                        resume_run=args.resume_run,
                        stop_after=args.stop_after_fetch,
                        dictionary_only=args.evolution_dictionaries,
                    )
            finally:
                if lock.dialect.name == "postgresql":
                    await lock.execute(text("SELECT pg_advisory_unlock(20261029, 1)"))
    finally:
        await engine.dispose()


def main(argv: list[str] | None = None) -> None:
    args = parser().parse_args(argv)
    if args.limit is not None and args.limit < 1:
        raise ValueError("--limit must be positive")
    if not 1 <= args.page_size <= 500:
        raise ValueError("--page-size must be 1..500")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    result = asyncio.run(run(args))
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if args.report:
        args.report.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    if result["status"] != "success":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
