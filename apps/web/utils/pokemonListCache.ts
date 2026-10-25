import type { PaginatedPokemon } from '~/types/api'

export interface PokemonListQuery {
  locale: string
  q?: string
  type?: string
  generation?: number
  isLegendary?: boolean
  isMythical?: boolean
  sort: string
}

type QueryValue = string | null | readonly (string | null)[] | undefined

function single(value: QueryValue): string | undefined {
  const first = Array.isArray(value) ? value[0] : value
  return typeof first === 'string' ? first : undefined
}

export function pokemonListQuery(
  query: Record<string, QueryValue>,
  locale: string,
): PokemonListQuery {
  const rawGeneration = Number(single(query.generation))
  const q = single(query.q)?.trim()
  const type = single(query.type)
  const generation = single(query.generation)
  return {
    locale,
    q: q || undefined,
    type: type && type !== '__all__' ? type : undefined,
    generation:
      generation && Number.isInteger(rawGeneration) && rawGeneration > 0
        ? rawGeneration
        : undefined,
    isLegendary: single(query.isLegendary) === 'true' || undefined,
    isMythical: single(query.isMythical) === 'true' || undefined,
    sort: single(query.sort) || 'id',
  }
}

export function pokemonListKey(query: PokemonListQuery): string {
  return JSON.stringify([
    query.locale,
    query.q || '',
    query.type || '',
    query.generation || 0,
    query.sort,
    Boolean(query.isLegendary),
    Boolean(query.isMythical),
  ])
}

export function createPokemonListCache(maxLists = 3) {
  const lists = new Map<string, PaginatedPokemon>()
  const inFlight = new Map<string, Promise<PaginatedPokemon>>()

  function get(key: string): PaginatedPokemon | undefined {
    const list = lists.get(key)
    if (list) {
      lists.delete(key)
      lists.set(key, list)
    }
    return list
  }

  function set(key: string, list: PaginatedPokemon): void {
    lists.delete(key)
    lists.set(key, list)
    while (lists.size > maxLists) lists.delete(lists.keys().next().value!)
  }

  function load(
    key: string,
    fetchList: () => Promise<PaginatedPokemon>,
  ): Promise<PaginatedPokemon> {
    const cached = get(key)
    if (cached) return Promise.resolve(cached)
    const existing = inFlight.get(key)
    if (existing) return existing
    const request = fetchList()
      .then((list) => {
        set(key, list)
        return list
      })
      .finally(() => inFlight.delete(key))
    inFlight.set(key, request)
    return request
  }

  return { get, set, load }
}

// The shared cache is used only for browser navigation. SSR requests remain isolated.
export const pokemonListCache = createPokemonListCache()
