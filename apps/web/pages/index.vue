<script setup lang="ts">
import type { PaginatedPokemon } from '~/types/api'

const { t, locale } = useI18n()
const localePath = useLocalePath()
const { fetchApi } = usePokedexApi()
const search = ref('')

const { data, pending, error } = await useAsyncData(
  'home-featured',
  () =>
    fetchApi<PaginatedPokemon>('/pokemon', {
      params: { locale: locale.value, pageSize: 8, sort: 'newest' },
    }),
  { watch: [locale] },
)

useSeoMeta({
  title: () => t('home.title'),
  description: () => t('home.description'),
  ogTitle: () => t('home.title'),
  ogDescription: () => t('home.description'),
  ogType: 'website',
})

function submitSearch() {
  const q = search.value.trim()
  if (q) {
    navigateTo(localePath({ path: '/pokemon', query: { q } }))
  }
}
</script>

<template>
  <div>
    <section class="relative overflow-hidden border-b border-slate-200 bg-white">
      <div
        class="absolute inset-0 bg-[radial-gradient(circle_at_20%_20%,rgba(239,68,68,0.16),transparent_35%),radial-gradient(circle_at_80%_30%,rgba(59,130,246,0.13),transparent_32%)]"
      />
      <div
        class="dex-home-hero relative mx-auto grid max-w-7xl gap-12 px-4 py-20 lg:grid-cols-[1.1fr_0.9fr] lg:px-8 lg:py-28"
      >
        <div class="flex flex-col justify-center">
          <p class="mb-4 text-sm font-black uppercase tracking-[0.24em] text-red-500">
            {{ t('home.eyebrow') }}
          </p>
          <h1
            class="max-w-3xl text-5xl font-black tracking-[-0.04em] text-slate-950 sm:text-6xl lg:text-7xl"
          >
            {{ t('home.title') }}
          </h1>
          <p class="mt-6 max-w-2xl text-lg leading-8 text-slate-600">{{ t('home.description') }}</p>

          <form
            class="mt-9 flex max-w-2xl flex-col gap-3 sm:flex-row"
            @submit.prevent="submitSearch"
          >
            <UInput
              v-model="search"
              :placeholder="t('home.searchPlaceholder')"
              size="xl"
              icon="i-lucide-search"
              class="flex-1"
            />
            <UButton type="submit" size="xl" color="primary" class="justify-center">
              {{ t('home.search') }}
            </UButton>
          </form>

          <div class="mt-5 flex flex-wrap gap-3">
            <UButton :to="localePath('/pokemon')" variant="soft" color="neutral">
              {{ t('home.browse') }}
            </UButton>
            <UButton :to="localePath('/types')" variant="ghost" color="neutral">
              {{ t('nav.types') }}
            </UButton>
          </div>
        </div>

        <div class="dex-home-ornament relative hidden min-h-96 place-items-center lg:grid">
          <div class="absolute size-80 rounded-full bg-red-100 blur-3xl" />
          <div
            class="relative grid size-80 place-items-center rounded-full border-[18px] border-slate-900 bg-white shadow-2xl"
          >
            <div class="absolute left-0 top-1/2 h-16 w-full -translate-y-1/2 bg-slate-900" />
            <div
              class="relative grid size-40 place-items-center rounded-full border-[12px] border-slate-900 bg-slate-50 text-7xl font-black text-red-500 shadow-inner"
            >
              ?
            </div>
          </div>
        </div>
      </div>
    </section>

    <section class="dex-grid-container mx-auto max-w-7xl px-4 py-14 lg:px-8">
      <div class="mb-6 flex items-end justify-between gap-4">
        <div>
          <p class="text-sm font-bold uppercase tracking-[0.2em] text-red-500">Pokédex</p>
          <h2 class="mt-2 text-3xl font-black tracking-tight">{{ t('home.featured') }}</h2>
        </div>
        <UButton :to="localePath('/pokemon')" variant="ghost" color="neutral">
          {{ t('home.browse') }} →
        </UButton>
      </div>

      <div v-if="pending" class="pokemon-grid">
        <USkeleton v-for="item in 8" :key="item" class="h-48 rounded-[14px]" />
      </div>
      <UAlert v-else-if="error" color="error" variant="soft" :title="t('common.error')" />
      <div v-else class="pokemon-grid">
        <PokemonCard v-for="pokemon in data?.items || []" :key="pokemon.id" :pokemon="pokemon" />
      </div>
    </section>
  </div>
</template>
