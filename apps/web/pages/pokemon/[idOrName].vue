<script setup lang="ts">
import type { PokemonDetail } from '~/types/api'

const route = useRoute()
const { t, locale } = useI18n()
const localePath = useLocalePath()
const { fetchApi } = usePokedexApi()
const idOrName = computed(() => String(route.params.idOrName))

const {
  data: pokemon,
  pending,
  error,
} = await useAsyncData(
  () => `pokemon-${idOrName.value}-${locale.value}`,
  () => fetchApi<PokemonDetail>(`/pokemon/${idOrName.value}`, { params: { locale: locale.value } }),
)

const returnTo = computed(() => {
  const from = typeof route.query.from === 'string' ? route.query.from : ''
  if (from.startsWith('/zh-Hans') || from.startsWith('/en')) {
    if (!from.startsWith('//')) {
      const target = new URL(from, 'http://localhost')
      if (target.pathname.endsWith('/pokemon')) target.searchParams.delete('page')
      return `${target.pathname}${target.search}${target.hash}`
    }
  }
  return localePath('/pokemon')
})

useSeoMeta({
  title: () => pokemon.value?.localizedName || t('pokemon.notFound'),
  description: () => pokemon.value?.description || t('home.description'),
  ogTitle: () => pokemon.value?.localizedName || t('pokemon.notFound'),
  ogDescription: () => pokemon.value?.description || t('home.description'),
  ogImage: () => pokemon.value?.artworkUrl || pokemon.value?.spriteUrl || undefined,
  ogType: 'article',
})
</script>

<template>
  <section class="mx-auto max-w-7xl px-4 py-8 lg:px-8">
    <UButton :to="returnTo" variant="ghost" color="neutral" icon="i-lucide-arrow-left" class="mb-5">
      {{ t('pokemon.back') }}
    </UButton>
    <div v-if="pending" class="space-y-5">
      <USkeleton class="h-80 rounded-2xl" />
      <USkeleton class="h-60 rounded-2xl" />
    </div>
    <UAlert v-else-if="error" color="error" variant="soft" :title="t('pokemon.notFound')" />
    <PokemonDetailContent v-else-if="pokemon" :pokemon="pokemon" />
  </section>
</template>
