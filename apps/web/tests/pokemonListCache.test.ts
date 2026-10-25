import { describe, expect, it } from 'vitest'
import type { PaginatedPokemon } from '../types/api'
import { createPokemonListCache, pokemonListKey, pokemonListQuery } from '../utils/pokemonListCache'

const list: PaginatedPokemon = {
  items: [],
  page: 1,
  pageSize: 0,
  total: 0,
  totalPages: 1,
  hasNext: false,
  hasPrevious: false,
}

describe('Pokémon list cache', () => {
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
