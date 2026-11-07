// @vitest-environment node
import { createHash } from 'node:crypto'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'
import { nightVisitors, nightVisitorName } from '../utils/nightHome'

describe('homepage curated data and approved artwork', () => {
  it('keeps the 28 independent IDs, real display numbers and existing SHA-256 media addresses', () => {
    expect(nightVisitors).toHaveLength(28)
    expect(new Set(nightVisitors.map((row) => row.id)).size).toBe(28)
    expect(nightVisitors[0]?.id).toBe(711)
    for (const row of nightVisitors) {
      expect(row.displayNumber).toMatch(/^\d+(?:\.\d+)?$/)
      expect(row.sprite).toMatch(/^\/media\/version-sprites\/[a-f0-9]{2}\/[a-f0-9]{64}\.png$/)
      if (row.animation)
        expect(row.animation.path).toMatch(
          /^\/media\/version-sprites\/[a-f0-9]{2}\/[a-f0-9]{64}\.gif$/,
        )
      expect(nightVisitorName(row, 'zh-Hans')).toBe(row.name)
      expect(nightVisitorName(row, 'en')).toBe(row.englishName)
      expect(row.englishName).not.toMatch(/[\u4e00-\u9fff]/)
    }
    expect(nightVisitors.filter((row) => row.animation)).toHaveLength(26)
  })
  it('retains byte-identical original background, edge assets and licensed font', () => {
    const hash = (file: string) =>
      createHash('sha256')
        .update(readFileSync(resolve(file)))
        .digest('hex')
    for (const file of [
      'observatory-night.png',
      'catalog-border.svg',
      'edge-branches.svg',
      'frame-edge-mask.svg',
      'moving-bush.svg',
    ]) {
      expect(hash(`public/home/night/${file}`)).toBe(
        hash(`../../../design/halloween-native-review/assets/${file}`),
      )
    }
    expect(hash('public/home/night/Baloo2-variable.ttf')).toBe(
      hash('../../../design/logo-review/fonts/Baloo2-variable.ttf'),
    )
    expect(readFileSync('public/home/night/OFL.txt', 'utf8')).toContain('SIL OPEN FONT LICENSE')
  })
})
