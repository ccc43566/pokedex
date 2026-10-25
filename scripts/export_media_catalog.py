"""Print every registered, locally stored image as JSON from inside the API container.

Example (PowerShell, from repository root):
  Get-Content -Raw scripts/export_media_catalog.py | docker compose exec -T api python - > apps/web/public/image-review/data.json
"""

import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import asyncpg


async def main() -> None:
    dsn = os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://")
    connection = await asyncpg.connect(dsn)
    try:
        rows = await connection.fetch("""
            SELECT m.id, m.pokemon_id, m.form_id, m.kind, m.local_path,
                   m.width, m.height, m.checksum,
                   s.id AS species_id, s.name AS species_name, s.generation_id,
                   COALESCE(p.name, owner_p.name) AS pokemon_name,
                   COALESCE(pf.name, p.name) AS image_owner_name,
                   names.name AS chinese_name
            FROM media_asset m
            LEFT JOIN pokemon p ON p.id = m.pokemon_id
            LEFT JOIN pokemon_form pf ON pf.id = m.form_id
            LEFT JOIN pokemon owner_p ON owner_p.id = pf.pokemon_id
            LEFT JOIN pokemon_species s
              ON s.id = COALESCE(p.species_id, owner_p.species_id)
            LEFT JOIN LATERAL (
              SELECT ln.name FROM localized_name ln
              WHERE ln.entity_type = 'pokemon-species'
                AND ln.entity_id = s.id AND ln.locale = 'zh-Hans'
              ORDER BY ln.is_canonical DESC, ln.id
              LIMIT 1
            ) names ON true
            WHERE m.local_path IS NOT NULL
            ORDER BY m.id
        """)
    finally:
        await connection.close()

    root = Path(os.environ.get("MEDIA_ROOT", "/app/media"))
    records = []
    missing = []
    for row in rows:
        relative = row["local_path"]
        path = root / relative
        if not path.is_file():
            missing.append(relative)
            continue
        records.append({
            "id": row["id"],
            "pokemonId": row["pokemon_id"],
            "formId": row["form_id"],
            "speciesId": row["species_id"],
            "generation": row["generation_id"],
            "chineseName": row["chinese_name"],
            "speciesName": row["species_name"],
            "pokemonName": row["pokemon_name"],
            "ownerName": row["image_owner_name"],
            "kind": row["kind"],
            "width": row["width"],
            "height": row["height"],
            "bytes": path.stat().st_size,
            "path": relative,
            "checksum": row["checksum"],
        })

    records.sort(key=lambda item: (-item["bytes"], item["path"]))
    print(json.dumps({
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "count": len(records),
        "missingPaths": missing,
        "sort": "bytes descending, path ascending",
        "images": records,
    }, ensure_ascii=False, separators=(",", ":")))


asyncio.run(main())
