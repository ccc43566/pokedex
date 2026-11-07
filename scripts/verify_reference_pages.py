"""Read-only integrity + actual API/media checks for the item/move UI. No upstream calls."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from pathlib import Path
from typing import Any

import httpx
from reference_data_db import local_database_url
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


async def verify(api: str, media: str) -> dict[str, Any]:
    engine = create_async_engine(local_database_url())
    report: dict[str, Any] = {}
    async with engine.connect() as db:
        await db.execute(text("SET TRANSACTION READ ONLY"))
        counts = {}
        for table in [
            "item",
            "move",
            "berry",
            "item_media",
            "catalog_machine",
            "item_price",
            "move_past_value",
            "pokemon_move",
            "pokemon_held_item",
            "evolution_item_reference",
            "catalog_reference_issue",
        ]:
            counts[table] = await db.scalar(text(f"SELECT count(*) FROM {table}"))
        report["counts"] = counts
        report["languageCoverage"] = [
            dict(r)
            for r in (
                await db.execute(
                    text("""
            SELECT entity_type,locale,count(distinct entity_id) records FROM localized_name
            WHERE entity_type IN ('item','move') AND locale IN ('zh-Hans','en')
            GROUP BY 1,2 ORDER BY 1,2
        """)
                )
            ).mappings()
        ]
        report["priceCoverage"] = dict(
            (
                await db.execute(
                    text("""
            SELECT count(distinct item_id) items,count(*) records,
              count(*) FILTER (WHERE purchase_price IS NULL) purchase_null,
              count(*) FILTER (WHERE sell_price IS NULL) sell_null,
              count(*) FILTER (WHERE purchase_price=0) purchase_zero,
              count(*) FILTER (WHERE sell_price=0) sell_zero FROM item_price
        """)
                )
            )
            .mappings()
            .one()
        )
        report["media"] = dict(
            (
                await db.execute(
                    text("""
            SELECT count(*) items,count(distinct source_url) source_urls,
              count(distinct checksum) hashes,count(distinct local_path) files,
              count(*) FILTER (WHERE status<>'downloaded') not_downloaded,
              count(*) FILTER (WHERE source_url IS DISTINCT FROM i.sprites->>'default')
                wrong_source FROM item_media m JOIN item i ON i.id=m.item_id
        """)
                )
            )
            .mappings()
            .one()
        )
        conflicts = await db.scalar(
            text("""
            SELECT count(*) FROM (SELECT checksum FROM (
              SELECT checksum,local_path FROM media_asset WHERE local_path IS NOT NULL
              UNION SELECT checksum,local_path FROM version_sprite WHERE status='downloaded'
              UNION SELECT checksum,local_path FROM item_media WHERE status='downloaded'
            ) all_media GROUP BY checksum HAVING count(distinct local_path)>1) conflicts
        """)
        )
        report["globalHashPathConflicts"] = conflicts
        report["berryPocket"] = dict(
            (
                await db.execute(
                    text("""
            SELECT count(*) item_records,count(b.id) with_berry FROM item i
              JOIN catalog_dictionary_link l ON l.dictionary_id=i.category_id AND l.path='$.pocket'
              JOIN catalog_dictionary p ON p.id=l.target_id
              LEFT JOIN berry b ON b.item_id=i.id
            WHERE p.resource_type='item-pocket' AND p.resource_id=5
        """)
                )
            )
            .mappings()
            .one()
        )
        report["berriesOutsideBerryPocket"] = [
            dict(r)
            for r in (
                await db.execute(
                    text("""
            SELECT b.id berry_id,i.id item_id,i.name,p.resource_id pocket_id,p.name pocket
            FROM berry b JOIN item i ON i.id=b.item_id
              LEFT JOIN catalog_dictionary_link l ON l.dictionary_id=i.category_id
                AND l.path='$.pocket'
              LEFT JOIN catalog_dictionary p ON p.id=l.target_id
            WHERE p.resource_id IS DISTINCT FROM 5 ORDER BY b.id
        """)
                )
            ).mappings()
        ]
        report["berryPocketWithoutDedicatedData"] = [
            dict(r)
            for r in (
                await db.execute(
                    text("""
            SELECT i.id,i.name FROM item i
              JOIN catalog_dictionary_link l ON l.dictionary_id=i.category_id AND l.path='$.pocket'
              JOIN catalog_dictionary p ON p.id=l.target_id
              LEFT JOIN berry b ON b.item_id=i.id
            WHERE p.resource_type='item-pocket' AND p.resource_id=5 AND b.id IS NULL ORDER BY i.id
        """)
                )
            ).mappings()
        ]
        report["fallbackExamples"] = [
            dict(r)
            for r in (
                await db.execute(
                    text("""
            SELECT i.id,i.name FROM item i WHERE NOT EXISTS (SELECT 1 FROM localized_name n
              WHERE n.entity_type='item' AND n.entity_id=i.id AND n.locale='zh-Hans')
            ORDER BY i.id LIMIT 8
        """)
                )
            ).mappings()
        ]
        report["moveNulls"] = dict(
            (
                await db.execute(
                    text("""
            SELECT count(*) FILTER (WHERE power IS NULL) power,
              count(*) FILTER (WHERE accuracy IS NULL) accuracy,
              count(*) FILTER (WHERE pp IS NULL) pp,
              count(*) FILTER (WHERE effect_chance IS NULL) effect_chance FROM move
        """)
                )
            )
            .mappings()
            .one()
        )
        report["unresolvedReferenceIssues"] = await db.scalar(
            text("SELECT count(*) FROM catalog_reference_issue WHERE NOT resolved")
        )
        report["dangling"] = {}
        for relation, target, foreign in [
            ("pokemon_move", "move", "move_id"),
            ("pokemon_held_item", "item", "item_id"),
            ("evolution_item_reference", "item", "item_id"),
            ("berry", "item", "item_id"),
            ("catalog_machine", "move", "move_id"),
            ("catalog_machine", "item", "item_id"),
            ("item_media", "item", "item_id"),
        ]:
            report["dangling"][f"{relation}.{foreign}"] = await db.scalar(
                text(
                    f"SELECT count(*) FROM {relation} r LEFT JOIN {target} t ON t.id=r.{foreign} "
                    "WHERE t.id IS NULL"
                )
            )
        image_rows = (
            await db.execute(
                text(
                    "SELECT DISTINCT local_path,checksum FROM item_media WHERE status='downloaded'"
                )
            )
        ).all()
        price_ids = (
            (await db.execute(text("SELECT DISTINCT item_id FROM item_price"))).scalars().all()
        )
        expected = {
            kind: (await db.execute(text(f"SELECT id FROM {table} ORDER BY id"))).scalars().all()
            for kind, table in [("items", "item"), ("moves", "move")]
        }
    await engine.dispose()
    async with httpx.AsyncClient(timeout=30) as client:
        report["pagination"] = {}
        for kind, ids in expected.items():
            found = []
            page, pages = 1, 1
            while page <= pages:
                response = await client.get(
                    f"{api}/{kind}", params={"page": page, "page_size": 100}
                )
                response.raise_for_status()
                payload = response.json()
                assert payload["total"] == len(ids)
                found.extend(r["id"] for r in payload["items"])
                assert "rawPayload" not in response.text and "raw_payload" not in response.text
                pages = payload["totalPages"]
                page += 1
            assert found == ids and len(set(found)) == len(ids)
            report["pagination"][kind] = {
                "pages": pages,
                "records": len(found),
                "exactIdMatch": True,
            }
        price_rows = 0
        for item_id in price_ids:
            response = await client.get(f"{api}/items/{item_id}")
            response.raise_for_status()
            price_rows += len(response.json()["fields"]["prices"])
        assert price_rows == counts["item_price"]
        report["pricesReturnedExactly"] = price_rows
        ambiguous = await client.get(f"{api}/items/roseli-berry")
        assert ambiguous.status_code == 409
        report["ambiguousIdentifierIds"] = ambiguous.json()["detail"]["ids"]
        semaphore = asyncio.Semaphore(8)

        async def check_image(path: str, checksum: str) -> None:
            async with semaphore:
                response = await client.get(f"{media}/{path}")
                response.raise_for_status()
                assert hashlib.sha256(response.content).hexdigest() == checksum, path

        await asyncio.gather(*(check_image(path, checksum) for path, checksum in image_rows))
        report["localMediaHashesVerified"] = len(image_rows)
    assert not any(report["dangling"].values())
    assert conflicts == 0
    assert report["media"]["not_downloaded"] == report["media"]["wrong_source"] == 0
    report["status"] = "passed"
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api", default="http://127.0.0.1:8001/api/v1")
    parser.add_argument("--media", default="http://127.0.0.1:8080/media")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = asyncio.run(verify(args.api.rstrip("/"), args.media.rstrip("/")))
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
