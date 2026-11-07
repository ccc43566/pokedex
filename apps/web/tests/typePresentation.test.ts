// @vitest-environment node
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'
import { isVisibleType, typeColors } from '../utils/typePresentation'
import { typePalette } from '../utils/typePalette'

describe('reviewed type presentation assets', () => {
  it('retains dark and hides only the two explicit legacy identifiers without mutating records', () => {
    const records = [{ name: 'dark' }, { name: 'shadow' }, { name: 'unknown' }]
    expect(records.filter(isVisibleType)).toEqual([{ name: 'dark' }])
    expect(records).toHaveLength(3)
    expect(isVisibleType(null)).toBe(false)
    expect(isVisibleType({ name: 'darkrai' })).toBe(true)
  })
  it('keeps all eighteen reviewed pairs in their original left/right order', () => {
    const source = JSON.parse(
      readFileSync(resolve('../../../design/type-palette/pokemon-type-colors.json'), 'utf8'),
    )
    expect(Object.keys(typePalette)).toHaveLength(19)
    for (const t of source.types)
      expect(typeColors(t.type)).toEqual({ icon: t.icon, label: t.label })
    expect(typeColors('stellar').icon).toContain('#C6F2FF')
    expect(typeColors('stellar').label).toContain('#286A85')
  })
  it('keeps the exact original stellar PNG and white glyph masks with black cutouts', () => {
    expect(readFileSync(resolve('public/type-icons/stellar.png'))).toEqual(
      readFileSync(resolve('../../../UI/icons/stellar.png')),
    )
    for (const name of Object.keys(typePalette).filter((n) => n !== 'stellar')) {
      const svg = readFileSync(resolve(`public/type-icons/${name}.svg`), 'utf8')
      expect(svg).toContain('<mask id="glyph"')
      expect(svg).not.toMatch(/<style|class=|r="128"/)
      expect(svg).toContain('fill="white"')
    }
    expect(readFileSync(resolve('public/type-icons/normal.svg'), 'utf8')).toContain('fill="black"')
  })
})
