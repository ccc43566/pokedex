"""Read-only inventory of stored PokeAPI sprites.versions. Run inside the API container."""

import asyncio
import json
import os
from collections import Counter, defaultdict
from pathlib import PurePosixPath
from urllib.parse import urlsplit

import asyncpg


def leaves(value, prefix=()):
    if isinstance(value, dict):
        for key, child in value.items():
            yield from leaves(child, (*prefix, key))
    elif value is None or isinstance(value, str):
        yield prefix, value


async def main():
    dsn = os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://")
    db = await asyncpg.connect(dsn)
    try:
        records = []
        for owner, table in (("pokemon", "pokemon"), ("form", "pokemon_form")):
            for row in await db.fetch(f"SELECT id, sprites FROM {table} ORDER BY id"):
                sprites = row["sprites"]
                if isinstance(sprites, str):
                    sprites = json.loads(sprites)
                for path, url in leaves((sprites or {}).get("versions") or {}):
                    if len(path) < 3:
                        continue
                    generation, game, *kind = path
                    if url is not None and not url.startswith(("https://", "http://")):
                        continue
                    records.append((owner, row["id"], generation, game, "/".join(kind), url))
    finally:
        await db.close()

    total = Counter()
    groups = defaultdict(lambda: {"urls": 0, "null": 0, "url_set": set()})
    url_refs = Counter()
    owner_counts = Counter()
    for owner, owner_id, generation, game, kind, url in records:
        owner_counts[owner] += 1
        fmt = PurePosixPath(urlsplit(url).path).suffix.lower().lstrip(".") if url else "null"
        group = groups[(generation, game, kind, fmt)]
        if url:
            total["urls"] += 1
            group["urls"] += 1
            group["url_set"].add(url)
            url_refs[url] += 1
        else:
            total["null"] += 1
            group["null"] += 1
    generation_rows = []
    for generation in sorted({record[2] for record in records}):
        subset = [record for record in records if record[2] == generation]
        urls = [record[5] for record in subset if record[5]]
        generation_rows.append({
            "generation": generation,
            "urls": len(urls),
            "null": len(subset) - len(urls),
            "uniqueUrls": len(set(urls)),
            "duplicateUrlReferences": len(urls) - len(set(urls)),
            "games": sorted({record[3] for record in subset}),
        })
    output = {
        "summary": {
            "urlReferences": total["urls"],
            "nullFields": total["null"],
            "uniqueUrls": len(url_refs),
            "duplicateUrlReferences": total["urls"] - len(url_refs),
            "owners": dict(owner_counts),
            "formats": dict(Counter(PurePosixPath(urlsplit(url).path).suffix.lower().lstrip(".") for url in url_refs)),
            "generationCount": len(generation_rows),
            "gameCount": len({record[3] for record in records}),
        },
        "generations": generation_rows,
        "groups": [
            {"generation": generation, "game": game, "kind": kind, "format": fmt,
             "urls": group["urls"], "null": group["null"],
             "uniqueUrls": len(group["url_set"]),
             "duplicateUrlReferences": group["urls"] - len(group["url_set"])}
            for (generation, game, kind, fmt), group in sorted(groups.items())
        ],
        "mostRepeatedUrls": [{"url": url, "references": count} for url, count in url_refs.most_common(20)],
    }
    print(json.dumps(output, ensure_ascii=False))


asyncio.run(main())
