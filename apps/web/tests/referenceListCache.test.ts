import { describe, expect, it } from 'vitest'
import {
  createReferenceListCache,
  referenceListKey,
  referenceListQuery,
} from '../utils/referenceListCache'
import type { ReferencePage, ReferenceCard } from '../types/references'

function page(n: number, total = 350): ReferencePage {
  return {
    items: Array.from(
      { length: Math.min(100, Math.max(0, total - (n - 1) * 100)) },
      (_, i) => ({ id: (n - 1) * 100 + i + 1 }) as ReferenceCard,
    ),
    page: n,
    pageSize: 100,
    total,
    totalPages: Math.ceil(total / 100),
  }
}
describe('continuous list checkpoints and bounded caches', () => {
  it('normalizes only applied fields, isolates resource/locale and ignores details and old pages', () => {
    const key = (
      raw: Record<string, string>,
      kind: 'items' | 'moves' = 'items',
      locale = 'zh-Hans',
    ) => referenceListKey(kind, referenceListQuery(kind, locale, raw))
    expect(key({ q: ' BERRY ', sort: 'id', pocket: '05', detail: '723', page: '9' })).toBe(
      key({ pocket: '5', q: 'berry' }),
    )
    expect(key({ category: '', sort: '' })).toBe(key({}))
    expect(key({})).not.toBe(key({}, 'moves'))
    expect(key({})).not.toBe(key({}, 'items', 'en'))
  })
  it('coalesces first/full fetches, bounds concurrency and publishes only a sorted contiguous prefix', async () => {
    const cache = createReferenceListCache({ concurrency: 2 })
    const calls: number[] = [],
      visible: number[][] = []
    let active = 0,
      peak = 0
    const fetcher = async (n: number) => {
      calls.push(n)
      active++
      peak = Math.max(peak, active)
      await new Promise((r) => setTimeout(r, n === 2 ? 15 : 1))
      active--
      return page(n)
    }
    cache.subscribe('x', (s) => visible.push(s.items.map((r) => r.id)))
    const first = cache.first('x', fetcher)
    const a = cache.load('x', fetcher)
    expect(cache.load('x', fetcher)).toBe(a)
    await first
    await a
    expect(calls.sort()).toEqual([1, 2, 3, 4])
    expect(peak).toBe(2)
    for (const ids of visible)
      expect(ids).toEqual(Array.from({ length: ids.length }, (_, i) => i + 1))
    expect(cache.peek('x')?.items).toHaveLength(350)
    await cache.load('x', fetcher)
    expect(calls).toHaveLength(4)
  })
  it('keeps successful out-of-order pages on failure and retries only missing pages', async () => {
    const cache = createReferenceListCache()
    const calls: number[] = []
    let fail = true
    const fetcher = async (n: number) => {
      calls.push(n)
      if (n === 2 && fail) throw Error('network')
      return page(n)
    }
    await expect(cache.load('x', fetcher)).rejects.toThrow()
    expect(cache.peek('x')).toMatchObject({ error: true, loading: false, loadedPages: [1, 3, 4] })
    expect(cache.peek('x')?.items).toHaveLength(100)
    fail = false
    await cache.load('x', fetcher)
    expect(calls.filter((n) => n === 1)).toHaveLength(1)
    expect(calls.filter((n) => n === 2)).toHaveLength(2)
    expect(cache.peek('x')).toMatchObject({ complete: true, error: false, loading: false })
  })
  it('uses LRU capacity, expiry and explicit invalidation without poisoning fresh requests', async () => {
    let time = 0
    const cache = createReferenceListCache({ capacity: 3, ttl: 10, now: () => time })
    const fetcher = async () => page(1, 1)
    for (const k of ['a', 'b', 'c']) await cache.load(k, fetcher)
    cache.peek('a')
    await cache.load('d', fetcher)
    expect(cache.peek('b')).toBeUndefined()
    expect(cache.peek('a')?.complete).toBe(true)
    time = 11
    expect(cache.peek('a')).toBeUndefined()
    await cache.load('a', fetcher)
    cache.invalidate('a')
    expect(cache.peek('a')).toBeUndefined()
    await cache.load('a', fetcher)
    expect(cache.peek('a')?.complete).toBe(true)
  })
  it('evicted or invalidated responses cannot change their replacement and pending is cleared', async () => {
    const cache = createReferenceListCache()
    let release!: (p: ReferencePage) => void
    const old = cache.load(
      'x',
      () =>
        new Promise((r) => {
          release = r
        }),
    )
    await Promise.resolve()
    cache.invalidate('x')
    const fresh = cache.load('x', async () => page(1, 2))
    release(page(1, 1))
    await expect(old).rejects.toThrow()
    await fresh
    expect(cache.peek('x')).toMatchObject({ total: 2, complete: true, loading: false })
  })
  it('supports empty results and isolates SSR store instances', async () => {
    const a = createReferenceListCache(),
      b = createReferenceListCache()
    await a.load('x', async () => page(1, 0))
    expect(a.peek('x')).toMatchObject({ total: 0, items: [], complete: true })
    expect(b.peek('x')).toBeUndefined()
  })
})
