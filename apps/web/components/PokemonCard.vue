<script setup lang="ts">
import type { PokemonListItem } from '~/types/api'
import { isVisibleType, typeColors } from '~/utils/typePresentation'
import { formatDexNumber } from '~/utils/pokemon'

const props = defineProps<{ pokemon: PokemonListItem; priority?: boolean }>()
const { t, locale } = useI18n()
const route = useRoute()
const router = useRouter()
const localePath = useLocalePath()
const visibleTypes = computed(() => props.pokemon.types.filter(isVisibleType))
const image = computed(() => props.pokemon.artworkUrl || props.pokemon.spriteUrl)
const selected = computed(() => String(route.query.detail || '') === String(props.pokemon.id))
const detailPath = computed(() => {
  const onBrowsePage = route.path === localePath('/') || route.path === localePath('/pokemon')
  return onBrowsePage
    ? {
        path: route.path,
        query: { ...route.query, detail: String(props.pokemon.id), form: undefined },
      }
    : localePath(`/pokemon/${props.pokemon.id}`)
})
const detailHref = computed(() => router.resolve(detailPath.value).href)
function openDetail(event: MouseEvent) {
  if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return
  event.preventDefault()
  void router.push(detailPath.value)
}
const accessibleName = computed(() =>
  [
    formatDexNumber(props.pokemon.displayNumber || props.pokemon.id),
    props.pokemon.displayName || props.pokemon.localizedName,
    ...visibleTypes.value.map((type) => type.localizedName),
  ].join(' '),
)
</script>

<template>
  <a
    :href="detailHref"
    @click="openDetail"
    :data-pokemon-id="pokemon.id"
    :aria-label="accessibleName"
    :aria-current="selected ? 'true' : undefined"
    :title="pokemon.displayName || pokemon.localizedName"
    :data-display-number="pokemon.displayNumber"
    class="pokemon-card pk"
    :class="{ 'pokemon-card--selected': selected }"
    :style="{ '--accent': typeColors(visibleTypes[0]?.name || 'normal').icon }"
  >
    <span class="pk-grid" aria-hidden="true" />
    <span class="pk-rings" aria-hidden="true" />
    <div class="pokemon-card__top">
      <span class="pokemon-card__number">{{
        formatDexNumber(pokemon.displayNumber || pokemon.id)
      }}</span>
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
      <img
        v-if="image"
        :src="image"
        alt=""
        class="pokemon-card__image"
        width="128"
        height="128"
        :loading="priority ? 'eager' : 'lazy'"
        :fetchpriority="priority ? 'high' : undefined"
        decoding="async"
      />
      <span v-else class="pokemon-card__missing">?</span>
      <span v-if="selected" class="pokemon-card__selected-label" aria-hidden="true">{{
        t('pokemon.selected')
      }}</span>
    </div>

    <div class="pokemon-card__details">
      <h2 class="pokemon-card__name">
        <span>{{ pokemon.localizedName }}</span>
        <span v-if="pokemon.variantLabel" class="pokemon-card__form-label"
          >（{{ pokemon.variantLabel }}）</span
        >
      </h2>
      <div class="pokemon-card__types" aria-hidden="true">
        <TypeBadge
          v-for="type in visibleTypes.slice(0, 2)"
          :key="type.id"
          :type="type"
          :label="locale === 'zh-Hans' && type.name === 'psychic' ? '超能' : undefined"
          size="card"
        />
      </div>
    </div>
  </a>
</template>

<style scoped>
.pk {
  position:relative;
  isolation:isolate;
  /* Scaled to the existing 6rem image well, rather than the earlier 168px demo. */
  --ring-step:1.5rem;
  --grid-step:1rem;
  --texture-line:.0625rem;
  /* Existing card padding + number row + art top margin + art height + border. */
  --art-end:calc(10px + 1.125rem + .4375rem + 6rem + 1px);
  background:color-mix(in srgb,var(--pokemon-card-paper,color-mix(in srgb,#79CA57 2%,#fff)) var(--pokemon-card-bg-opacity,80%),transparent);
}
.pk > .pokemon-card__top,
.pk > .pokemon-card__art,
.pk > .pokemon-card__details { position:relative; z-index:1; }
.pk .pokemon-card__art {
  background:transparent;
  border-color:transparent;
  border-radius:0;
  overflow:visible;
  /* Preserve the original 1px border's geometry while removing its appearance. */
}
.pk .pokemon-card__image {
  position:absolute;
  left:50%;
  top:50%;
  width:6.5rem;
  height:6.5rem;
  margin:-3.25rem 0 0 -3.25rem;
  /* Increase the resting artwork size without changing the original image well. */
}
.pk-grid,.pk-rings {
  position:absolute;
  inset:0;
  border-radius:inherit;
  pointer-events:none;
  z-index:0;
}
.pk-grid {
  background:
    repeating-linear-gradient(to right,var(--pokemon-card-grid-line,rgba(16,24,40,.020)) 0 var(--texture-line),transparent var(--texture-line) var(--grid-step)),
    repeating-linear-gradient(to bottom,var(--pokemon-card-grid-line,rgba(16,24,40,.020)) 0 var(--texture-line),transparent var(--texture-line) var(--grid-step));
  mask-image:radial-gradient(ellipse 75% 70% at 50% 40%,#000 0%,#000 25%,transparent 100%);
}
.pk-rings {
  /* Background contains lines ONLY. The ordinary gradients below are masks. */
  background:repeating-radial-gradient(circle at 50% 34%,transparent 0 calc(var(--ring-step) - var(--texture-line)),color-mix(in srgb,var(--accent) var(--pokemon-card-ring-opacity,13%),transparent) calc(var(--ring-step) - var(--texture-line)) var(--ring-step));
  mask-image:
    radial-gradient(ellipse 72% 55% at 50% 34%,#000 0%,#000 15%,transparent 100%),
    linear-gradient(to bottom,#000 0%,#000 calc(var(--art-end) - 1.25rem),transparent var(--art-end));
  mask-composite:intersect;
}

</style>
