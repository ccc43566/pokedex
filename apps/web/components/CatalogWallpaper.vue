<script setup lang="ts">
import type { AppearanceBackground, AppearanceMode } from '~/utils/appearance'
const props = defineProps<{
  background: AppearanceBackground
  mode: AppearanceMode
  dimming?: number
}>()
const emit = defineEmits<{ state: [value: 'loading' | 'ready' | 'error'] }>()
const mobile = ref(false)
const painted = shallowRef<{ source: string; asset: AppearanceBackground; mobile: boolean } | null>(
  null,
)
const loaded = new Set<string>()
const state = ref<'loading' | 'ready' | 'error'>('ready')
let media: MediaQueryList | undefined
let request = 0
let alive = true
function setState(value: typeof state.value) {
  state.value = value
  emit('state', value)
}
async function update() {
  const ticket = ++request
  const asset = props.background
  const mobileVariant = mobile.value && Boolean(asset.mobileImage)
  const source = mobileVariant ? asset.mobileImage : asset.image
  if (!source) {
    painted.value = null
    setState('ready')
    return
  }
  setState('loading')
  try {
    if (!loaded.has(source)) {
      const image = new Image()
      image.decoding = 'async'
      image.fetchPriority = 'low'
      await new Promise<void>((resolve, reject) => {
        const timer = setTimeout(() => {
          image.onload = image.onerror = null
          reject(new Error('Wallpaper timeout'))
        }, 20000)
        image.onload = () => {
          clearTimeout(timer)
          resolve()
        }
        image.onerror = () => {
          clearTimeout(timer)
          reject(new Error('Wallpaper unavailable'))
        }
        image.src = source
      })
      await image.decode()
      loaded.add(source)
      while (loaded.size > 4) loaded.delete(loaded.values().next().value!)
    }
    if (!alive || ticket !== request) return
    painted.value = { source, asset, mobile: mobileVariant }
    setState('ready')
  } catch {
    if (!alive || ticket !== request) return
    painted.value = null
    setState('error')
  }
}
const style = computed(() => {
  const visibleAsset = painted.value?.asset ?? props.background
  const visibleMobile =
    painted.value?.mobile ?? (mobile.value && Boolean(props.background.mobileImage))
  const base =
    (visibleMobile ? visibleAsset.mobileBase : undefined) ||
    visibleAsset.base ||
    (props.mode === 'night' ? '#101A2A' : '#EEF4EC')
  if (!props.background.image)
    return {
      backgroundColor: base,
      backgroundImage: 'linear-gradient(125deg,#E8EFE5 0%,#F7F9F4 43%,#EEF4EC 100%)',
    }
  if (!painted.value) return { backgroundColor: base, backgroundImage: 'none' }
  const { source, asset } = painted.value
  const amount =
    props.dimming !== undefined ? props.dimming / 100 : (props.background.overlay ?? 0.12)
  const tint = props.mode === 'night' ? `rgba(16,26,42,${amount})` : `rgba(247,249,244,${amount})`
  const overlay =
    props.background.id === 'night-1'
      ? `linear-gradient(rgba(16,26,42,${amount}),rgba(16,32,51,${Math.min(1, amount + 0.09)}))`
      : `linear-gradient(${tint},${tint})`
  // Fade only the actual fitted image edges, rather than the viewport edges.
  // All gradients are static while scrolling and share the wallpaper's raster.
  const ratio = (painted.value.mobile ? asset.mobileAspectRatio : asset.aspectRatio) ?? 16 / 9
  const fitted = `min(100vw, calc(100dvh * ${ratio})) min(100dvh, calc(100vw / ${ratio}))`
  const softened = asset.size === 'contain'
  const layers = softened
    ? `linear-gradient(to bottom,${base},transparent 72px),linear-gradient(to right,${base},transparent 32px,transparent calc(100% - 32px),${base}),`
    : ''
  return {
    backgroundColor: base,
    backgroundImage: `${overlay},${layers}url("${source}")`,
    backgroundSize: `100% 100%,${softened ? `${fitted},${fitted},` : ''}${asset.size || 'cover'}`,
    backgroundPosition: `center,${softened ? 'center bottom,center bottom,' : ''}${asset.position || 'center top'}`,
    backgroundRepeat: 'no-repeat',
  }
})
function resized() {
  if (media) mobile.value = media.matches
}
watch([() => props.background.id, mobile], () => {
  if (import.meta.client) void update()
})
onMounted(() => {
  media = matchMedia('(max-width:767px), (orientation:portrait) and (max-width:1024px)')
  resized()
  media.addEventListener('change', resized)
  if (!mobile.value) void update()
})
onUnmounted(() => {
  alive = false
  ++request
  media?.removeEventListener('change', resized)
})
</script>

<template>
  <div
    class="catalog-wallpaper"
    :data-kind="background.image ? 'image' : 'css'"
    :data-state="state"
    :data-loaded-background="painted?.asset.id"
    :data-source="painted?.source"
    :style="style"
    aria-hidden="true"
  />
</template>

<style scoped>
.catalog-wallpaper[data-kind='image']::before {
  display: none;
}
</style>
