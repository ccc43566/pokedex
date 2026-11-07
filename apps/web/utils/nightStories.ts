import type { NightVisitor } from './nightHome'

interface Rect {
  x: number
  y: number
  w: number
  h: number
}
interface Placement {
  x: number
  y: number
  bounds: Rect
  dx?: number
  dy?: number
  size?: number
  scale?: number
  bush?: number
}

// Approved finite stories. No preview controls or document-global state.
export function startNightStories(
  home: HTMLElement,
  rows: NightVisitor[],
  allowed: () => boolean,
  signal: AbortSignal,
): () => void {
  const host = home.querySelector<HTMLElement>('.scene-stories')!
  const order = ['flight', 'scare', 'bush'] as const
  const reduced = matchMedia('(prefers-reduced-motion:reduce)')
  let next = 0,
    timer = 0,
    deadline = 0,
    lastScroll = -Infinity,
    due = performance.now() + 8000
  let animations: Animation[] = [],
    alive = true,
    active = false,
    removePointer = () => {}
  const cooldown = () => 25000 + Math.random() * 15000
  const eligible = () =>
    allowed() &&
    !home.querySelector('input:focus,select:focus') &&
    !document.querySelector('[role="dialog"]')
  function clear() {
    clearTimeout(timer)
    clearTimeout(deadline)
    removePointer()
    removePointer = () => {}
    animations.forEach((animation) => animation.cancel())
    animations = []
    host.replaceChildren()
    active = false
  }
  function arm() {
    if (!alive || active || !eligible()) return
    clearTimeout(timer)
    timer = window.setTimeout(
      attempt,
      Math.max(40, due - performance.now(), 1200 - (performance.now() - lastScroll)),
    )
  }
  function finish() {
    clear()
    due = performance.now() + cooldown()
    arm()
  }
  function safe(rect: Rect, obstacles: DOMRect[]) {
    return (
      rect.x >= 6 &&
      rect.y >= 8 &&
      rect.x + rect.w <= innerWidth - 6 &&
      rect.y + rect.h <= innerHeight - 8 &&
      !obstacles.some(
        (r) =>
          rect.x < r.right + 5 &&
          rect.x + rect.w > r.left - 5 &&
          rect.y < r.bottom + 5 &&
          rect.y + rect.h > r.top - 5,
      )
    )
  }
  function plan(name: string): Placement | undefined {
    const width = innerWidth,
      height = innerHeight
    const hero = home.querySelector('.hero-intro')!.getBoundingClientRect(),
      copy = home.querySelector('.search-copy')!.getBoundingClientRect()
    const obstacles = [
      ...home.querySelectorAll(
        '.search-copy,.brand-trigger,.nav-links,.compact-brand,.catalog-heading,.visitor-name,.visitor-number,.lantern-yard,.page-footer,.home-settings',
      ),
    ]
      .map((e) => e.getBoundingClientRect())
      .filter((r) => r.width && r.height && r.bottom > 0 && r.top < height)
    const style = getComputedStyle(host),
      size = Number(style.getPropertyValue('--flight-size')),
      scale = Number(style.getPropertyValue('--scare-scale')),
      bush = Number(style.getPropertyValue('--bush-width'))
    if (name === 'flight') {
      const moon = home.querySelector('.moon')!.getBoundingClientRect(),
        right = Math.min(width - size - 18, width * 0.76)
      const starts =
        width <= 600
          ? [
              {
                x: width - size - 18,
                y: hero.bottom - size - 12,
                dx: -Math.min(70, width * 0.17),
                dy: -72,
              },
              { x: 18, y: hero.bottom - size - 12, dx: Math.min(70, width * 0.17), dy: -72 },
            ]
          : [
              {
                x: right,
                y: Math.max(215, hero.top + 38),
                dx: Math.max(
                  12 - right,
                  Math.min(
                    width - size - 12 - right,
                    moon.left + moon.width / 2 - size / 2 - right,
                  ),
                ),
                dy: -130,
              },
              { x: width - size - 18, y: height * 0.55, dx: -60, dy: -110 },
            ]
      for (const p of starts) {
        const bounds = {
          x: Math.min(p.x, p.x + p.dx),
          y: Math.min(p.y, p.y + p.dy),
          w: Math.abs(p.dx) + size,
          h: Math.abs(p.dy) + size,
        }
        if (safe(bounds, obstacles)) return { ...p, size, bounds }
      }
    } else {
      const w = name === 'scare' ? 180 * scale : bush,
        h = name === 'scare' ? 72 * scale : (bush * 52) / 70,
        drift = name === 'bush' ? (9 * bush) / 70 : 0
      const xs =
        name === 'scare'
          ? [width * 0.13, width * 0.3, 18, width * 0.58]
          : [width - w - 24, 18 + drift, width * 0.72, width * 0.32]
      for (const y of [copy.bottom + 14, hero.bottom - h - 12, height * 0.7, height * 0.46])
        for (const x of xs) {
          const bounds = { x: x - drift, y, w: w + drift, h }
          if (safe(bounds, obstacles)) return { x, y, scale, bush, bounds }
        }
    }
  }
  function attempt() {
    if (!alive || !eligible()) {
      clearTimeout(timer)
      return
    }
    if (performance.now() - lastScroll < 1200) {
      arm()
      return
    }
    const name = order[next]!
    next = (next + 1) % order.length
    const placement = plan(name)
    if (!placement) {
      due = performance.now() + cooldown()
      arm()
      return
    }
    active = true
    const element = document.createElement('div')
    element.className = `story story-${name}`
    element.style.left = `${placement.x}px`
    element.style.top = `${placement.y}px`
    const actor = (id: number, className: string) => {
      const image = new Image(96, 96)
      image.className = `story-actor ${className}`
      image.alt = ''
      image.src = rows.find((row) => row.id === id)!.sprite
      image.addEventListener('error', finish, { once: true })
      element.append(image)
      return image
    }
    const animate = (target: Element, keyframes: Keyframe[], duration: number) => {
      animations.push(target.animate(keyframes, { duration, easing: 'linear', fill: 'both' }))
    }
    if (name === 'flight') {
      const bat = actor(169, 'story-bat'),
        dx = placement.dx!,
        dy = placement.dy!,
        end = 32 / placement.size!
      animate(
        bat,
        [
          { transform: 'translate(0,0) scale(1)', opacity: 0 },
          { offset: 0.12, transform: 'translate(0,0) scale(1)', opacity: 1 },
          {
            offset: 0.38,
            transform: `translate(${dx * 0.18}px,${dy * 0.15}px) scale(.95)`,
            opacity: 1,
          },
          {
            offset: 0.8,
            transform: `translate(${dx * 0.85}px,${dy * 0.82}px) scale(${end})`,
            opacity: 0.9,
          },
          { transform: `translate(${dx}px,${dy}px) scale(${end})`, opacity: 0 },
        ],
        6500,
      )
    } else if (name === 'scare') {
      const ghost = actor(92, 'story-ghost'),
        phantump = actor(708, 'story-phantump'),
        s = placement.scale!
      const tree = document.createElementNS('http://www.w3.org/2000/svg', 'svg')
      tree.setAttribute('viewBox', '0 0 48 72')
      tree.setAttribute('class', 'story-tree')
      tree.setAttribute('shape-rendering', 'crispEdges')
      tree.innerHTML =
        '<path fill="#222c38" d="M19 72V38h-5V25H8V15h7V7h17v10h9v12h-8v13h-6v30z"/><path fill="#2e3d40" d="M3 28V17h7V9h10V2h9v9h11v9h6v15H33v-6H19v8H8v-9z"/><path fill="#394644" d="M13 16h9V9h7v9h8v8H22v-5h-9z"/>'
      element.append(tree)
      animate(
        ghost,
        [
          { opacity: 0, transform: `translateX(${12 * s}px)` },
          { offset: 0.22, opacity: 0, transform: `translateX(${12 * s}px)` },
          { offset: 0.35, opacity: 0.9, transform: 'translateX(0)' },
          { offset: 0.72, opacity: 0.85, transform: `translateX(${-5 * s}px)` },
          { opacity: 0, transform: `translateX(${5 * s}px)` },
        ],
        3900,
      )
      animate(
        phantump,
        [
          { transform: 'translate(0,0)', opacity: 0 },
          { offset: 0.12, transform: 'translate(0,0)', opacity: 0.95 },
          { offset: 0.28, transform: 'translate(0,0)', opacity: 0.95 },
          { offset: 0.38, transform: `translate(${-14 * s}px,${-9 * s}px)`, opacity: 0.95 },
          { offset: 0.48, transform: `translate(${-24 * s}px,0)`, opacity: 0.95 },
          { offset: 0.61, transform: `translate(${-43 * s}px,${-8 * s}px)`, opacity: 0.95 },
          { offset: 0.72, transform: `translate(${-57 * s}px,0)`, opacity: 0.9 },
          { offset: 0.84, transform: `translate(${-76 * s}px,${s}px)`, opacity: 0 },
          { transform: `translate(${-76 * s}px,${s}px)`, opacity: 0 },
        ],
        3900,
      )
    } else {
      const bush = new Image()
      bush.className = 'story-bush-image'
      bush.alt = ''
      bush.src = '/home/night/moving-bush.svg'
      element.append(bush)
      const step = placement.bush! / 70
      animate(
        bush,
        [
          { transform: 'translateX(0)', opacity: 0 },
          { offset: 0.12, transform: 'translateX(0)', opacity: 0.85 },
          { offset: 0.3, transform: 'translateX(0)', opacity: 0.85, easing: 'steps(1,end)' },
          { offset: 0.4, transform: `translateX(${-4 * step}px)`, opacity: 0.85 },
          {
            offset: 0.55,
            transform: `translateX(${-4 * step}px)`,
            opacity: 0.85,
            easing: 'steps(1,end)',
          },
          { offset: 0.65, transform: `translateX(${-9 * step}px)`, opacity: 0.85 },
          { offset: 0.88, transform: `translateX(${-9 * step}px)`, opacity: 0.85 },
          { transform: `translateX(${-9 * step}px)`, opacity: 0 },
        ],
        3200,
      )
      const pointer = (event: PointerEvent) => {
        if (event.pointerType && event.pointerType !== 'mouse') return
        const dx = event.clientX - placement.x - placement.bush! / 2,
          dy = event.clientY - placement.y - (placement.bush! * 26) / 70
        const near = dx * dx + dy * dy < Math.max(90, placement.bush! * 0.8) ** 2
        animations.forEach((animation) => (near ? animation.pause() : animation.play()))
      }
      document.addEventListener('pointermove', pointer, { passive: true, signal })
      removePointer = () => document.removeEventListener('pointermove', pointer)
    }
    host.replaceChildren(element)
    deadline = window.setTimeout(finish, 8000)
    void Promise.all(animations.map((animation) => animation.finished))
      .then(finish)
      .catch(() => {})
  }
  window.addEventListener(
    'scroll',
    () => {
      lastScroll = performance.now()
      // An idle story host needs no DOM mutation or timer reset on every scroll tick.
      // The existing wake-up checks lastScroll before starting the next scene.
      if (active) finish()
    },
    { passive: true, signal },
  )
  window.addEventListener('resize', finish, { signal })
  document.addEventListener('visibilitychange', finish, { signal })
  document.addEventListener(
    'focusin',
    () => {
      if (!eligible()) clear()
      else arm()
    },
    { signal },
  )
  reduced.addEventListener('change', finish, { signal })
  home.querySelector('#home-ambient')!.addEventListener('change', finish, { signal })
  window.addEventListener('pagehide', clear, { signal })
  window.addEventListener(
    'pageshow',
    () => {
      due = performance.now() + cooldown()
      arm()
    },
    { signal },
  )
  arm()
  return () => {
    alive = false
    clear()
  }
}
