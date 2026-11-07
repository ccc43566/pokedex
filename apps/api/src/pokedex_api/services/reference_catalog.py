"""Query helpers for future pages: language fallback is per historical context."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pokedex_api.models import LocalizedName, LocalizedText, SourceRecord


async def reference_name(
    session: AsyncSession, kind: str, resource_id: int, locale: str = "zh-Hans"
) -> str | None:
    if kind == "berry":
        from pokedex_api.reference_models import Berry

        berry = await session.get(Berry, resource_id)
        if berry is None:
            return None
        return await reference_name(session, "item", berry.item_id, locale)
    rows = (
        await session.scalars(
            select(LocalizedName)
            .where(
                LocalizedName.entity_type == kind,
                LocalizedName.entity_id == resource_id,
                LocalizedName.locale.in_([locale, "en"]),
            )
            .order_by(LocalizedName.id)
        )
    ).all()
    for language in dict.fromkeys([locale, "en"]):
        for row in rows:
            if row.locale == language:
                return row.name
    return await session.scalar(
        select(SourceRecord.name).where(
            SourceRecord.resource_type == kind, SourceRecord.resource_id == resource_id
        )
    )


async def reference_texts(
    session: AsyncSession, kind: str, resource_id: int, locale: str = "zh-Hans"
) -> list[LocalizedText]:
    if kind == "berry":
        from pokedex_api.reference_models import Berry

        berry = await session.get(Berry, resource_id)
        if berry is None:
            return []
        return await reference_texts(session, "item", berry.item_id, locale)
    rows = (
        await session.scalars(
            select(LocalizedText)
            .where(
                LocalizedText.entity_type == kind,
                LocalizedText.entity_id == resource_id,
                LocalizedText.locale.in_([locale, "en"]),
            )
            .order_by(LocalizedText.id)
        )
    ).all()
    preferred = {(r.text_kind, r.version) for r in rows if r.locale == locale}
    return [r for r in rows if r.locale == locale or (r.text_kind, r.version) not in preferred]
