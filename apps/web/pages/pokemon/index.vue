<script setup lang="ts">
import type { GenerationSummary, PaginatedPokemon, TypeSummary } from '~/types/api'
import { onBeforeRouteUpdate } from 'vue-router'
import {
  pokemonListCache,
  pokemonListKey,
  pokemonListQuery,
  type PokemonListQuery,
} from '~/utils/pokemonListCache'

const { t, locale } = useI18n()
const route = useRoute()
const router = useRouter()
const localePath = useLocalePath()
const { fetchApi } = usePokedexApi()
const toast = useToast()
const allFilters = '__all__'
const batchSize = 100 // The current API caps pageSize at 100.
const filterAnchor = ref<HTMLElement | null>(null)
const filterStuck = ref(false)
const filtersExpanded = ref(false)

const filters = reactive({
  q: String(route.query.q || ''),
  type: String(route.query.type || allFilters),
  generation: String(route.query.generation || allFilters),
  sort: String(route.query.sort || 'id'),
  legendary: route.query.isLegendary === 'true',
  mythical: route.query.isMythical === 'true',
})

async function fetchAllPokemon(
  query: PokemonListQuery,
  initial?: PaginatedPokemon,
): Promise<PaginatedPokemon> {
  const first =
    initial ||
    (await fetchApi<PaginatedPokemon>('/pokemon', {
      params: { ...query, page: 1, pageSize: batchSize },
    }))
  if (first.totalPages <= 1)
    return { ...first, pageSize: first.total, totalPages: 1, hasNext: false }

  const pages: PaginatedPokemon[] = Array(first.totalPages)
  pages[0] = first
  let nextPage = 2
  await Promise.all(
    Array.from({ length: Math.min(4, first.totalPages - 1) }, async () => {
      while (nextPage <= first.totalPages) {
        const page = nextPage++
        pages[page - 1] = await fetchApi<PaginatedPokemon>('/pokemon', {
          params: { ...query, page, pageSize: batchSize },
        })
      }
    }),
  )
  return {
    ...first,
    items: pages.flatMap((batch) => batch.items),
    page: 1,
    pageSize: first.total,
    totalPages: 1,
    hasNext: false,
    hasPrevious: false,
  }
}

const initialQuery = pokemonListQuery(route.query, locale.value)
const initialKey = pokemonListKey(initialQuery)
const {
  data: initialData,
  pending,
  error,
} = await useAsyncData(`pokemon-first-${initialKey}`, () =>
  fetchApi<PaginatedPokemon>('/pokemon', {
    params: { ...initialQuery, page: 1, pageSize: batchSize },
  }),
)
const data = shallowRef<PaginatedPokemon | null>(null)
const hydrated = ref(false)
const loadingAll = ref(Boolean(initialData.value && initialData.value.totalPages > 1))
const loadError = ref(false)
const displayedKey = ref(initialKey)
const navigating = ref(false)

function localeForPath(path: string): string {
  return path === '/en' || path.startsWith('/en/') ? 'en' : 'zh-Hans'
}

function appliedQuery(): PokemonListQuery {
  return pokemonListQuery(route.query, locale.value)
}

function syncDraft(query: PokemonListQuery) {
  filters.q = query.q || ''
  filters.type = query.type || allFilters
  filters.generation = query.generation ? String(query.generation) : allFilters
  filters.sort = query.sort
  filters.legendary = Boolean(query.isLegendary)
  filters.mythical = Boolean(query.isMythical)
}

function loadList(query: PokemonListQuery): Promise<PaginatedPokemon> {
  const initial = pokemonListKey(query) === initialKey ? initialData.value || undefined : undefined
  return pokemonListCache.load(pokemonListKey(query), () => fetchAllPokemon(query, initial))
}

async function loadInitialList() {
  if (!initialData.value || data.value?.items.length === data.value?.total) return
  loadingAll.value = true
  loadError.value = false
  try {
    const list = await loadList(initialQuery)
    if (pokemonListKey(appliedQuery()) === initialKey) data.value = list
  } catch {
    if (pokemonListKey(appliedQuery()) === initialKey) loadError.value = true
  } finally {
    loadingAll.value = false
  }
}

function updateFilterPosition() {
  const anchorTop = filterAnchor.value?.getBoundingClientRect().top
  const headerBottom = document.querySelector('header')?.getBoundingClientRect().bottom || 68
  filterStuck.value = anchorTop !== undefined && anchorTop <= headerBottom
}

onMounted(() => {
  hydrated.value = true
  data.value = initialData.value
  if (data.value && !loadingAll.value) pokemonListCache.set(initialKey, data.value)
  void loadInitialList()
  if (route.query.page) {
    void router.replace({ path: route.path, query: { ...route.query, page: undefined } })
  }
  updateFilterPosition()
  window.addEventListener('scroll', updateFilterPosition, { passive: true })
})
onUnmounted(() => window.removeEventListener('scroll', updateFilterPosition))

onBeforeRouteUpdate(async (to) => {
  const target = pokemonListQuery(to.query, localeForPath(to.path))
  const key = pokemonListKey(target)
  if (key === displayedKey.value || pokemonListCache.get(key)) return
  const loadingToast = toast.add({
    title: t('common.loadingAll'),
    duration: 120000,
  })
  try {
    await loadList(target)
  } catch {
    toast.add({ title: t('common.error'), description: t('common.retry'), color: 'error' })
    return false
  } finally {
    toast.remove(loadingToast.id)
  }
})

watch(
  () => route.fullPath,
  () => {
    const query = appliedQuery()
    const key = pokemonListKey(query)
    if (key !== displayedKey.value) {
      const next = pokemonListCache.get(key)
      if (next) {
        data.value = next
        displayedKey.value = key
      }
      syncDraft(query)
    }
  },
  { flush: 'sync' },
)

const { data: types } = await useAsyncData(
  'pokemon-list-types',
  () => fetchApi<TypeSummary[]>('/types', { params: { locale: locale.value } }),
  { watch: [locale] },
)

const { data: generations } = await useAsyncData(
  'pokemon-list-generations',
  () => fetchApi<GenerationSummary[]>('/generations', { params: { locale: locale.value } }),
  { watch: [locale] },
)

useSeoMeta({
  title: () => t('nav.pokemon'),
  description: () => t('home.description'),
})

async function navigateToQuery(
  targetQuery: Record<string, string | undefined>,
  target: PokemonListQuery,
) {
  if (navigating.value) return
  const key = pokemonListKey(target)
  const cached = pokemonListCache.get(key)
  const loadingToast = cached
    ? undefined
    : toast.add({ title: t('common.loadingAll'), duration: 120000 })
  const origin = route.fullPath
  navigating.value = true
  try {
    if (!cached) await loadList(target)
    if (route.fullPath !== origin) return
    await router.push(localePath({ path: '/pokemon', query: targetQuery }))
    window.scrollTo({ top: 0, behavior: 'instant' })
  } catch {
    toast.add({ title: t('common.error'), description: t('common.retry'), color: 'error' })
  } finally {
    if (loadingToast) toast.remove(loadingToast.id)
    navigating.value = false
  }
}

function applyFilters() {
  const targetQuery = {
    q: filters.q.trim() || undefined,
    type: filters.type === allFilters ? undefined : filters.type,
    generation: filters.generation === allFilters ? undefined : filters.generation,
    sort: filters.sort === 'id' ? undefined : filters.sort,
    isLegendary: filters.legendary ? 'true' : undefined,
    isMythical: filters.mythical ? 'true' : undefined,
  }
  filtersExpanded.value = false
  void navigateToQuery(targetQuery, pokemonListQuery(targetQuery, locale.value))
}

function clearFilters() {
  filters.q = ''
  filters.type = allFilters
  filters.generation = allFilters
  filters.sort = 'id'
  filters.legendary = false
  filters.mythical = false
  applyFilters()
}
</script>

<template>
  <section class="dex-grid-container mx-auto max-w-7xl px-4 py-8 lg:px-8">
    <div class="mb-6">
      <p class="text-sm font-bold uppercase tracking-[0.22em] text-red-500">Pokédex</p>
      <h1 class="mt-2 text-4xl font-black tracking-tight">{{ t('nav.pokemon') }}</h1>
    </div>

    <div ref="filterAnchor" aria-hidden="true" class="h-px" />
    <form
      class="dex-filter-form mb-6 rounded-2xl border border-[#CCD7DE] bg-white p-4 sm:p-5"
      :class="{
        'dex-filter-form--stuck': filterStuck,
        'dex-filter-form--expanded': filtersExpanded,
      }"
      @submit.prevent="applyFilters"
    >
      <div class="dex-filter-grid">
        <UInput
          v-model="filters.q"
          class="dex-filter-search"
          :placeholder="t('filters.searchPlaceholder')"
          icon="i-lucide-search"
        />
        <USelect
          v-model="filters.type"
          class="dex-filter-extra"
          :items="[
            { label: t('filters.allTypes'), value: allFilters },
            ...(types || []).map((item) => ({ label: item.localizedName, value: item.name })),
          ]"
        />
        <USelect
          v-model="filters.generation"
          class="dex-filter-extra"
          :items="[
            { label: t('filters.allGenerations'), value: allFilters },
            ...(generations || []).map((item) => ({
              label: item.localizedName,
              value: String(item.id),
            })),
          ]"
        />
        <USelect
          v-model="filters.sort"
          class="dex-filter-extra"
          :items="[
            { label: t('filters.sortId'), value: 'id' },
            { label: t('filters.sortName'), value: 'name' },
            { label: t('filters.sortBaseExperience'), value: 'base_experience' },
            { label: t('filters.sortNewest'), value: 'newest' },
          ]"
        />
        <div class="dex-filter-actions flex gap-2">
          <UButton type="submit" :disabled="navigating" class="justify-center">{{
            t('filters.apply')
          }}</UButton>
          <UButton
            type="button"
            :disabled="navigating"
            color="neutral"
            variant="soft"
            class="dex-filter-clear"
            @click="clearFilters"
            >{{ t('filters.clear') }}</UButton
          >
          <UButton
            type="button"
            color="neutral"
            variant="soft"
            class="dex-filter-more"
            :aria-expanded="filtersExpanded"
            @click="filtersExpanded = !filtersExpanded"
            >{{ t(filtersExpanded ? 'filters.less' : 'filters.more') }}</UButton
          >
        </div>
      </div>
      <div class="dex-filter-flags mt-3 flex flex-wrap gap-4">
        <UCheckbox v-model="filters.legendary" :label="t('filters.legendary')" />
        <UCheckbox v-model="filters.mythical" :label="t('filters.mythical')" />
      </div>
    </form>

    <div v-if="data" class="mb-4 flex items-center justify-between">
      <p class="text-sm font-medium text-slate-500">
        {{ t('filters.results', { count: data.total }) }}
      </p>
      <p class="text-sm text-slate-400">
        {{
          data.items.length < data.total
            ? t(loadingAll ? 'filters.loadingRemaining' : 'filters.partialShown', {
                count: data.items.length,
                total: data.total,
              })
            : t('filters.allShown')
        }}
      </p>
    </div>

    <div v-if="pending || !hydrated" class="pokemon-grid">
      <USkeleton v-for="item in 16" :key="item" class="h-48 rounded-[14px]" />
    </div>
    <UAlert v-else-if="error" color="error" variant="soft" :title="t('common.error')" />
    <div v-else-if="data?.items.length" class="pokemon-grid">
      <PokemonCard v-for="pokemon in data.items" :key="pokemon.id" :pokemon="pokemon" />
    </div>
    <UAlert v-else color="neutral" variant="soft" :title="t('common.empty')" />
    <div v-if="loadError" class="mt-5 flex items-center gap-3">
      <p role="alert" class="text-sm text-red-700">{{ t('common.error') }}</p>
      <UButton @click="loadInitialList">{{ t('common.retry') }}</UButton>
    </div>
  </section>
</template>
