"""Target only item.sprites.default; reuse shared SHA-256 bytes, never Pokemon IDs."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import logging
import os
from collections import Counter
from collections.abc import Coroutine
from pathlib import Path
from uuid import uuid4

import asyncpg  # type: ignore[import-untyped]
import httpx

from pokedex_api.sync.version_sprites import SYNC_LOCK_KEY, inspect_image

logger = logging.getLogger(__name__)


def shared_path(root: Path, relative: str) -> Path:
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError("Media path escapes the shared root")
    return path


def store_content(root: Path, data: bytes, existing: dict[str, str]) -> tuple[str, str, bool]:
    checksum = hashlib.sha256(data).hexdigest()
    fmt, _, _, _ = inspect_image(data)
    relative = existing.get(checksum)
    if relative:
        path = shared_path(root, relative)
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != checksum:
            raise ValueError("Existing shared media is missing or has a different checksum")
        return checksum, relative, False
    relative = f"version-sprites/{checksum[:2]}/{checksum}.{fmt}"
    destination = shared_path(root, relative)
    destination.parent.mkdir(parents=True, exist_ok=True)
    created = False
    if destination.exists():
        if hashlib.sha256(destination.read_bytes()).hexdigest() != checksum:
            raise ValueError("Canonical media checksum mismatch")
    else:
        temporary = destination.with_name(destination.name + f".{uuid4().hex}.part")
        try:
            temporary.write_bytes(data)
            os.replace(temporary, destination)
            created = True
        finally:
            temporary.unlink(missing_ok=True)
    existing[checksum] = relative
    return checksum, relative, created


async def collect(
    *,
    database_url: str,
    media_root: Path,
    concurrency: int = 6,
    limit: int | None = None,
    retry_failed: bool = False,
) -> dict[str, object]:
    if concurrency not in range(1, 13) or (limit is not None and limit < 0):
        raise ValueError("concurrency must be 1..12; limit must be nonnegative")
    db = await asyncpg.connect(database_url.replace("postgresql+asyncpg://", "postgresql://"))
    counts: Counter[str] = Counter()
    try:
        if not await db.fetchval("SELECT pg_try_advisory_lock($1)", SYNC_LOCK_KEY):
            raise RuntimeError("Another media task is running")
        await db.execute("""
            INSERT INTO item_media(item_id,source_url,status,attempts,updated_at)
              SELECT id,nullif(sprites->>'default',''),
                CASE WHEN nullif(sprites->>'default','') IS NULL
                  THEN 'no_source' ELSE 'pending' END,
                0,now() FROM item
            ON CONFLICT(item_id) DO UPDATE SET source_url=excluded.source_url,
              status=excluded.status,checksum=NULL,local_path=NULL,error=NULL,
              format=NULL,byte_size=NULL,width=NULL,height=NULL,frame_count=NULL,updated_at=now()
            WHERE item_media.source_url IS DISTINCT FROM excluded.source_url
        """)
        old = await db.fetch("""
            SELECT source_url,checksum,local_path FROM media_asset WHERE local_path IS NOT NULL
            UNION SELECT source_url,checksum,local_path FROM version_sprite
              WHERE status='downloaded'
            UNION SELECT source_url,checksum,local_path FROM item_media WHERE status='downloaded'
        """)
        existing = {row["checksum"]: row["local_path"] for row in old if row["checksum"]}
        urls = {row["source_url"]: row for row in old if row["checksum"] and row["source_url"]}
        pending = await db.fetch(
            """
            SELECT DISTINCT source_url FROM item_media WHERE source_url IS NOT NULL
              AND (status IN ('pending','download_failed','corrupt') OR ($1 AND status='missing'))
            ORDER BY source_url
        """,
            retry_failed,
        )
        if limit is not None:
            pending = pending[:limit]
        semaphore = asyncio.Semaphore(concurrency)
        async with httpx.AsyncClient(
            timeout=35, follow_redirects=True, headers={"User-Agent": "pokedex-local/0.1"}
        ) as client:

            async def fetch(url: str) -> tuple[str, bytes | None, str | None]:
                for attempt in range(3):
                    try:
                        async with semaphore:
                            response = await client.get(url)
                        if response.status_code == 404:
                            return "missing", None, "HTTP 404: default image unavailable at source"
                        response.raise_for_status()
                        inspect_image(response.content)
                        return "downloaded", response.content, None
                    except (httpx.HTTPError, ValueError, OSError) as exc:
                        if attempt == 2:
                            return "download_failed", None, str(exc)[:500]
                        await asyncio.sleep(0.5 * (2**attempt))
                return "download_failed", None, "Retry limit reached"

            for offset in range(0, len(pending), concurrency):
                batch = pending[offset : offset + concurrency]
                requests: list[Coroutine[object, object, tuple[str, bytes | None, str | None]]] = []
                for row in batch:
                    cached = urls.get(row["source_url"])
                    if cached:
                        path = shared_path(media_root, cached["local_path"])
                        if path.is_file():
                            cached_data = await asyncio.to_thread(path.read_bytes)
                            if hashlib.sha256(cached_data).hexdigest() == cached["checksum"]:
                                counts["reused_urls"] += 1
                                requests.append(
                                    asyncio.sleep(0, result=("downloaded", cached_data, None))
                                )
                                continue
                    requests.append(fetch(row["source_url"]))
                    counts["requested_urls"] += 1
                results = await asyncio.gather(*requests)
                for row, (status, data, error) in zip(batch, results, strict=True):
                    checksum = relative = fmt = None
                    width = height = frames = size = None
                    if data is not None:
                        try:
                            fmt, width, height, frames = inspect_image(data)
                            checksum, relative, created = await asyncio.to_thread(
                                store_content, media_root, data, existing
                            )
                            size = len(data)
                            counts["new_files" if created else "reused_hashes"] += 1
                            if created:
                                counts["new_bytes"] += size
                        except (ValueError, OSError) as exc:
                            status, error = "corrupt", str(exc)
                    counts[status] += 1
                    await db.execute(
                        """
                        UPDATE item_media SET status=$1,checksum=$2,local_path=$3,format=$4,
                          byte_size=$5,width=$6,height=$7,frame_count=$8,error=$9,
                          attempts=attempts+1,updated_at=now() WHERE source_url=$10
                    """,
                        status,
                        checksum,
                        relative,
                        fmt,
                        size,
                        width,
                        height,
                        frames,
                        error,
                        row["source_url"],
                    )
                logger.info(
                    "Default image URLs %s/%s: %s", offset + len(batch), len(pending), dict(counts)
                )
        states = [
            dict(r)
            for r in await db.fetch(
                "SELECT status,count(*) count FROM item_media GROUP BY status ORDER BY status"
            )
        ]
        failures = [
            dict(r)
            for r in await db.fetch("""
            SELECT item_id,source_url,status,error FROM item_media
            WHERE status IN ('missing','download_failed','corrupt') ORDER BY item_id
        """)
        ]
        return dict(
            urls_processed=len(pending), counts=dict(counts), states=states, failures=failures
        )
    finally:
        await db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--concurrency", type=int, default=6, choices=range(1, 13))
    parser.add_argument("--retry-failed", action="store_true")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    result = asyncio.run(
        collect(
            database_url=os.environ["DATABASE_URL"],
            media_root=Path(os.environ.get("MEDIA_ROOT", "/app/media")),
            concurrency=args.concurrency,
            limit=args.limit,
            retry_failed=args.retry_failed,
        )
    )
    output = json.dumps(result, ensure_ascii=False, indent=2)
    if args.report:
        args.report.write_text(output, encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "failures"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
