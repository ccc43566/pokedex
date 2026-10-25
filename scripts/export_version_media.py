"""Export version-sprite API snapshots for the unchanged 8080 + Nuxt 3000 preview."""

import asyncio
import json
import os
from pathlib import Path

import asyncpg


async def main():
    dsn = os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://")
    output = Path(os.environ.get("VERSION_EXPORT_ROOT", "/tmp/version-media"))
    output.mkdir(parents=True, exist_ok=True)
    only_id = os.environ.get("VERSION_EXPORT_ID")
    db = await asyncpg.connect(dsn)
    try:
        pokemon = await db.fetch(
            "SELECT id, name FROM pokemon WHERE ($1::integer IS NULL OR id=$1) ORDER BY id",
            int(only_id) if only_id else None,
        )
        count = 0
        for entry in pokemon:
            forms = await db.fetch(
                "SELECT id, name FROM pokemon_form WHERE pokemon_id=$1 ORDER BY id", entry["id"]
            )
            form_ids = [form["id"] for form in forms]
            sprites = await db.fetch("""
                SELECT owner_type, owner_id, generation, game, kind, status, format,
                       source_url, local_path, checksum, byte_size, width, height, frame_count
                FROM version_sprite
                WHERE (owner_type='pokemon' AND owner_id=$1)
                   OR (owner_type='form' AND owner_id=ANY($2::integer[]))
                ORDER BY owner_type, owner_id, generation, game, kind
            """, entry["id"], form_ids)
            payload = {
                "pokemonId": entry["id"],
                "owners": [{"ownerType": "pokemon", "ownerId": entry["id"], "name": entry["name"]}]
                          + [{"ownerType": "form", "ownerId": form["id"], "name": form["name"]}
                             for form in forms],
                "sprites": [{
                    "ownerType": row["owner_type"], "ownerId": row["owner_id"],
                    "generation": row["generation"], "game": row["game"],
                    "kind": row["kind"], "status": row["status"], "format": row["format"],
                    "sourceUrl": row["source_url"],
                    "url": f"/media/{row['local_path']}" if row["local_path"] else None,
                    "checksum": row["checksum"], "byteSize": row["byte_size"],
                    "width": row["width"], "height": row["height"],
                    "frameCount": row["frame_count"],
                } for row in sprites],
            }
            (output / f"{entry['id']}.json").write_text(
                json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
            )
            count += 1
        print(json.dumps({"pokemon": count, "directory": str(output)}))
    finally:
        await db.close()


asyncio.run(main())
