"""Resolve species edges to exact stored forms, then project the selected form's component.

No region/name heuristics and no persistence changes. Raw chain payloads preserve every OR
method; the historical normalized table only kept details[0]. Both paths remain readable.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pokedex_api.models import EvolutionChain, EvolutionNode, Pokemon, PokemonForm, PokemonSpecies
from pokedex_api.schemas import (
    EvolutionGraph,
    EvolutionGraphEdge,
    EvolutionGraphNode,
    EvolutionNodeOut,
    PokemonFormOption,
)
from pokedex_api.services.catalog import species_options
from pokedex_api.services.evolution_conditions import explain_method, load_condition_context


def resource_id(resource: Any, kind: str) -> int | None:
    if not isinstance(resource, dict):
        return None
    parts = str(resource.get("url", "")).rstrip("/").split("/")
    return int(parts[-1]) if len(parts) > 1 and parts[-2] == kind and parts[-1].isdigit() else None


async def evolution_graph(
    session: AsyncSession,
    pokemon: Pokemon,
    current: PokemonFormOption,
    *,
    locale: str,
    media_public_path: str,
) -> EvolutionGraph:
    species = await session.get(PokemonSpecies, pokemon.species_id) if pokemon.species_id else None
    chain = (
        await session.get(EvolutionChain, species.evolution_chain_id)
        if species and species.evolution_chain_id is not None
        else None
    )
    source_url = f"https://pokeapi.co/api/v2/evolution-chain/{chain.id}/" if chain else None
    warnings: list[str] = []
    relations: list[tuple[int, int, list[dict[str, Any]]]] = []
    species_ids: set[int] = {pokemon.species_id or pokemon.id}
    babies: set[int] = set()

    def walk(node: dict[str, Any], parent: int | None = None) -> None:
        sid = resource_id(node.get("species"), "pokemon-species")
        if sid is None:
            warnings.append("进化节点缺少有效 species 引用，已跳过。")
            return
        species_ids.add(sid)
        if node.get("is_baby"):
            babies.add(sid)
        if parent is not None:
            details = node.get("evolution_details")
            if isinstance(details, list) and details:
                relations.append((parent, sid, details))
            else:
                warnings.append(f"#{parent} → #{sid} 缺少进化条件，未建立有效连线。")
        for child in node.get("evolves_to") or []:
            walk(child, sid)

    if chain and (chain.raw_payload or {}).get("chain"):
        walk(chain.raw_payload["chain"])
    elif species and species.evolution_chain_id is not None:
        stored = list(
            (
                await session.scalars(
                    select(EvolutionNode).where(
                        EvolutionNode.chain_id == species.evolution_chain_id
                    )
                )
            ).all()
        )
        by_id = {n.id: n for n in stored}
        for node in stored:
            species_ids.add(node.species_id)
            if node.is_baby:
                babies.add(node.species_id)
            if node.parent_id in by_id:
                condition = node.condition or {}
                details = condition.get("alternatives", [condition]) if condition else []
                if details:
                    relations.append((by_id[node.parent_id].species_id, node.species_id, details))
        if stored:
            warnings.append("完整原始进化链缺失；仅使用已保存条件，可能缺少其他可选途径。")

    records = list(
        (
            await session.scalars(
                select(Pokemon)
                .where(Pokemon.species_id.in_(species_ids))
                .order_by(Pokemon.is_default.desc(), Pokemon.id)
            )
        ).all()
    )
    records_by_id = {p.id: p for p in records}
    default_records = {p.species_id: p.id for p in reversed(records) if p.is_default}
    forms = list(
        (
            await session.scalars(
                select(PokemonForm).where(PokemonForm.pokemon_id.in_(records_by_id))
            )
        ).all()
    )
    form_by_id = {f.id: f for f in forms}
    choices: dict[int, list[PokemonFormOption]] = {}
    for sid in sorted(species_ids):
        representative = next((p for p in records if p.species_id == sid), None)
        if representative:
            choices[sid] = await species_options(
                session, representative, locale=locale, media_public_path=media_public_path
            )
    choices.setdefault(pokemon.species_id or pokemon.id, [current])
    all_choices = {o.key: (sid, o) for sid, group in choices.items() for o in group}

    def exact(resource: Any, sid: int) -> list[PokemonFormOption]:
        fid = resource_id(resource, "pokemon-form")
        candidates = [o for o in choices.get(sid, []) if o.form_id == fid] if fid else []
        if not candidates:
            warnings.append(f"#{sid} 的指定形态引用缺失或归属不符，相关进化途径已跳过。")
        return candidates

    def default_target(sid: int) -> list[PokemonFormOption]:
        return [
            o
            for o in choices.get(sid, [])
            if o.pokemon_id == default_records.get(sid) and o.is_default
        ]

    explicitly_evolving = {
        resource_id(method.get("required_pokemon_form"), "pokemon-form")
        for _, _, methods in relations
        for method in methods
        if method.get("required_pokemon_form")
    }

    def unrestricted_sources(sid: int) -> list[PokemonFormOption]:
        # PokéAPI null required form is unspecified/any form. Applying these legacy
        # species-level rules to distinct regional/battle/Totem records gives known
        # invalid evolutions (e.g. Alolan Meowth -> ordinary Persian). Only ordinary
        # appearances within the original record are safe. Non-default appearances
        # must also be explicitly evolution-capable elsewhere in the source data;
        # otherwise even a cosmetic-looking form can be unable to evolve (Spiky Pichu).
        result = []
        for option in choices.get(sid, []):
            form = form_by_id.get(option.form_id) if option.form_id else None
            if (
                option.pokemon_id == default_records.get(sid)
                and option.is_listed
                and not (form and form.is_battle_only)
                and (option.is_default or option.form_id in explicitly_evolving)
            ):
                result.append(option)
        return result

    edge_methods: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for source_sid, target_sid, methods in relations:
        for method in methods:
            sources = (
                exact(method["required_pokemon_form"], source_sid)
                if method.get("required_pokemon_form")
                else unrestricted_sources(source_sid)
            )
            targets = (
                exact(method["evolved_pokemon_form"], target_sid)
                if method.get("evolved_pokemon_form")
                else default_target(target_sid)
            )
            if not sources or not targets:
                warnings.append(f"#{source_sid} → #{target_sid} 无法定位来源或目标形态，已跳过。")
            for source in sources:
                for target in targets:
                    # Do not discard false/0/empty values or nested condition expressions.
                    edge_methods[(source.key, target.key)].append(method)

    # Only the selected appearance of this species may participate. Other species are
    # matched at their OWN source vertices, never against the current species' form.
    allowed = {
        key
        for key, (sid, _) in all_choices.items()
        if sid != pokemon.species_id or key == current.key
    }
    adjacency: dict[str, set[str]] = defaultdict(set)
    for source_key, target_key in edge_methods:
        if source_key in allowed and target_key in allowed:
            adjacency[source_key].add(target_key)
            adjacency[target_key].add(source_key)
    reachable = {current.key}
    frontier = [current.key]
    while frontier:
        for key in adjacency[frontier.pop()] - reachable:
            reachable.add(key)
            frontier.append(key)
    edges = [
        EvolutionGraphEdge(key=f"{s}>{t}", source=s, target=t, methods=methods)
        for (s, t), methods in edge_methods.items()
        if s in reachable and t in reachable
    ]
    if relations and not edges:
        warnings.append(
            "本地进化条件未明确关联当前形态；未套用普通形态的关系。形态变化不等于进化。"
        )
    nodes = [
        EvolutionGraphNode(
            key=key,
            species_id=sid,
            pokemon_id=o.pokemon_id,
            form_id=o.form_id,
            form_key=o.key,
            name=o.name,
            label=o.label,
            display_number=o.display_number,
            sprite_url=o.artwork_url or o.sprite_url,
            is_current=key == current.key,
            is_baby=sid in babies,
            query={} if o.is_default else {"form": o.key},
        )
        for key, (sid, o) in all_choices.items()
        if key in reachable
    ]
    context = await load_condition_context(session, [m for e in edges for m in e.methods], locale)
    nodes_by_key = {node.key: node for node in nodes}
    for edge in edges:
        source_node, target_node = nodes_by_key[edge.source], nodes_by_key[edge.target]
        edge.method_explanations = [
            explain_method(
                method,
                context,
                source_species_id=source_node.species_id,
                target_species_id=target_node.species_id,
                source_label=source_node.label,
                target_label=target_node.label,
            )
            for method in edge.methods
        ]
    return EvolutionGraph(
        nodes=nodes, edges=edges, warnings=list(dict.fromkeys(warnings)), source_url=source_url
    )


def legacy_tree(graph: EvolutionGraph) -> list[EvolutionNodeOut]:
    """Keep the original nested response, now with exact identities and all alternatives."""
    nodes = {node.key: node for node in graph.nodes}
    children: dict[str, list[EvolutionGraphEdge]] = defaultdict(list)
    targets = set()
    for edge in graph.edges:
        children[edge.source].append(edge)
        targets.add(edge.target)

    def build(key: str, methods: list[dict[str, Any]], seen: set[str]) -> EvolutionNodeOut:
        node = nodes[key]
        return EvolutionNodeOut(
            species_id=node.species_id,
            name=node.name,
            localized_name=node.label,
            pokemon_id=node.pokemon_id,
            form_key=node.form_key,
            display_number=node.display_number,
            display_name=node.label,
            sprite_url=node.sprite_url,
            is_baby=node.is_baby,
            condition=methods[0] if methods else {},
            conditions=methods,
            children=[
                build(e.target, e.methods, seen | {key})
                for e in children[key]
                if e.target not in seen | {key}
            ],
        )

    return [build(key, [], set()) for key in nodes if key not in targets]
