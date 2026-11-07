"""One naming policy for cards, form choices and evolution vertices.

English text is the seed, not permission to discard structured identifier qualifiers.
Only the Minior Core terminology needs a species-specific presentation convention.
"""

from __future__ import annotations

import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pokedex_api.models import (
    Ability,
    LocalizedName,
    Pokemon,
    PokemonAbility,
    PokemonForm,
    PokemonSpecies,
)

REGIONS = {"alola": "Alolan", "galar": "Galarian", "hisui": "Hisuian", "paldea": "Paldean"}
WORDS = {**REGIONS, "gmax": "Gigantamax", "phd": "Ph.D.", "starter": "Partner"}
ALIASES = {**{k: v.lower() for k, v in WORDS.items()}, "ph.d.": "phd"}
# pokemon-form identifiers specify the enclosed core colour even in Meteor state.
# Existing English names of the corresponding exposed-core records supply “Core”.
MINIOR_CORE_COLOURS = {"red", "orange", "yellow", "green", "blue", "indigo", "violet"}


def english_name(entries: list[dict[str, Any]]) -> str:
    return next(
        (str(n.get("name", "")) for n in entries if n.get("language", {}).get("name") == "en"), ""
    )


def readable_slug(value: str) -> str:
    return " ".join(WORDS.get(word, word.title()) for word in value.split("-") if word)


def terms(value: str) -> list[str]:
    value = unicodedata.normalize("NFKD", value)
    value = "".join(char for char in value if not unicodedata.combining(char))
    value = value.casefold().replace("ph.d.", "phd").replace("pa’u", "pau")
    value = (
        value.replace("???", " unknown ").replace("!", " exclamation ").replace("?", " question ")
    )
    return [ALIASES.get(w, w) for w in re.findall(r"[a-z]+|\d+", value)]


def suffix(pokemon: Pokemon, species: PokemonSpecies) -> str:
    return pokemon.name.removeprefix(species.name).strip("-")


def form_label(
    form: PokemonForm | None,
    species_name: str,
    fallback: str,
    *,
    species_slug: str = "",
    excluded: tuple[str, ...] = (),
) -> str:
    def clean(value: str) -> str:
        value = re.sub(re.escape(species_name), "", value, flags=re.IGNORECASE)
        for ability in excluded:
            value = re.sub(re.escape(ability).replace(r"\-", "[- ]"), "", value, flags=re.I)
            value = re.sub(re.escape(readable_slug(ability)), "", value, flags=re.I)
        value = re.sub(r"\s+(Form|Style)$", "", value, flags=re.I)
        value = " ".join(value.strip(" -()").split())
        return "" if value.lower() == "default" else value

    raw = (form.raw_payload or {}) if form else {}
    prefix = species_slug or species_name.lower().replace(" ", "-")
    structural = "-".join(
        part.removeprefix(prefix).strip("-")
        for part in [form.form_name or "" if form else "", fallback]
        if part
    )
    for ability in excluded:
        structural = re.sub(rf"(^|-){re.escape(ability)}(?=-|$)", "-", structural)
    primary = clean(english_name(raw.get("form_names") or []))
    full = clean(english_name(raw.get("names") or []))
    label = primary or full or readable_slug(clean(structural))
    # Full names often qualify a generic Gigantamax seed (e.g. Single Strike).
    if primary == "Gigantamax" and full:
        label = full
    tokens = list(dict.fromkeys(structural.split("-")))
    if species_slug == "minior" and "meteor" in tokens:
        colour = next((word for word in tokens if word in MINIOR_CORE_COLOURS), None)
        if colour:
            return f"Meteor · {colour.title()} Core"
    for token in tokens:
        if not token or token == "default" or set(terms(token)) <= set(terms(label)):
            continue
        readable = readable_slug(token)
        if token in REGIONS or token in {"mega", "primal", "gmax"}:
            label = f"{readable} {label}".strip()
        elif token in {"zen", "standard"}:
            label = f"{label} {readable} Mode".strip()
        else:
            label = f"{label} {readable}".strip()
    return label


@dataclass
class Names:
    pokemon: dict[int, Pokemon]
    species: dict[int, PokemonSpecies]
    forms: dict[int, list[PokemonForm]]
    base: dict[int, str]
    english: dict[int, str]
    configurations: dict[int, str]

    def label(self, pokemon: Pokemon, form: PokemonForm | None) -> str:
        species = self.species[pokemon.species_id or pokemon.id]
        config = self.configurations.get(pokemon.id, "")
        identifier = suffix(pokemon, species)
        if form and not form.is_default and form.form_name:
            # A cosmetic form supplies its own appearance (including sex/colour).
            # Only shared regional/battle context is inherited from its owner record.
            identifier = "-".join(
                token
                for token in identifier.split("-")
                if token in REGIONS or token in {"mega", "gmax", "primal", "totem"}
            )
        label = form_label(
            form,
            self.english[species.id],
            identifier,
            species_slug=species.name,
            excluded=(config,) if config else (),
        )
        if config:
            tag = readable_slug(config)
            label = f"{label} · {tag}" if label else tag
        return label

    def display(self, pokemon: Pokemon, form: PokemonForm | None) -> str:
        label = self.label(pokemon, form)
        base = self.base[pokemon.species_id or pokemon.id]
        return f"{base}（{label}）" if label else base


async def load_names(session: AsyncSession, species_ids: list[int], locale: str) -> Names:
    """Load COMPLETE families so ability qualifiers never depend on filters/pages."""
    species = {
        s.id: s
        for s in (
            await session.scalars(select(PokemonSpecies).where(PokemonSpecies.id.in_(species_ids)))
        ).all()
    }
    pokemon = {
        p.id: p
        for p in (
            await session.scalars(select(Pokemon).where(Pokemon.species_id.in_(species_ids)))
        ).all()
    }
    forms: dict[int, list[PokemonForm]] = defaultdict(list)
    for f in (
        await session.scalars(
            select(PokemonForm)
            .where(PokemonForm.pokemon_id.in_(pokemon))
            .order_by(PokemonForm.is_default.desc(), PokemonForm.id)
        )
    ).all():
        if f.pokemon_id is not None:
            forms[f.pokemon_id].append(f)
    names: dict[int, dict[str, str]] = defaultdict(dict)
    for n in (
        await session.scalars(
            select(LocalizedName)
            .where(
                LocalizedName.entity_type == "pokemon-species",
                LocalizedName.entity_id.in_(species_ids),
                LocalizedName.locale.in_([locale, "en"]),
            )
            .order_by(LocalizedName.id)
        )
    ).all():
        names[n.entity_id][n.locale] = n.name
    english = {
        sid: names[sid].get("en")
        or english_name((s.raw_payload or {}).get("names") or [])
        or readable_slug(s.name)
        for sid, s in species.items()
    }
    base = {sid: names[sid].get(locale) or english[sid] for sid in species}
    abilities: dict[int, list[str]] = defaultdict(list)
    for pid, name in (
        await session.execute(
            select(PokemonAbility.pokemon_id, Ability.name)
            .join(Ability, PokemonAbility.ability_id == Ability.id)
            .where(PokemonAbility.pokemon_id.in_(pokemon))
        )
    ).all():
        abilities[pid].append(name)
    explicit: dict[int, tuple[str, ...]] = {}
    shapes: dict[tuple[int, tuple[str, ...]], list[Pokemon]] = defaultdict(list)
    for p in pokemon.values():
        sid = p.species_id or p.id
        preferred = forms[p.id][0] if forms[p.id] else None
        identifier = "-".join(
            [suffix(p, species[sid]), preferred.form_name or "" if preferred else ""]
        )
        selectors = tuple(
            a for a in abilities[p.id] if re.search(rf"(^|-){re.escape(a)}(?=-|$)", identifier)
        )
        explicit[p.id] = selectors
        shape = form_label(
            preferred,
            english[sid],
            suffix(p, species[sid]),
            species_slug=species[sid].name,
            excluded=selectors,
        )
        shapes[(sid, tuple(sorted(terms(shape))))].append(p)
    configs: dict[int, str] = {}
    for group in shapes.values():
        if not any(explicit[p.id] for p in group):
            continue
        distinct = {tuple(sorted(abilities[p.id])) for p in group}
        for p in group:
            selectors = explicit[p.id]
            if len(selectors) == 1:
                configs[p.id] = selectors[0]
            elif len(group) > 1 and len(distinct) > 1 and len(abilities[p.id]) == 1:
                configs[p.id] = abilities[p.id][0]
    return Names(pokemon, species, forms, base, english, configs)


def search_terms(value: str) -> list[str]:
    return re.findall(r"[\w]+", value.casefold().replace("ph.d.", "phd").replace("pa’u", "pau"))


async def matching_name_ids(session: AsyncSession, query: str, locale: str) -> list[int]:
    species_ids = list((await session.scalars(select(PokemonSpecies.id))).all())
    context = await load_names(session, species_ids, locale)
    needles = search_terms(query)
    matches = []
    for p in context.pokemon.values():
        sid = p.species_id or p.id
        appearances: list[PokemonForm | None] = [*context.forms[p.id]] or [None]
        for form in appearances:
            haystack = " ".join(
                [p.name, context.english[sid], context.display(p, form), form.name if form else ""]
            )
            if needles and set(needles) <= set(search_terms(haystack)):
                matches.append(p.id)
                break
    return matches
