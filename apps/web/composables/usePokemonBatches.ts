import type { PaginatedPokemon, PokemonListItem } from '~/types/api'
import { pokemonListCache, pokemonListKey, type PokemonListQuery } from '~/utils/pokemonListCache'

export const pokemonBatchSize = 48

export function usePokemonBatches(
  query: ComputedRef<PokemonListQuery | null>,
  initial: PaginatedPokemon | null,
) {
  const { fetchApi } = usePokedexApi()
  const route = useRoute()
  const key = computed(() => (query.value ? pokemonListKey(query.value) : ''))
  let displayedKey = key.value
  const data = shallowRef<PaginatedPokemon | null>(initial)
  const placeholders = shallowRef<PokemonListItem[]>([])
  const pending = ref(false)
  const failed = ref(false)
  let retryMore = false
  const restoring = ref(false)
  const requests = new Map<string, { promise: Promise<PaginatedPokemon>; controller: AbortController }>()
  let firstLease: { release: () => void } | undefined
  let revisionController: AbortController | undefined
  let revision: string | undefined
  function cancelRequests() {
    firstLease?.release()
    firstLease = undefined
    revisionController?.abort()
    for (const entry of requests.values()) entry.controller.abort()
    requests.clear()
  }
  const prepared = new Map<string, PaginatedPokemon>()
  let alive = true
  let operation = 0
  let idleTask: ReturnType<typeof setTimeout> | undefined
  let warming = 0

  // Allow the browser to paint between groups. A microtask/nextTick alone keeps
  // Vue mounting in the same long task as the network response.
  function nextPaint(): Promise<void> {
    return new Promise((resolve) => requestAnimationFrame(() => setTimeout(resolve, 0)))
  }
  function whenIdle(): Promise<void> {
    return new Promise((resolve) => {
      if ('requestIdleCallback' in window)
        window.requestIdleCallback(() => resolve(), { timeout: 150 })
      else setTimeout(resolve, 32)
    })
  }
  async function publish(list: PaginatedPokemon, targetKey: string, ticket: number) {
    let count = data.value?.items.length || 0
    // The active key is checked both before and after yielding; old requests
    // cannot append cards to a newly selected generation or filtered result.
    while (count < list.items.length) {
      if (!alive || key.value !== targetKey || ticket !== operation) return
      count = Math.min(count + 8, list.items.length)
      placeholders.value = list.items.slice(count)
      data.value = { ...list, items: list.items.slice(0, count) }
      await nextTick()
      if (count < list.items.length) await nextPaint()
    }
    if (alive && key.value === targetKey && ticket === operation) data.value = list
  }

  function prepareNext() {
    clearTimeout(idleTask)
    const target = query.value
    const current = data.value
    const targetKey = key.value
    const version = ++warming
    const connection = (navigator as Navigator & { connection?: { saveData?: boolean } }).connection
    if (!target || !current?.hasNext || connection?.saveData) return
    idleTask = setTimeout(async () => {
      await whenIdle()
      if (
        !alive ||
        version !== warming ||
        key.value !== targetKey ||
        route.query.detail ||
        document.hidden
      )
        return
      try {
        const next = await requestPage(target, current.page + 1)
        // Decode a bounded number of the nearest upcoming images, two at a
        // time during idle periods. Keep distant artwork under native lazy load.
        for (let offset = 0; offset < Math.min(16, next.items.length); offset += 2) {
          await whenIdle()
          if (
            !alive ||
            version !== warming ||
            key.value !== targetKey ||
            route.query.detail ||
            document.hidden
          )
            return
          await Promise.all(
            next.items.slice(offset, offset + 2).map(async (pokemon) => {
              const src = pokemon.artworkUrl || pokemon.spriteUrl
              if (!src) return
              const image = new Image()
              image.decoding = 'async'
              image.fetchPriority = 'low'
              image.src = src
              await image.decode().catch(() => {})
            }),
          )
        }
      } catch {
        // Background speculation must not interrupt the current list. A real
        // demand retries the failed page and exposes the existing retry button.
      }
    }, 120)
  }

  function rememberPages(listKey: string, page: number) {
    try {
      sessionStorage.setItem(`pokedex:batches:${listKey}`, String(page))
    } catch {
      /* Optional storage. */
    }
  }
  function savedPages(listKey: string): number {
    try {
      return Math.min(
        40,
        Math.max(1, Number(sessionStorage.getItem(`pokedex:batches:${listKey}`)) || 1),
      )
    } catch {
      return 1
    }
  }
  function requestPage(target: PokemonListQuery, page: number) {
    const listKey = pokemonListKey(target)
    const requestKey = `${listKey}:${page}`
    const cached = prepared.get(requestKey)
    if (cached) return Promise.resolve(cached)
    const existing = requests.get(requestKey)
    if (existing) return existing.promise
    const controller = new AbortController()
    const request = fetchApi<PaginatedPokemon>('/pokemon', {
      params: { ...target, page, pageSize: pokemonBatchSize },
      signal: controller.signal,
      retry: 0,
    })
      .then((list) => {
        if (controller.signal.aborted || (revision && list.dataVersion !== revision)) return list
        prepared.set(requestKey, list)
        while (prepared.size > 12) prepared.delete(prepared.keys().next().value!)
        return list
      })
      .finally(() => {
        if (requests.get(requestKey)?.promise === request) requests.delete(requestKey)
      })
    requests.set(requestKey, { promise: request, controller })
    return request
  }
  async function activate() {
    const ticket = ++operation
    cancelRequests()
    ++warming
    clearTimeout(idleTask)
    const target = query.value
    const targetKey = key.value
    failed.value = false
    retryMore = false
    if (!target) {
      data.value = null
      placeholders.value = []
      displayedKey = ''
      pending.value = false
      return
    }
    if (displayedKey !== targetKey) {
      data.value = null
      placeholders.value = []
    }
    displayedKey = targetKey
    pending.value = true
    try {
      revisionController = new AbortController()
      const current = await fetchApi<{ version: string }>('/pokemon/revision', {
        signal: revisionController.signal, retry: 0,
      })
      if (!alive || ticket !== operation || key.value !== targetKey) return
      if (revision !== current.version) prepared.clear()
      revision = current.version
      pokemonListCache.setVersion(revision)
      // A shared first batch belongs to its leases, not this component's
      // private prefetch pool. Release cancels it only when nobody needs it.
      const lease = pokemonListCache.acquire(targetKey, (signal) =>
        fetchApi<PaginatedPokemon>('/pokemon', {
          params: { ...target, page: 1, pageSize: pokemonBatchSize }, signal, retry: 0,
        }),
      )
      firstLease = lease
      let result: PaginatedPokemon
      try { result = await lease.promise } finally { lease.release() }
      if (!alive || ticket !== operation || key.value !== targetKey) return
      if (result.dataVersion !== revision) {
        // A sync committed between revision validation and the list response.
        revision = result.dataVersion || undefined
        if (revision) pokemonListCache.setVersion(revision)
        prepared.clear()
        pokemonListCache.set(targetKey, result)
      }
      if (alive && key.value === targetKey && ticket === operation) {
        await publish(result, targetKey, ticket)
        prepareNext()
      }
    } catch {
      if (alive && key.value === targetKey && ticket === operation) {
        failed.value = true
      }
    } finally {
      if (alive && key.value === targetKey && ticket === operation) pending.value = false
    }
  }
  async function loadMore() {
    const target = query.value
    const current = data.value
    const targetKey = key.value
    if (!target || !current || !current.hasNext || pending.value) return
    const ticket = ++operation
    pending.value = true
    failed.value = false
    try {
      const next = await requestPage(target, current.page + 1)
      if (!alive || ticket !== operation || key.value !== targetKey) return
      if (next.dataVersion !== current.dataVersion) { await activate(); return }
      const result = { ...next, items: [...current.items, ...next.items] }
      pokemonListCache.set(targetKey, result)
      rememberPages(targetKey, result.page)
      if (alive && key.value === targetKey && ticket === operation) {
        await publish(result, targetKey, ticket)
        prepareNext()
      }
    } catch {
      if (alive && key.value === targetKey && ticket === operation) {
        retryMore = true
        failed.value = true
      }
    } finally {
      if (alive && key.value === targetKey && ticket === operation) pending.value = false
    }
  }
  async function restore(top?: number) {
    restoring.value = true
    const targetKey = key.value
    await activate()
    if (top && top > 0 && targetKey) {
      const pages = savedPages(targetKey)
      while (alive && key.value === targetKey && data.value?.hasNext && data.value.page < pages) {
        await loadMore()
        if (failed.value) break
      }
    }
    restoring.value = false
  }
  watch(key, () => {
    if (import.meta.client) void activate()
  })
  onMounted(() => {
    if (
      initial &&
      key.value &&
      (!pokemonListCache.get(key.value) || pokemonListCache.get(key.value)!.page < initial.page)
    ) {
      pokemonListCache.set(key.value, initial)
    }
  })
  onUnmounted(() => {
    alive = false
    cancelRequests()
    ++operation
    ++warming
    clearTimeout(idleTask)
  })
  return {
    data,
    placeholders,
    pending,
    failed,
    restoring,
    restore,
    loadMore,
    retry: () => (retryMore ? loadMore() : activate()),
  }
}
