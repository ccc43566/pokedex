"""Summarize the persisted historical sprite catalog and its on-disk files."""

import asyncio
import json
import os
from pathlib import Path

import asyncpg


async def main() -> None:
    dsn = os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://")
    db = await asyncpg.connect(dsn, command_timeout=600)
    try:
        totals = await db.fetchrow("""
            SELECT count(*) AS fields,
                count(*) FILTER (WHERE status='null') AS null_fields,
                count(*) FILTER (WHERE status='pending') AS pending,
                count(*) FILTER (WHERE status='downloaded') AS downloaded,
                count(*) FILTER (WHERE status='download_failed') AS download_failed,
                count(*) FILTER (WHERE status='corrupt') AS corrupt,
                count(DISTINCT source_url) AS unique_urls,
                count(DISTINCT source_url) FILTER (WHERE status='downloaded') AS downloaded_urls,
                count(DISTINCT checksum) FILTER (WHERE status='downloaded') AS unique_hashes,
                count(DISTINCT local_path) FILTER
                    (WHERE status='downloaded' AND local_path NOT LIKE 'version-sprites/%')
                    AS existing_media_files_reused,
                count(*) FILTER (WHERE status='downloaded' AND frame_count > 1) AS animated_references
            FROM version_sprite
        """)
        by_generation = await db.fetch("""
            SELECT generation,
                count(*) FILTER (WHERE source_url IS NOT NULL) AS url_references,
                count(*) FILTER (WHERE status='null') AS null_fields,
                count(*) FILTER (WHERE status='downloaded') AS downloaded,
                count(*) FILTER (WHERE status='pending') AS pending,
                count(*) FILTER (WHERE status='download_failed') AS download_failed,
                count(*) FILTER (WHERE status='corrupt') AS corrupt,
                count(DISTINCT source_url) AS unique_urls,
                count(DISTINCT checksum) FILTER (WHERE status='downloaded') AS unique_hashes,
                count(*) FILTER (WHERE status='downloaded' AND format='gif') AS gif_references,
                count(*) FILTER (WHERE status='downloaded' AND frame_count > 1) AS animated_references
            FROM version_sprite GROUP BY generation ORDER BY generation
        """)
        by_game = await db.fetch("""
            SELECT generation, game, count(*) FILTER (WHERE status='downloaded') AS downloaded,
                count(*) FILTER (WHERE status='null') AS null_fields,
                count(*) FILTER (WHERE status='download_failed') AS download_failed,
                count(*) FILTER (WHERE status='corrupt') AS corrupt
            FROM version_sprite GROUP BY generation, game ORDER BY generation, game
        """)
        by_format = await db.fetch("""
            SELECT format, count(*) AS references, count(DISTINCT source_url) AS unique_urls,
                count(DISTINCT checksum) AS unique_hashes
            FROM version_sprite WHERE status='downloaded'
            GROUP BY format ORDER BY format
        """)
        failures = await db.fetch("""
            SELECT source_url, status, error, max(attempts) AS attempts,
                count(*) AS references
            FROM version_sprite WHERE status IN ('download_failed', 'corrupt')
            GROUP BY source_url, status, error ORDER BY references DESC, source_url
        """)
        root = Path(os.environ.get("MEDIA_ROOT", "/app/media")) / "version-sprites"
        files = list(root.rglob("*")) if root.exists() else []
        files = [
            path for path in files if path.is_file() and not path.name.endswith(".part")
        ]
        disk = {
            "files": len(files),
            "bytes": sum(path.stat().st_size for path in files),
        }
        result = {
            "totals": dict(totals),
            "byGeneration": [dict(row) for row in by_generation],
            "byGame": [dict(row) for row in by_game],
            "byFormat": [dict(row) for row in by_format],
            "failures": [dict(row) for row in failures],
            "newDisk": disk,
        }
        print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
    finally:
        await db.close()


asyncio.run(main())
