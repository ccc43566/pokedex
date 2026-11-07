"""Compare the legacy algorithm and indexed API in the SAME process/database.

Run via search_check_env.py against the disposable PostgreSQL database.
The legacy function is reconstructed from the unchanged list/filter path by
replacing only the two optimized name operations. No source data is written.
"""

import asyncio
import inspect
import json
import statistics
import sys
import time
from pathlib import Path

from httpx import ASGITransport, AsyncClient
from pokedex_api.db import engine
from pokedex_api.main import app
from pokedex_api.services import pokemon, search_index
from pokedex_api.services.names import matching_name_ids


async def main() -> None:
    original = pokemon.list_pokemon
    source = inspect.getsource(pokemon._list_pokemon)
    source = source.replace(
        "    index = await search_index(session, locale, version)\n", ""
    )
    source = source.replace(
        "matching_ids(index, q)", "await matching_name_ids(session, q, locale)"
    )
    source = source.replace(
        'display = {pid: index["identities"][str(pid)] for pid in ids}',
        "display = await identities(session, ids, locale)",
    )
    namespace = {**vars(pokemon), "matching_name_ids": matching_name_ids}
    # Trusted local source only, to retain exactly the current SQL/filter path.
    exec(compile(source, "<legacy-list-benchmark>", "exec"), namespace)  # noqa: S102

    async def legacy(session, **kwargs):
        return await namespace["_list_pokemon"](session, version="", **kwargs)

    queries = ["皮卡", "Pikachu", "Mega Female", "Galarian Zen Mode", "25"]
    report = {
        "environment": "same Python process, ASGI HTTP, PostgreSQL search-check copy",
        "runs": 4,
        "results": {},
    }
    try:
        async with AsyncClient(
            transport=ASGITransport(app), base_url="http://benchmark"
        ) as client:
            for query in queries:
                entry = {}
                expected = None
                for name, implementation in [("before", legacy), ("after", original)]:
                    pokemon.list_pokemon = implementation
                    search_index._workers.clear()
                    times = []
                    for _ in range(4):
                        start = time.perf_counter()
                        response = await client.get(
                            "/api/v1/pokemon",
                            params={
                                "q": query,
                                "locale": "zh-Hans",
                                "pageSize": 48,
                            },
                        )
                        response.raise_for_status()
                        times.append(round((time.perf_counter() - start) * 1000, 2))
                        payload = response.json()
                        payload.pop("dataVersion", None)
                        if expected is None:
                            expected = payload
                        assert payload == expected, (query, name, "result changed")
                    entry[name] = {
                        "first_ms": times[0],
                        "repeat_median_ms": statistics.median(times[1:]),
                        "all_ms": times,
                    }
                report["results"][query] = entry
        output = (
            Path(__file__).resolve().parents[2]
            / "migration-audit/search-same-environment.json"
        )
        output.write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        sys.stdout.reconfigure(encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False, indent=2))
    finally:
        pokemon.list_pokemon = original
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
