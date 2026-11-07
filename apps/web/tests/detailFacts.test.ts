import { describe, expect, it } from 'vitest'
import { genderRatio } from '../utils/detailFacts'

describe('species gender ratios', () => {
  it('distinguishes unknown, genderless, single-sex and eighth-based rates', () => {
    expect(genderRatio(null, 'zh-Hans')).toBe('—')
    expect(genderRatio(-1, 'zh-Hans')).toBe('无性别')
    expect(genderRatio(0, 'zh-Hans')).toBe('雄性 100% · 雌性 0%')
    expect(genderRatio(8, 'en')).toBe('Male 0% · Female 100%')
    expect(genderRatio(1, 'zh-Hans')).toBe('雄性 87.5% · 雌性 12.5%')
    expect(genderRatio(4, 'zh-Hans')).toBe('雄性 50% · 雌性 50%')
    expect(genderRatio(10, 'en')).toBe('—')
  })
})
