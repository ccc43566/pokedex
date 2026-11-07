<script setup lang="ts">
import type { StatValue } from '~/types/api'

const props = defineProps<{ stats: StatValue[] }>()
const { t } = useI18n()
const maxStat = 255
const definitions = [
  { name: 'hp', labelKey: 'hp', color: '#82BD7A' },
  { name: 'attack', labelKey: 'attack', color: '#F7CF58' },
  { name: 'defense', labelKey: 'defense', color: '#F3B04E' },
  { name: 'special-attack', labelKey: 'specialAttack', color: '#60B8F1' },
  { name: 'special-defense', labelKey: 'specialDefense', color: '#66A9EF' },
  { name: 'speed', labelKey: 'speed', color: '#A457BA' },
]
const rows = computed(() =>
  definitions.flatMap((definition) => {
    const stat = props.stats.find((item) => item.name === definition.name)
    return stat
      ? [
          {
            ...stat,
            ...definition,
            width: `${(Math.max(0, Math.min(maxStat, stat.baseStat)) / maxStat) * 100}%`,
          },
        ]
      : []
  }),
)
const total = computed(() =>
  props.stats.length ? props.stats.reduce((sum, stat) => sum + stat.baseStat, 0) : null,
)
</script>

<template>
  <div class="stat-bars" role="group" :aria-label="t('pokemon.stats')">
    <div
      v-for="stat in rows"
      :key="stat.name"
      class="stat-bars__row"
      :data-stat="stat.name"
      :style="{ '--stat-width': stat.width, '--stat-color': stat.color }"
      role="meter"
      :aria-label="t(`pokemon.statNames.${stat.labelKey}`)"
      :aria-valuenow="stat.baseStat"
      :aria-valuemin="0"
      :aria-valuemax="maxStat"
    >
      <span class="stat-bars__fill" aria-hidden="true" />
      <span class="stat-bars__content">
        <span class="stat-bars__label" :class="{ 'stat-bars__label--hp': stat.name === 'hp' }">{{
          t(`pokemon.statNames.${stat.labelKey}`)
        }}</span>
        <span class="stat-bars__value">{{ stat.baseStat }}</span>
      </span>
      <!-- Clip dark text to the fill, keeping uncovered text legible in either theme. -->
      <span class="stat-bars__on-fill" aria-hidden="true">
        <span
          class="stat-bars__label-copy"
          :class="{ 'stat-bars__label--hp': stat.name === 'hp' }"
          >{{ t(`pokemon.statNames.${stat.labelKey}`) }}</span
        >
        <span class="stat-bars__value-copy">{{ stat.baseStat }}</span>
      </span>
    </div>
    <div class="stat-bars__total">
      <span class="stat-bars__label">{{ t('pokemon.statTotalShort') }}</span>
      <output class="stat-bars__total-value" data-stat-total :aria-label="t('pokemon.statTotal')">{{
        total ?? '—'
      }}</output>
    </div>
  </div>
</template>

<style scoped>
.stat-bars {
  container-type: inline-size;
  display: grid;
  gap: 8px;
}
.stat-bars__row,
.stat-bars__total {
  position: relative;
  isolation: isolate;
  min-width: 0;
  height: clamp(34px, 10.5cqi, 44px);
  font-size: clamp(18px, 6.2cqi, 24px);
  line-height: 1;
}
.stat-bars__fill {
  position: absolute;
  inset: 0 auto 0 0;
  width: var(--stat-width);
  border-radius: 8px;
  background: var(--stat-color);
  pointer-events: none;
}
.stat-bars__content,
.stat-bars__on-fill,
.stat-bars__total {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding-inline: 6px;
}
.stat-bars__content,
.stat-bars__on-fill {
  position: absolute;
  inset: 0;
}
.stat-bars__content {
  z-index: 1;
  clip-path: inset(0 0 0 var(--stat-width));
}
.stat-bars__label,
.stat-bars__label-copy {
  font-weight: 400;
  white-space: nowrap;
}
.stat-bars__label {
  color: var(--catalog-panel-text, #222);
}
.stat-bars__label--hp {
  font-family: Arial, sans-serif;
  font-weight: 900;
}
.stat-bars__value,
.stat-bars__total-value,
.stat-bars__value-copy {
  flex: none;
  margin-left: auto;
  font-family: Arial, sans-serif;
  font-weight: 800;
  font-variant-numeric: tabular-nums;
  letter-spacing: 0.045em;
}
.stat-bars__value,
.stat-bars__total-value {
  color: var(--pokemon-stat-value, #757575);
}
.stat-bars__on-fill {
  z-index: 2;
  clip-path: inset(0 calc(100% - var(--stat-width)) 0 0);
  color: color-mix(in srgb, var(--stat-color) 13.3333%, #000);
  pointer-events: none;
  user-select: none;
}
.stat-bars__value-copy {
  color: color-mix(in srgb, var(--stat-color) 46%, #000);
}
</style>
