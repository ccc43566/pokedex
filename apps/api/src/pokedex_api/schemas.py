
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
    sprite_url: str | None = None
    artwork_url: str | None = None
    types: list[NamedResource] = Field(default_factory=list)
    generation_id: int | None = None
    is_legendary: bool = False
    is_mythical: bool = False


class PaginatedPokemon(ApiModel):
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
    children: list[EvolutionNodeOut] = Field(default_factory=list)


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
    forms: list[PokemonFormValue] = Field(default_factory=list)
    evolution_chain: list[EvolutionNodeOut] = Field(default_factory=list)
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
