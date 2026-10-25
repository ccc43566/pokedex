<script setup lang="ts">
import type { StatValue } from '~/types/api'

const props = defineProps<{ stats: StatValue[] }>()
const maxStat = 255
const labels: Record<string, string> = {
  hp: 'HP',
  attack: 'ATK',
  defense: 'DEF',
  'special-attack': 'SP. ATK',
  'special-defense': 'SP. DEF',
  speed: 'SPD',
}
const rows = computed(() =>
  props.stats.map((stat) => ({
    ...stat,
    label: labels[stat.name] || stat.name,
    width: `${Math.max(4, Math.round((stat.baseStat / maxStat) * 100))}%`,
  })),
)
</script>

<template>
  <div class="space-y-4">
    <div
      v-for="stat in rows"
      :key="stat.name"
      class="grid grid-cols-[84px_44px_1fr] items-center gap-3 text-sm"
    >
      <span class="font-bold text-slate-500">{{ stat.label }}</span>
      <span class="text-right font-black text-slate-900">{{ stat.baseStat }}</span>
      <span class="h-2.5 overflow-hidden rounded-full bg-slate-100">
        <span
          class="block h-full rounded-full bg-gradient-to-r from-red-400 to-orange-400"
          :style="{ width: stat.width }"
        />
      </span>
    </div>
  </div>
</template>
