<script setup lang="ts">
import { generationRange, type GenerationEntry } from '~/utils/generationCatalog'
defineProps<{
  generation: GenerationEntry
  expanded: boolean
  disabled?: boolean
  loading?: boolean
}>()
defineEmits<{ toggle: [] }>()
const { locale } = useI18n()
</script>

<template>
  <button
    :id="`generation-${generation.id}-trigger`"
    type="button"
    class="generation-bar"
    :disabled="disabled"
    :aria-busy="loading || undefined"
    :aria-expanded="expanded"
    :aria-controls="`generation-${generation.id}-content`"
    @click="$emit('toggle')"
  >
    <span class="generation-bar__heading">
      <span class="generation-bar__title">{{
        locale === 'zh-Hans' ? `第${generation.numeral}世代` : `Generation ${generation.id}`
      }}</span>
      <span class="generation-bar__range">{{ generationRange(generation) }}</span>
    </span>
    <span class="generation-bar__starters" aria-hidden="true">
      <img
        v-for="id in generation.starters"
        :key="id"
        :src="`/generation-starters/${id}.png`"
        alt=""
        width="64"
        height="64"
        decoding="async"
      />
    </span>
    <svg
      class="generation-bar__chevron"
      :class="{ 'is-open': expanded }"
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden="true"
    >
      <path
        d="m7 10 5 5 5-5"
        stroke="currentColor"
        stroke-width="1.5"
        stroke-linecap="round"
        stroke-linejoin="round"
      />
    </svg>
  </button>
</template>

<style>
.generation-bar {
  position: relative;
  display: flex;
  align-items: center;
  gap: 28px;
  width: 100%;
  min-height: 76px;
  padding: 7px 24px;
  border: 1px solid var(--catalog-line, #d3dfd5);
  border-radius: 12px;
  background: color-mix(
    in srgb,
    var(--pokemon-card-paper, color-mix(in srgb, #79ca57 2%, #fff))
      var(--pokemon-card-bg-opacity, 80%),
    transparent
  );
  color: var(--dex-ink, #1b2733);
  text-align: left;
  cursor: pointer;
  scroll-margin-top: calc(var(--dex-header-height) + var(--dex-filter-height, 130px) + 12px);
}
.generation-bar:hover {
  border-color: var(--catalog-accent, #3e6650);
}
.generation-bar:focus-visible {
  outline: 2px solid var(--catalog-accent, #3e6650);
  outline-offset: 3px;
}
.generation-bar__heading {
  display: contents;
}
.generation-bar__title {
  font-size: 22px;
  flex: 1;
  font-weight: 750;
  letter-spacing: 0.03em;
  line-height: 1.3;
  white-space: nowrap;
}
.generation-bar__range {
  order: 2;
  font-size: 15px;
  font-weight: 500;
  font-variant-numeric: tabular-nums;
  letter-spacing: 0.04em;
  color: var(--dex-muted, #667685);
  white-space: nowrap;
}
.generation-bar__starters {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  flex: none;
}
.generation-bar__starters img {
  image-rendering: pixelated;
  display: block;
  width: 50px;
  height: 54px;
  object-fit: contain;
}
.generation-bar__chevron {
  order: 3;
  width: 24px;
  height: 24px;
  flex: none;
  color: var(--catalog-accent, #3e6650);
  transition: transform 0.18s ease;
}
.generation-bar__chevron.is-open {
  transform: rotate(180deg);
}
.generation-section--open > .generation-bar {
  position: sticky;
  top: calc(var(--dex-header-height) + var(--dex-filter-height, 130px) + 8px);
  z-index: 20;
  border-color: var(--catalog-accent, #3e6650);
  box-shadow: 0 3px 10px #1423380a;
}
@media (max-width: 700px) {
  .generation-bar {
    gap: 8px;
    padding: 12px 16px;
    min-height: 78px;
    flex-wrap: wrap;
  }
  .generation-bar__title {
    font-size: 20px;
  }
  .generation-bar__range {
    font-size: 11px;
  }
  .generation-bar__starters {
    gap: 3px;
  }
  .generation-bar__starters img {
    width: 33px;
    height: 45px;
  }
  .generation-bar__chevron {
    width: 20px;
    height: 20px;
  }
}
@media (max-width: 360px) {
  .generation-bar {
    padding-inline: 10px;
    gap: 8px;
  }
  .generation-bar__starters img {
    width: 25px;
  }
}
@media (prefers-reduced-motion: reduce) {
  .generation-bar__chevron {
    transition: none;
  }
}
</style>
