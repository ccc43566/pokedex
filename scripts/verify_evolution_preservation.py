"""Check original rows remain identical after additive dictionaries/explanations."""

from __future__ import annotations

import asyncio
import json

from reference_data_db import ROOT, local_database_url
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


async def main() -> None:
    audit = ROOT.parent / "migration-audit"
    before = json.loads((audit / "evolution-conditions-before.json").read_text(encoding="utf-8"))
    after = json.loads((audit / "evolution-conditions-after.json").read_text(encoding="utf-8"))
    changed = {
        "source_record",
        "sync_run",
        "localized_name",
        "localized_text",
        "catalog_dictionary",
        "catalog_dictionary_link",
        "catalog_sync_entry",
        "catalog_discovery_page",
    }
    checks = []
    for table, value in before.items():
        if isinstance(value, dict) and "digest" in value and table not in changed:
            checks.append(dict(table=table, unchanged=value == after[table]))
    engine = create_async_engine(local_database_url())
    filters = {
        "source_record": (
            "resource_type NOT IN ('evolution-trigger','evolution-variable',"
            "'project-evolution-glossary','evolution-supplement')"
        ),
        "localized_name": "entity_type NOT IN ('evolution-trigger','evolution-variable')",
        "localized_text": "entity_type NOT IN ('evolution-trigger','evolution-variable')",
        "catalog_dictionary": "resource_type NOT IN ('evolution-trigger','evolution-variable')",
        "catalog_dictionary_link": (
            "dictionary_id IN (SELECT id FROM catalog_dictionary WHERE "
            "resource_type NOT IN ('evolution-trigger','evolution-variable'))"
        ),
        "catalog_sync_entry": "resource_type NOT IN ('evolution-trigger','evolution-variable')",
        "catalog_discovery_page": "resource_type NOT IN ('evolution-trigger','evolution-variable')",
        "sync_run": "coalesce(counts->>'scope','') <> 'evolution-dictionaries'",
    }
    async with engine.connect() as connection:
        for table, where in filters.items():
            row = (
                (
                    await connection.execute(
                        text(
                            f"SELECT count(*) count,md5(string_agg(h,'' ORDER BY h)) digest FROM "
                            f'(SELECT md5(to_jsonb(t)::text) h FROM "{table}" t WHERE {where}) s'
                        )
                    )
                )
                .mappings()
                .one()
            )
            checks.append(
                dict(
                    table=table + ":original-rows",
                    unchanged=dict(row) == before[table],
                    current=dict(row),
                    before=before[table],
                )
            )
    await engine.dispose()
    result = dict(
        checks=checks,
        unchanged=sum(r["unchanged"] for r in checks),
        differences=[r for r in checks if not r["unchanged"]],
    )
    await asyncio.to_thread(
        (audit / "evolution-conditions-preservation.json").write_text,
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["differences"]:
        raise SystemExit(2)


if __name__ == "__main__":
    asyncio.run(main())
