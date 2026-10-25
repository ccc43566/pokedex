from __future__ import annotations

from typing import Literal, cast

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from pokedex_api.models import Pokemon, PokemonForm, VersionSprite
from pokedex_api.schemas import PokemonVersionMedia, VersionSpriteOut, VersionSpriteOwner


async def get_version_media(
    session: AsyncSession, id_or_name: str, media_public_path: str = "/media"
) -> PokemonVersionMedia | None:
    conditions = [Pokemon.name == id_or_name.lower()]
    if id_or_name.isdigit():
        conditions.append(Pokemon.id == int(id_or_name))
    pokemon = await session.scalar(select(Pokemon).where(or_(*conditions)))
    if pokemon is None:
        return None

    forms = list(
        (
            await session.scalars(
                select(PokemonForm)
                .where(PokemonForm.pokemon_id == pokemon.id)
                .order_by(PokemonForm.id)
            )
        ).all()
    )
    owners = [VersionSpriteOwner(owner_type="pokemon", owner_id=pokemon.id, name=pokemon.name)]
    owners.extend(
        VersionSpriteOwner(owner_type="form", owner_id=form.id, name=form.name) for form in forms
    )
    conditions = [(VersionSprite.owner_type == "pokemon") & (VersionSprite.owner_id == pokemon.id)]
    if forms:
        conditions.append(
            (VersionSprite.owner_type == "form")
            & (VersionSprite.owner_id.in_([form.id for form in forms]))
        )
    rows = (
        await session.scalars(
            select(VersionSprite)
            .where(or_(*conditions))
            .order_by(
                VersionSprite.owner_type,
                VersionSprite.owner_id,
                VersionSprite.generation,
                VersionSprite.game,
                VersionSprite.kind,
            )
        )
    ).all()
    sprites = [
        VersionSpriteOut(
            owner_type=cast(Literal["pokemon", "form"], row.owner_type),
            owner_id=row.owner_id,
            generation=row.generation,
            game=row.game,
            kind=row.kind,
            status=cast(
                Literal["null", "pending", "downloaded", "download_failed", "corrupt"],
                row.status,
            ),
            format=row.format,
            source_url=row.source_url,
            url=f"{media_public_path.rstrip('/')}/{row.local_path}" if row.local_path else None,
            checksum=row.checksum,
            byte_size=row.byte_size,
            width=row.width,
            height=row.height,
            frame_count=row.frame_count,
        )
        for row in rows
    ]
    return PokemonVersionMedia(pokemon_id=pokemon.id, owners=owners, sprites=sprites)
