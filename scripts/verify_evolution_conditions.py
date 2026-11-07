"""Explain every stored method and report unresolved conditions, without changing chains."""

from __future__ import annotations

import asyncio
import json
from collections import Counter

from reference_data_db import ROOT, local_database_url
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from pokedex_api.models import EvolutionChain, LocalizedName
from pokedex_api.services.evolution_conditions import (
    explain_method,
    load_condition_context,
)


async def main() -> None:
    engine = create_async_engine(local_database_url())
    factory = async_sessionmaker(engine, expire_on_commit=False)
    rows = []

    def walk(chain_id, node, parent=None):
        if parent:
            for index, method in enumerate(node.get("evolution_details") or []):
                rows.append(
                    dict(
                        chain_id=chain_id,
                        source=parent["species"],
                        target=node["species"],
                        method_index=index,
                        method=method,
                    )
                )
        for child in node.get("evolves_to") or []:
            walk(chain_id, child, node)

    async with factory() as session:
        for chain in (await session.scalars(select(EvolutionChain))).all():
            walk(chain.id, chain.raw_payload["chain"])
        context = await load_condition_context(
            session, [r["method"] for r in rows], "zh-Hans"
        )
        names = {
            (r.entity_type, r.entity_id): r.name
            for r in (
                await session.scalars(
                    select(LocalizedName).where(
                        LocalizedName.entity_type == "pokemon-species",
                        LocalizedName.locale == "zh-Hans",
                    )
                )
            ).all()
        }

        def sid(ref):
            return int(ref["url"].rstrip("/").split("/")[-1])

        for row in rows:
            source, target = sid(row["source"]), sid(row["target"])
            explanation = explain_method(
                row["method"],
                context,
                source_species_id=source,
                target_species_id=target,
                source_label=names.get(("pokemon-species", source), ""),
                target_label=names.get(("pokemon-species", target), ""),
            )
            row["explanation"] = explanation.model_dump(mode="json")
    await engine.dispose()
    pending = [r for r in rows if r["explanation"]["unresolved"]]
    report = dict(
        methods=len(rows),
        explained=len(rows) - len(pending),
        pending=len(pending),
        expression_methods=sum(
            bool(r["method"].get("condition_expression")) for r in rows
        ),
        trigger_origins=dict(
            Counter(r["explanation"]["trigger_name_origin"] for r in rows)
        ),
        unresolved=pending,
        results=rows,
    )
    output = ROOT.parent / "migration-audit/evolution-condition-explanations.json"
    await asyncio.to_thread(
        output.write_text,
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {k: v for k, v in report.items() if k != "results"},
            ensure_ascii=False,
            indent=2,
        )
    )
    if pending:
        raise SystemExit(2)


if __name__ == "__main__":
    asyncio.run(main())
