<script setup lang="ts">
import type { PokemonDetail } from '~/types/api'
import { currentPokemonName } from '~/utils/pokemon'

const route = useRoute()
const { t, locale } = useI18n()
const { returnTo } = usePokemonNavigation()
const { fetchApi } = usePokedexApi()
const idOrName = computed(() => String(route.params.idOrName))

const {
  data: pokemon,
  pending,
  error,
} = await useAsyncData(
  () => `pokemon-${idOrName.value}-${locale.value}-${route.query.form || ''}`,
  () =>
    fetchApi<PokemonDetail>(`/pokemon/${idOrName.value}`, {
      params: { locale: locale.value, form: route.query.form },
    }),
)

const title = computed(() =>
  pokemon.value ? currentPokemonName(pokemon.value, route.query.form) : t('pokemon.notFound'),
)
const returnLabel = computed(() =>
  /^\/(zh-Hans|en)\/items(?:[/?#]|$)/.test(returnTo.value)
    ? locale.value === 'zh-Hans'
      ? '返回道具列表'
      : 'Return to items'
    : /^\/(zh-Hans|en)\/moves(?:[/?#]|$)/.test(returnTo.value)
      ? locale.value === 'zh-Hans'
        ? '返回招式列表'
        : 'Return to moves'
      : /^\/(zh-Hans|en)\/pokemon\/[^/?#]+/.test(returnTo.value)
        ? t('pokemon.backDetail')
        : t('pokemon.back'),
)

useSeoMeta({
  title: () => title.value,
  description: () => pokemon.value?.description || t('home.description'),
  ogTitle: () => title.value,
  ogDescription: () => pokemon.value?.description || t('home.description'),
  ogImage: () => pokemon.value?.artworkUrl || pokemon.value?.spriteUrl || undefined,
  ogType: 'article',
})
</script>

<template>
  <section class="mx-auto max-w-7xl px-4 py-8 lg:px-8">
    <UButton :to="returnTo" variant="ghost" color="neutral" icon="i-lucide-arrow-left" class="mb-5">
      {{ returnLabel }}
    </UButton>
    <div v-if="pending" class="space-y-5">
      <USkeleton class="h-80 rounded-2xl" />
      <USkeleton class="h-60 rounded-2xl" />
    </div>
    <UAlert v-else-if="error" color="error" variant="soft" :title="t('pokemon.notFound')" />
    <PokemonDetailContent v-else-if="pokemon" :pokemon="pokemon" />
  </section>
</template>
