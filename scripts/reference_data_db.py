"""Local database maintenance for the reference-data import; never prints credentials."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine

from pokedex_api.config import Settings

ROOT = Path(__file__).resolve().parents[1]


def local_database_url() -> str:
    settings = Settings(_env_file=ROOT / ".env")  # type: ignore[call-arg]
    url = make_url(settings.database_url)
    if url.host == "db":
        url = url.set(host="127.0.0.1", port=15432)
    return url.render_as_string(hide_password=False)


async def snapshot(output: Path) -> None:
    engine = create_async_engine(local_database_url())
    result: dict[str, object] = {}
    async with engine.connect() as connection:
        tables = (
            (
                await connection.execute(
                    text(
                        "SELECT tablename FROM pg_tables "
                        "WHERE schemaname='public' ORDER BY tablename"
                    )
                )
            )
            .scalars()
            .all()
        )
        for table in tables:
            row = (
                (
                    await connection.execute(
                        text(
                            "SELECT count(*) AS count, "
                            "md5(string_agg(h, '' ORDER BY h)) AS digest "
                            f'FROM (SELECT md5(to_jsonb(t)::text) h FROM "{table}" t) s'
                        )
                    )
                )
                .mappings()
                .one()
            )
            result[table] = dict(row)
        result["sources"] = [
            dict(r)
            for r in (
                await connection.execute(
                    text("SELECT resource_type, count(*) FROM source_record GROUP BY 1 ORDER BY 1")
                )
            ).mappings()
        ]
        result["pokemon_raw"] = dict(
            (
                await connection.execute(
                    text("""
            SELECT count(*) records,
              count(*) FILTER (WHERE raw_payload ? 'moves') with_moves,
              count(*) FILTER (WHERE raw_payload ? 'held_items') with_held_items,
              sum(jsonb_array_length(coalesce(raw_payload->'moves','[]'))) move_entries,
              sum(jsonb_array_length(coalesce(raw_payload->'held_items','[]'))) held_entries
            FROM pokemon
        """)
                )
            )
            .mappings()
            .one()
        )
        result["revision"] = (
            await connection.execute(text("SELECT version_num FROM alembic_version"))
        ).scalar()
    await engine.dispose()
    await asyncio.to_thread(
        output.write_text, json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["snapshot", "upgrade", "sync"])
    parser.add_argument("--output", type=Path)
    args, rest = parser.parse_known_args()
    os.environ["DATABASE_URL"] = local_database_url()
    if args.action == "snapshot":
        if not args.output:
            parser.error("snapshot requires --output")
        asyncio.run(snapshot(args.output))
    elif args.action == "upgrade":
        from alembic import command
        from alembic.config import Config

        config = Config(str(ROOT / "apps/api/alembic.ini"))
        config.set_main_option("script_location", str(ROOT / "apps/api/alembic"))
        command.upgrade(config, "0006_item_media")
    else:
        from pokedex_api.sync.reference_cli import main as sync_main

        sync_main(rest)


if __name__ == "__main__":
    main()
