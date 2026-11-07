import { onBeforeRouteLeave, onBeforeRouteUpdate } from 'vue-router'
import { browseContextKey, readBrowsePosition, saveBrowsePosition } from '~/utils/detailNavigation'

export function useBrowsePosition(
  whenReady: (top?: number) => Promise<void> = async () => {},
  defaultTop?: number,
  options: { scrollSaveDelay?: number } = {},
) {
  const route = useRoute()
  const router = useRouter()
  const pagePath = route.path
  let restoring = true
  let alive = true
  let restoration = 0
  let leaving = false
  let saveTimer: ReturnType<typeof setTimeout> | undefined
  function remember() {
    if (!leaving && !restoring && route.path === pagePath && !route.query.detail)
      saveBrowsePosition(route, window.scrollY)
  }
  function stopPendingSave() {
    clearTimeout(saveTimer)
    saveTimer = undefined
  }
  function rememberScroll() {
    if (leaving) return
    if (!options.scrollSaveDelay) return remember()
    stopPendingSave()
    saveTimer = setTimeout(() => {
      saveTimer = undefined
      remember()
    }, options.scrollSaveDelay)
  }
  function flushPosition() {
    stopPendingSave()
    remember()
  }
  async function restore(top: number | undefined) {
    stopPendingSave()
    const request = ++restoration
    restoring = true
    await whenReady(top)
    await nextTick()
    await new Promise<void>((resolve) =>
      requestAnimationFrame(() => requestAnimationFrame(() => resolve())),
    )
    if (!alive || leaving || request !== restoration || route.path !== pagePath) return
    if (top !== undefined) {
      window.scrollTo({ top, behavior: 'instant' })
      // Mobile sticky filters shrink only after the restored scroll crosses
      // their anchor. Let that layout settle, then correct native anchoring.
      await nextTick()
      await new Promise<void>((resolve) =>
        requestAnimationFrame(() => requestAnimationFrame(() => resolve())),
      )
      if (!alive || leaving || request !== restoration || route.path !== pagePath) return
      if (Math.abs(window.scrollY - top) > 1) window.scrollTo({ top, behavior: 'instant' })
    }
    restoring = false
    remember()
  }
  onBeforeRouteUpdate((to, from) => {
    stopPendingSave()
    if (!from.query.detail) saveBrowsePosition(from, window.scrollY)
  })
  watch(
    () => [browseContextKey(route), Boolean(route.query.detail)] as const,
    ([key, detail], [previousKey, previousDetail]) => {
      // Nuxt can keep the outgoing page alive while the next page suspends.
      // Never restore/save that next route's position from this page instance.
      if (leaving || route.path !== pagePath) return
      if (key !== previousKey || (previousDetail && !detail)) {
        void restore(readBrowsePosition(route) ?? defaultTop)
      }
    },
    { flush: 'post' },
  )
  onBeforeRouteLeave(() => {
    flushPosition()
    leaving = true
    ++restoration
  })
  const removeNavigationHook = router.afterEach((to, from, failure) => {
    // A fast Back or a cancelled navigation may reuse this still-mounted page.
    if (leaving && (failure || to.path === pagePath)) {
      leaving = false
      void restore(readBrowsePosition(failure ? from : to) ?? defaultTop)
    }
  })
  onMounted(() => {
    void restore(readBrowsePosition(route) ?? defaultTop)
    window.addEventListener('scroll', rememberScroll, { passive: true })
    window.addEventListener('pagehide', flushPosition)
  })
  onUnmounted(() => {
    alive = false
    stopPendingSave()
    removeNavigationHook()
    window.removeEventListener('scroll', rememberScroll)
    window.removeEventListener('pagehide', flushPosition)
  })
}
