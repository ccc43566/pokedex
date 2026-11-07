import type { ReferenceKind, ReferencePage, ReferenceCard } from '~/types/references'
import { createListCache } from './listCache'

type QueryValue = string | null | readonly (string | null)[] | undefined
export function referenceListQuery(
  kind: ReferenceKind,
  locale: string,
  raw: Record<string, QueryValue>,
) {
  const one = (key: string) => {
    const v = raw[key]
    return typeof v === 'string' ? v : Array.isArray(v) ? v[0] || '' : ''
  }
  const sorts =
    kind === 'items'
      ? ['id', 'id_desc', 'name']
      : ['id', 'id_desc', 'name', 'power_desc', 'priority_desc']
  const query: Record<string, string | number> = {
    locale,
    q: one('q').trim().toLowerCase(),
    sort: sorts.includes(one('sort')) ? one('sort') : 'id',
  }
  for (const key of kind === 'items'
    ? ['category', 'pocket']
    : ['type', 'damage_class', 'generation']) {
    const value = Number(one(key))
    if (Number.isSafeInteger(value) && value > 0) query[key] = value
  }
  return query
}
export function referenceListKey(kind: ReferenceKind, query: Record<string, string | number>) {
  return JSON.stringify([
    kind,
    ...Object.keys(query)
      .sort()
      .map((key) => [key, query[key]]),
  ])
}
export interface ReferenceListState {
  items: ReferenceCard[]
  total: number
  loadedPages: number[]
  complete: boolean
  loading: boolean
  error: boolean
}
type FetchPage = (page: number, signal: AbortSignal) => Promise<ReferencePage>
interface Entry {
  created: number
  pages: Map<number, ReferencePage>
  pending: Map<number, Promise<ReferencePage>>
  controller: AbortController
  listeners: Set<(state: ReferenceListState) => void>
  running?: Promise<ReferenceListState>
  loading: boolean
  error: boolean
}

export function createReferenceListCache({
  capacity = 3,
  ttl = 600_000,
  now = Date.now,
  concurrency = 4,
} = {}) {
  const cache = createListCache<Entry>(capacity, (e) => {
    e.controller.abort()
    e.listeners.clear()
  })
  // A resource-wide pool also bounds requests across quickly changing queries.
  let active = 0
  const queue: (() => void)[] = []
  async function pooled<T>(run: () => Promise<T>): Promise<T> {
    if (active >= concurrency) await new Promise<void>((resolve) => queue.push(resolve))
    else active++
    try {
      return await run()
    } finally {
      const next = queue.shift()
      if (next) next()
      else active--
    }
  }
  function entry(key: string, seed?: ReferencePage): Entry {
    let e = cache.get(key)
    if (e && now() - e.created >= ttl) {
      cache.remove(key)
      e = undefined
    }
    if (!e) {
      e = {
        created: now(),
        pages: new Map(),
        pending: new Map(),
        controller: new AbortController(),
        listeners: new Set(),
        loading: false,
        error: false,
      }
      if (seed) e.pages.set(1, seed)
      cache.set(key, e)
    }
    return e
  }
  function snapshot(e: Entry): ReferenceListState {
    const first = e.pages.get(1)
    const items: ReferenceCard[] = []
    const ids = new Set<number>()
    // Only the contiguous prefix is visible; later pages may finish first.
    for (let p = 1; e.pages.has(p); p++)
      for (const item of e.pages.get(p)!.items) {
        if (!ids.has(item.id)) {
          ids.add(item.id)
          items.push(item)
        }
      }
    return {
      items,
      total: first?.total || 0,
      loadedPages: [...e.pages.keys()].sort((a, b) => a - b),
      complete: Boolean(first && e.pages.size >= first.totalPages && items.length === first.total),
      loading: e.loading,
      error: e.error,
    }
  }
  function publish(e: Entry) {
    const state = snapshot(e)
    for (const listener of e.listeners) listener(state)
  }
  function batch(e: Entry, page: number, fetcher: FetchPage): Promise<ReferencePage> {
    if (e.pages.has(page)) return Promise.resolve(e.pages.get(page)!)
    const existing = e.pending.get(page)
    if (existing) return existing
    const request = pooled(async () => {
      e.controller.signal.throwIfAborted()
      const result = await fetcher(page, e.controller.signal)
      e.controller.signal.throwIfAborted()
      if (result.page !== page || result.pageSize !== 100 || result.items.length > 100)
        throw new Error('Invalid list batch')
      const first = e.pages.get(1)
      if (first && (first.total !== result.total || first.totalPages !== result.totalPages))
        throw new Error('List changed; reload required')
      e.pages.set(page, result)
      publish(e)
      return result
    }).finally(() => e.pending.delete(page))
    e.pending.set(page, request)
    return request
  }
  async function first(key: string, fetcher: FetchPage) {
    return batch(entry(key), 1, fetcher)
  }
  function load(
    key: string,
    fetcher: FetchPage,
    seed?: ReferencePage,
  ): Promise<ReferenceListState> {
    const e = entry(key, seed)
    if (e.running) return e.running
    if (snapshot(e).complete) return Promise.resolve(snapshot(e))
    e.loading = true
    e.error = false
    publish(e)
    const work = (async () => {
      try {
        const initial = await batch(e, 1, fetcher)
        const missing = Array.from(
          { length: Math.max(0, initial.totalPages - 1) },
          (_, i) => i + 2,
        ).filter((p) => !e.pages.has(p))
        let next = 0
        let failed = false
        await Promise.all(
          Array.from({ length: Math.min(concurrency, missing.length) }, async () => {
            while (next < missing.length && !e.controller.signal.aborted) {
              const p = missing[next++]!
              try {
                await batch(e, p, fetcher)
              } catch {
                failed = true
              }
            }
          }),
        )
        if (failed || !snapshot(e).complete) throw new Error('Incomplete list; retry or reload')
        return snapshot(e)
      } catch (error) {
        e.error = !e.controller.signal.aborted
        throw error
      } finally {
        e.loading = false
        e.running = undefined
        publish(e)
      }
    })()
    e.running = work
    return work
  }
  return {
    first,
    load,
    peek(key: string) {
      const e = cache.get(key)
      if (!e) return
      if (now() - e.created >= ttl) {
        cache.remove(key)
        return
      }
      return snapshot(e)
    },
    subscribe(key: string, listener: (state: ReferenceListState) => void, seed?: ReferencePage) {
      const e = entry(key, seed)
      e.listeners.add(listener)
      listener(snapshot(e))
      return () => {
        e.listeners.delete(listener)
      }
    },
    invalidate(key: string) {
      cache.remove(key)
    },
  }
}

// Never access these stores from SSR: each SSR component creates its own instance.
export const referenceListCaches = {
  items: createReferenceListCache(),
  moves: createReferenceListCache(),
}
