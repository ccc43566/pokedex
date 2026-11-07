"""Read-only raw evolution audit and representative test-data export."""

from __future__ import annotations

import asyncio
import json
from collections import Counter
from typing import Any

from reference_data_db import ROOT, local_database_url
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


async def main() -> None:
    engine = create_async_engine(local_database_url())
    methods: list[dict[str, Any]] = []
    chains: list[dict[str, Any]] = []

    def walk(
        chain_id: int, node: dict[str, Any], parent: dict[str, Any] | None = None
    ) -> None:
        if parent:
            for index, method in enumerate(node.get("evolution_details") or []):
                methods.append(
                    dict(
                        chain_id=chain_id,
                        source=parent["species"],
                        target=node["species"],
                        index=index,
                        method=method,
                    )
                )
        for child in node.get("evolves_to") or []:
            walk(chain_id, child, node)

    async with engine.connect() as db:
        for chain_id, payload in (
            await db.execute(
                text("SELECT id,raw_payload FROM evolution_chain ORDER BY id")
            )
        ).all():
            chains.append(payload)
            if payload.get("chain"):
                walk(chain_id, payload["chain"])
        sources = [
            dict(r)
            for r in (
                await db.execute(
                    text(
                        "SELECT resource_type,count(*) count FROM source_record "
                        "WHERE resource_type LIKE '%evolution%' GROUP BY 1 ORDER BY 1"
                    )
                )
            ).mappings()
        ]
    await engine.dispose()
    keys = Counter(
        k for row in methods for k, v in row["method"].items() if v is not None
    )
    expressions = Counter(
        json.dumps(r["method"]["condition_expression"], sort_keys=True)
        for r in methods
        if r["method"].get("condition_expression")
    )
    triggers = Counter(r["method"].get("trigger", {}).get("name") for r in methods)
    selected = {
        "nincada",
        "ninjask",
        "shedinja",
        "wurmple",
        "silcoon",
        "cascoon",
        "dunsparce",
        "dudunsparce",
        "tandemaus",
        "maushold",
        "milcery",
        "alcremie",
    }
    report = dict(
        sources=sources,
        chains=len(chains),
        methods=len(methods),
        keys=dict(keys),
        triggers=dict(triggers),
        expressions=[
            dict(condition=json.loads(k), count=v) for k, v in expressions.items()
        ],
        samples=[
            r
            for r in methods
            if r["source"]["name"] in selected or r["target"]["name"] in selected
        ],
    )
    output = ROOT.parent / "migration-audit/evolution-conditions-raw-audit.json"
    await asyncio.to_thread(
        output.write_text,
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    await asyncio.to_thread(
        (output.parent / "evolution-chain-methods.json").write_text,
        json.dumps(methods, ensure_ascii=False),
        encoding="utf-8",
    )
    print(
        json.dumps(
            dict(
                chains=len(chains),
                methods=len(methods),
                keys=dict(keys),
                triggers=dict(triggers),
                expressions=report["expressions"],
            ),
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
