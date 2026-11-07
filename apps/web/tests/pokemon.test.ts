import { describe, expect, it } from 'vitest'
import { buildPokedexApiUrl } from '../composables/usePokedexApi'
import { conditionSummary, formatDexNumber, typeClass } from '../utils/pokemon'

describe('Pokémon format helpers', () => {
  it('formats national dex numbers', () => {
    expect(formatDexNumber(25)).toBe('#25')
    expect(formatDexNumber(1025)).toBe('#1025')
    expect(formatDexNumber('892.9')).toBe('#892.9')
    expect(formatDexNumber('892.10')).toBe('#892.10')
  })

  it('normalizes type CSS classes', () => {
    expect(typeClass('electric')).toBe('type-electric')
    expect(typeClass('')).toBe('type-unknown')
  })

  it('summarizes evolution conditions', () => {
    expect(conditionSummary({ min_level: 16, trigger: { name: 'level-up' } })).toEqual([
      'Lv.: 16',
      'Trigger: level up',
    ])
  })

  it('keeps trigger, zero stats, nested expressions, nature alternatives and version context', () => {
    const summary = conditionSummary({
      relative_physical_stats: 0,
      gender: 1,
      version_group: { name: 'scarlet-violet' },
      allowed_natures: [{ name: 'bold' }, { name: 'modest' }],
      condition_expression: { expression: 'EC 100 % 0 ==', percentage_chance: 1 },
      turn_upside_down: true,
    })
    expect(summary).toEqual([
      'Attack / Defense: Attack = Defense',
      'Gender: Female',
      'Introduced in: scarlet violet',
      'Allowed natures (any): bold / modest',
      'Additional expression: expression: EC 100 % 0 ==; percentage_chance: 1',
      'Turn console upside down: true',
    ])
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
