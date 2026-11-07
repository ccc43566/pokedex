"""Durable, finite collection job. Runs in the API container without rebuilding it.

Stage this script beside the current version_sprites.py and run with Docker exec -d.
Progress/report files live in MEDIA_ROOT/.collection/2026-10-26 (no credentials).
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import shutil
import traceback
from datetime import UTC, datetime
from pathlib import Path

import asyncpg

from version_sprites import mirror_versions

ROOT = Path(os.environ.get("MEDIA_ROOT", "/app/media"))
JOB = ROOT / ".collection" / "2026-10-26"
DSN = os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://")


def now():
    return datetime.now(UTC).isoformat()


def save(name, value):
    temporary = JOB / f"{name}.{os.getpid()}.tmp"
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(JOB / name)


async def snapshot(db):
    statuses = {row["status"]: row["n"] for row in await db.fetch(
        "SELECT status,count(*) n FROM version_sprite GROUP BY status"
    )}
    return {
        "at": now(), "statuses": statuses,
        "remainingUrls": await db.fetchval("""
            SELECT count(DISTINCT source_url) FROM version_sprite
            WHERE status IN ('pending','download_failed','corrupt')
        """),
        "uniqueDownloadedHashes": await db.fetchval("""
            SELECT count(DISTINCT checksum) FROM version_sprite WHERE status='downloaded'
        """),
        "byGeneration": [dict(r) for r in await db.fetch("""
            SELECT generation,status,count(*) AS associations,count(DISTINCT source_url) AS urls
            FROM version_sprite GROUP BY generation,status ORDER BY generation,status
        """)],
    }


async def verify(db):
    refs = await db.fetch("""
        SELECT checksum,local_path,NULL::bigint AS byte_size FROM media_asset
        WHERE local_path IS NOT NULL
        UNION SELECT checksum,local_path,byte_size FROM version_sprite WHERE status='downloaded'
    """)
    missing, bad_hash, bad_size = [], [], []
    checked = {}
    for row in refs:
        relative = row["local_path"]
        path = ROOT / (relative or "")
        if not relative or not path.resolve().is_relative_to(ROOT.resolve()) or not path.is_file():
            missing.append(relative)
            continue
        stat = path.stat()
        inode = (stat.st_dev, stat.st_ino)
        if inode not in checked:
            with path.open("rb") as handle:
                checked[inode] = hashlib.file_digest(handle, "sha256").hexdigest()
        if checked[inode] != row["checksum"]:
            bad_hash.append(relative)
        if row["byte_size"] is not None and row["byte_size"] != stat.st_size:
            bad_size.append(relative)
    disk = {}
    paths = 0
    for path in ROOT.rglob("*"):
        if path.is_file() and not path.is_relative_to(ROOT / ".collection"):
            stat = path.stat()
            disk[(stat.st_dev, stat.st_ino)] = stat.st_size
            paths += 1
    multiple_paths = await db.fetchval("""
        SELECT count(*) FROM (
            SELECT checksum FROM (
                SELECT checksum,local_path FROM media_asset
                UNION ALL SELECT checksum,local_path FROM version_sprite WHERE status='downloaded'
            ) r WHERE checksum IS NOT NULL GROUP BY checksum HAVING count(DISTINCT local_path)>1
        ) t
    """)
    return {
        "uniquePhysicalFilesSha256Verified": len(checked),
        "missingFiles": sorted(set(missing), key=str),
        "checksumMismatches": sorted(set(bad_hash)),
        "sizeMismatches": sorted(set(bad_size)),
        "hashGroupsWithMultipleDatabasePaths": multiple_paths,
        "diskPathsIncludingLegacyAliases": paths,
        "physicalFiles": len(disk), "physicalBytes": sum(disk.values()),
    }


async def run():
    JOB.mkdir(parents=True, exist_ok=True)
    os.environ["VERSION_SPRITE_SKIP_MATERIALIZE"] = "1"
    os.environ["VERSION_SPRITE_PROGRESS_PATH"] = str(JOB / "progress.json")
    db = await asyncpg.connect(DSN, command_timeout=600)
    state = {"status": "starting", "pid": os.getpid(), "startedAt": now(), "rounds": []}
    owns_job = False
    try:
        owns_job = await db.fetchval("SELECT pg_try_advisory_lock($1)", 73150821920261027)
        if not owns_job:
            raise RuntimeError("Another durable collection job is running")
        state["before"] = await snapshot(db)
        state["status"] = "running"
        save("state.json", state)
        concurrency = int(os.environ.get("VERSION_SPRITE_CONCURRENCY", "32"))
        for attempt in range(3):
            if shutil.disk_usage(ROOT).free < 10 * 1024**3:
                raise RuntimeError("Less than 10 GiB free in the media filesystem")
            state["round"] = attempt + 1
            save("state.json", state)
            result = await mirror_versions(
                database_url=os.environ["DATABASE_URL"], media_root=ROOT,
                concurrency=concurrency,
            )
            state["rounds"].append(result)
            state["current"] = await snapshot(db)
            save("state.json", state)
            if state["current"]["remainingUrls"] == 0:
                break
            if attempt < 2:
                await asyncio.sleep(30)
        state["status"] = "verifying"
        save("state.json", state)
        state["integrity"] = await verify(db)
        state["after"] = await snapshot(db)
        state["failures"] = [dict(r) for r in await db.fetch("""
            SELECT source_url,status,error,max(attempts) AS attempts,count(*) AS associations
            FROM version_sprite WHERE status IN ('download_failed','corrupt')
            GROUP BY source_url,status,error ORDER BY source_url
        """)]
        integrity = state["integrity"]
        good = not any(integrity[k] for k in (
            "missingFiles", "checksumMismatches", "sizeMismatches",
            "hashGroupsWithMultipleDatabasePaths",
        ))
        state["status"] = (
            "complete" if good and state["after"]["remainingUrls"] == 0 else "needs_attention"
        )
        state["finishedAt"] = now()
        save("state.json", state)
        save("report.json", state)
        return 0 if state["status"] == "complete" else 2
    except BaseException as error:
        state.update(status="failed", finishedAt=now(), error=str(error))
        if owns_job:
            save("state.json", state)
            save("report.json", state)
        traceback.print_exc()
        raise
    finally:
        await db.close()


if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    raise SystemExit(asyncio.run(run()))
