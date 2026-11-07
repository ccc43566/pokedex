"""Unify content references while retaining legacy URLs as physical hard links.

Standalone: pipe this module into the API container's ``python - [--apply]``.
All registered bytes are checked before changing files or database references.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
from collections import defaultdict
from pathlib import Path
from uuid import uuid4

import asyncpg  # type: ignore[import-untyped]

SYNC_LOCK_KEY = 73150821920261026


def link_alias(source: Path, destination: Path) -> bool:
    """Replace a verified identical alias atomically; its URL keeps working."""
    if destination.exists() and source.samefile(destination):
        return False
    temporary = destination.with_name(f"{destination.name}.{uuid4().hex}.link")
    try:
        os.link(source, temporary)
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
    return True


async def deduplicate(*, database_url: str, media_root: Path, apply: bool) -> dict[str, object]:
    root = await asyncio.to_thread(media_root.resolve)
    db = await asyncpg.connect(
        database_url.replace("postgresql+asyncpg://", "postgresql://"), command_timeout=600
    )
    try:
        if not await db.fetchval("SELECT pg_try_advisory_lock($1)", SYNC_LOCK_KEY):
            raise RuntimeError("Another version sprite or media maintenance task is running")
        rows = await db.fetch("""
            SELECT checksum,local_path FROM media_asset WHERE local_path IS NOT NULL
            UNION
            SELECT checksum,local_path FROM version_sprite WHERE status='downloaded'
        """)
        groups: dict[str, set[str]] = defaultdict(set)
        checked: dict[str, str] = {}
        for row in rows:
            relative, expected = row["local_path"], row["checksum"]
            if not relative or not expected:
                raise ValueError("Registered local media is missing its path or checksum")
            path = (root / relative).resolve()
            if not path.is_relative_to(root) or not path.is_file():
                raise ValueError(f"Missing or invalid registered path: {relative}")
            if relative not in checked:
                with path.open("rb") as handle:
                    checked[relative] = hashlib.file_digest(handle, "sha256").hexdigest()
            if checked[relative] != expected:
                raise ValueError(f"Checksum mismatch: {relative}")
            groups[expected].add(relative)

        changed_links = 0
        canonical_created = 0
        canonical_updates = []
        physical_before: dict[tuple[int, int], int] = {}
        for relative in checked:
            stat = (root / relative).stat()
            physical_before[(stat.st_dev, stat.st_ino)] = stat.st_size
        for checksum, aliases in sorted(groups.items()):
            paths = sorted(aliases)
            known = [p for p in paths if p.startswith("version-sprites/")]
            if known:
                canonical = known[0]
            else:
                extension = Path(paths[0]).suffix.lower()
                if extension not in {".png", ".gif", ".webp"}:
                    raise ValueError(f"Unsupported media extension: {paths[0]}")
                canonical = f"version-sprites/{checksum[:2]}/{checksum}{extension}"
            destination = root / canonical
            if destination.exists():
                with destination.open("rb") as handle:
                    if hashlib.file_digest(handle, "sha256").hexdigest() != checksum:
                        raise ValueError(f"Canonical checksum mismatch: {canonical}")
            if apply:
                destination.parent.mkdir(parents=True, exist_ok=True)
                if not destination.exists():
                    os.link(root / paths[0], destination)
                    canonical_created += 1
                for relative in paths:
                    changed_links += int(link_alias(destination, root / relative))
            canonical_updates.append((canonical, checksum))
        if apply:
            async with db.transaction():
                await db.execute("""
                    CREATE TEMP TABLE canonical_media_paths
                    (local_path text, checksum text PRIMARY KEY) ON COMMIT DROP
                """)
                await db.copy_records_to_table(
                    "canonical_media_paths", records=canonical_updates,
                    columns=["local_path", "checksum"],
                )
                await db.execute("""
                    UPDATE media_asset m SET local_path=c.local_path
                    FROM canonical_media_paths c
                    WHERE m.checksum=c.checksum AND m.local_path IS NOT NULL
                    AND m.local_path<>c.local_path
                """)
                await db.execute("""
                    UPDATE version_sprite v SET local_path=c.local_path
                    FROM canonical_media_paths c
                    WHERE v.checksum=c.checksum AND v.status='downloaded'
                    AND v.local_path<>c.local_path
                """)
        unique_bytes = sum((root / next(iter(paths))).stat().st_size for paths in groups.values())
        return {
            "applied": apply,
            "registeredPathsVerified": len(checked),
            "uniqueHashes": len(groups),
            "duplicateHashGroups": sum(len(paths) > 1 for paths in groups.values()),
            "physicalFilesBefore": len(physical_before),
            "physicalBytesBefore": sum(physical_before.values()),
            "uniqueContentBytes": unique_bytes,
            "estimatedBytesSaved": sum(physical_before.values()) - unique_bytes,
            "aliasesRelinked": changed_links,
            "canonicalPathsCreated": canonical_created,
        }
    finally:
        await db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    print(json.dumps(asyncio.run(deduplicate(
        database_url=os.environ["DATABASE_URL"],
        media_root=Path(os.environ.get("MEDIA_ROOT", "/app/media")),
        apply=args.apply,
    )), indent=2))
