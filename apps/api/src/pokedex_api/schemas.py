from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

Locale = Literal["zh-Hans", "en"]


def to_camel(value: str) -> str:
    first, *rest = value.split("_")
    return first + "".join(part.capitalize() for part in rest)


class ApiModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )


class HealthResponse(ApiModel):
    status: str
    database: str
    version: str


class NamedResource(ApiModel):
    id: int
    name: str
    localized_name: str


class PokemonListItem(ApiModel):
    id: int
    name: str
    localized_name: str
    species_id: int | None = None
    national_dex_number: int | None = None
    variant_index: int | None = 0
    is_listed: bool = True
    display_number: str = ""
    variant_label: str = ""
    display_name: str = ""
    sprite_url: str | None = None
    artwork_url: str | None = None
    types: list[NamedResource] = Field(default_factory=list)
    generation_id: int | None = None
    is_legendary: bool = False
    is_mythical: bool = False


class PaginatedPokemon(ApiModel):
    data_version: str | None = None
    items: list[PokemonListItem]
    page: int
    page_size: int
    total: int
    total_pages: int
    has_next: bool
    has_previous: bool


class StatValue(ApiModel):
    name: str
    localized_name: str
    base_stat: int
    effort: int


class AbilityValue(ApiModel):
    id: int
    name: str
    localized_name: str
    effect: str | None = None
    short_effect: str | None = None
    is_hidden: bool = False
    slot: int


class PokemonFormValue(ApiModel):
    id: int
    name: str
    form_name: str | None = None
    is_default: bool = False
    is_battle_only: bool = False
    is_mega: bool = False
    sprite_url: str | None = None


class EvolutionNodeOut(ApiModel):
    species_id: int
    name: str
    localized_name: str
    is_baby: bool = False
    condition: dict[str, Any] = Field(default_factory=dict)
    conditions: list[dict[str, Any]] = Field(default_factory=list)
    pokemon_id: int | None = None
    form_key: str | None = None
    display_number: str = ""
    display_name: str = ""
    sprite_url: str | None = None
    children: list[EvolutionNodeOut] = Field(default_factory=list)


class EvolutionGraphNode(ApiModel):
    key: str
    species_id: int
    pokemon_id: int
    form_id: int | None = None
    form_key: str
    name: str
    label: str
    display_number: str
    sprite_url: str | None = None
    is_current: bool = False
    is_baby: bool = False
    query: dict[str, str] = Field(default_factory=dict)


class EvolutionConditionSource(ApiModel):
    kind: str
    label: str
    url: str | None = None
    content_hash: str | None = None


class EvolutionMethodExplanation(ApiModel):
    rule_version: str
    status: Literal["explained", "partial"] = "explained"
    conditions: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    trigger_label: str = ""
    trigger_name_origin: str = "identifier"
    version_label: str | None = None
    version_group: dict[str, Any] | None = None
    is_default: bool | None = None
    sources: list[EvolutionConditionSource] = Field(default_factory=list)
    variables: list[dict[str, Any]] = Field(default_factory=list)
    supplements: list[dict[str, Any]] = Field(default_factory=list)
    unresolved: list[str] = Field(default_factory=list)


class EvolutionGraphEdge(ApiModel):
    key: str
    source: str
    target: str
    # OR between methods; every field within a method is kept together (AND).
    methods: list[dict[str, Any]] = Field(default_factory=list)
    method_explanations: list[EvolutionMethodExplanation] = Field(default_factory=list)


class EvolutionGraph(ApiModel):
    nodes: list[EvolutionGraphNode] = Field(default_factory=list)
    edges: list[EvolutionGraphEdge] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    source_url: str | None = None


class MediaAssetOut(ApiModel):
    kind: str
    url: str
    width: int | None = None
    height: int | None = None


class VersionSpriteOwner(ApiModel):
    owner_type: Literal["pokemon", "form"]
    owner_id: int
    name: str


class VersionSpriteOut(ApiModel):
    owner_type: Literal["pokemon", "form"]
    owner_id: int
    generation: str
    game: str
    kind: str
    status: Literal["null", "pending", "downloaded", "download_failed", "corrupt"]
    format: str | None = None
    source_url: str | None = None
    url: str | None = None
    checksum: str | None = None
    byte_size: int | None = None
    width: int | None = None
    height: int | None = None
    frame_count: int | None = None


class PokemonVersionMedia(ApiModel):
    pokemon_id: int
    owners: list[VersionSpriteOwner]
    sprites: list[VersionSpriteOut]


class PokemonFormOption(ApiModel):
    key: str
    pokemon_id: int
    form_id: int | None = None
    name: str
    label: str
    form_label: str
    display_number: str
    is_listed: bool = True
    is_default: bool = False
    sprite_url: str | None = None
    artwork_url: str | None = None
    types: list[NamedResource] = Field(default_factory=list)
    sources: list[VersionSpriteOwner] = Field(default_factory=list)


class StatChange(ApiModel):
    generation_id: int
    name: str
    localized_name: str
    previous_name: str
    previous_localized_name: str
    old_value: int
    new_value: int
    is_split: bool = False


class PokemonDetail(PokemonListItem):
    height: int | None = None
    weight: int | None = None
    base_experience: int | None = None
    order: int | None = None
    is_default: bool = True
    description: str | None = None
    genus: str | None = None
    abilities: list[AbilityValue] = Field(default_factory=list)
    stats: list[StatValue] = Field(default_factory=list)
    base_stat_total: int = 0
    egg_groups: list[NamedResource] = Field(default_factory=list)
    gender_rate: int | None = None
    stat_changes: list[StatChange] = Field(default_factory=list)
    stat_history_available: bool = False
    forms: list[PokemonFormValue] = Field(default_factory=list)
    form_options: list[PokemonFormOption] = Field(default_factory=list)
    evolution_chain: list[EvolutionNodeOut] = Field(default_factory=list)
    evolution_graph: EvolutionGraph = Field(default_factory=EvolutionGraph)
    media: list[MediaAssetOut] = Field(default_factory=list)


class TypeSummary(ApiModel):
    id: int
    name: str
    localized_name: str


class TypeDetail(TypeSummary):
    damage_relations: dict[str, list[NamedResource]] = Field(default_factory=dict)
    past_damage_relations: list[dict[str, Any]] = Field(default_factory=list)


class AbilityDetail(ApiModel):
    id: int
    name: str
    localized_name: str
    generation_id: int | None = None
    is_main_series: bool = True
    effect: str | None = None
    short_effect: str | None = None
    flavor_text: str | None = None


class GenerationSummary(ApiModel):
    id: int
    name: str
    localized_name: str
    main_region: str | None = None
    species_count: int = 0


class SearchSuggestion(ApiModel):
    id: int
    name: str
    localized_name: str
    sprite_url: str | None = None
