<script setup lang="ts">
const { t, locale } = useI18n()
const localePath = useLocalePath()
const route = useRoute()
const router = useRouter()
const root = ref<HTMLElement | null>(null)
const slider = ref<HTMLElement | null>(null)
const enhanced = ref(false)
const visual = ref('')
let requested = ''
let observer: ResizeObserver | undefined
let motion: Animation | undefined
let frame = 0
let reduced: MediaQueryList | undefined
let alive = true
function section(path: string) {
  return (
    ['/pokemon', '/types', '/items', '/moves'].find(
      (item) => path === localePath(item) || path.startsWith(`${localePath(item)}/`),
    ) || ''
  )
}
const selected = computed(() => section(route.path))
function move(animate = true) {
  const nav = root.value,
    pill = slider.value
  const target = nav?.querySelector<HTMLElement>(
    `[data-nav-path="${visual.value || selected.value}"]`,
  )
  if (!nav || !pill || !target) {
    enhanced.value = false
    return
  }
  const container = nav.getBoundingClientRect(),
    next = target.getBoundingClientRect()
  const previous = enhanced.value ? pill.getBoundingClientRect() : next
  const x = next.left - container.left - nav.clientLeft,
    y = next.top - container.top - nav.clientTop
  const fromX = previous.left - container.left - nav.clientLeft,
    fromY = previous.top - container.top - nav.clientTop
  motion?.cancel()
  pill.style.width = `${next.width}px`
  pill.style.height = `${next.height}px`
  pill.style.transform = `translate3d(${x}px,${y}px,0)`
  const wasReady = enhanced.value
  enhanced.value = true
  if (
    wasReady &&
    animate &&
    !reduced?.matches &&
    (Math.abs(x - fromX) > 0.5 ||
      Math.abs(y - fromY) > 0.5 ||
      Math.abs(previous.width - next.width) > 0.5)
  ) {
    const direction = Math.sign(x - fromX)
    motion = pill.animate(
      [
        {
          transform: `translate3d(${fromX}px,${fromY}px,0) scale(${previous.width / next.width},${previous.height / next.height})`,
        },
        {
          transform: `translate3d(${x + direction * 2}px,${y}px,0) scale(1.035,.97)`,
          offset: 0.72,
        },
        { transform: `translate3d(${x}px,${y}px,0) scale(1,1)` },
      ],
      { duration: 300, easing: 'cubic-bezier(.22,1,.36,1)' },
    )
  }
}
function schedule(animate = true) {
  if (import.meta.server || !alive) return
  cancelAnimationFrame(frame)
  frame = requestAnimationFrame(() => move(animate))
}
function choose(event: MouseEvent, path: string) {
  if (
    event.button ||
    event.metaKey ||
    event.ctrlKey ||
    event.shiftKey ||
    event.altKey ||
    event.defaultPrevented
  )
    return
  requested = localePath(path)
  visual.value = path
  schedule()
}
watch(selected, (value) => {
  if (value !== section(router.currentRoute.value.path)) return
  visual.value = value
  requested = ''
  void nextTick(() => schedule())
})
watch(locale, () => {
  void nextTick(() => schedule(false))
})
const removeStartHook = router.beforeEach((to) => {
  requested = to.path
  visual.value = section(to.path)
  schedule()
})
const removeRouteHook = router.afterEach((to, _from, failure) => {
  if (failure && to.path === requested) {
    visual.value = section(router.currentRoute.value.path)
    requested = ''
    schedule()
  } else if (!failure && to.path === requested) {
    visual.value = section(to.path)
    requested = ''
    void nextTick(() => schedule())
  }
})
const reduceMotion = () => {
  if (reduced?.matches) {
    motion?.cancel()
    schedule(false)
  }
}
onMounted(() => {
  visual.value = selected.value
  reduced = matchMedia('(prefers-reduced-motion: reduce)')
  reduced.addEventListener('change', reduceMotion)
  observer = new ResizeObserver(() => schedule(false))
  if (root.value) {
    observer.observe(root.value)
    root.value.querySelectorAll('a').forEach((link) => observer!.observe(link))
  }
  schedule(false)
  void document.fonts.ready.then(() => {
    if (alive) schedule(false)
  })
})
onUnmounted(() => {
  alive = false
  observer?.disconnect()
  motion?.cancel()
  cancelAnimationFrame(frame)
  removeRouteHook()
  removeStartHook()
  reduced?.removeEventListener('change', reduceMotion)
})
const items = computed(() => [
  {
    path: '/pokemon',
    label: t('nav.pokemon'),
    icon: 'M3 12h18M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18Z M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z',
  },
  {
    path: '/types',
    label: t('nav.types'),
    icon: 'm12 3 9 5-9 5-9-5 9-5Zm-9 9 9 5 9-5M3 16l9 5 9-5',
  },
  {
    path: '/items',
    label: locale.value === 'zh-Hans' ? '道具' : 'Items',
    icon: 'M5 7h14l1 14H4L5 7Zm3 0V6a4 4 0 0 1 8 0v1',
  },
  {
    path: '/moves',
    label: locale.value === 'zh-Hans' ? '招式' : 'Moves',
    icon: 'm14 2-9 12h6l-1 8 9-12h-6l1-8Z',
  },
])
</script>
<template>
  <nav
    ref="root"
    class="catalog-nav"
    :class="{ 'catalog-nav--enhanced': enhanced }"
    :aria-label="locale === 'zh-Hans' ? '主导航' : 'Main navigation'"
  >
    <span ref="slider" v-show="enhanced" class="catalog-nav__slider" aria-hidden="true" />
    <NuxtLink
      v-for="item in items"
      :key="item.path"
      :to="localePath(item.path)"
      :data-nav-path="item.path"
      class="catalog-nav__link"
      :class="{ 'is-active': (visual || selected) === item.path }"
      :aria-current="selected === item.path ? 'page' : undefined"
      @click.capture="choose($event, item.path)"
    >
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="1.5"
        stroke-linejoin="round"
        stroke-linecap="round"
        aria-hidden="true"
      >
        <path :d="item.icon" /></svg
      ><span>{{ item.label }}</span>
    </NuxtLink>
  </nav>
</template>
<style scoped>
.catalog-nav {
  display: flex;
  gap: 4px;
  align-items: center;
}
.catalog-nav {
  position: relative;
  isolation: isolate;
}
.catalog-nav__slider {
  position: absolute;
  left: 0;
  top: 0;
  pointer-events: none;
  z-index: -1;
  border-radius: 8px;
  background: var(--nav-slider-paper, #fff);
  box-shadow: 0 1px 4px #243b2d10;
  transform-origin: 0 0;
}
.catalog-nav__link {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  padding: 9px 13px;
  border-radius: 8px;
  color: #60717d;
  font-size: 13px;
  font-weight: 650;
  text-decoration: none;
}
.catalog-nav__link svg {
  display: none;
  width: 16px;
  height: 16px;
}
.catalog-nav__link:hover {
  background: #f1f5f2;
  color: #274737;
}
.catalog-nav__link.is-active {
  color: #274737;
  background: #edf4ed;
}
.catalog-nav__link:focus-visible {
  outline: 2px solid #568465;
  outline-offset: 3px;
}
@media (max-width: 767px) {
  .catalog-nav {
    order: 3;
    width: 100%;
    justify-content: space-between;
  }
  .catalog-nav__link {
    flex: 1;
    padding: 9px 8px;
  }
}
</style>
