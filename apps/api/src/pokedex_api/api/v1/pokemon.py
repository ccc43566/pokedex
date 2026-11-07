from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from pokedex_api.config import Settings, get_settings
from pokedex_api.db import get_session
from pokedex_api.schemas import Locale, PaginatedPokemon, PokemonDetail, PokemonVersionMedia
from pokedex_api.services import pokemon as pokemon_service
from pokedex_api.services.version_sprites import get_version_media

router = APIRouter()


@router.get("/pokemon/revision")
async def pokemon_revision(
    response: Response,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, str]:
    from pokedex_api.services.search_index import data_version

    response.headers["Cache-Control"] = "no-store"
    return {"version": await data_version(session)}


@router.get("/pokemon/{id_or_name}/version-sprites", response_model=PokemonVersionMedia)
async def get_pokemon_version_sprites(
    id_or_name: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> PokemonVersionMedia:
    result = await get_version_media(session, id_or_name, settings.media_public_path)
    if result is None:
        raise HTTPException(status_code=404, detail="Pokemon not found")
    return result


@router.get("/pokemon", response_model=PaginatedPokemon)
async def list_pokemon(
    response: Response,
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    locale: Locale = "zh-Hans",
    q: Annotated[str | None, Query(max_length=120)] = None,
    type: Annotated[str | None, Query(max_length=40)] = None,
    generation: Annotated[int | None, Query(ge=1, le=99)] = None,
    is_legendary: Annotated[bool | None, Query(alias="isLegendary")] = None,
    is_mythical: Annotated[bool | None, Query(alias="isMythical")] = None,
    is_mega: Annotated[bool | None, Query(alias="isMega")] = None,
    is_gigantamax: Annotated[bool | None, Query(alias="isGigantamax")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=100)] = 24,
    sort: Literal["id", "name", "base_experience", "newest"] = "id",
) -> PaginatedPokemon:
    response.headers["Cache-Control"] = "no-store"
    return await pokemon_service.list_pokemon(
        session,
        locale=locale,
        q=q,
        type_name=type,
        generation=generation,
        is_legendary=is_legendary,
        is_mythical=is_mythical,
        is_mega=is_mega,
        is_gigantamax=is_gigantamax,
        page=page,
        page_size=page_size,
        sort=sort,
        media_public_path=settings.media_public_path,
    )


@router.get("/pokemon/{id_or_name}", response_model=PokemonDetail)
async def get_pokemon(
    id_or_name: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    locale: Locale = "zh-Hans",
    form: Annotated[str | None, Query(max_length=80)] = None,
) -> PokemonDetail:
    result = await pokemon_service.get_pokemon(
        session,
        id_or_name,
        locale=locale,
        media_public_path=settings.media_public_path,
        form_key=form,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Pokemon not found")
    return result
