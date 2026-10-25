from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from pokedex_api.db import get_session
from pokedex_api.schemas import Locale, TypeDetail, TypeSummary
from pokedex_api.services import pokemon as pokemon_service

router = APIRouter()


@router.get("/types", response_model=list[TypeSummary])
async def list_types(
    session: Annotated[AsyncSession, Depends(get_session)],
    locale: Locale = "zh-Hans",
) -> list[TypeSummary]:
    return await pokemon_service.list_types(session, locale=locale)


@router.get("/types/{id_or_name}", response_model=TypeDetail)
async def get_type(
    id_or_name: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    locale: Locale = "zh-Hans",
) -> TypeDetail:
    result = await pokemon_service.get_type(session, id_or_name, locale=locale)
    if result is None:
        raise HTTPException(status_code=404, detail="Type not found")
    return result
