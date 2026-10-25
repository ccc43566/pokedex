from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from pokedex_api.config import Settings, get_settings
from pokedex_api.db import get_session
from pokedex_api.schemas import Locale, SearchSuggestion
from pokedex_api.services import pokemon as pokemon_service

router = APIRouter()


@router.get("/search/suggest", response_model=list[SearchSuggestion])
async def suggest(
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    q: Annotated[str, Query(min_length=1, max_length=80)],
    locale: Locale = "zh-Hans",
    limit: Annotated[int, Query(ge=1, le=20)] = 8,
) -> list[SearchSuggestion]:
    return await pokemon_service.search_suggestions(
        session,
        q=q,
        locale=locale,
        limit=limit,
        media_public_path=settings.media_public_path,
    )
