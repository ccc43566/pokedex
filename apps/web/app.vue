<script setup lang="ts">
const { locale, locales, t } = useI18n()
const localePath = useLocalePath()
const switchLocalePath = useSwitchLocalePath()
const route = useRoute()
const router = useRouter()
const siteUrl = useRuntimeConfig().public.siteUrl
const detailId = computed(() => {
  const isBrowsePage = route.path === localePath('/') || route.path === localePath('/pokemon')
  const value = typeof route.query.detail === 'string' ? route.query.detail : ''
  return isBrowsePage && /^\d+$/.test(value) ? value : null
})
const detailReturnTo = computed(
  () => router.resolve({ path: route.path, query: { ...route.query, detail: undefined } }).fullPath,
)

function closeDetail() {
  router.replace({ path: route.path, query: { ...route.query, detail: undefined } })
}

function switchLanguage(value: string) {
  navigateTo(switchLocalePath(value as 'zh-Hans' | 'en'))
}

useHead(() => ({
  htmlAttrs: { lang: locale.value },
  link: [
    { rel: 'canonical', href: `${siteUrl}${route.path}` },
    ...locales.value.map((item) => ({
      rel: 'alternate',
      hreflang: item.language,
      href: `${siteUrl}${switchLocalePath(item.code)}`,
    })),
  ],
}))
</script>

<template>
  <UApp>
    <div class="site-shell">
      <header class="sticky top-0 z-40 border-b border-[#CCD7DE] bg-white/90 backdrop-blur">
        <div class="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-3 lg:px-8">
          <NuxtLink :to="localePath('/')" class="flex items-center gap-3">
            <span
              class="grid size-10 place-items-center rounded-full bg-red-500 text-lg font-black text-white shadow-lg shadow-red-500/25"
            >
              宝
            </span>
            <span>
              <span class="block text-lg font-black tracking-tight">Pokédex</span>
              <span class="block text-xs text-slate-500">{{ t('app.subtitle') }}</span>
            </span>
          </NuxtLink>
          <nav class="hidden items-center gap-2 md:flex">
            <UButton :to="localePath('/pokemon')" color="neutral" variant="ghost">
              {{ t('nav.pokemon') }}
            </UButton>
            <UButton :to="localePath('/types')" color="neutral" variant="ghost">
              {{ t('nav.types') }}
            </UButton>
          </nav>
          <USelect
            :model-value="locale"
            :items="locales.map((item) => ({ label: item.name, value: item.code }))"
            class="w-32"
            @update:model-value="(value) => switchLanguage(String(value))"
          />
        </div>
      </header>

      <main :class="{ 'dex-main--with-detail': detailId }">
        <NuxtPage />
      </main>
      <PokemonDetailDrawer
        v-if="detailId"
        :id="detailId"
        :return-to="detailReturnTo"
        @close="closeDetail"
      />

      <footer class="mt-20 border-t border-[#CCD7DE] bg-white">
        <div
          class="mx-auto flex max-w-7xl flex-col gap-4 px-4 py-8 text-sm text-slate-500 lg:flex-row lg:items-center lg:justify-between lg:px-8"
        >
          <p>{{ t('app.attribution') }}</p>
          <p>Nuxt 3 · FastAPI · PostgreSQL</p>
        </div>
      </footer>
    </div>
  </UApp>
</template>
