import type { PaginatedPokemon } from '~/types/api'
import { createListCache } from './listCache'

export interface PokemonListQuery {
  locale: string
  q?: string
  type?: string
  generation?: number
  isLegendary?: boolean
  isMythical?: boolean
  isMega?: boolean
  isGigantamax?: boolean
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
    isMega: single(query.isMega) === 'true' || undefined,
    isGigantamax: single(query.isGigantamax) === 'true' || undefined,
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
    Boolean(query.isMega),
    Boolean(query.isGigantamax),
  ])
}

export function createPokemonListCache(maxLists = 3, ttl = 120_000, now = Date.now) {
  const lists = createListCache<{ list: PaginatedPokemon; expires: number }>(maxLists)
  const inFlight = new Map<string, {
    promise: Promise<PaginatedPokemon>
    controller: AbortController
    users: number
  }>()
  let version: string | undefined

  function get(key: string): PaginatedPokemon | undefined {
    const entry = lists.get(key)
    if (!entry) return
    if (entry.expires <= now() || (version && entry.list.dataVersion !== version)) {
      lists.remove(key)
      return
    }
    return entry.list
  }
  function set(key: string, list: PaginatedPokemon): void {
    if (version && list.dataVersion !== version) return
    lists.set(key, { list, expires: now() + ttl })
  }
  function setVersion(next: string) {
    version = next
  }
  function acquire(key: string, fetchList: (signal: AbortSignal) => Promise<PaginatedPokemon>) {
    const cached = get(key)
    if (cached) return { promise: Promise.resolve(cached), release: () => {} }
    // Consumers that validated different revisions must not share a response
    // that was already produced before a data update.
    const flightKey = `${version || ''}:${key}`
    let entry = inFlight.get(flightKey)
    if (!entry) {
      const controller = new AbortController()
      // Entry creation precedes promise callbacks, including synchronous throws.
      entry = { controller, users: 0, promise: undefined! }
      const current = entry
      let request: Promise<PaginatedPokemon>
      try { request = fetchList(controller.signal) } catch (error) { request = Promise.reject(error) }
      current.promise = request
        .then((list) => {
          if (!controller.signal.aborted) set(key, list)
          return list
        })
        .finally(() => {
          if (inFlight.get(flightKey) === current) inFlight.delete(flightKey)
        })
      inFlight.set(flightKey, current)
    }
    entry.users++
    const current = entry
    let released = false
    return {
      promise: current.promise,
      release() {
        if (released) return
        released = true
        if (--current.users === 0 && inFlight.get(flightKey) === current) {
          inFlight.delete(flightKey)
          current.controller.abort()
        }
      },
    }
  }
  function load(key: string, fetchList: () => Promise<PaginatedPokemon>) {
    // Compatibility for existing callers: an ordinary load holds its lease
    // until completion. Cancellable page consumers use acquire directly.
    const lease = acquire(key, fetchList)
    void lease.promise.then(lease.release, lease.release)
    return lease.promise
  }
  return { get, set, load, acquire, setVersion }
}

// The shared cache is used only for browser navigation. SSR requests remain isolated.
export const pokemonListCache = createPokemonListCache(12)

export function hasPokemonFilters(query: PokemonListQuery): boolean {
  return Boolean(
    query.q ||
    query.type ||
    query.generation ||
    query.isLegendary ||
    query.isMythical ||
    query.isMega ||
    query.isGigantamax,
  )
}
