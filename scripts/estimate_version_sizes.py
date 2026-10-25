"""Read-only stratified HEAD sample for historical sprite disk estimate."""

import asyncio
import json
import os
import random
from collections import defaultdict
from pathlib import PurePosixPath
from statistics import mean, median
from urllib.parse import urlsplit

import asyncpg
import httpx


def urls(value):
    if isinstance(value, dict):
        for child in value.values():
            yield from urls(child)
    elif isinstance(value, str) and value.startswith("https://"):
        yield value


async def main():
    dsn = os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://")
    db = await asyncpg.connect(dsn)
    try:
        by_format = defaultdict(set)
        for table in ("pokemon", "pokemon_form"):
            for row in await db.fetch(f"SELECT sprites FROM {table}"):
                sprites = row["sprites"]
                if isinstance(sprites, str):
                    sprites = json.loads(sprites)
                for url in urls((sprites or {}).get("versions") or {}):
                    by_format[PurePosixPath(urlsplit(url).path).suffix.lower().lstrip(".")].add(url)
    finally:
        await db.close()
    rng = random.Random(20261023)
    sample = [(fmt, url) for fmt, source in by_format.items() for url in rng.sample(sorted(source), min(30, len(source)))]
    semaphore = asyncio.Semaphore(10)
    async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
        async def head(fmt, url):
            async with semaphore:
                try:
                    response = await client.head(url)
                    response.raise_for_status()
                    return fmt, int(response.headers["content-length"])
                except Exception:
                    return fmt, None
        results = await asyncio.gather(*(head(fmt, url) for fmt, url in sample))
    totals = {}
    for fmt, source in by_format.items():
        sizes = [size for kind, size in results if kind == fmt and size is not None]
        totals[fmt] = {
            "uniqueUrls": len(source), "sampleCount": len(sizes), "sampleFailures": 30-len(sizes),
            "meanBytes": round(mean(sizes)) if sizes else None,
            "medianBytes": round(median(sizes)) if sizes else None,
            "estimatedBytes": round(mean(sizes)*len(source)) if sizes else None,
        }
    print(json.dumps(totals, indent=2))


asyncio.run(main())
