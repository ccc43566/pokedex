import type { ReferenceKind, ReferencePage } from '~/types/references'
import {
  createReferenceListCache,
  referenceListCaches,
  referenceListKey,
  referenceListQuery,
  type ReferenceListState,
} from '~/utils/referenceListCache'

export function useReferenceList(kind: ReferenceKind) {
  const route = useRoute()
  const router = useRouter()
  const { locale } = useI18n()
  const { fetchApi } = usePokedexApi()
  const cache = import.meta.client ? referenceListCaches[kind] : createReferenceListCache()
  const query = computed(() => referenceListQuery(kind, locale.value, route.query))
  const key = computed(() => referenceListKey(kind, query.value))
  const initialKey = key.value
  const initialQuery = { ...query.value }
  const fetcher =
    (params: Record<string, string | number>) => (page: number, signal: AbortSignal) =>
      fetchApi<ReferencePage>(`/${kind}`, {
        params: { ...params, page, page_size: 100 },
        signal,
        retry: 0,
      })
  const ready = useAsyncData(
    `reference-first-${initialKey}`,
    () => cache.first(initialKey, fetcher(initialQuery)),
    { getCachedData: (k, app) => (app.isHydrating ? app.payload.data[k] : undefined) },
  )
  const { data: initial, error: initialError } = ready
  const state = shallowRef<ReferenceListState>({
    items: initial.value?.items || [],
    total: initial.value?.total || 0,
    loadedPages: initial.value ? [1] : [],
    complete: Boolean(initial.value && initial.value.totalPages <= 1),
    loading: false,
    error: Boolean(initialError.value),
  })
  let alive = false
  const hydrated = ref(false)
  watch(
    [initial, initialError],
    () => {
      if (!alive)
        state.value = {
          items: initial.value?.items || [],
          total: initial.value?.total || 0,
          loadedPages: initial.value ? [1] : [],
          complete: Boolean(initial.value && initial.value.totalPages <= 1),
          loading: !initial.value && !initialError.value,
          error: Boolean(initialError.value),
        }
    },
    { immediate: true, flush: 'sync' },
  )
  let unsubscribe: (() => void) | undefined
  function activate(seed?: ReferencePage) {
    unsubscribe?.()
    const currentKey = key.value
    unsubscribe = cache.subscribe(
      currentKey,
      (next) => {
        if (alive && key.value === currentKey) state.value = next
      },
      seed,
    )
    void cache.load(currentKey, fetcher({ ...query.value })).catch(() => {})
  }
  onMounted(() => {
    alive = true
    hydrated.value = true
    activate(initial.value || undefined)
    if (route.query.page !== undefined)
      void router.replace({ path: route.path, query: { ...route.query, page: undefined } })
    window.addEventListener('focus', revalidate)
  })
  watch(
    key,
    () => {
      if (alive) activate()
    },
    { flush: 'sync' },
  )
  onUnmounted(() => {
    alive = false
    unsubscribe?.()
    window.removeEventListener('focus', revalidate)
    // The bounded list store owns reuse; do not retain extra first batches in Nuxt's payload.
    ready.clear()
  })
  function revalidate() {
    if (!cache.peek(key.value)) activate()
  }
  function retry() {
    void cache.load(key.value, fetcher({ ...query.value })).catch(() => {})
  }
  function reload() {
    cache.invalidate(key.value)
    activate()
  }
  // Do not delay ordinary browsing. Deep restoration waits for sufficient rendered content.
  const waiters = new Set<() => void>()
  async function whenReady(top?: number) {
    if (!top || top <= 0) return
    const current = key.value
    await new Promise<void>((resolve) => {
      const done = () => {
        stop()
        waiters.delete(done)
        resolve()
      }
      waiters.add(done)
      const check = () => {
        if (
          key.value !== current ||
          state.value.complete ||
          document.documentElement.scrollHeight >= top + innerHeight
        )
          done()
      }
      const stop = watch([state, key], check, { flush: 'post' })
      void nextTick(check)
    })
  }
  onScopeDispose(() => {
    for (const done of waiters) done()
  })
  return { state, query, key, retry, reload, whenReady, ready, hydrated }
}
