<script setup lang="ts">
import type { AbilityDetail } from '~/types/api'

const route = useRoute()
const { locale } = useI18n()
const { fetchApi } = usePokedexApi()
const idOrName = String(route.params.idOrName)

const {
  data: ability,
  pending,
  error,
} = await useAsyncData(
  `ability-${idOrName}`,
  () => fetchApi<AbilityDetail>(`/abilities/${idOrName}`, { params: { locale: locale.value } }),
  { watch: [locale, () => route.params.idOrName] },
)

if (error.value) {
  throw createError({ statusCode: 404, statusMessage: 'Ability not found' })
}

useSeoMeta({
  title: () => ability.value?.localizedName,
  description: () => ability.value?.shortEffect || ability.value?.effect || '',
})
</script>

<template>
  <section class="mx-auto max-w-4xl px-4 py-12 lg:px-8">
    <div v-if="pending">
      <USkeleton class="h-80 rounded-3xl" />
    </div>
    <article
      v-else-if="ability"
      class="rounded-[2rem] border border-slate-200 bg-white p-8 shadow-sm lg:p-12"
    >
      <p class="text-sm font-bold uppercase tracking-[0.2em] text-red-500">
        Ability #{{ ability.id }}
      </p>
      <h1 class="mt-3 text-4xl font-black tracking-tight">{{ ability.localizedName }}</h1>
      <p class="mt-1 capitalize text-slate-400">{{ ability.name }}</p>
      <div class="mt-8 space-y-5 text-lg leading-8 text-slate-600">
        <p v-if="ability.shortEffect">{{ ability.shortEffect }}</p>
        <p v-if="ability.effect && ability.effect !== ability.shortEffect">{{ ability.effect }}</p>
        <p v-if="ability.flavorText">{{ ability.flavorText }}</p>
      </div>
    </article>
  </section>
</template>
