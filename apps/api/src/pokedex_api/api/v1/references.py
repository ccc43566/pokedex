from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from pokedex_api.db import get_session
from pokedex_api.reference_schemas import ReferenceDetail, ReferencePage, RelationPage
from pokedex_api.schemas import Locale
from pokedex_api.services import reference_browser as browser

router = APIRouter()
Session = Annotated[AsyncSession, Depends(get_session)]
Page = Annotated[int, Query(ge=1)]
Size = Annotated[int, Query(ge=1, le=100)]
Filter = Annotated[int | None, Query(ge=1)]
Search = Annotated[str, Query(max_length=200)]
Sort = Annotated[str, Query(pattern="^(id|id_desc|name|power_desc|priority_desc)$")]


@router.get("/items", response_model=ReferencePage)
async def items(
    session: Session,
    locale: Locale = "zh-Hans",
    q: Search = "",
    page: Page = 1,
    page_size: Size = 60,
    sort: Sort = "id",
    category: Filter = None,
    pocket: Filter = None,
) -> ReferencePage:
    return await browser.browse(
        session,
        "item",
        locale,
        q=q,
        page=page,
        page_size=page_size,
        sort=sort,
        category=category,
        pocket=pocket,
    )


@router.get("/moves", response_model=ReferencePage)
async def moves(
    session: Session,
    locale: Locale = "zh-Hans",
    q: Search = "",
    page: Page = 1,
    page_size: Size = 48,
    sort: Sort = "id",
    type: Filter = None,
    damage_class: Filter = None,
    generation: Filter = None,
) -> ReferencePage:
    return await browser.browse(
        session,
        "move",
        locale,
        q=q,
        page=page,
        page_size=page_size,
        sort=sort,
        type_id=type,
        damage_class=damage_class,
        generation=generation,
    )


@router.get("/items/filters")
async def item_filters(session: Session, locale: Locale = "zh-Hans") -> dict[str, object]:
    return await browser.filters(session, "item", locale)


@router.get("/moves/filters")
async def move_filters(session: Session, locale: Locale = "zh-Hans") -> dict[str, object]:
    return await browser.filters(session, "move", locale)


@router.get("/items/{key}", response_model=ReferenceDetail)
async def item_detail(key: str, session: Session, locale: Locale = "zh-Hans") -> ReferenceDetail:
    return await browser.detail(session, "item", key, locale)


@router.get("/moves/{key}", response_model=ReferenceDetail)
async def move_detail(key: str, session: Session, locale: Locale = "zh-Hans") -> ReferenceDetail:
    return await browser.detail(session, "move", key, locale)


@router.get("/items/{key}/{relation}", response_model=RelationPage)
async def item_relations(
    key: str,
    relation: str,
    session: Session,
    locale: Locale = "zh-Hans",
    page: Page = 1,
    page_size: Size = 24,
    version_group: Filter = None,
    version: Filter = None,
) -> RelationPage:
    return await browser.relations(
        session,
        "item",
        key,
        relation,
        locale,
        page=page,
        page_size=page_size,
        version_group=version_group,
        version=version,
    )


@router.get("/moves/{key}/{relation}", response_model=RelationPage)
async def move_relations(
    key: str,
    relation: str,
    session: Session,
    locale: Locale = "zh-Hans",
    page: Page = 1,
    page_size: Size = 24,
    version_group: Filter = None,
    method: Filter = None,
) -> RelationPage:
    return await browser.relations(
        session,
        "move",
        key,
        relation,
        locale,
        page=page,
        page_size=page_size,
        version_group=version_group,
        method=method,
    )
