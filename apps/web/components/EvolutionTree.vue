<script setup lang="ts">
import type { EvolutionNodeOut } from '~/types/api'
import { conditionSummary } from '~/utils/pokemon'

const props = defineProps<{ node: EvolutionNodeOut }>()
const localePath = useLocalePath()
const image = computed(() => `/media/pokemon/${props.node.speciesId}/official-artwork.png`)
const conditions = computed(() => conditionSummary(props.node.condition))
</script>

<template>
  <div class="flex min-w-48 flex-col items-center gap-3">
    <NuxtLink
      :to="localePath(`/pokemon/${node.speciesId}`)"
      class="group flex w-40 flex-col items-center rounded-3xl border border-slate-200 bg-white p-3 text-center shadow-sm transition hover:-translate-y-1 hover:shadow-lg"
    >
      <NuxtImg
        :src="image"
        :alt="node.localizedName"
        class="size-24 object-contain transition group-hover:scale-105"
        width="96"
        height="96"
        loading="lazy"
      />
      <span class="mt-1 font-black">{{ node.localizedName }}</span>
      <span class="text-xs capitalize text-slate-400">{{ node.name }}</span>
    </NuxtLink>
    <div v-if="conditions.length" class="max-w-40 text-center text-xs leading-5 text-slate-500">
      <span v-for="condition in conditions" :key="condition" class="block">{{ condition }}</span>
    </div>
    <div v-if="node.children.length" class="mt-4 flex flex-wrap items-start justify-center gap-6">
      <div v-for="child in node.children" :key="child.speciesId" class="relative">
        <span class="absolute -left-3 top-16 text-2xl text-slate-300">→</span>
        <EvolutionTree :node="child" />
      </div>
    </div>
  </div>
</template>
