import { describe, expect, it } from 'vitest'
import { formatPrice } from '../utils/references'
import { browseContextKey, isBrowsePath } from '../utils/detailNavigation'

describe('reference browsing semantics', () => {
  it('distinguishes an explicit zero, unavailable scoped price and unknown value', () => {
    expect(formatPrice({ value: 0, status: 'value' }, false, true)).toBe('0')
    expect(formatPrice({ value: null, status: 'unavailable' }, true, true)).toBe('不可购买')
    expect(formatPrice({ value: null, status: 'unavailable' }, false, false)).toBe('Not sellable')
    expect(formatPrice({ value: null, status: 'unknown' }, true, true)).toBe('未提供')
  })
  it('normalizes old page URLs and shares drawer and relation scroll contexts', () => {
    const list = { path: '/zh-Hans/items', query: { page: '2', q: 'berry' } }
    const drawer = {
      ...list,
      query: { ...list.query, detail: '723', rel: 'holders', rel_page: '3' },
    }
    expect(browseContextKey(list)).toBe(browseContextKey(drawer))
    expect(browseContextKey(list)).toBe(
      browseContextKey({ ...list, query: { ...list.query, page: '3' } }),
    )
    expect(isBrowsePath('/zh-Hans/items')).toBe(true)
    expect(isBrowsePath('/en/moves')).toBe(true)
    expect(isBrowsePath('/en/moves/85')).toBe(false)
  })
})
