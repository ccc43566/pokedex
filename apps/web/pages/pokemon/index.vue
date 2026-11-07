<script setup lang="ts">
import type { PaginatedPokemon, TypeSummary } from '~/types/api'
import { generationCatalog } from '~/utils/generationCatalog'
import { hasPokemonFilters, pokemonListKey, pokemonListQuery } from '~/utils/pokemonListCache'
import { saveBrowsePosition } from '~/utils/detailNavigation'

const { t, locale } = useI18n()
const route = useRoute()
const router = useRouter()
const localePath = useLocalePath()
const { fetchApi } = usePokedexApi()
const allFilters = '__all__'
const filterAnchor = ref<HTMLElement | null>(null)
const filterForm = ref<HTMLFormElement | null>(null)
const filterStuck = ref(false)
const filtersExpanded = ref(false)
const hydrated = ref(false)
const submitting = ref(false)
const filterHeight = ref(130)
const openGeneration = useState<number | null>('pokemon-open-generation', () => null)
const animateGeneration = ref<number | null>(null)
const applied = computed(() => pokemonListQuery(route.query, locale.value))
const filtered = computed(() => hasPokemonFilters(applied.value))
const activeQuery = computed(() =>
  filtered.value
    ? applied.value
    : openGeneration.value
      ? { locale: locale.value, sort: 'id', generation: openGeneration.value }
      : null,
)
const filters = reactive({
  q: '',
  type: allFilters,
  legendary: false,
  mythical: false,
  mega: false,
  gigantamax: false,
})
function syncDraft() {
  const query = applied.value
  filters.q = query.q || ''
  filters.type = query.type || allFilters
  filters.legendary = Boolean(query.isLegendary)
  filters.mythical = Boolean(query.isMythical)
  filters.mega = Boolean(query.isMega)
  filters.gigantamax = Boolean(query.isGigantamax)
}
syncDraft()
watch(() => pokemonListKey(applied.value), syncDraft)

// A fresh directory has no list request, on either the server or the client.
const firstQuery = activeQuery.value
const { data: initial } = await useAsyncData(
  `pokemon-first-batch-${firstQuery ? pokemonListKey(firstQuery) : 'directory'}`,
  async () => ({
    list: firstQuery
      ? await fetchApi<PaginatedPokemon>('/pokemon', {
          params: { ...firstQuery, page: 1, pageSize: pokemonBatchSize },
        })
      : null,
  }),
)
const batches = usePokemonBatches(activeQuery, initial.value?.list || null)
const { data, pending, failed, restoring, placeholders } = batches
const { data: types } = await useAsyncData(
  'pokemon-list-types',
  () => fetchApi<TypeSummary[]>('/types', { params: { locale: locale.value } }),
  { watch: [locale] },
)

let filterObserver: IntersectionObserver | undefined
let sizeObserver: ResizeObserver | undefined
function observeFilterPosition() {
  filterObserver?.disconnect()
  if (!filterAnchor.value) return
  const headerHeight = document.querySelector('header')?.getBoundingClientRect().height || 68
  filterObserver = new IntersectionObserver(
    ([entry]) => {
      if (entry) filterStuck.value = entry.boundingClientRect.top <= headerHeight
    },
    { rootMargin: `-${headerHeight}px 0px 0px 0px`, threshold: [0, 1] },
  )
  filterObserver.observe(filterAnchor.value)
}
function saveOpenGeneration() {
  try {
    sessionStorage.setItem('pokedex:open-generation', String(openGeneration.value || ''))
  } catch {
    /* Optional storage. */
  }
}
watch(openGeneration, saveOpenGeneration)
onMounted(() => {
  try {
    const saved = Number(sessionStorage.getItem('pokedex:open-generation'))
    openGeneration.value = generationCatalog.some((item) => item.id === saved) ? saved : null
  } catch {
    openGeneration.value = null
  }
  sizeObserver = new ResizeObserver((entries) => {
    for (const entry of entries) {
      if (entry.target === filterForm.value)
        filterHeight.value =
          entry.borderBoxSize[0]?.blockSize || entry.target.getBoundingClientRect().height
      else observeFilterPosition()
    }
  })
  if (filterForm.value) sizeObserver.observe(filterForm.value)
  const header = document.querySelector('header')
  if (header) sizeObserver.observe(header)
  observeFilterPosition()
  hydrated.value = true
  if (route.query.page || 'cardPreview' in route.query || 'cardStyle' in route.query) {
    void router.replace({
      path: route.path,
      query: { ...route.query, page: undefined, cardPreview: undefined, cardStyle: undefined },
    })
  }
})
onUnmounted(() => {
  filterObserver?.disconnect()
  sizeObserver?.disconnect()
})
useBrowsePosition(
  async (top) => {
    await nextTick()
    await batches.restore(top)
  },
  0,
  { scrollSaveDelay: 150 },
)

async function toggleGeneration(id: number) {
  const previous = openGeneration.value
  animateGeneration.value = openGeneration.value === id ? null : id
  openGeneration.value = openGeneration.value === id ? null : id
  saveOpenGeneration()
  // Opening a visible bar must not pull the filter into its sticky position.
  // Only recover visibility if collapsing an earlier section hid the new bar.
  if (previous === null || previous === id) return
  await nextTick()
  const bar = document.getElementById(`generation-${id}-trigger`)
  const top = (filterForm.value?.getBoundingClientRect().bottom || 0) + 8
  if (bar && bar.getBoundingClientRect().top < top) {
    window.scrollBy({ top: bar.getBoundingClientRect().top - top, behavior: 'instant' })
  }
}
function applyFilters() {
  filtersExpanded.value = false
  const query = {
    q: filters.q.trim() || undefined,
    type: filters.type === allFilters ? undefined : filters.type,
    isLegendary: filters.legendary ? 'true' : undefined,
    isMythical: filters.mythical ? 'true' : undefined,
    isMega: filters.mega ? 'true' : undefined,
    isGigantamax: filters.gigantamax ? 'true' : undefined,
  }
  const location = router.resolve(localePath({ path: '/pokemon', query }))
  saveBrowsePosition(location, 0)
  submitting.value = true
  if (location.fullPath === route.fullPath) {
    void batches.restore(0).finally(() => {
      submitting.value = false
    })
    return
  }
  void router
    .push(location)
    .then(() => window.scrollTo({ top: 0, behavior: 'instant' }))
    .finally(() => {
      submitting.value = false
    })
}
function clearFilters() {
  Object.assign(filters, {
    q: '',
    type: allFilters,
    legendary: false,
    mythical: false,
    mega: false,
    gigantamax: false,
  })
  applyFilters()
}
useSeoMeta({ title: () => t('nav.pokemon'), description: () => t('home.description') })
</script>

<template>
  <section
    class="dex-grid-container pokemon-catalog mx-auto max-w-7xl px-4 py-8 lg:px-8"
    :style="{ '--dex-filter-height': `${filterHeight}px` }"
  >
    <h1 class="sr-only">{{ t('nav.pokemon') }}</h1>
    <div ref="filterAnchor" aria-hidden="true" class="h-px" />
    <form
      ref="filterForm"
      class="dex-filter-form mb-6 rounded-2xl border border-[#CCD7DE] bg-white p-4 sm:p-5"
      :class="{
        'dex-filter-form--stuck': filterStuck,
        'dex-filter-form--expanded': filtersExpanded,
      }"
      :aria-busy="submitting || pending"
      @submit.prevent="applyFilters"
    >
      <div class="dex-filter-grid">
        <UInput
          v-model="filters.q"
          :disabled="!hydrated"
          class="dex-filter-search"
          :placeholder="t('filters.searchPlaceholder')"
          :aria-label="t('filters.searchPlaceholder')"
          icon="i-lucide-search"
        />
        <TypeSelect
          v-model="filters.type"
          :disabled="!hydrated"
          class="dex-filter-extra dex-filter-type"
          :types="types || []"
          :all-value="allFilters"
          :all-label="t('filters.allTypes')"
          :label="locale === 'zh-Hans' ? '属性' : 'Type'"
          show-icon
        />
        <div class="dex-filter-actions flex gap-2">
          <UButton type="submit" class="justify-center" :disabled="!hydrated">{{
            t('filters.apply')
          }}</UButton>
          <UButton
            type="button"
            color="neutral"
            variant="soft"
            class="dex-filter-clear"
            :disabled="!hydrated"
            @click="clearFilters"
            >{{ t('filters.clear') }}</UButton
          >
          <UButton
            type="button"
            color="neutral"
            variant="soft"
            class="dex-filter-more"
            :disabled="!hydrated"
            :aria-expanded="filtersExpanded"
            @click="filtersExpanded = !filtersExpanded"
            >{{ t(filtersExpanded ? 'filters.less' : 'filters.more') }}</UButton
          >
        </div>
      </div>
      <div class="dex-filter-flags mt-3 flex flex-wrap gap-4">
        <AppCheckbox
          v-model="filters.legendary"
          :disabled="!hydrated"
          :label="t('filters.legendary')"
        />
        <AppCheckbox
          v-model="filters.mythical"
          :disabled="!hydrated"
          :label="t('filters.mythical')"
        />
        <AppCheckbox v-model="filters.mega" :disabled="!hydrated" label="Mega" />
        <AppCheckbox
          v-model="filters.gigantamax"
          :disabled="!hydrated"
          :label="locale === 'zh-Hans' ? '超极巨化' : 'Gigantamax'"
        />
      </div>
    </form>

    <p
      v-if="submitting || (filtered && pending && !data)"
      role="status"
      aria-live="polite"
      class="mb-4 text-sm text-slate-500"
    >
      {{ locale === 'zh-Hans' ? '正在搜索宝可梦…' : 'Searching Pokémon…' }}
    </p>
    <PokemonBatchList
      v-if="filtered"
      :placeholders="placeholders"
      :data="data"
      :pending="pending"
      :failed="failed"
      :restoring="restoring"
      :paused="Boolean(route.query.detail)"
      @more="batches.loadMore"
      @retry="batches.retry"
    />
    <template v-else>
      <div class="generation-directory">
        <section
          v-for="generation in generationCatalog"
          :key="generation.id"
          class="generation-section"
          :class="{ 'generation-section--open': openGeneration === generation.id }"
          :aria-labelledby="`generation-${generation.id}-trigger`"
        >
          <GenerationBar
            :generation="generation"
            :loading="openGeneration === generation.id && pending && !data"
            :disabled="!hydrated"
            :expanded="openGeneration === generation.id"
            @toggle="toggleGeneration(generation.id)"
          />
          <div
            :id="`generation-${generation.id}-content`"
            :hidden="openGeneration !== generation.id"
          >
            <PokemonBatchList
              v-if="openGeneration === generation.id"
              generation
              :animate-entry="animateGeneration === generation.id"
              :placeholders="placeholders"
              class="generation-content"
              :data="data"
              :pending="pending"
              :failed="failed"
              :restoring="restoring"
              :paused="Boolean(route.query.detail)"
              @more="batches.loadMore"
              @retry="batches.retry"
            />
          </div>
        </section>
      </div>
    </template>
  </section>
</template>

<style>
.generation-directory {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.generation-section {
  min-width: 0;
}
.generation-content {
  padding-top: 20px;
  padding-bottom: 20px;
}
</style>
