"""Precomputed name tokens/identities and bounded, version-aware process caches.

The database revision is read for every list request, including cache hits. A
worker never serves another revision's entries. Requests do not write snapshots;
startup and sync/CLI publish them atomically. Missing snapshots rebuild in memory
once per revision/worker so failed maintenance does not disable search.
"""

from __future__ import annotations

import asyncio
import time
from collections import OrderedDict
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar
from weakref import WeakKeyDictionary

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from pokedex_api.models import PokemonForm, PokemonSearchIndex, PokemonSearchVersion, PokemonSpecies
from pokedex_api.services.catalog import identities
from pokedex_api.services.names import load_names, search_terms

T = TypeVar("T")
INDEX_FORMAT = 1


class SearchCache:
    def __init__(self, capacity: int = 128, ttl: float = 120) -> None:
        self.capacity = capacity
        self.ttl = ttl
        self.values: OrderedDict[tuple[Any, ...], tuple[float, Any]] = OrderedDict()
        self.locks: dict[tuple[Any, ...], asyncio.Lock] = {}

    async def load(self, key: tuple[Any, ...], build: Callable[[], Awaitable[T]]) -> T:
        # Keep the producer in its request's session/lifetime. Cancellation
        # releases the lock and a waiter can retry; no detached session users.
        lock = self.locks.setdefault(key, asyncio.Lock())
        try:
            async with lock:
                entry = self.values.get(key)
                if entry and entry[0] > time.monotonic():
                    self.values.move_to_end(key)
                    return entry[1]  # type: ignore[no-any-return]
                value = await build()
                self.values[key] = (time.monotonic() + self.ttl, value)
                self.values.move_to_end(key)
                while len(self.values) > self.capacity:
                    self.values.popitem(last=False)
                return value
        finally:
            # Do not replace a lock while waiters still hold references to it.
            if not lock.locked() and not getattr(lock, "_waiters", None):
                self.locks.pop(key, None)


class WorkerCaches:
    def __init__(self) -> None:
        self.index = SearchCache(capacity=4, ttl=3600)
        self.results = SearchCache()


_workers: WeakKeyDictionary[Any, WorkerCaches] = WeakKeyDictionary()


def worker(session: AsyncSession) -> WorkerCaches:
    bind = session.get_bind()
    if bind not in _workers:
        _workers[bind] = WorkerCaches()
    return _workers[bind]


async def data_version(session: AsyncSession) -> str:
    version = await session.scalar(
        select(PokemonSearchVersion.version).where(PokemonSearchVersion.id == 1)
    )
    if version is None:
        raise RuntimeError("Missing Pokémon search version; run alembic upgrade head")
    return version


async def build_index(session: AsyncSession, locale: str) -> dict[str, Any]:
    species_ids = list((await session.scalars(select(PokemonSpecies.id))).all())
    context = await load_names(session, species_ids, locale)
    # Each appearance retains its own token set: words from different cosmetic
    # forms must never accidentally combine into a new match.
    tokens: dict[str, list[list[str]]] = {}
    for p in context.pokemon.values():
        appearances: list[PokemonForm | None] = list(context.forms[p.id]) or [None]
        sid = p.species_id or p.id
        tokens[str(p.id)] = [
            sorted(
                set(
                    search_terms(
                        " ".join(
                            [
                                p.name,
                                context.english[sid],
                                context.display(p, form),
                                form.name if form else "",
                            ]
                        )
                    )
                )
            )
            for form in appearances
        ]
    display = await identities(session, list(context.pokemon), locale, context)
    return {
        "format": INDEX_FORMAT,
        "tokens": tokens,
        "identities": {str(k): v for k, v in display.items()},
    }


async def search_index(session: AsyncSession, locale: str, version: str) -> dict[str, Any]:
    async def load() -> dict[str, Any]:
        payload = await session.scalar(
            select(PokemonSearchIndex.payload).where(
                PokemonSearchIndex.locale == locale,
                PokemonSearchIndex.version == version,
            )
        )
        if payload is not None and payload.get("format") == INDEX_FORMAT:
            return dict(payload)
        return await build_index(session, locale)

    return await worker(session).index.load((INDEX_FORMAT, locale, version), load)


def matching_ids(index: dict[str, Any], query: str) -> list[int]:
    needles = set(search_terms(query))
    if not needles:
        return []
    return [
        int(pid)
        for pid, forms in index["tokens"].items()
        if any(needles.issubset(tokens) for tokens in forms)
    ]


async def rebuild_indexes(session: AsyncSession, *, force: bool = False) -> str:
    if session.get_bind().dialect.name == "postgresql":
        await session.execute(text("SELECT pg_advisory_xact_lock(709150007)"))
    version = await data_version(session)
    # Lock the revision row: source writes either precede this snapshot or
    # invalidate it after commit, including writes in another API/sync process.
    await session.execute(select(PokemonSearchVersion).with_for_update())
    version = await data_version(session)
    for locale in ("zh-Hans", "en"):
        existing = await session.get(PokemonSearchIndex, locale)
        if (
            not force
            and existing
            and existing.version == version
            and existing.payload.get("format") == INDEX_FORMAT
        ):
            continue
        payload = await build_index(session, locale)
        if existing:
            existing.version, existing.payload = version, payload
        else:
            session.add(PokemonSearchIndex(locale=locale, version=version, payload=payload))
    await session.flush()
    return version
