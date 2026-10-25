import { describe, expect, it } from 'vitest'
import { buildPokedexApiUrl } from '../composables/usePokedexApi'
import { conditionSummary, formatDexNumber, typeClass } from '../utils/pokemon'

describe('Pokémon format helpers', () => {
  it('formats national dex numbers', () => {
    expect(formatDexNumber(25)).toBe('#0025')
    expect(formatDexNumber(1025)).toBe('#1025')
  })

  it('normalizes type CSS classes', () => {
    expect(typeClass('electric')).toBe('type-electric')
    expect(typeClass('')).toBe('type-unknown')
  })

  it('summarizes evolution conditions', () => {
    expect(conditionSummary({ min_level: 16, trigger: { name: 'level-up' } })).toEqual(['Lv.: 16'])
  })

  it('builds the browser API path without duplicating /api', () => {
    expect(buildPokedexApiUrl('/pokemon', { server: false })).toBe('/api/v1/pokemon')
    expect(buildPokedexApiUrl('pokemon', { publicApiBase: '/api/' })).toBe('/api/v1/pokemon')
  })

  it('builds the server API path from the internal API base', () => {
    expect(
      buildPokedexApiUrl('/pokemon', {
        server: true,
        apiBase: 'http://api:8000',
      }),
    ).toBe('http://api:8000/api/v1/pokemon')
  })
})
