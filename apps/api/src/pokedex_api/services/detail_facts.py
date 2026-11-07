"""Read-only projections of locally mirrored species and historical stat data."""

from __future__ import annotations

import re
from typing import Any

from pokedex_api.schemas import NamedResource, StatChange, StatValue

# PokéAPI egg-group identifiers use older English terms (ground, plant, humanshape).
EGG_GROUPS = {
    "monster": ("怪兽", "Monster"),
    "water1": ("水中1", "Water 1"),
    "bug": ("虫", "Bug"),
    "flying": ("飞行", "Flying"),
    "ground": ("陆上", "Field"),
    "fairy": ("妖精", "Fairy"),
    "plant": ("植物", "Grass"),
    "humanshape": ("人型", "Human-Like"),
    "water3": ("水中3", "Water 3"),
    "mineral": ("矿物", "Mineral"),
    "indeterminate": ("不定形", "Amorphous"),
    "water2": ("水中2", "Water 2"),
    "ditto": ("百变怪", "Ditto"),
    "dragon": ("龙", "Dragon"),
    "no-eggs": ("未发现", "Undiscovered"),
}


def egg_groups(payload: dict[str, Any], locale: str) -> list[NamedResource]:
    result = []
    for entry in payload.get("egg_groups") or []:
        name = entry.get("name", "")
        match = re.search(r"/(\d+)/?$", entry.get("url", ""))
        if not match or not name:
            continue
        labels = EGG_GROUPS.get(name, (name.replace("-", " ").title(),) * 2)
        result.append(
            NamedResource(id=int(match[1]), name=name, localized_name=labels[locale != "zh-Hans"])
        )
    return result


def stat_changes(
    payload: dict[str, Any], current: list[StatValue], names: dict[str, str]
) -> list[StatChange]:
    # Each sparse entry supplies the old value THROUGH its generation, inclusive.
    # The next entry for that same stat (or the current value) supplies its successor.
    history: dict[str, list[tuple[int, int]]] = {}
    for entry in payload.get("past_stats") or []:
        match = re.search(r"/(\d+)/?$", (entry.get("generation") or {}).get("url", ""))
        if not match:
            continue
        generation = int(match[1])
        for stat in entry.get("stats") or []:
            name = (stat.get("stat") or {}).get("name")
            value = stat.get("base_stat")
            if name and isinstance(value, int):
                history.setdefault(name, []).append((generation, value))
    values = {stat.name: stat.base_stat for stat in current}
    result = []
    for previous_name, entries in history.items():
        for generation, old in sorted(set(entries)):
            targets = (
                ("special-attack", "special-defense")
                if previous_name == "special" and generation == 1
                else (previous_name,)
            )
            for name in targets:
                later = sorted((g, v) for g, v in history.get(name, []) if g > generation)
                new = later[0][1] if later else values.get(name)
                split = name != previous_name
                if new is None or (old == new and not split):
                    continue
                result.append(
                    StatChange(
                        generation_id=generation + 1,
                        name=name,
                        localized_name=names.get(name, name),
                        previous_name=previous_name,
                        previous_localized_name=names.get(previous_name, previous_name),
                        old_value=old,
                        new_value=new,
                        is_split=split,
                    )
                )
    return sorted(result, key=lambda change: (change.generation_id, change.name))
