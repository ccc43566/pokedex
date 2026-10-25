<script setup lang="ts">
import type { NamedResource } from '~/types/api'
import { typeClass } from '~/utils/pokemon'

defineProps<{ type: NamedResource; link?: boolean; compact?: boolean }>()
</script>

<template>
  <NuxtLink
    v-if="link"
    :to="`/types/${type.name}`"
    class="inline-flex items-center rounded-full font-bold capitalize transition hover:-translate-y-0.5"
    :class="[
      typeClass(type.name),
      compact ? 'px-1.5 py-0.5 text-[10px] leading-4' : 'px-3 py-1 text-xs',
    ]"
  >
    {{ type.localizedName }}
  </NuxtLink>
  <span
    v-else
    class="inline-flex items-center rounded-full font-bold capitalize"
    :class="[
      typeClass(type.name),
      compact ? 'px-1.5 py-0.5 text-[10px] leading-4' : 'px-3 py-1 text-xs',
    ]"
  >
    {{ type.localizedName }}
  </span>
</template>
