"""Thin browsing DTOs: raw upstream documents stay in PostgreSQL."""

from typing import Any

from pydantic import Field

from pokedex_api.schemas import ApiModel


class CatalogLabel(ApiModel):
    id: int
    name: str
    localized_name: str
    name_locale: str = ""
    resource_type: str = ""
    generation_id: int | None = None


class ReferenceCard(CatalogLabel):
    category: CatalogLabel | None = None
    pocket: CatalogLabel | None = None
    type: CatalogLabel | None = None
    damage_class: CatalogLabel | None = None
    generation: CatalogLabel | None = None
    power: int | None = None
    accuracy: int | None = None
    pp: int | None = None
    priority: int | None = None
    image_url: str | None = None
    image_status: str | None = None


class ReferencePage(ApiModel):
    items: list[ReferenceCard]
    total: int
    page: int
    page_size: int
    total_pages: int


class ReferenceDetail(ApiModel):
    record: ReferenceCard
    texts: list[dict[str, Any]] = Field(default_factory=list)
    fields: dict[str, Any] = Field(default_factory=dict)
    source: dict[str, Any] = Field(default_factory=dict)
    relation_counts: dict[str, int] = Field(default_factory=dict)


class RelationPage(ApiModel):
    items: list[dict[str, Any]]
    total: int
    page: int
    page_size: int
    total_pages: int
