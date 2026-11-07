"""Controlled failure injection against one existing record, followed by real remote retry."""

from __future__ import annotations

import asyncio
import json

import httpx
from reference_data_db import ROOT, local_database_url
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from pokedex_api.models import SourceRecord
from pokedex_api.reference_models import CatalogSyncEntry, Move
from pokedex_api.sync.provider import PokeApiProvider
from pokedex_api.sync.reference_data import ReferenceImporter


class ControlledFailureProvider(PokeApiProvider):
    async def get_resource(self, url: str) -> dict[str, object]:
        raise httpx.ReadTimeout("Controlled checkpoint/retry verification; no remote request sent")


async def main() -> None:
    engine = create_async_engine(local_database_url())
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with engine.connect() as lock:
            from sqlalchemy import text

            if not await lock.scalar(text("SELECT pg_try_advisory_lock(20261029, 1)")):
                raise RuntimeError("Wait for the main importer to finish")
            try:
                async with factory() as session:
                    before = await session.scalar(
                        select(SourceRecord.source_hash).where(
                            SourceRecord.resource_type == "move", SourceRecord.resource_id == 1
                        )
                    )
                async with ControlledFailureProvider(
                    "https://pokeapi.co/api/v2", "pokedex-local/0.1"
                ) as p:
                    failed = await ReferenceImporter(factory, p).run(
                        only={("move", 1)}, refresh=True, skip_links=True
                    )
                async with factory() as session:
                    state = await session.get(CatalogSyncEntry, ("move", 1))
                    after = await session.scalar(
                        select(SourceRecord.source_hash).where(
                            SourceRecord.resource_type == "move", SourceRecord.resource_id == 1
                        )
                    )
                    retained = await session.get(Move, 1)
                    assert state and state.status == "failed" and retained and before == after
                async with PokeApiProvider("https://pokeapi.co/api/v2", "pokedex-local/0.1") as p:
                    recovered = await ReferenceImporter(factory, p).run(
                        only={("move", 1)}, retry_failed=True, skip_links=True
                    )
                assert recovered["status"] == "success"
                output = ROOT.parent / "migration-audit/reference-data-retry-verification.json"
                output.write_text(
                    json.dumps(
                        dict(
                            injection="Controlled httpx.ReadTimeout before remote request",
                            failed_run=failed["run_id"],
                            failed_status=failed["status"],
                            original_source_and_move_retained=True,
                            real_remote_retry=True,
                            recovered_run=recovered["run_id"],
                            recovered_status=recovered["status"],
                        ),
                        ensure_ascii=False,
                        indent=2,
                    ),
                    encoding="utf-8",
                )
                print(output.read_text())
            finally:
                await lock.execute(text("SELECT pg_advisory_unlock(20261029, 1)"))
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
