// Route suspense decides when content is ready; no artificial navigation delay
// or page key that would remount the list on drawer/filter query changes.
export function useCatalogPageMotion() {
  if (import.meta.server) return
  const router = useRouter()
  const nuxt = useNuxtApp()
  let pending = ''
  let alive = true
  const animations = new Set<Animation>()
  let reduced: MediaQueryList | undefined
  const category = (path: string) =>
    path.match(/^\/(?:zh-Hans|en)\/(pokemon|types|items|moves)(?:\/|$)/)?.[1]
  function cancel() {
    animations.forEach((animation) => animation.cancel())
    animations.clear()
  }
  function enter() {
    if (!alive || !pending || router.currentRoute.value.path !== pending) return
    pending = ''
    if (reduced?.matches) return
    const page = document.querySelector('main')?.lastElementChild as HTMLElement | null
    if (!page) return
    const bounds = page.getBoundingClientRect()
    // Compact pages can move as one group. Long catalogues only animate their
    // small heading/filter blocks, never the entire tall result grid.
    const candidates =
      bounds.height <= innerHeight * 1.2
        ? [page]
        : ([...page.children].filter((element) => {
            const box = element.getBoundingClientRect()
            return (
              box.width >= 40 &&
              box.height >= 12 &&
              box.height <= Math.min(420, innerHeight * 0.6) &&
              box.bottom > 0 &&
              box.top < innerHeight
            )
          }) as HTMLElement[])
    for (const element of candidates.slice(0, 5)) {
      const animation = element.animate(
        [
          { opacity: 0, transform: 'translateY(4px)' },
          { opacity: 1, transform: 'translateY(0)' },
        ],
        { duration: 160, easing: 'cubic-bezier(.16,1,.3,1)' },
      )
      animations.add(animation)
      animation.onfinish = () => animations.delete(animation)
      animation.oncancel = () => animations.delete(animation)
    }
  }
  const removeGuard = router.beforeResolve((to, from) => {
    if (to.path !== from.path) {
      cancel()
      pending =
        category(to.path) && category(from.path) && category(to.path) !== category(from.path)
          ? to.path
          : ''
    }
  })
  const removeAfter = router.afterEach((to, _from, failure) => {
    if (failure && pending === to.path) {
      pending = ''
      cancel()
    }
  })
  const removeReady = nuxt.hook('page:finish', () => {
    if (pending)
      void nextTick(() => {
        if (alive) {
          enter()
        }
      })
  })
  const changeMotion = () => {
    if (reduced?.matches) cancel()
  }
  onMounted(() => {
    reduced = matchMedia('(prefers-reduced-motion: reduce)')
    reduced.addEventListener('change', changeMotion)
  })
  onUnmounted(() => {
    alive = false
    cancel()
    removeGuard()
    removeAfter()
    removeReady()
    reduced?.removeEventListener('change', changeMotion)
  })
}
