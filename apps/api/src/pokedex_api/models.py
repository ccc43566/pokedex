from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

JsonType = JSON().with_variant(JSONB, "postgresql")


def utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class SourceRecord(Base):
    __tablename__ = "source_record"
    __table_args__ = (UniqueConstraint("resource_type", "resource_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    resource_type: Mapped[str] = mapped_column(String(64), index=True)
    resource_id: Mapped[int] = mapped_column(Integer)
    name: Mapped[str | None] = mapped_column(String(160), index=True, nullable=True)
    source_url: Mapped[str] = mapped_column(Text)
    source_hash: Mapped[str] = mapped_column(String(64), index=True)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JsonType)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SyncRun(Base):
    __tablename__ = "sync_run"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    status: Mapped[str] = mapped_column(String(24), index=True)
    source_hash: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    counts: Mapped[dict[str, Any]] = mapped_column(JsonType, default=dict)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)


class LocalizedName(Base):
    __tablename__ = "localized_name"
    __table_args__ = (
        UniqueConstraint("entity_type", "entity_id", "locale", "name"),
        Index("ix_localized_name_lookup", "entity_type", "entity_id", "locale"),
        Index("ix_localized_name_search", "locale", "name"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(64), index=True)
    entity_id: Mapped[int] = mapped_column(Integer, index=True)
    locale: Mapped[str] = mapped_column(String(16), index=True)
    name: Mapped[str] = mapped_column(String(200), index=True)
    is_canonical: Mapped[bool] = mapped_column(Boolean, default=False)


class LocalizedText(Base):
    __tablename__ = "localized_text"
    __table_args__ = (
        Index("ix_localized_text_lookup", "entity_type", "entity_id", "locale", "text_kind"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(64), index=True)
    entity_id: Mapped[int] = mapped_column(Integer, index=True)
    locale: Mapped[str] = mapped_column(String(16), index=True)
    text_kind: Mapped[str] = mapped_column(String(40), index=True)
    version: Mapped[str | None] = mapped_column(String(80), nullable=True)
    text: Mapped[str] = mapped_column(Text)


class GenerationEntity(Base):
    __tablename__ = "generation"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    main_region: Mapped[str | None] = mapped_column(String(80), nullable=True)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JsonType, default=dict)

    species: Mapped[list[PokemonSpecies]] = relationship(back_populates="generation")


class TypeEntity(Base):
    __tablename__ = "type"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    damage_relations: Mapped[dict[str, Any]] = mapped_column(JsonType, default=dict)
    past_damage_relations: Mapped[list[dict[str, Any]]] = mapped_column(JsonType, default=list)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JsonType, default=dict)


class Ability(Base):
    __tablename__ = "ability"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    generation_id: Mapped[int | None] = mapped_column(ForeignKey("generation.id"), nullable=True)
    is_main_series: Mapped[bool] = mapped_column(Boolean, default=True)
    effect_entries: Mapped[list[dict[str, Any]]] = mapped_column(JsonType, default=list)
    flavor_text_entries: Mapped[list[dict[str, Any]]] = mapped_column(JsonType, default=list)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JsonType, default=dict)


class StatEntity(Base):
    __tablename__ = "stat"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    is_battle_only: Mapped[bool] = mapped_column(Boolean, default=False)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JsonType, default=dict)


class PokedexEntity(Base):
    __tablename__ = "pokedex"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    is_main_series: Mapped[bool] = mapped_column(Boolean, default=False)
    region_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JsonType, default=dict)


class PokemonSpecies(Base):
    __tablename__ = "pokemon_species"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    generation_id: Mapped[int | None] = mapped_column(ForeignKey("generation.id"), nullable=True)
    evolution_chain_id: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    color: Mapped[str | None] = mapped_column(String(40), nullable=True)
    habitat: Mapped[str | None] = mapped_column(String(40), nullable=True)
    shape: Mapped[str | None] = mapped_column(String(40), nullable=True)
    capture_rate: Mapped[int | None] = mapped_column(Integer, nullable=True)
    base_happiness: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hatch_counter: Mapped[int | None] = mapped_column(Integer, nullable=True)
    gender_rate: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_baby: Mapped[bool] = mapped_column(Boolean, default=False)
    is_legendary: Mapped[bool] = mapped_column(Boolean, default=False)
    is_mythical: Mapped[bool] = mapped_column(Boolean, default=False)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JsonType, default=dict)

    generation: Mapped[GenerationEntity | None] = relationship(back_populates="species")
    pokemon: Mapped[list[Pokemon]] = relationship(back_populates="species")
    evolution_nodes: Mapped[list[EvolutionNode]] = relationship(back_populates="species")


class Pokemon(Base):
    __tablename__ = "pokemon"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    species_id: Mapped[int | None] = mapped_column(ForeignKey("pokemon_species.id"), nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    weight: Mapped[int | None] = mapped_column(Integer, nullable=True)
    base_experience: Mapped[int | None] = mapped_column(Integer, nullable=True)
    order: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=True)
    sprites: Mapped[dict[str, Any]] = mapped_column(JsonType, default=dict)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JsonType, default=dict)

    species: Mapped[PokemonSpecies | None] = relationship(back_populates="pokemon")
    forms: Mapped[list[PokemonForm]] = relationship(back_populates="pokemon")
    media_assets: Mapped[list[MediaAsset]] = relationship(back_populates="pokemon")


class PokemonForm(Base):
    __tablename__ = "pokemon_form"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    pokemon_id: Mapped[int | None] = mapped_column(ForeignKey("pokemon.id"), nullable=True)
    form_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    is_battle_only: Mapped[bool] = mapped_column(Boolean, default=False)
    is_mega: Mapped[bool] = mapped_column(Boolean, default=False)
    version_group: Mapped[str | None] = mapped_column(String(80), nullable=True)
    sprites: Mapped[dict[str, Any]] = mapped_column(JsonType, default=dict)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JsonType, default=dict)

    pokemon: Mapped[Pokemon | None] = relationship(back_populates="forms")


class PokemonType(Base):
    __tablename__ = "pokemon_type"
    __table_args__ = (UniqueConstraint("pokemon_id", "slot"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pokemon_id: Mapped[int] = mapped_column(
        ForeignKey("pokemon.id", ondelete="CASCADE"), index=True
    )
    type_id: Mapped[int] = mapped_column(ForeignKey("type.id"), index=True)
    slot: Mapped[int] = mapped_column(Integer)


class PokemonAbility(Base):
    __tablename__ = "pokemon_ability"
    __table_args__ = (UniqueConstraint("pokemon_id", "slot"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pokemon_id: Mapped[int] = mapped_column(
        ForeignKey("pokemon.id", ondelete="CASCADE"), index=True
    )
    ability_id: Mapped[int] = mapped_column(ForeignKey("ability.id"), index=True)
    slot: Mapped[int] = mapped_column(Integer)
    is_hidden: Mapped[bool] = mapped_column(Boolean, default=False)


class PokemonStat(Base):
    __tablename__ = "pokemon_stat"
    __table_args__ = (UniqueConstraint("pokemon_id", "stat_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pokemon_id: Mapped[int] = mapped_column(
        ForeignKey("pokemon.id", ondelete="CASCADE"), index=True
    )
    stat_id: Mapped[int] = mapped_column(ForeignKey("stat.id"), index=True)
    base_stat: Mapped[int] = mapped_column(Integer)
    effort: Mapped[int] = mapped_column(Integer, default=0)


class EvolutionChain(Base):
    __tablename__ = "evolution_chain"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    baby_trigger_item: Mapped[str | None] = mapped_column(String(120), nullable=True)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JsonType, default=dict)

    nodes: Mapped[list[EvolutionNode]] = relationship(back_populates="chain")


class EvolutionNode(Base):
    __tablename__ = "evolution_node"
    __table_args__ = (UniqueConstraint("chain_id", "species_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    chain_id: Mapped[int] = mapped_column(
        ForeignKey("evolution_chain.id", ondelete="CASCADE"), index=True
    )
    species_id: Mapped[int] = mapped_column(ForeignKey("pokemon_species.id"), index=True)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("evolution_node.id"), nullable=True)
    stage: Mapped[int] = mapped_column(Integer, default=0)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_baby: Mapped[bool] = mapped_column(Boolean, default=False)
    condition: Mapped[dict[str, Any]] = mapped_column(JsonType, default=dict)

    chain: Mapped[EvolutionChain] = relationship(back_populates="nodes")
    species: Mapped[PokemonSpecies] = relationship(back_populates="evolution_nodes")
    parent: Mapped[EvolutionNode | None] = relationship(remote_side=[id], back_populates="children")
    children: Mapped[list[EvolutionNode]] = relationship(back_populates="parent")


class MediaAsset(Base):
    __tablename__ = "media_asset"
    __table_args__ = (UniqueConstraint("pokemon_id", "form_id", "kind"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pokemon_id: Mapped[int | None] = mapped_column(
        ForeignKey("pokemon.id", ondelete="CASCADE"), nullable=True, index=True
    )
    form_id: Mapped[int | None] = mapped_column(
        ForeignKey("pokemon_form.id"), nullable=True, index=True
    )
    kind: Mapped[str] = mapped_column(String(40), index=True)
    source_url: Mapped[str] = mapped_column(Text)
    local_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    checksum: Mapped[str | None] = mapped_column(String(64), nullable=True)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)

    pokemon: Mapped[Pokemon | None] = relationship(back_populates="media_assets")


class VersionSprite(Base):
    """One source field, including nulls, in a Pokémon or form's versions tree."""

    __tablename__ = "version_sprite"
    __table_args__ = (
        UniqueConstraint("owner_type", "owner_id", "generation", "game", "kind"),
        Index("ix_version_sprite_owner", "owner_type", "owner_id"),
        Index("ix_version_sprite_source_url", "source_url"),
        Index("ix_version_sprite_status", "status"),
        Index("ix_version_sprite_checksum", "checksum"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_type: Mapped[str] = mapped_column(String(12))
    owner_id: Mapped[int] = mapped_column(Integer)
    generation: Mapped[str] = mapped_column(String(32))
    game: Mapped[str] = mapped_column(String(64))
    kind: Mapped[str] = mapped_column(String(80))
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(24))
    format: Mapped[str | None] = mapped_column(String(8), nullable=True)
    checksum: Mapped[str | None] = mapped_column(String(64), nullable=True)
    local_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    byte_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    frame_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ContentChunk(Base):
    __tablename__ = "content_chunk"
    __table_args__ = (UniqueConstraint("entity_type", "entity_id", "locale", "chunk_index"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(64), index=True)
    entity_id: Mapped[int] = mapped_column(Integer, index=True)
    locale: Mapped[str] = mapped_column(String(16), index=True)
    chunk_index: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    source_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
