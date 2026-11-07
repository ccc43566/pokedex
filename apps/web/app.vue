<script setup lang="ts">
import SiteLogo from '~/components/SiteLogo.vue'
import SiteNavigation from '~/components/SiteNavigation.vue'
import CardBackgroundControl from '~/components/CardBackgroundControl.vue'
import SiteAppearanceControl from '~/components/SiteAppearanceControl.vue'
import CatalogWallpaper from '~/components/CatalogWallpaper.vue'
import '~/assets/css/catalog-field.css'
import '~/assets/css/catalog-night.css'
import '~/assets/css/ui-interactions.css'
const { locale, locales, t } = useI18n()
const localePath = useLocalePath()
const switchLocalePath = useSwitchLocalePath()
const route = useRoute()
const router = useRouter()
useCatalogPageMotion()
const {mode,background,cardOpacity,backgroundDimming,setMode,setBackground}=useAppearance()
const wallpaperState = ref<'loading' | 'ready' | 'error'>('ready')
function clearPreviewQuery() {
  if ('uiPreview' in route.query) void router.replace({path:route.path,query:{...route.query,uiPreview:undefined}})
}
watch(() => route.query.uiPreview, () => { if(import.meta.client) clearPreviewQuery() })
const siteUrl = useRuntimeConfig().public.siteUrl
const headerElement = ref<HTMLElement | null>(null)
const isHomepage = computed(
  () => route.path.replace(/\/$/, '') === localePath('/').replace(/\/$/, ''),
)
let headerObserver: ResizeObserver | undefined
onMounted(() => {
  clearPreviewQuery()
  headerObserver = new ResizeObserver(([entry]) => {
    if (entry)
      document.documentElement.style.setProperty(
        '--dex-header-height',
        `${entry.target.getBoundingClientRect().height}px`,
      )
  })
  if (headerElement.value) headerObserver.observe(headerElement.value)
})
watch(
  headerElement,
  (element, previous) => {
    if (previous) headerObserver?.unobserve(previous)
    if (element) headerObserver?.observe(element)
  },
  { flush: 'post' },
)
onUnmounted(() => headerObserver?.disconnect())
const detailId = computed(() => {
  const isBrowsePage = route.path === localePath('/') || route.path === localePath('/pokemon')
  const value = typeof route.query.detail === 'string' ? route.query.detail : ''
  return isBrowsePage && /^\d+$/.test(value) ? value : null
})
const referenceKind = computed(() => {
  if (route.path === localePath('/items')) return 'items'
  if (route.path === localePath('/moves')) return 'moves'
  return null
})
const referenceDetailId = computed(() => {
  const value = typeof route.query.detail === 'string' ? route.query.detail : ''
  return referenceKind.value && /^\d+$/.test(value) ? value : null
})

function closeDetail() {
  router.replace({
    path: route.path,
    query: { ...route.query, detail: undefined, form: undefined },
  })
}

function switchLanguage(value: string) {
  navigateTo(switchLocalePath(value as 'zh-Hans' | 'en'))
}

useHead(() => ({
  htmlAttrs: { lang: locale.value, 'data-catalog-mode':isHomepage.value?'day':mode.value },
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
    <div class="site-shell" :class="{'catalog-field':!isHomepage}" :data-mode="!isHomepage?mode:undefined" :data-background="!isHomepage?background.id:undefined" :data-wallpaper="background.image?'image':'css'" :style="{'--pokemon-card-bg-opacity':`${cardOpacity}%`}">
      <CatalogWallpaper v-if="!isHomepage" :background="background" :mode="mode" :dimming="backgroundDimming" @state="wallpaperState = $event" />
      <header
        v-if="!isHomepage"
        ref="headerElement"
        class="sticky top-0 z-40 border-b border-[#CCD7DE] bg-white/90 backdrop-blur"
      >
        <div
          class="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3 px-4 py-3 lg:px-8"
        >
          <NuxtLink :to="localePath('/')" class="catalog-brand" aria-label="PokéCodex"><SiteLogo /></NuxtLink>
          <SiteNavigation />
          <div class="catalog-header-actions">
          <SiteAppearanceControl v-model:dimming="backgroundDimming" :mode="mode" :background-id="background.id" :state="wallpaperState" @update:mode="setMode" @update:background="setBackground" />
          <USelect
            :model-value="locale"
            :items="locales.map((item) => ({ label: item.name, value: item.code }))"
            class="catalog-language w-32"
            @update:model-value="(value) => switchLanguage(String(value))"
          />
          </div>
        </div>
      </header>

      <main :class="{ 'dex-main--with-detail': referenceDetailId }">
        <NuxtPage />
      </main>
      <CardBackgroundControl v-if="route.path===localePath('/pokemon')" v-model="cardOpacity" :mode="mode" />
      <PokemonDetailDrawer v-if="detailId" :id="detailId" @close="closeDetail" />
      <ReferenceDetailDrawer
        v-if="referenceDetailId && referenceKind"
        :id="referenceDetailId"
        :kind="referenceKind"
        @close="closeDetail"
      />

      <footer v-if="!isHomepage" class="mt-20 border-t border-[#CCD7DE] bg-white">
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
