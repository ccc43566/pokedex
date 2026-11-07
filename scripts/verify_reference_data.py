"""Read-only completeness audit and baseline comparison for Navicat/data handoff."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

from reference_data_db import ROOT, local_database_url
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from pokedex_api.sync.importer import json_hash


async def verify(output: Path) -> dict[str, Any]:
    engine = create_async_engine(local_database_url())
    result: dict[str, Any] = {}
    async with engine.connect() as db:
        await db.execute(text("SET TRANSACTION READ ONLY"))

        async def rows(sql: str) -> list[dict[str, Any]]:
            return [dict(row) for row in (await db.execute(text(sql))).mappings()]

        result["entities"] = await rows("""
            SELECT 'move' kind, count(*) count FROM move UNION ALL
            SELECT 'item', count(*) FROM item UNION ALL SELECT 'berry', count(*) FROM berry
            UNION ALL SELECT 'catalog_machine', count(*) FROM catalog_machine
        """)
        result["upstream_identifier_collisions"] = await rows("""
            WITH entities AS (
              SELECT 'item' kind,id,name FROM item UNION ALL SELECT 'move',id,name FROM move
              UNION ALL SELECT 'berry',id,name FROM berry
            ) SELECT kind,name,array_agg(id ORDER BY id) ids FROM entities
              GROUP BY kind,name HAVING count(*)>1 ORDER BY 1,2
        """)
        result["states"] = await rows("""
            SELECT resource_type,status,count(*) count,sum(attempts) attempts
            FROM catalog_sync_entry GROUP BY 1,2 ORDER BY 1,2
        """)
        result["failures"] = await rows("""
            SELECT resource_type,resource_id,status,attempts,error FROM catalog_sync_entry
            WHERE status <> 'success' ORDER BY 1,2
        """)
        result["issues"] = await rows("""
            SELECT owner_type,owner_id,path,target_url,reason FROM catalog_reference_issue
            WHERE NOT resolved ORDER BY 1,2,3
        """)
        result["discovery"] = await rows("""
            WITH latest AS (
              SELECT resource_type,max(run_id) run_id FROM catalog_discovery_page
              WHERE resource_type IN ('move','item','berry') GROUP BY 1
            ), discovered AS (
              SELECT p.run_id,p.resource_type,p.page_url,
                (p.raw_payload->>'count')::int expected,
                jsonb_array_elements(p.raw_payload->'results')->>'url' url
              FROM catalog_discovery_page p JOIN latest l USING(resource_type,run_id)
            ) SELECT resource_type,run_id,min(expected) expected_min,max(expected) expected_max,
                count(DISTINCT page_url) pages,count(*) listed,
                count(DISTINCT url) unique_listed
              FROM discovered GROUP BY 1,2 ORDER BY 1
        """)
        result["dictionary"] = await rows("""
            SELECT resource_type,count(*) count FROM catalog_dictionary GROUP BY 1 ORDER BY 1
        """)
        result["source_entity_mismatches"] = await rows("""
            WITH entities AS (
              SELECT 'move' kind,id,source_record_id FROM move UNION ALL
              SELECT 'item',id,source_record_id FROM item UNION ALL
              SELECT 'berry',id,source_record_id FROM berry UNION ALL
              SELECT 'machine',id,source_record_id FROM catalog_machine
            ) SELECT e.kind,e.id,s.resource_type,s.resource_id FROM entities e
              JOIN source_record s ON s.id=e.source_record_id
              WHERE e.kind<>s.resource_type OR e.id<>s.resource_id
        """)
        result["reverse_pokemon_references_missing_locally"] = await rows("""
            WITH refs AS (
              SELECT s.resource_type,s.resource_id,r->>'url' url
                FROM source_record s,
                LATERAL jsonb_array_elements(s.raw_payload->'learned_by_pokemon') r
                WHERE s.resource_type='move'
              UNION ALL
              SELECT s.resource_type,s.resource_id,r->'pokemon'->>'url' url
                FROM source_record s,
                LATERAL jsonb_array_elements(s.raw_payload->'held_by_pokemon') r
                WHERE s.resource_type='item'
            ) SELECT resource_type,resource_id,url FROM refs
              LEFT JOIN pokemon p ON p.id=(regexp_match(url,'/([0-9]+)/$'))[1]::int
              WHERE p.id IS NULL ORDER BY 1,2,3
        """)
        result["relations"] = await rows("""
            SELECT 'learning_details' kind,
              (SELECT sum(jsonb_array_length(m->'version_group_details')) FROM pokemon p,
                  LATERAL jsonb_array_elements(p.raw_payload->'moves') m) expected,
              (SELECT count(*) FROM pokemon_move) actual
            UNION ALL SELECT 'held_item_details',
              (SELECT sum(jsonb_array_length(i->'version_details')) FROM pokemon p,
                  LATERAL jsonb_array_elements(p.raw_payload->'held_items') i),
              (SELECT count(*) FROM pokemon_held_item)
            UNION ALL SELECT 'berry_item', (SELECT count(*) FROM berry),
              (SELECT count(*) FROM berry b JOIN item i ON i.id=b.item_id)
            UNION ALL SELECT 'berry_flavors',
              (SELECT sum(jsonb_array_length(s.raw_payload->'flavors')) FROM source_record s
                  WHERE resource_type='berry'), (SELECT count(*) FROM berry_flavor_link)
            UNION ALL SELECT 'item_prices',
              (SELECT sum(jsonb_array_length(raw_payload->'prices')) FROM source_record
                  WHERE resource_type='item'),(SELECT count(*) FROM item_price)
            UNION ALL SELECT 'evolution_item_refs',
              (SELECT count(*) FROM evolution_chain e,
                LATERAL jsonb_path_query(e.raw_payload,
                  'strict $.** ? (@.url like_regex "/item/[0-9]+/$")') r),
              (SELECT count(*) FROM evolution_item_reference)
        """)
        result["raw_learning_match_errors"] = await rows("""
            SELECT p.id pokemon_id,pm.move_ordinal,pm.detail_ordinal FROM pokemon_move pm
            JOIN pokemon p ON p.id=pm.pokemon_id
            JOIN catalog_dictionary vg ON vg.id=pm.version_group_id
            JOIN catalog_dictionary lm ON lm.id=pm.learn_method_id
            WHERE pm.raw_payload IS DISTINCT FROM
                p.raw_payload->'moves'->pm.move_ordinal->'version_group_details'->pm.detail_ordinal
              OR pm.move_id <> (regexp_match(
                p.raw_payload->'moves'->pm.move_ordinal->'move'->>'url','/([0-9]+)/$'))[1]::int
              OR pm.level_learned_at <> (pm.raw_payload->>'level_learned_at')::int
              OR pm.learn_order IS DISTINCT FROM (pm.raw_payload->>'order')::int
              OR vg.resource_id <> (regexp_match(pm.raw_payload->'version_group'->>'url',
                '/([0-9]+)/$'))[1]::int
              OR lm.resource_id <> (regexp_match(pm.raw_payload->'move_learn_method'->>'url',
                '/([0-9]+)/$'))[1]::int
        """)
        result["raw_held_match_errors"] = await rows("""
            SELECT p.id pokemon_id,h.item_ordinal,h.detail_ordinal FROM pokemon_held_item h
            JOIN pokemon p ON p.id=h.pokemon_id
            JOIN catalog_dictionary v ON v.id=h.version_id
            WHERE h.raw_payload IS DISTINCT FROM
                p.raw_payload->'held_items'->h.item_ordinal->'version_details'->h.detail_ordinal
              OR h.rarity <> (h.raw_payload->>'rarity')::int
              OR h.item_id <> (regexp_match(
                  p.raw_payload->'held_items'->h.item_ordinal->'item'->>'url','/([0-9]+)/$'))[1]::int
              OR v.resource_id <> (regexp_match(h.raw_payload->'version'->>'url',
                  '/([0-9]+)/$'))[1]::int
        """)
        result["raw_price_match_errors"] = await rows("""
            SELECT p.item_id,p.ordinal FROM item_price p JOIN item i ON i.id=p.item_id
            JOIN source_record s ON s.id=i.source_record_id
            JOIN catalog_dictionary vg ON vg.id=p.version_group_id
            JOIN catalog_dictionary c ON c.id=p.currency_id
            WHERE p.raw_payload IS DISTINCT FROM s.raw_payload->'prices'->p.ordinal
              OR p.purchase_price IS DISTINCT FROM (p.raw_payload->>'purchase_price')::int
              OR p.sell_price IS DISTINCT FROM (p.raw_payload->>'sell_price')::int
              OR vg.resource_id <> (regexp_match(p.raw_payload->'version_group'->>'url',
                  '/([0-9]+)/$'))[1]::int
              OR c.resource_id <> (regexp_match(p.raw_payload->'currency'->>'url',
                  '/([0-9]+)/$'))[1]::int
        """)
        result["languages"] = await rows("""
            SELECT s.resource_type,count(*) resources,
              count(*) FILTER (WHERE EXISTS(SELECT 1 FROM localized_name n
                WHERE n.entity_type=s.resource_type AND n.entity_id=s.resource_id
                  AND n.locale='zh-Hans')) zh_hans_names,
              count(*) FILTER (WHERE EXISTS(SELECT 1 FROM localized_name n
                WHERE n.entity_type=s.resource_type AND n.entity_id=s.resource_id
                  AND n.locale='zh-Hant')) zh_hant_names,
              count(*) FILTER (WHERE EXISTS(SELECT 1 FROM localized_name n
                WHERE n.entity_type=s.resource_type AND n.entity_id=s.resource_id
                  AND n.locale='en')) en_names,
              count(*) FILTER (WHERE EXISTS(SELECT 1 FROM localized_text t
                WHERE t.entity_type=s.resource_type AND t.entity_id=s.resource_id
                  AND t.locale='zh-Hans')) zh_hans_texts,
              count(*) FILTER (WHERE EXISTS(SELECT 1 FROM localized_text t
                WHERE t.entity_type=s.resource_type AND t.entity_id=s.resource_id
                  AND t.locale='en')) en_texts
            FROM source_record s WHERE resource_type IN ('move','item') GROUP BY 1 ORDER BY 1
        """)
        result["language_gaps"] = await rows("""
            SELECT s.resource_type,s.resource_id,s.name,
              EXISTS(SELECT 1 FROM localized_name n WHERE n.entity_type=s.resource_type
                AND n.entity_id=s.resource_id AND n.locale='en') has_english_name,
              EXISTS(SELECT 1 FROM localized_name n WHERE n.entity_type=s.resource_type
                AND n.entity_id=s.resource_id AND n.locale='zh-Hans') has_zh_hans_name
            FROM source_record s WHERE resource_type IN ('move','item') AND
              (NOT EXISTS(SELECT 1 FROM localized_name n WHERE n.entity_type=s.resource_type
                AND n.entity_id=s.resource_id AND n.locale='en') OR
               NOT EXISTS(SELECT 1 FROM localized_name n WHERE n.entity_type=s.resource_type
                AND n.entity_id=s.resource_id AND n.locale='zh-Hans'))
            ORDER BY s.resource_type,s.resource_id
        """)
        result["source_availability"] = await rows("""
            SELECT
              (SELECT count(DISTINCT item_id) FROM item_price) items_with_prices,
              (SELECT count(*) FROM item_price WHERE purchase_price IS NULL) null_purchase_prices,
              (SELECT count(*) FROM item_price WHERE sell_price IS NULL) null_sell_prices,
              (SELECT count(*) FROM source_record WHERE resource_type='item'
                AND raw_payload ? 'cost') source_items_with_legacy_cost,
              (SELECT count(*) FROM pokemon WHERE raw_payload->'moves'='[]'::jsonb)
                pokemon_with_empty_source_moves,
              (SELECT count(*) FROM source_record WHERE resource_type='berry'
                AND raw_payload->'flavors'='[]'::jsonb) berries_with_empty_source_flavors
        """)
        result["historical_texts"] = await rows("""
            SELECT entity_type,locale,text_kind,count(*) entries,
              count(DISTINCT version) contexts FROM localized_text
              WHERE entity_type IN ('move','item') GROUP BY 1,2,3 ORDER BY 1,2,3
        """)
        result["history"] = await rows("""
            SELECT (SELECT count(*) FROM move_past_value) move_past_values,
              (SELECT sum(jsonb_array_length(raw_payload->'past_values')) FROM source_record
                WHERE resource_type='move') raw_past_values,
              (SELECT count(DISTINCT pokemon_id) FROM pokemon_move) pokemon_with_moves,
              (SELECT count(DISTINCT pokemon_id) FROM pokemon_held_item) pokemon_with_held_items,
              (SELECT count(*) FROM evolution_item_reference) evolution_item_references
        """)
        result["duplicate_names"] = await rows("""
            SELECT entity_type,entity_id,locale,name,count(*) FROM localized_name
            GROUP BY 1,2,3,4 HAVING count(*)>1
        """)
        result["duplicate_texts"] = await rows("""
            SELECT entity_type,entity_id,locale,text_kind,version,text,count(*)
            FROM localized_text WHERE entity_type IN ('move','item')
            GROUP BY 1,2,3,4,5,6 HAVING count(*)>1
        """)
        result["foreign_keys"] = await rows("""
            SELECT count(*) checked, count(*) FILTER (WHERE NOT convalidated) unvalidated
            FROM pg_constraint c JOIN pg_class t ON t.oid=c.conrelid
            WHERE contype='f' AND t.relname IN (
              'move','item','berry','pokemon_move','pokemon_held_item','catalog_machine',
              'catalog_dictionary','catalog_dictionary_link','item_game_index','item_attribute_link',
              'move_past_value','move_stat_change','berry_flavor_link','evolution_item_reference',
              'item_price')
        """)
        result["source_hash_errors"] = []
        last_source = 0
        while True:
            source_rows = (
                (
                    await db.execute(
                        text("""
                SELECT id,resource_type,resource_id,source_hash,raw_payload FROM source_record
                WHERE id > :last AND resource_type NOT IN
                  ('pokemon','pokemon-species','pokemon-form','evolution-chain','ability','pokedex')
                ORDER BY id LIMIT 100
            """),
                        {"last": last_source},
                    )
                )
                .mappings()
                .all()
            )
            if not source_rows:
                break
            for source in source_rows:
                if source["source_hash"] != json_hash(source["raw_payload"]):
                    result["source_hash_errors"].append(
                        dict(
                            resource_type=source["resource_type"],
                            resource_id=source["resource_id"],
                        )
                    )
                last_source = source["id"]
        result["example_queries"] = []
        sql_file = ROOT / "scripts/reference_data_examples.sql"
        sql_text = await asyncio.to_thread(sql_file.read_text, encoding="utf-8")
        statements = "\n".join(
            line for line in sql_text.splitlines() if not line.lstrip().startswith("--")
        ).split(";")
        for statement in statements:
            if statement.strip():
                examples = await rows(statement)
                result["example_queries"].append(
                    dict(
                        rows=len(examples),
                        columns=list(examples[0]) if examples else [],
                    )
                )
        baseline = json.loads(
            (ROOT.parent / "migration-audit/reference-data-before.json").read_text()
        )
        immutable = [
            name
            for name in baseline
            if isinstance(baseline[name], dict)
            and "digest" in baseline[name]
            and name
            not in {
                "source_record",
                "localized_name",
                "localized_text",
                "sync_run",
                "alembic_version",
            }
        ]
        result["baseline_comparison"] = []
        for table in immutable:
            now = (
                await rows(f"""
                SELECT count(*) count,md5(string_agg(h,'' ORDER BY h)) digest
                FROM (SELECT md5(to_jsonb(t)::text) h FROM "{table}" t) x
            """)
            )[0]
            result["baseline_comparison"].append(
                {
                    "table": table,
                    "unchanged": now == baseline[table],
                    "before": baseline[table],
                    "after": now,
                }
            )
        original_types = (
            "'ability','evolution-chain','generation','pokedex','pokemon',"
            "'pokemon-form','pokemon-species','stat','type'"
        )
        for table, field in (
            ("source_record", "resource_type"),
            ("localized_name", "entity_type"),
            ("localized_text", "entity_type"),
        ):
            now = (
                await rows(f"""
                SELECT count(*) count,md5(string_agg(h,'' ORDER BY h)) digest
                FROM (SELECT md5(to_jsonb(t)::text) h FROM {table} t
                      WHERE {field} IN ({original_types})) x
            """)
            )[0]
            result["baseline_comparison"].append(
                {
                    "table": f"{table}:original-resources",
                    "unchanged": now == baseline[table],
                    "before": baseline[table],
                    "after": now,
                }
            )
        result["success"] = (
            not any(
                result[k]
                for k in (
                    "failures",
                    "issues",
                    "raw_learning_match_errors",
                    "raw_held_match_errors",
                    "duplicate_names",
                    "duplicate_texts",
                    "source_hash_errors",
                    "source_entity_mismatches",
                    "raw_price_match_errors",
                )
            )
            and all(r["expected"] == r["actual"] for r in result["relations"])
            and all(r["unchanged"] for r in result["baseline_comparison"])
            and all(
                r["expected_min"]
                == r["expected_max"]
                == r["listed"]
                == r["unique_listed"]
                for r in result["discovery"]
            )
            and all(
                next(
                    e["count"]
                    for e in result["entities"]
                    if e["kind"] == r["resource_type"]
                )
                == r["unique_listed"]
                for r in result["discovery"]
            )
        )
    await engine.dispose()
    await asyncio.to_thread(
        output.write_text,
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                k: v
                for k, v in result.items()
                if k
                not in {"historical_texts", "baseline_comparison", "issues", "failures"}
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = asyncio.run(verify(args.output))
    raise SystemExit(0 if result["success"] else 2)
