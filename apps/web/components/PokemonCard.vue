<script setup lang="ts">
import type { PokemonListItem } from '~/types/api'
import { formatDexNumber } from '~/utils/pokemon'

const props = defineProps<{ pokemon: PokemonListItem }>()
const { t } = useI18n()
const route = useRoute()
const localePath = useLocalePath()
const image = computed(() => props.pokemon.artworkUrl || props.pokemon.spriteUrl)
const selected = computed(() => String(route.query.detail || '') === String(props.pokemon.id))
const detailPath = computed(() => {
  const onBrowsePage = route.path === localePath('/') || route.path === localePath('/pokemon')
  return onBrowsePage
    ? { path: route.path, query: { ...route.query, detail: String(props.pokemon.id) } }
    : localePath(`/pokemon/${props.pokemon.id}`)
})
const accessibleName = computed(() =>
  [
    formatDexNumber(props.pokemon.id),
    props.pokemon.localizedName,
    ...props.pokemon.types.map((type) => type.localizedName),
  ].join(' '),
)
</script>

<template>
  <NuxtLink
    :to="detailPath"
    :data-pokemon-id="pokemon.id"
    :aria-label="accessibleName"
    :aria-current="selected ? 'true' : undefined"
    :title="pokemon.localizedName"
    class="pokemon-card"
    :class="{ 'pokemon-card--selected': selected }"
  >
    <div class="pokemon-card__top">
      <span class="pokemon-card__number">{{ formatDexNumber(pokemon.id) }}</span>
      <span
        v-if="pokemon.isLegendary"
        class="pokemon-card__special pokemon-card__special--legendary"
      >
        {{ t('pokemon.legendaryShort') }}
      </span>
      <span
        v-else-if="pokemon.isMythical"
        class="pokemon-card__special pokemon-card__special--mythical"
      >
        {{ t('pokemon.mythicalShort') }}
      </span>
    </div>

    <div class="pokemon-card__art" aria-hidden="true">
      <NuxtImg
        v-if="image"
        :src="image"
        alt=""
        class="pokemon-card__image"
        width="128"
        height="128"
        loading="lazy"
        decoding="async"
      />
      <span v-else class="pokemon-card__missing">?</span>
      <span v-if="selected" class="pokemon-card__selected-label" aria-hidden="true">{{
        t('pokemon.selected')
      }}</span>
    </div>

    <div class="pokemon-card__details">
      <h2 class="pokemon-card__name">{{ pokemon.localizedName }}</h2>
      <div class="pokemon-card__types" aria-hidden="true">
        <TypeBadge v-for="type in pokemon.types.slice(0, 2)" :key="type.id" :type="type" compact />
      </div>
    </div>
  </NuxtLink>
</template>
