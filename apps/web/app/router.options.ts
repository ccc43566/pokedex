import type { RouterConfig } from '@nuxt/schema'
import { browseContextKey, isBrowsePath } from '../utils/detailNavigation'

export default <RouterConfig>{
  scrollBehavior(to, from, savedPosition) {
    // Browse pages restore after their asynchronous card layout is ready.
    // Query-only drawer navigation must never reset the underlying document.
    if (isBrowsePath(to.path)) return false
    if (to.path === from.path && browseContextKey(to) === browseContextKey(from)) return false
    return savedPosition || { left: 0, top: 0 }
  },
}
