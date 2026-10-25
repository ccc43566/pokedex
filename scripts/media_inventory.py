"""Read-only Docker media audit. Run by piping this file to `docker compose exec -T api python -`."""

import asyncio
import json
import os
from collections import defaultdict
from pathlib import Path
from statistics import median

import asyncpg


async def main() -> None:
    dsn = os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://")
    connection = await asyncpg.connect(dsn)
    try:
        rows = await connection.fetch("""
            SELECT s.generation_id, p.id AS pokemon_id, m.kind, m.local_path
            FROM pokemon p
            JOIN pokemon_species s ON s.id = p.species_id
            LEFT JOIN media_asset m ON m.pokemon_id = p.id AND m.local_path IS NOT NULL
            ORDER BY s.generation_id, p.id
        """)
    finally:
        await connection.close()

    root = Path(os.environ.get("MEDIA_ROOT", "/app/media"))
    pokemon_by_generation = defaultdict(set)
    image_by_generation = defaultdict(set)
    files_by_kind = defaultdict(list)
    missing_paths = []
    for row in rows:
        generation = row["generation_id"]
        pokemon_id = row["pokemon_id"]
        pokemon_by_generation[generation].add(pokemon_id)
        relative = row["local_path"]
        if not relative:
            continue
        path = root / relative
        if not path.is_file():
            missing_paths.append(relative)
            continue
        image_by_generation[generation].add(pokemon_id)
        files_by_kind[row["kind"]].append(path.stat().st_size)

    disk_files = [path for path in root.rglob("*") if path.is_file()]
    result = {
        "volume": {
            "file_count": len(disk_files),
            "bytes": sum(path.stat().st_size for path in disk_files),
        },
        "generations": [
            {
                "id": generation,
                "pokemon": len(pokemon_by_generation[generation]),
                "with_local_image": len(image_by_generation[generation]),
                "missing_pokemon_ids": sorted(pokemon_by_generation[generation] - image_by_generation[generation]),
            }
            for generation in sorted(pokemon_by_generation)
        ],
        "registered_missing_files": len(missing_paths),
        "examples_of_missing_files": missing_paths[:10],
        "kinds": {
            kind: {
                "files": len(sizes),
                "total_bytes": sum(sizes),
                "median_bytes": int(median(sizes)),
                "p90_bytes": sorted(sizes)[int((len(sizes) - 1) * 0.9)],
                "max_bytes": max(sizes),
            }
            for kind, sizes in sorted(files_by_kind.items())
        },
    }
    print(json.dumps(result, ensure_ascii=False))


asyncio.run(main())
