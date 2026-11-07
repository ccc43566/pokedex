import type { Ref } from 'vue'
import { nightVisitors } from '~/utils/nightHome'
import { startNightStories } from '~/utils/nightStories'

// One mounted homepage owns all observers, listeners, frames and animations.
export function useNightHome(root: Ref<HTMLElement | null>, ambient: Ref<boolean>) {
  let dispose = () => {}
  onMounted(() => {
    if (!root.value) return
    const home = root.value
    const element = (selector: string) => home.querySelector<HTMLElement>(selector)!
    const reduced = matchMedia('(prefers-reduced-motion:reduce)')
    const mobile = matchMedia('(max-width:600px), (hover:none) and (pointer:coarse)')
    const abort = new AbortController()
    const signal = abort.signal
    const scene = element('.scene'),
      art = element('.scene-art'),
      brand = element('.brand-trigger')
    const sky = element('.sky'),
      copy = element('.search-copy'),
      hero = element('.hero-intro')
    const logo = element('.night-logo'),
      masthead = element('.masthead')
    const ghosts = [element('.wandering-ghost'), element('.quiet-ghost')]
    const foreground = [element('.front-branches'), element('.ground-mist')]
    const anchors = [...home.querySelectorAll<HTMLAnchorElement>('.visitor')]
    const rows = new Map(nightVisitors.map((row) => [String(row.id), row]))
    const visible = new Set<HTMLAnchorElement>(),
      failed = new Set<string>()
    let alive = true,
      inView = true,
      suspended = false,
      frame = 0,
      dirty = true,
      logoRun = 0
    let geometry = { width: 0, height: 0, header: 0, imageWidth: 0, imageHeight: 0 }
    let tracks: Animation[] = [],
      native = false
    let navigationScrolled: boolean | undefined
    let logoTimer: ReturnType<typeof setTimeout> | undefined
    let logoReady = false,
      logoVisible = true
    const set = (target: HTMLElement, property: string, value: string) => {
      if (target.style.getPropertyValue(property) !== value)
        target.style.setProperty(property, value)
    }
    const motionAllowed = () => ambient.value && !reduced.matches && !document.hidden && !suspended
    function updateSprites() {
      home.classList.toggle('visitor-motion-enabled', motionAllowed())
      for (const anchor of anchors) {
        const row = rows.get(anchor.dataset.id!)!,
          image = anchor.querySelector('img')!
        const playing =
          motionAllowed() &&
          !mobile.matches &&
          visible.has(anchor) &&
          row.animation &&
          !failed.has(String(row.id))
        const source = playing ? row.animation!.path : row.sprite
        if (image.getAttribute('src') !== source) image.src = source
        const state = playing ? 'true' : 'false'
        if (image.dataset.playing !== state) image.dataset.playing = state
      }
      for (const target of home.querySelectorAll<HTMLElement>('.cloud,.moon,.wandering-ghost')) {
        set(target, 'animation-play-state', motionAllowed() && inView ? 'running' : 'paused')
      }
      updateLogo()
    }
    for (const anchor of anchors) {
      anchor.querySelector('img')!.addEventListener(
        'error',
        () => {
          const image = anchor.querySelector('img')!
          if (image.dataset.playing === 'true') {
            failed.add(anchor.dataset.id!)
            updateSprites()
          } else image.style.visibility = 'hidden'
        },
        { signal },
      )
    }
    const spriteObserver = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          const anchor = entry.target as HTMLAnchorElement
          if (entry.isIntersecting && entry.intersectionRatio >= 0.35) visible.add(anchor)
          else visible.delete(anchor)
        }
        updateSprites()
      },
      { threshold: [0, 0.35] },
    )
    anchors.forEach((anchor) => spriteObserver.observe(anchor))
    const heroObserver = new IntersectionObserver(([entry]) => {
      inView = Boolean(entry?.isIntersecting)
      updateSprites()
    })
    heroObserver.observe(hero)
    const logoObserver = new IntersectionObserver(([entry]) => {
      logoVisible = Boolean(entry?.isIntersecting)
      updateLogo()
    })
    logoObserver.observe(brand)
    const logoAllowed = () =>
      alive && logoReady && logoVisible && !reduced.matches && !document.hidden && !suspended
    function clearLogoTimer() {
      clearTimeout(logoTimer)
      logoTimer = undefined
    }
    function scheduleLogo() {
      if (!logoAllowed() || logo.dataset.playing === 'true' || logoTimer !== undefined) return
      // Start the gap after the entire staggered animation has finished, not every 2s.
      logoTimer = setTimeout(() => {
        logoTimer = undefined
        void replayLogo()
      }, 2000)
    }
    function updateLogo() {
      const allowed = logoAllowed()
      set(logo, '--logo-play-state', allowed ? 'running' : 'paused')
      if (!allowed) {
        clearLogoTimer()
        if (reduced.matches && logo.dataset.playing === 'true') {
          ++logoRun
          logo.dataset.playing = 'false'
        }
      } else scheduleLogo()
    }
    async function replayLogo() {
      if (!logoAllowed() || logo.dataset.playing === 'true') return
      clearLogoTimer()
      const run = ++logoRun
      logo.dataset.playing = 'false'
      void logo.offsetWidth
      logo.dataset.playing = 'true'
      await Promise.allSettled(
        logo.getAnimations({ subtree: true }).map((animation) => animation.finished),
      )
      if (alive && run === logoRun) {
        logo.dataset.playing = 'false'
        scheduleLogo()
      }
    }
    void document.fonts.ready.then(() => {
      if (!alive) return
      logoReady = true
      updateLogo()
      void replayLogo()
    })
    brand.addEventListener(
      'click',
      () => {
        logo.dataset.playing = 'false'
        void replayLogo()
      },
      { signal },
    )
    brand.addEventListener(
      'pointerenter',
      (event) => {
        if (event.pointerType === 'mouse') void replayLogo()
      },
      { signal },
    )
    brand.addEventListener(
      'focus',
      () => {
        void replayLogo()
      },
      { signal },
    )
    let pressed: HTMLElement | null = null
    const clearPress = () => {
      pressed?.classList.remove('visitor--pressed')
      pressed = null
    }
    home.addEventListener(
      'pointerdown',
      (event) => {
        if (!mobile.matches || !motionAllowed()) return
        clearPress()
        pressed = (event.target as Element).closest('.visitor')
        pressed?.classList.add('visitor--pressed')
      },
      { signal },
    )
    document.addEventListener('pointerup', clearPress, { signal })
    document.addEventListener('pointercancel', clearPress, { signal })
    window.addEventListener('blur', clearPress, { signal })

    const Timeline = (
      window as unknown as {
        ScrollTimeline?: new (options: { source: Element; axis: string }) => AnimationTimeline
      }
    ).ScrollTimeline
    let timeline: AnimationTimeline | undefined
    if (Timeline && CSS.supports('animation-range', '0px 100px')) {
      try {
        timeline = new Timeline({ source: document.documentElement, axis: 'block' })
      } catch {
        /* Local fallback below. */
      }
    }
    const cancelTracks = () => {
      tracks.forEach((animation) => animation.cancel())
      tracks = []
    }
    function configure() {
      cancelTracks()
      const width = innerWidth,
        height = innerHeight
      const scale = (width <= 600 ? 850 / 940 : Math.max(width / 1672, (height + 260) / 940)) * 0.75
      geometry = {
        width,
        height,
        header: masthead.offsetHeight,
        imageWidth: 1672 * scale,
        imageHeight: 940 * scale,
      }
      set(scene, '--frame-width', `${geometry.imageWidth}px`)
      set(scene, '--frame-height', `${geometry.imageHeight}px`)
      scene.classList.toggle('scene--flattened', reduced.matches || geometry.imageHeight >= height)
      native = Boolean(timeline)
      if (native) {
        const range = height * 0.9,
          moving = !reduced.matches
        const track = (
          target: HTMLElement,
          property: string,
          from: string,
          to: string,
          end: number,
        ) => {
          set(target, property, from)
          if (from === to || end <= 0) return
          const animation = target.animate([{ [property]: from }, { [property]: to }], {
            timeline,
            rangeStart: '0px',
            rangeEnd: `${end}px`,
            fill: 'both',
            easing: 'linear',
            duration: 'auto',
          } as KeyframeAnimationOptions)
          if (!('rangeEnd' in animation)) {
            animation.cancel()
            throw new Error('Missing animation attachment ranges')
          }
          tracks.push(animation)
        }
        try {
          const fade = (target: HTMLElement, amount = 1) =>
            track(target, 'opacity', String(amount), String(moving ? amount * 0.28 : amount), range)
          fade(scene)
          ghosts.forEach((target) => fade(target))
          fade(foreground[0]!, 0.35)
          fade(foreground[1]!, 0.55)
          track(brand, 'opacity', '1', moving ? '0' : '1', range / 1.7)
          track(
            sky,
            'opacity',
            width <= 900 ? '.8' : '1',
            moving ? '0' : width <= 900 ? '.8' : '1',
            range / 1.7,
          )
          track(copy, 'opacity', '1', moving ? '.35' : '1', range)
          for (const [target, factor] of [
            [sky, 0.38],
            [foreground[0]!, 0.08],
            [foreground[1]!, 0.08],
          ] as const) {
            track(
              target,
              'transform',
              'translate3d(0,0,0)',
              `translate3d(0,${moving ? range * factor : 0}px,0)`,
              range,
            )
          }
          const gap = Math.max(0, height - geometry.imageHeight)
          track(
            art,
            'transform',
            'translate3d(0,0,0)',
            `translate3d(0,${moving ? -gap : 0}px,0)`,
            gap / 0.08,
          )
        } catch {
          cancelTracks()
          native = false
          timeline = undefined
        }
      }
      home.dataset.motionEngine = native ? 'native' : 'compatible'
      dirty = false
    }
    function updateNavigation(y = Math.max(0, scrollY)) {
      const scrolled = y >= geometry.header
      if (navigationScrolled === scrolled) return
      navigationScrolled = scrolled
      home.classList.toggle('is-scrolled', scrolled)
    }
    function updateScroll() {
      frame = 0
      if (!alive || document.hidden || suspended) return
      if (dirty) configure()
      const y = Math.max(0, scrollY),
        range = geometry.height * 0.9
      const p = Math.min(1, y / range),
        moving = !reduced.matches
      updateNavigation(y)
      if (native) return
      const opacity = moving ? Math.max(0.28, 1 - p * 0.72) : 1
      set(scene, 'opacity', String(opacity))
      set(brand, 'opacity', String(moving ? Math.max(0, 1 - p * 1.7) : 1))
      set(
        sky,
        'opacity',
        String((geometry.width <= 900 ? 0.8 : 1) * (moving ? Math.max(0, 1 - p * 1.7) : 1)),
      )
      set(copy, 'opacity', String(moving ? 1 - p * 0.65 : 1))
      ghosts.forEach((target) => set(target, 'opacity', String(opacity)))
      set(foreground[0]!, 'opacity', String(opacity * 0.35))
      set(foreground[1]!, 'opacity', String(opacity * 0.55))
      set(
        art,
        'transform',
        `translate3d(0,${moving ? -Math.min(y * 0.08, Math.max(0, geometry.height - geometry.imageHeight)) : 0}px,0)`,
      )
      for (const [target, factor] of [
        [sky, 0.38],
        [foreground[0]!, 0.08],
        [foreground[1]!, 0.08],
      ] as const) {
        set(target, 'transform', `translate3d(0,${moving ? Math.min(y, range) * factor : 0}px,0)`)
      }
    }
    function schedule(resize = false) {
      if (resize) dirty = true
      if (alive && !suspended && !frame) frame = requestAnimationFrame(updateScroll)
    }
    window.addEventListener(
      'scroll',
      () => {
        // The native timeline already drives transforms/opacity on the compositor.
        // Only the header threshold needs JS, and it changes twice per round trip.
        if (native && !dirty) updateNavigation()
        else schedule()
      },
      { passive: true, signal },
    )
    window.addEventListener('resize', () => schedule(true), { signal })
    const resizeObserver = new ResizeObserver(() => schedule(true))
    resizeObserver.observe(masthead)
    const preference = () => {
      if (reduced.matches) {
        ++logoRun
        logo.dataset.playing = 'false'
      }
      updateSprites()
      schedule(true)
    }
    reduced.addEventListener('change', preference, { signal })
    mobile.addEventListener('change', updateSprites, { signal })
    document.addEventListener(
      'visibilitychange',
      () => {
        updateSprites()
        schedule(true)
      },
      { signal },
    )
    window.addEventListener(
      'pagehide',
      () => {
        suspended = true
        cancelTracks()
        updateSprites()
      },
      { signal },
    )
    window.addEventListener(
      'pageshow',
      () => {
        suspended = false
        updateSprites()
        schedule(true)
      },
      { signal },
    )
    const stopAmbientWatch = watch(ambient, updateSprites)
    const stopStories = startNightStories(home, nightVisitors, motionAllowed, signal)
    schedule(true)
    updateSprites()
    dispose = () => {
      alive = false
      suspended = true
      ++logoRun
      clearLogoTimer()
      abort.abort()
      stopStories()
      stopAmbientWatch()
      clearPress()
      spriteObserver.disconnect()
      heroObserver.disconnect()
      logoObserver.disconnect()
      resizeObserver.disconnect()
      if (frame) cancelAnimationFrame(frame)
      cancelTracks()
      home.getAnimations({ subtree: true }).forEach((animation) => animation.cancel())
    }
  })
  onBeforeUnmount(() => dispose())
}
