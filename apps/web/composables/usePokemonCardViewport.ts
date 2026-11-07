import type { PokemonListItem } from '~/types/api'

// Measure with lightweight text-only cards, then keep those exact row heights
// while offscreen card contents sleep. No guessed intrinsic sizes during scroll.
export function usePokemonCardViewport(
  grid: Ref<HTMLElement | null>,
  items: ComputedRef<PokemonListItem[]>,
) {
  const heights = shallowRef<Record<number, number>>({})
  const columns = ref(2)
  const visible = shallowRef(new Set<number>())
  let resize: ResizeObserver | undefined
  let visibility: IntersectionObserver | undefined
  let textChanges: MutationObserver | undefined
  let measuredWidth = 0
  let measuredIds: number[] = []
  let frame = 0
  let alive = true
  let observed = new WeakSet<Element>()

  function node(tag: string, className: string, text?: string) {
    const element = document.createElement(tag)
    element.className = className
    if (text) element.textContent = text
    return element
  }
  function measure() {
    frame = 0
    const element = grid.value
    if (!element || !alive || !items.value.length) return
    const width = element.getBoundingClientRect().width
    if (!width) return
    const ids = items.value.map((item) => item.id)
    const columnCount = getComputedStyle(element).gridTemplateColumns.split(' ').length
    columns.value = columnCount
    const appendOnly =
      Math.abs(width - measuredWidth) < 0.5 &&
      ids.length > measuredIds.length &&
      measuredIds.every((id, index) => ids[index] === id)
    const start = appendOnly ? Math.floor(measuredIds.length / columnCount) * columnCount : 0
    measuredWidth = width
    measuredIds = ids
    const names = new Map<number, Element>()
    for (const card of element.querySelectorAll<HTMLElement>('.pokemon-card')) {
      const name = card.querySelector('.pokemon-card__name')
      if (name) names.set(Number(card.dataset.pokemonId), name)
    }
    const probe = node('div', 'pokemon-grid')
    probe.setAttribute('aria-hidden', 'true')
    probe.style.cssText = `position:absolute;left:0;top:0;width:${width}px;visibility:hidden;pointer-events:none;contain:layout style paint;`
    for (const pokemon of items.value.slice(start)) {
      const card = node('div', 'pokemon-card-placeholder')
      const details = node('div', 'pokemon-card__details')
      const existingName = names.get(pokemon.id)
      const name = existingName ? existingName.cloneNode(true) : node('h2', 'pokemon-card__name')
      if (!existingName) {
        name.appendChild(node('span', '', pokemon.localizedName))
        if (pokemon.variantLabel)
          name.appendChild(node('span', 'pokemon-card__form-label', `（${pokemon.variantLabel}）`))
      }
      const types = node('div', 'pokemon-card__types')
      types.style.height = '30px'
      details.append(name, types)
      card.append(node('div', 'pokemon-card__top'), node('div', 'pokemon-card__art'), details)
      probe.append(card)
    }
    element.parentElement?.append(probe)
    const next: Record<number, number> = appendOnly ? { ...heights.value } : {}
    for (let index = 0; index < probe.children.length; index++) {
      next[items.value[start + index]!.id] = probe.children[index]!.getBoundingClientRect().height
    }
    probe.remove()
    heights.value = next
  }
  function scheduleMeasure() {
    if (!frame && alive) frame = requestAnimationFrame(measure)
  }
  function observeCards() {
    for (const card of grid.value?.querySelectorAll('.pokemon-card') || []) {
      if (!observed.has(card)) {
        observed.add(card)
        visibility?.observe(card)
      }
    }
  }
  function cardStyle(id: number) {
    const height = heights.value[id]
    return height
      ? {
          height: `${height}px`,
          contentVisibility: visible.value.has(id) ? ('visible' as const) : ('hidden' as const),
        }
      : undefined
  }
  watch(() => items.value.map((item) => item.id).join(','), scheduleMeasure, { flush: 'post' })
  watch(
    grid,
    (element) => {
      resize?.disconnect()
      textChanges?.disconnect()
      visibility?.disconnect()
      observed = new WeakSet<Element>()
      visible.value = new Set()
      if (element) {
        resize?.observe(element)
        textChanges?.observe(element, { subtree: true, childList: true, characterData: true })
        scheduleMeasure()
        observeCards()
      }
    },
    { flush: 'post' },
  )
  onUpdated(observeCards)
  onMounted(() => {
    textChanges = new MutationObserver((records) => {
      if (
        records.some((record) => {
          const element =
            record.target instanceof Element ? record.target : record.target.parentElement
          return element?.closest('.pokemon-card__name')
        })
      )
        scheduleMeasure()
    })
    visibility = new IntersectionObserver(
      (entries) => {
        const next = new Set(visible.value)
        for (const entry of entries) {
          const id = Number((entry.target as HTMLElement).dataset.pokemonId)
          if (entry.isIntersecting) next.add(id)
          else next.delete(id)
        }
        visible.value = next
      },
      { rootMargin: '700px 0px' },
    )
    resize = new ResizeObserver(([entry]) => {
      if (entry && Math.abs(entry.contentRect.width - measuredWidth) > 0.5) scheduleMeasure()
    })
    if (grid.value) {
      resize.observe(grid.value)
      textChanges.observe(grid.value, { subtree: true, childList: true, characterData: true })
    }
    scheduleMeasure()
    observeCards()
    void document.fonts.ready.then(scheduleMeasure)
  })
  onUnmounted(() => {
    alive = false
    cancelAnimationFrame(frame)
    resize?.disconnect()
    visibility?.disconnect()
    textChanges?.disconnect()
  })
  return {
    columns,
    cardStyle,
    cardLayoutKey: (id: number) => `${heights.value[id] || 0}:${visible.value.has(id)}`,
  }
}
