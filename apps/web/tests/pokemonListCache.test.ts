import { describe, expect, it } from 'vitest'
import type { PaginatedPokemon } from '../types/api'
import {
  createPokemonListCache,
  hasPokemonFilters,
  pokemonListKey,
  pokemonListQuery,
} from '../utils/pokemonListCache'

const list: PaginatedPokemon = {
  items: [],
  page: 1,
  pageSize: 0,
  total: 0,
  totalPages: 1,
  hasNext: false,
  hasPrevious: false,
}

it('cancels only the final lease and discards aborted responses', async () => {
  const cache = createPokemonListCache()
  let signal!: AbortSignal
  let resolve!: (value: PaginatedPokemon) => void
  let calls = 0
  const fetcher = (s: AbortSignal) => {
    calls++
    signal = s
    return new Promise<PaginatedPokemon>((done) => { resolve = done })
  }
  const first = cache.acquire('same', fetcher)
  const second = cache.acquire('same', fetcher)
  expect(calls).toBe(1)
  first.release()
  expect(signal.aborted).toBe(false)
  second.release()
  expect(signal.aborted).toBe(true)
  resolve(list)
  await first.promise
  expect(cache.get('same')).toBeUndefined()
})

it('expires old versions and retries failed requests', async () => {
  let now = 0
  const cache = createPokemonListCache(3, 100, () => now)
  cache.setVersion('v1')
  cache.set('old', { ...list, dataVersion: 'v1' })
  expect(cache.get('old')).toBeDefined()
  now = 101
  expect(cache.get('old')).toBeUndefined()
  cache.set('old', { ...list, dataVersion: 'v1' })
  cache.setVersion('v2')
  expect(cache.get('old')).toBeUndefined()
  cache.set('late', { ...list, dataVersion: 'v1' })
  expect(cache.get('late')).toBeUndefined()
  await expect(cache.load('fail', async () => { throw new Error('offline') })).rejects.toThrow('offline')
  const current = { ...list, dataVersion: 'v2' }
  expect(await cache.load('fail', async () => current)).toBe(current)
})

it('does not share an old in-flight response with consumers of a new revision', async () => {
  const cache = createPokemonListCache()
  cache.setVersion('v1')
  let resolve!: (value: PaginatedPokemon) => void
  const old = cache.acquire('same', () => new Promise((done) => { resolve = done }))
  cache.setVersion('v2')
  const current = { ...list, dataVersion: 'v2' }
  const fresh = cache.acquire('same', async () => current)
  expect(await fresh.promise).toBe(current)
  resolve({ ...list, dataVersion: 'v1' })
  await old.promise
  expect(cache.get('same')).toBe(current)
  old.release()
  fresh.release()
})

describe('Pokémon list cache', () => {
  it('distinguishes directory browsing from global form filters and caches each combination', () => {
    const directory = pokemonListQuery({ detail: '6', sort: 'id' }, 'zh-Hans')
    expect(hasPokemonFilters(directory)).toBe(false)
    const mega = pokemonListQuery({ isMega: 'true' }, 'zh-Hans')
    const gmax = pokemonListQuery({ isGigantamax: 'true' }, 'zh-Hans')
    const both = pokemonListQuery({ isMega: 'true', isGigantamax: 'true' }, 'zh-Hans')
    for (const query of [mega, gmax, both]) expect(hasPokemonFilters(query)).toBe(true)
    expect(new Set([directory, mega, gmax, both].map(pokemonListKey)).size).toBe(4)
    expect(hasPokemonFilters(pokemonListQuery({ isMega: 'false' }, 'zh-Hans'))).toBe(false)
  })
  it('keys applied filters and language, ignoring old page and drawer parameters', () => {
    const query = pokemonListQuery(
      { q: ' Pikachu ', type: 'electric', page: '2', detail: '25' },
      'zh-Hans',
    )
    expect(query.q).toBe('Pikachu')
    expect(pokemonListKey(query)).toBe(
      pokemonListKey(pokemonListQuery({ q: 'Pikachu', type: 'electric' }, 'zh-Hans')),
    )
    expect(pokemonListKey(query)).not.toBe(pokemonListKey({ ...query, locale: 'en' }))
    expect(pokemonListKey(query)).not.toBe(pokemonListKey({ ...query, isLegendary: true }))
  })

  it('reuses an in-flight list and keeps only recent filter results', async () => {
    const cache = createPokemonListCache(2)
    let resolve!: (value: PaginatedPokemon) => void
    let calls = 0
    const fetchList = () => {
      calls++
      return new Promise<PaginatedPokemon>((done) => {
        resolve = done
      })
    }
    const first = cache.load('first', fetchList)
    expect(cache.load('first', fetchList)).toBe(first)
    expect(calls).toBe(1)
    resolve(list)
    await first
    cache.set('second', list)
    cache.get('first')
    cache.set('third', list)
    expect(cache.get('first')).toBe(list)
    expect(cache.get('second')).toBeUndefined()
  })
})
