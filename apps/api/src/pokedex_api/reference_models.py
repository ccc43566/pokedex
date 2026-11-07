"""Additive reference catalog. SourceRecord retains unabridged upstream payloads."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from pokedex_api.models import Base, JsonType, utcnow


class CatalogDictionary(Base):
    __tablename__ = "catalog_dictionary"
    __table_args__ = (UniqueConstraint("resource_type", "resource_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    resource_type: Mapped[str] = mapped_column(String(64), index=True)
    resource_id: Mapped[int] = mapped_column(Integer)
    name: Mapped[str] = mapped_column(String(160), index=True)
    source_record_id: Mapped[int] = mapped_column(ForeignKey("source_record.id"))
    sort_order: Mapped[int | None] = mapped_column(Integer)


class CatalogDictionaryLink(Base):
    __tablename__ = "catalog_dictionary_link"
    __table_args__ = (UniqueConstraint("dictionary_id", "path"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    dictionary_id: Mapped[int] = mapped_column(ForeignKey("catalog_dictionary.id"), index=True)
    path: Mapped[str] = mapped_column(Text)
    target_id: Mapped[int] = mapped_column(ForeignKey("catalog_dictionary.id"), index=True)


class Move(Base):
    __tablename__ = "move"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160), index=True)
    source_record_id: Mapped[int] = mapped_column(ForeignKey("source_record.id"))
    power: Mapped[int | None] = mapped_column(Integer, index=True)
    accuracy: Mapped[int | None] = mapped_column(Integer)
    pp: Mapped[int | None] = mapped_column(Integer)
    priority: Mapped[int] = mapped_column(Integer, index=True)
    effect_chance: Mapped[int | None] = mapped_column(Integer)
    type_id: Mapped[int | None] = mapped_column(ForeignKey("catalog_dictionary.id"), index=True)
    generation_id: Mapped[int | None] = mapped_column(
        ForeignKey("catalog_dictionary.id"), index=True
    )
    damage_class_id: Mapped[int | None] = mapped_column(
        ForeignKey("catalog_dictionary.id"), index=True
    )
    target_id: Mapped[int | None] = mapped_column(ForeignKey("catalog_dictionary.id"), index=True)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("catalog_dictionary.id"), index=True)
    ailment_id: Mapped[int | None] = mapped_column(ForeignKey("catalog_dictionary.id"), index=True)
    contest_type_id: Mapped[int | None] = mapped_column(ForeignKey("catalog_dictionary.id"))
    contest_effect_id: Mapped[int | None] = mapped_column(ForeignKey("catalog_dictionary.id"))
    super_contest_effect_id: Mapped[int | None] = mapped_column(ForeignKey("catalog_dictionary.id"))
    meta: Mapped[dict[str, Any] | None] = mapped_column(JsonType)


class MoveStatChange(Base):
    __tablename__ = "move_stat_change"
    __table_args__ = (UniqueConstraint("move_id", "ordinal"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    move_id: Mapped[int] = mapped_column(ForeignKey("move.id"), index=True)
    ordinal: Mapped[int] = mapped_column(Integer)
    stat_id: Mapped[int] = mapped_column(ForeignKey("catalog_dictionary.id"), index=True)
    change: Mapped[int] = mapped_column(Integer)


class MovePastValue(Base):
    __tablename__ = "move_past_value"
    __table_args__ = (UniqueConstraint("move_id", "ordinal"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    move_id: Mapped[int] = mapped_column(ForeignKey("move.id"), index=True)
    ordinal: Mapped[int] = mapped_column(Integer)
    version_group_id: Mapped[int | None] = mapped_column(
        ForeignKey("catalog_dictionary.id"), index=True
    )
    type_id: Mapped[int | None] = mapped_column(ForeignKey("catalog_dictionary.id"))
    power: Mapped[int | None] = mapped_column(Integer)
    accuracy: Mapped[int | None] = mapped_column(Integer)
    pp: Mapped[int | None] = mapped_column(Integer)
    effect_chance: Mapped[int | None] = mapped_column(Integer)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JsonType)


class Item(Base):
    __tablename__ = "item"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160), index=True)
    source_record_id: Mapped[int] = mapped_column(ForeignKey("source_record.id"))
    category_id: Mapped[int | None] = mapped_column(ForeignKey("catalog_dictionary.id"), index=True)
    cost: Mapped[int | None] = mapped_column(Integer, index=True)
    fling_power: Mapped[int | None] = mapped_column(Integer)
    fling_effect_id: Mapped[int | None] = mapped_column(
        ForeignKey("catalog_dictionary.id"), index=True
    )
    sprites: Mapped[dict[str, Any]] = mapped_column(JsonType)


class ItemAttribute(Base):
    __tablename__ = "item_attribute_link"
    item_id: Mapped[int] = mapped_column(ForeignKey("item.id"), primary_key=True)
    attribute_id: Mapped[int] = mapped_column(
        ForeignKey("catalog_dictionary.id"), primary_key=True, index=True
    )


class ItemMedia(Base):
    """Default Item image only; numeric IDs never imply Pokemon ownership."""

    __tablename__ = "item_media"
    item_id: Mapped[int] = mapped_column(ForeignKey("item.id"), primary_key=True)
    source_url: Mapped[str | None] = mapped_column(Text, index=True)
    status: Mapped[str] = mapped_column(String(24), index=True)
    checksum: Mapped[str | None] = mapped_column(String(64), index=True)
    local_path: Mapped[str | None] = mapped_column(Text)
    format: Mapped[str | None] = mapped_column(String(8))
    byte_size: Mapped[int | None] = mapped_column(Integer)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    frame_count: Mapped[int | None] = mapped_column(Integer)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ItemGameIndex(Base):
    __tablename__ = "item_game_index"
    __table_args__ = (UniqueConstraint("item_id", "ordinal"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("item.id"), index=True)
    ordinal: Mapped[int] = mapped_column(Integer)
    generation_id: Mapped[int] = mapped_column(ForeignKey("catalog_dictionary.id"), index=True)
    game_index: Mapped[int] = mapped_column(Integer, index=True)


class ItemPrice(Base):
    __tablename__ = "item_price"
    __table_args__ = (UniqueConstraint("item_id", "ordinal"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("item.id"), index=True)
    ordinal: Mapped[int] = mapped_column(Integer)
    version_group_id: Mapped[int] = mapped_column(ForeignKey("catalog_dictionary.id"), index=True)
    currency_id: Mapped[int] = mapped_column(ForeignKey("catalog_dictionary.id"), index=True)
    purchase_price: Mapped[int | None] = mapped_column(Integer, index=True)
    sell_price: Mapped[int | None] = mapped_column(Integer, index=True)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JsonType)


class CatalogMachine(Base):
    __tablename__ = "catalog_machine"
    id: Mapped[int] = mapped_column(primary_key=True)
    source_record_id: Mapped[int] = mapped_column(ForeignKey("source_record.id"))
    item_id: Mapped[int] = mapped_column(ForeignKey("item.id"), index=True)
    move_id: Mapped[int] = mapped_column(ForeignKey("move.id"), index=True)
    version_group_id: Mapped[int] = mapped_column(ForeignKey("catalog_dictionary.id"), index=True)


class Berry(Base):
    __tablename__ = "berry"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160), index=True)
    source_record_id: Mapped[int] = mapped_column(ForeignKey("source_record.id"))
    item_id: Mapped[int] = mapped_column(ForeignKey("item.id"), unique=True)
    firmness_id: Mapped[int | None] = mapped_column(ForeignKey("catalog_dictionary.id"), index=True)
    natural_gift_type_id: Mapped[int | None] = mapped_column(
        ForeignKey("catalog_dictionary.id"), index=True
    )
    growth_time: Mapped[int | None] = mapped_column(Integer)
    max_harvest: Mapped[int | None] = mapped_column(Integer)
    natural_gift_power: Mapped[int | None] = mapped_column(Integer)
    size: Mapped[int | None] = mapped_column(Integer)
    smoothness: Mapped[int | None] = mapped_column(Integer)
    soil_dryness: Mapped[int | None] = mapped_column(Integer)


class BerryFlavor(Base):
    __tablename__ = "berry_flavor_link"
    berry_id: Mapped[int] = mapped_column(ForeignKey("berry.id"), primary_key=True)
    flavor_id: Mapped[int] = mapped_column(
        ForeignKey("catalog_dictionary.id"), primary_key=True, index=True
    )
    potency: Mapped[int] = mapped_column(Integer, index=True)


class PokemonMove(Base):
    __tablename__ = "pokemon_move"
    __table_args__ = (
        Index("ix_pokemon_move_lookup", "pokemon_id", "version_group_id", "learn_method_id"),
    )
    pokemon_id: Mapped[int] = mapped_column(ForeignKey("pokemon.id"), primary_key=True)
    move_ordinal: Mapped[int] = mapped_column(Integer, primary_key=True)
    detail_ordinal: Mapped[int] = mapped_column(Integer, primary_key=True)
    move_id: Mapped[int] = mapped_column(ForeignKey("move.id"), index=True)
    version_group_id: Mapped[int] = mapped_column(ForeignKey("catalog_dictionary.id"), index=True)
    learn_method_id: Mapped[int] = mapped_column(ForeignKey("catalog_dictionary.id"), index=True)
    level_learned_at: Mapped[int] = mapped_column(Integer, index=True)
    learn_order: Mapped[int | None] = mapped_column(Integer)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JsonType)


class PokemonHeldItem(Base):
    __tablename__ = "pokemon_held_item"
    __table_args__ = (Index("ix_pokemon_held_item_lookup", "pokemon_id", "version_id"),)
    pokemon_id: Mapped[int] = mapped_column(ForeignKey("pokemon.id"), primary_key=True)
    item_ordinal: Mapped[int] = mapped_column(Integer, primary_key=True)
    detail_ordinal: Mapped[int] = mapped_column(Integer, primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("item.id"), index=True)
    version_id: Mapped[int] = mapped_column(ForeignKey("catalog_dictionary.id"), index=True)
    rarity: Mapped[int] = mapped_column(Integer, index=True)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JsonType)


class EvolutionItemReference(Base):
    __tablename__ = "evolution_item_reference"
    __table_args__ = (UniqueConstraint("chain_id", "path"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    chain_id: Mapped[int] = mapped_column(ForeignKey("evolution_chain.id"), index=True)
    path: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String(64), index=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("item.id"), index=True)
    raw_reference: Mapped[dict[str, Any]] = mapped_column(JsonType)


class CatalogSyncEntry(Base):
    __tablename__ = "catalog_sync_entry"
    resource_type: Mapped[str] = mapped_column(String(64), primary_key=True)
    resource_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_url: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(24), index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text)
    fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    normalized_hash: Mapped[str | None] = mapped_column(String(64))
    run_id: Mapped[int | None] = mapped_column(ForeignKey("sync_run.id"))


class CatalogDiscoveryPage(Base):
    __tablename__ = "catalog_discovery_page"
    __table_args__ = (UniqueConstraint("run_id", "resource_type", "page_url"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("sync_run.id"), index=True)
    resource_type: Mapped[str] = mapped_column(String(64))
    page_url: Mapped[str] = mapped_column(Text)
    source_hash: Mapped[str] = mapped_column(String(64))
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JsonType)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class CatalogReferenceIssue(Base):
    __tablename__ = "catalog_reference_issue"
    fingerprint: Mapped[str] = mapped_column(String(64), primary_key=True)
    owner_type: Mapped[str] = mapped_column(String(64), index=True)
    owner_id: Mapped[int] = mapped_column(Integer, index=True)
    path: Mapped[str] = mapped_column(Text)
    target_url: Mapped[str | None] = mapped_column(Text)
    reason: Mapped[str] = mapped_column(Text)
    resolved: Mapped[bool] = mapped_column(default=False, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


REFERENCE_TABLES = (
    CatalogDictionary,
    CatalogDictionaryLink,
    Move,
    MoveStatChange,
    MovePastValue,
    Item,
    ItemAttribute,
    ItemGameIndex,
    ItemPrice,
    CatalogMachine,
    Berry,
    BerryFlavor,
    PokemonMove,
    PokemonHeldItem,
    EvolutionItemReference,
    CatalogSyncEntry,
    CatalogDiscoveryPage,
    CatalogReferenceIssue,
)
