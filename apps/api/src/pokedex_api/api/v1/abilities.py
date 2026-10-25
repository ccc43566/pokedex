from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from pokedex_api.db import get_session
from pokedex_api.schemas import AbilityDetail, Locale
from pokedex_api.services import pokemon as pokemon_service

router = APIRouter()


@router.get("/abilities/{id_or_name}", response_model=AbilityDetail)
async def get_ability(
    id_or_name: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    locale: Locale = "zh-Hans",
) -> AbilityDetail:
    result = await pokemon_service.get_ability(session, id_or_name, locale=locale)
    if result is None:
        raise HTTPException(status_code=404, detail="Ability not found")
    return result
