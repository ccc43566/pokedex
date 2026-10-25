from fastapi import APIRouter

from pokedex_api.api.v1 import abilities, generations, pokemon, search, types

router = APIRouter()
router.include_router(pokemon.router, tags=["pokemon"])
router.include_router(types.router, tags=["types"])
router.include_router(abilities.router, tags=["abilities"])
router.include_router(generations.router, tags=["generations"])
router.include_router(search.router, tags=["search"])
