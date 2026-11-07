import { describe, it, expect } from 'vitest'
import { appearanceBackgrounds, normalizeAppearance } from '../utils/appearance'
describe('catalog backgrounds', () => {
  it('registers completed pairs as 11 choices while preserving both original defaults', () => {
    expect(appearanceBackgrounds).toHaveLength(13)
    expect(appearanceBackgrounds.filter((item) => item.mobileImage)).toHaveLength(8)
    expect(new Set(appearanceBackgrounds.map((item) => item.id)).size).toBe(13)
    expect(normalizeAppearance(null).backgrounds).toEqual({ day: 'day-1', night: 'night-1' })
    expect(appearanceBackgrounds.every((item) => !item.image || item.image.endsWith('.webp'))).toBe(
      true,
    )
  })
  it('keeps valid stored selections and independent opacity, and rejects invalid modes and IDs', () => {
    const stored = normalizeAppearance({
      mode: 'night',
      backgrounds: { day: 'day-red', night: 'night-red-pikachu' },
      opacity: { day: 0, night: 88 },
    })
    expect(stored.backgrounds).toEqual({ day: 'day-red', night: 'night-red-pikachu' })
    expect(stored.opacity).toEqual({ day: 0, night: 88 })
    expect(
      normalizeAppearance({ mode: 'no', backgrounds: { day: 'missing', night: 'day-red' } })
        .backgrounds,
    ).toEqual({ day: 'day-1', night: 'night-1' })
  })
  it('saves per-image dimming independently of card opacity and rejects invalid saved values', () => {
    const stored = normalizeAppearance({
      dimming: {
        'day-red': 36,
        'night-groudon': 200,
        'day-blue': -3,
        'day-green': NaN,
        missing: 44,
      },
      opacity: { day: 0, night: 88 },
    })
    expect(stored.dimming).toEqual({ 'day-red': 36, 'night-groudon': 80, 'day-blue': 0 })
    expect(stored.opacity).toEqual({ day: 0, night: 88 })
  })
})
