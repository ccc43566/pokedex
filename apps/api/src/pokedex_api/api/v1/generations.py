from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from pokedex_api.db import get_session
from pokedex_api.schemas import GenerationSummary, Locale
from pokedex_api.services import pokemon as pokemon_service

router = APIRouter()


@router.get("/generations", response_model=list[GenerationSummary])
async def list_generations(
    session: Annotated[AsyncSession, Depends(get_session)],
    locale: Locale = "zh-Hans",
) -> list[GenerationSummary]:
    return await pokemon_service.list_generations(session, locale=locale)
