"""Persist project explanations and separately verified notes without changing upstream data."""

from __future__ import annotations

import asyncio

from reference_data_db import local_database_url
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from pokedex_api.models import SourceRecord, utcnow
from pokedex_api.services.evolution_conditions import policy
from pokedex_api.sync.importer import json_hash


async def main() -> None:
    engine = create_async_engine(local_database_url())
    factory = async_sessionmaker(engine, expire_on_commit=False)
    records = [("project-evolution-glossary", 1, policy(), policy()["source_url"])]
    records.extend(
        ("evolution-supplement", r["id"], r, r["source_url"])
        for r in policy()["supplements"]
    )
    async with factory() as session:
        for kind, resource_id, payload, url in records:
            record = await session.scalar(
                select(SourceRecord).where(
                    SourceRecord.resource_type == kind,
                    SourceRecord.resource_id == resource_id,
                )
            )
            digest = json_hash(payload)
            if record is not None and record.source_hash == digest:
                continue
            if record is None:
                record = SourceRecord(resource_type=kind, resource_id=resource_id)
                session.add(record)
            record.name = f"{kind}-{resource_id}"
            record.source_url = url
            record.raw_payload, record.source_hash = payload, digest
            record.fetched_at = utcnow()
        await session.commit()
    await engine.dispose()
    print(
        f"Stored {len(records)} separate project/supplement source records; no upstream overwrite."
    )


if __name__ == "__main__":
    asyncio.run(main())
