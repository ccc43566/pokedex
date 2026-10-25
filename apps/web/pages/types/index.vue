<script setup lang="ts">
import type { TypeSummary } from '~/types/api'

const { t, locale } = useI18n()
const localePath = useLocalePath()
const { fetchApi } = usePokedexApi()
const { data, pending, error } = await useAsyncData(
  'types-list',
  () => fetchApi<TypeSummary[]>('/types', { params: { locale: locale.value } }),
  { watch: [locale] },
)

useSeoMeta({ title: () => t('types.title'), description: () => t('types.description') })
</script>

<template>
  <section class="mx-auto max-w-7xl px-4 py-12 lg:px-8">
    <p class="text-sm font-bold uppercase tracking-[0.22em] text-red-500">Types</p>
    <h1 class="mt-2 text-4xl font-black tracking-tight">{{ t('types.title') }}</h1>
    <p class="mt-4 max-w-2xl text-lg text-slate-600">{{ t('types.description') }}</p>

    <div v-if="pending" class="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <USkeleton v-for="item in 12" :key="item" class="h-32 rounded-3xl" />
    </div>
    <UAlert
      v-else-if="error"
      class="mt-10"
      color="error"
      variant="soft"
      :title="t('common.error')"
    />
    <div v-else class="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <NuxtLink
        v-for="type in data || []"
        :key="type.id"
        :to="localePath(`/types/${type.name}`)"
        class="group rounded-3xl border border-slate-200 bg-white p-6 shadow-sm transition hover:-translate-y-1 hover:shadow-lg"
      >
        <div class="flex items-center justify-between">
          <TypeBadge :type="type" />
          <span class="text-sm font-black text-slate-300">#{{ type.id }}</span>
        </div>
        <p class="mt-5 text-xl font-black capitalize">{{ type.name }}</p>
      </NuxtLink>
    </div>
  </section>
</template>
