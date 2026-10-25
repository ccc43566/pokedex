<script setup lang="ts">
import type { TypeDetail } from '~/types/api'

const route = useRoute()
const { t, locale } = useI18n()
const { fetchApi } = usePokedexApi()
const idOrName = String(route.params.idOrName)
const relations = [
  'double_damage_to',
  'half_damage_to',
  'no_damage_to',
  'double_damage_from',
  'half_damage_from',
  'no_damage_from',
] as const

const {
  data: type,
  pending,
  error,
} = await useAsyncData(
  `type-${idOrName}`,
  () => fetchApi<TypeDetail>(`/types/${idOrName}`, { params: { locale: locale.value } }),
  { watch: [locale, () => route.params.idOrName] },
)

if (error.value) {
  throw createError({ statusCode: 404, statusMessage: 'Type not found' })
}

useSeoMeta({
  title: () => type.value?.localizedName,
  description: () =>
    type.value ? `${type.value.localizedName} type effectiveness` : t('types.description'),
})
</script>

<template>
  <section class="mx-auto max-w-7xl px-4 py-12 lg:px-8">
    <div v-if="pending" class="space-y-6">
      <USkeleton class="h-44 rounded-3xl" />
      <USkeleton class="h-80 rounded-3xl" />
    </div>
    <template v-else-if="type">
      <div class="rounded-[2rem] border border-slate-200 bg-white p-8 shadow-sm">
        <TypeBadge :type="type" />
        <h1 class="mt-5 text-5xl font-black capitalize tracking-tight">{{ type.localizedName }}</h1>
        <p class="mt-2 text-lg text-slate-400">#{{ type.id }} · {{ type.name }}</p>
      </div>

      <div class="mt-6 grid gap-5 lg:grid-cols-2">
        <section
          v-for="relation in relations"
          :key="relation"
          class="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm"
        >
          <h2 class="text-xl font-black">{{ t(`types.${relation}`) }}</h2>
          <div v-if="type.damageRelations[relation]?.length" class="mt-5 flex flex-wrap gap-2">
            <TypeBadge
              v-for="item in type.damageRelations[relation]"
              :key="item.id"
              :type="item"
              link
            />
          </div>
          <p v-else class="mt-5 text-sm text-slate-400">{{ t('common.empty') }}</p>
        </section>
      </div>
    </template>
  </section>
</template>
