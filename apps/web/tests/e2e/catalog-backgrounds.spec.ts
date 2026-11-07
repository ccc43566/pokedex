import { test, expect, type Page } from '@playwright/test'
import { catalogBackgrounds } from '../../utils/catalogBackgrounds'
import type { PokemonListItem } from '../../types/api'
test.setTimeout(120_000)
// Isolate wallpaper checks from the separately changing development API.
// These real records are read once from the existing read-only media/API mirror.
let records: PokemonListItem[] = []
test.beforeAll(async ({ request }) => {
  const response = await request.get(
    'http://127.0.0.1:8080/api/v1/pokemon?generation=1&pageSize=100',
  )
  expect(response.ok()).toBe(true)
  records = (await response.json()).items
})
test.beforeEach(async ({ page }) => {
  await page.route('**/api/v1/pokemon**', async (route) => {
    const url = new URL(route.request().url())
    if (url.pathname.endsWith('/revision'))
      return route.fulfill({ json: { version: 'wallpaper-fixture-v1' } })
    if (!url.pathname.endsWith('/pokemon')) return route.continue()
    const query = url.searchParams.get('q') || ''
    const items = query
      ? records.filter((item) => String(item.id) === query || item.localizedName.includes(query))
      : records
    const page = Number(url.searchParams.get('page') || 1)
    const pageSize = Number(url.searchParams.get('pageSize') || 48)
    await route.fulfill({
      json: {
        items: items.slice((page - 1) * pageSize, page * pageSize),
        page,
        pageSize,
        total: items.length,
        totalPages: Math.ceil(items.length / pageSize),
        hasNext: page * pageSize < items.length,
        hasPrevious: page > 1,
        dataVersion: 'wallpaper-fixture-v1',
      },
    })
  })
})
async function panel(page: Page) {
  await hydrated(page)
  const trigger = page.getByRole('button', { name: '选择页面背景', exact: true })
  if ((await trigger.getAttribute('aria-expanded')) !== 'true') await trigger.click()
  await expect(page.locator('.appearance-panel')).toBeVisible()
}
async function hydrated(page: Page) {
  await page.waitForFunction(() =>
    Boolean(
      (document.getElementById('__nuxt') as HTMLElement & { __vue_app__?: unknown })?.__vue_app__,
    ),
  )
}
async function choose(page: Page, id: string) {
  const bg = catalogBackgrounds.find((item) => item.id === id)!
  await panel(page)
  await page
    .locator('.appearance-mode-options')
    .getByRole('button', { name: bg.mode === 'day' ? '日间' : '夜间', exact: true })
    .click()
  await page
    .locator('.appearance-background')
    .filter({ has: page.getByText(bg.name, { exact: true }) })
    .click()
  await expect(page.locator('.catalog-wallpaper')).toHaveAttribute('data-state', 'ready')
  await expect(page.locator('.catalog-wallpaper')).toHaveAttribute('data-loaded-background', id)
}
test('all completed desktop and mobile backgrounds load, retain grid geometry, and use one fixed layer', async ({
  page,
}, info) => {
  const errors: string[] = []
  page.on('pageerror', (error) => errors.push(error.message))
  await page.setViewportSize({ width: 1440, height: 1000 })
  await page.goto('/zh-Hans/pokemon', { waitUntil: 'domcontentloaded' })
  await hydrated(page)
  await page.locator('#generation-1-trigger').click()
  await expect(page.locator('.pokemon-card')).toHaveCount(48)
  const first = page.locator('.pokemon-card').first()
  const geometry = () =>
    first.evaluate((element) => {
      const r = element.getBoundingClientRect()
      return [r.width, r.height]
    })
  const original = await geometry()
  await first.evaluate((element) => {
    ;(window as unknown as { firstCard: Element }).firstCard = element
  })
  const apiCalls: string[] = []
  page.on('request', (request) => {
    const url = new URL(request.url())
    if (
      url.pathname.endsWith('/pokemon/revision') ||
      (url.pathname.endsWith('/pokemon') && url.searchParams.get('page') === '1')
    )
      apiCalls.push(request.url())
  })
  for (const width of [1440, 393]) {
    await page.setViewportSize({ width, height: 1000 })
    for (const bg of catalogBackgrounds) {
      await choose(page, bg.id)
      const source = width === 393 && bg.mobileImage ? bg.mobileImage : bg.image!
      await expect(page.locator('.catalog-wallpaper')).toHaveAttribute('data-source', source)
      await expect(page.locator('.catalog-wallpaper')).toHaveCSS('background-size', /contain$/)
      await expect(page.locator('.catalog-wallpaper')).toHaveCSS('filter', 'none')
      await page.keyboard.press('Escape')
      await expect(page.getByRole('button', { name: '选择页面背景', exact: true })).toBeFocused()
      expect(
        await first.evaluate(
          (element) => element === (window as unknown as { firstCard: Element }).firstCard,
        ),
      ).toBe(true)
      if (width === 1440) {
        const current = await geometry()
        current.forEach((value, index) => expect(value).toBeCloseTo(original[index]!, 2))
      }
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(
        true,
      )
      await page.screenshot({
        path: `../../../design/catalog-review/background-${bg.id}-${width}.png`,
      })
    }
  }
  expect(apiCalls).toEqual([])
  expect(errors).toEqual([])
})
test('only current full-size image loads, panel scroll stays within viewport, preferences survive reload and language', async ({
  page,
}) => {
  const images: string[] = []
  page.on('request', (request) => {
    if (request.url().includes('/catalog-backgrounds/') && !request.url().includes('/thumbs/'))
      images.push(request.url())
  })
  await page.setViewportSize({ width: 393, height: 871 })
  await page.goto('/zh-Hans/pokemon', { waitUntil: 'domcontentloaded' })
  await panel(page)
  await expect(page.locator('.appearance-background')).toHaveCount(8)
  expect(images).toEqual([])
  const bounds = await page.locator('.appearance-panel').boundingBox()
  expect(bounds!.y + bounds!.height).toBeLessThanOrEqual(871)
  await choose(page, 'day-red')
  expect(images.every((url) => url.endsWith('/red-mobile.webp'))).toBe(true)
  const veil = page.getByRole('slider', { name: '背景淡化', exact: true })
  await veil.fill('36')
  await expect(page.locator('.appearance-dimming output')).toHaveText('36%')
  await expect(page.getByRole('button', { name: '卡片背景 80%', exact: true })).toBeVisible()
  await choose(page, 'night-groudon')
  await expect(veil).toHaveValue('12')
  await page.keyboard.press('Escape')
  await page.reload({ waitUntil: 'domcontentloaded' })
  await expect(page.locator('.catalog-wallpaper')).toHaveAttribute(
    'data-loaded-background',
    'night-groudon',
  )
  await panel(page)
  await page
    .locator('.appearance-mode-options')
    .getByRole('button', { name: '日间', exact: true })
    .click()
  await expect(page.locator('.site-shell')).toHaveAttribute('data-background', 'day-red')
  await expect(veil).toHaveValue('36')
  await page.goto('/en/pokemon', { waitUntil: 'domcontentloaded' })
  await expect(page.locator('.site-shell')).toHaveAttribute('data-background', 'day-red')
  await expect(page.locator('.catalog-wallpaper')).toHaveAttribute(
    'data-source',
    '/catalog-backgrounds/red-mobile.webp',
  )
  await expect(page.locator('.catalog-wallpaper')).toHaveCSS('background-image', /0\.36/)
})
test('failed images fall back to base color without blocking filters or resetting opacity', async ({
  page,
}) => {
  await page.route('**/catalog-backgrounds/red-desktop.webp', (route) => route.abort())
  await page.setViewportSize({ width: 1440, height: 1000 })
  await page.goto('/zh-Hans/pokemon', { waitUntil: 'domcontentloaded' })
  await panel(page)
  await page
    .locator('.appearance-background')
    .filter({ has: page.getByText('赤', { exact: true }) })
    .click()
  await expect(page.locator('.catalog-wallpaper')).toHaveAttribute('data-state', 'error')
  await expect(page.locator('.catalog-wallpaper')).toHaveCSS('background-image', 'none')
  await expect(page.locator('.appearance-panel [role="status"]')).toContainText('背景加载失败')
  await page.keyboard.press('Escape')
  await expect(page.getByRole('button', { name: '卡片背景 80%', exact: true })).toBeVisible()
  await page.getByRole('textbox', { name: '名称或编号', exact: true }).fill('25')
  await page.getByRole('button', { name: '筛选', exact: true }).click()
  await expect(page.locator('.pokemon-card').first()).toBeVisible()
})
test('previous picture stays visible until decoded and a stale response cannot overwrite a later choice', async ({
  page,
}) => {
  await page.setViewportSize({ width: 1440, height: 1000 })
  let release!: () => void
  const held = new Promise<void>((resolve) => {
    release = resolve
  })
  await page.route('**/catalog-backgrounds/red-desktop.webp', async (route) => {
    await held
    await route.continue()
  })
  await page.goto('/zh-Hans/pokemon', { waitUntil: 'domcontentloaded' })
  await choose(page, 'day-snorlax')
  await page
    .locator('.appearance-background')
    .filter({ has: page.getByText('赤', { exact: true }) })
    .click()
  await expect(page.locator('.catalog-wallpaper')).toHaveAttribute('data-state', 'loading')
  await expect(page.locator('.catalog-wallpaper')).toHaveAttribute(
    'data-loaded-background',
    'day-snorlax',
  )
  await choose(page, 'day-green')
  release()
  await page.waitForTimeout(200)
  await expect(page.locator('.catalog-wallpaper')).toHaveAttribute(
    'data-loaded-background',
    'day-green',
  )
})

test('night wallpaper remains a single viewport layer without repainting while scrolling at 4x CPU slowdown', async ({
  page,
}, info) => {
  await page.setViewportSize({ width: 1440, height: 1000 })
  await page.goto('/zh-Hans/pokemon', { waitUntil: 'domcontentloaded' })
  await hydrated(page)
  await page.locator('#generation-1-trigger').click()
  await expect(page.locator('.pokemon-card')).toHaveCount(48)
  await choose(page, 'night-red-pikachu')
  await page.keyboard.press('Escape')
  const wallpaper = page.locator('.catalog-wallpaper')
  const original = await wallpaper.boundingBox()
  const cdp = await page.context().newCDPSession(page)
  await cdp.send('DOM.enable')
  const { root } = await cdp.send('DOM.getDocument')
  const { nodeId } = await cdp.send('DOM.querySelector', {
    nodeId: root.nodeId,
    selector: '.catalog-wallpaper',
  })
  const { node } = await cdp.send('DOM.describeNode', { nodeId })
  let layers: { layerId: string; backendNodeId?: number; drawsContent: boolean }[] = []
  cdp.on('LayerTree.layerTreeDidChange', (event) => {
    layers = event.layers || []
  })
  await cdp.send('LayerTree.enable')
  await expect
    .poll(
      () =>
        layers.filter((layer) => layer.backendNodeId === node.backendNodeId && layer.drawsContent)
          .length,
    )
    .toBe(1)
  await page.waitForTimeout(250)
  let paints = 0
  cdp.on('LayerTree.layerPainted', ({ layerId }) => {
    if (
      layers.some(
        (layer) => layer.layerId === layerId && layer.backendNodeId === node.backendNodeId,
      )
    )
      paints++
  })
  await cdp.send('Emulation.setCPUThrottlingRate', { rate: 4 })
  const frames = await page.evaluate(async () => {
    const intervals: number[] = []
    let previous = 0
    for (let index = 0; index < 90; index++) {
      const time = await new Promise<number>((resolve) => requestAnimationFrame(resolve))
      if (previous) intervals.push(time - previous)
      previous = time
      window.scrollTo({ top: index < 45 ? index * 22 : (89 - index) * 22, behavior: 'instant' })
    }
    return intervals
  })
  await cdp.send('Emulation.setCPUThrottlingRate', { rate: 1 })
  expect(paints).toBe(0)
  expect(await wallpaper.boundingBox()).toEqual(original)
  await expect(wallpaper).toHaveCount(1)
  const sorted = [...frames].sort((a, b) => a - b)
  await info.attach('wallpaper-scroll-metrics.json', {
    body: JSON.stringify(
      {
        fixture: true,
        cpuSlowdown: 4,
        backgroundPaints: paints,
        averageFps: 1000 / (frames.reduce((a, b) => a + b, 0) / frames.length),
        frameP95Ms: sorted[Math.floor(sorted.length * 0.95)],
      },
      null,
      2,
    ),
    contentType: 'application/json',
  })
  await cdp.detach()
})

test('chooser fits short mobile and ultrawide screens and choosing a background preserves the current scroll position', async ({
  page,
}) => {
  for (const size of [
    { width: 320, height: 568 },
    { width: 2560, height: 1080 },
  ]) {
    await page.setViewportSize(size)
    await page.goto('/zh-Hans/pokemon', { waitUntil: 'domcontentloaded' })
    await hydrated(page)
    const generation = page.locator('#generation-1-trigger')
    if ((await generation.getAttribute('aria-expanded')) !== 'true') await generation.click()
    await expect.poll(() => page.locator('.pokemon-card').count()).toBeGreaterThanOrEqual(48)
    await choose(page, 'day-green')
    await page.keyboard.press('Escape')
    await page.evaluate(() => window.scrollTo({ top: 450, behavior: 'instant' }))
    await expect.poll(() => page.evaluate(() => window.scrollY)).toBe(450)
    await choose(page, 'day-red')
    await page.keyboard.press('Escape')
    expect(await page.evaluate(() => window.scrollY)).toBe(450)
    await panel(page)
    const bounds = (await page.locator('.appearance-panel').boundingBox())!
    expect(bounds.x).toBeGreaterThanOrEqual(0)
    expect(bounds.y).toBeGreaterThanOrEqual(0)
    expect(bounds.x + bounds.width).toBeLessThanOrEqual(size.width)
    expect(bounds.y + bounds.height).toBeLessThanOrEqual(size.height)
    await page.screenshot({ path: `../../../design/catalog-review/chooser-${size.width}.png` })
    await page.keyboard.press('Escape')
  }
})
