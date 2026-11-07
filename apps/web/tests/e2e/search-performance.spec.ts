import { expect, test, type Page } from '@playwright/test'

test.setTimeout(120_000)

test.beforeEach(async ({ page }) => {
  // Optional isolated API, without changing the user's running dev proxy.
  const backend = process.env.SEARCH_TEST_API
  if (backend) await page.route('**/api/v1/**', async (route) => {
    const url = new URL(route.request().url())
    const response = await route.fetch({ url: `${backend}${url.pathname}${url.search}` })
    await route.fulfill({ response })
  })
  const media = process.env.SEARCH_TEST_MEDIA
  if (media) await page.route('**/media/**', async (route) => {
    const url = new URL(route.request().url())
    const response = await route.fetch({ url: `${media}${url.pathname}` })
    // A card can disappear while its image is being proxied after a refresh.
    await route.fulfill({ response }).catch(() => {})
  })
})

test.afterEach(async ({ page }) => {
  // Finish proxy responses before Playwright disposes the API request context.
  await page.unrouteAll({ behavior: 'wait' })
})

async function search(page: Page, q: string) {
  await page.locator('.dex-filter-search input').fill(q)
  await page.locator('.dex-filter-form button[type="submit"]').click()
}

test('search reports progress, cancels obsolete work and shows text without artwork', async ({ page }) => {
  let release!: () => void
  const held = new Promise<void>((resolve) => { release = resolve })
  let started!: () => void
  const oldStarted = new Promise<void>((resolve) => { started = resolve })
  const aborted: string[] = []
  page.on('requestfailed', (request) => aborted.push(request.url()))
  await page.route('**/api/v1/pokemon?*', async (route) => {
    if (new URL(route.request().url()).searchParams.get('q') !== 'obsolete') return route.fallback()
    started()
    await held
    await route.fulfill({ json: {
      items: [], total: 0, page: 1, pageSize: 48, totalPages: 1,
      hasNext: false, hasPrevious: false, dataVersion: 'obsolete',
    } }).catch(() => {})
  })
  await page.route('**/media/**', (route) => route.abort())
  await page.goto('/zh-Hans/pokemon')
  await expect(page.locator('.dex-filter-search input')).toBeEnabled()
  await search(page, 'obsolete')
  await oldStarted
  await expect(page.getByRole('status').filter({ hasText: '正在搜索宝可梦' })).toBeVisible()
  await search(page, '25')
  await expect(page.locator('.pokemon-card[data-pokemon-id="25"]')).toBeVisible()
  await expect(page.locator('.pokemon-card[data-pokemon-id="25"]')).toContainText('皮卡丘')
  release()
  await expect.poll(() => aborted.some((url) => url.includes('q=obsolete'))).toBe(true)
  await expect(page.locator('.pokemon-card[data-pokemon-id="25"]')).toBeVisible()
  const images = page.locator('.pokemon-card__image')
  await expect(images.first()).toHaveAttribute('loading', 'eager')
  await expect(images.first()).toHaveAttribute('fetchpriority', 'high')
  if (await images.count() > 12) await expect(images.nth(12)).toHaveAttribute('loading', 'lazy')
})

test('failed searches expose a retry for the same query', async ({ page }) => {
  let fail = true
  await page.route('**/api/v1/pokemon?*', (route) => {
    if (new URL(route.request().url()).searchParams.get('q') === 'Pikachu' && fail)
      return route.fulfill({ status: 503, json: { detail: 'temporarily unavailable' } })
    return route.fallback()
  })
  await page.goto('/zh-Hans/pokemon')
  await expect(page.locator('.dex-filter-search input')).toBeEnabled()
  await search(page, 'Pikachu')
  await expect(page.locator('.pokemon-batch-list > div[role="alert"]')).toBeVisible()
  await expect(page.locator('.pokemon-card')).toHaveCount(0)
  fail = false
  await page.getByRole('button', { name: /重试/ }).click()
  await expect(page.locator('.pokemon-card[data-pokemon-id="25"]')).toBeVisible()
  await expect(page.getByRole('alert')).toHaveCount(0)
})

test('same-query refresh validates versions and retries revision failures', async ({ page }) => {
  let failRevision = false
  let updated = false
  await page.route('**/api/v1/pokemon/revision', (route) => {
    if (failRevision) return route.fulfill({ status: 503, json: {} })
    if (updated) return route.fulfill({ json: { version: 'updated-test-data' } })
    return route.fallback()
  })
  await page.route('**/api/v1/pokemon?*', async (route) => {
    if (!updated) return route.fallback()
    const url = new URL(route.request().url())
    const response = await route.fetch(process.env.SEARCH_TEST_API
      ? { url: `${process.env.SEARCH_TEST_API}${url.pathname}${url.search}` }
      : {})
    const data = await response.json()
    data.dataVersion = 'updated-test-data'
    for (const item of data.items) item.localizedName = '更新后的皮卡丘'
    await route.fulfill({ json: data })
  })
  await page.goto('/zh-Hans/pokemon')
  await expect(page.locator('.dex-filter-search input')).toBeEnabled()
  await search(page, 'Pikachu')
  await expect(page.locator('.pokemon-card[data-pokemon-id="25"]')).toBeVisible()
  await expect(page.locator('.pokemon-batch-list')).toHaveAttribute('aria-busy', 'false')
  failRevision = true
  await search(page, 'Pikachu')
  await expect(page.locator('.pokemon-batch-list > div[role="alert"]')).toBeVisible()
  failRevision = false
  updated = true
  await page.getByRole('button', { name: /重试/ }).click()
  await expect(page.locator('.pokemon-card[data-pokemon-id="25"]')).toContainText('更新后的皮卡丘')
})

test('records submit-to-card and first-screen image timings', async ({ page }, info) => {
  const api: { durationMs: number; url: string }[] = []
  page.on('requestfinished', (request) => {
    if (new URL(request.url()).pathname.endsWith('/v1/pokemon'))
      api.push({ durationMs: request.timing().responseEnd, url: request.url() })
  })
  await page.goto('/zh-Hans/pokemon')
  await expect(page.locator('.dex-filter-search input')).toBeEnabled()
  await page.evaluate(() => {
    const state = window as unknown as {
      searchTiming: { start: number; firstCardMs?: number; imagesMs?: number }
    }
    state.searchTiming = { start: 0 }
    document.querySelector('form')!.addEventListener('submit', () => {
      state.searchTiming.start = performance.now()
      const observer = new MutationObserver(() => {
        if (!document.querySelector('.pokemon-card')) return
        observer.disconnect()
        requestAnimationFrame(() => {
          state.searchTiming.firstCardMs = performance.now() - state.searchTiming.start
        })
      })
      observer.observe(document.body, { childList: true, subtree: true })
    }, { once: true })
  })
  await search(page, 'Pikachu')
  await expect(page.locator('.pokemon-card[data-pokemon-id="25"]')).toBeVisible()
  await expect(page.locator('.pokemon-batch-list')).toHaveAttribute('aria-busy', 'false')
  const timing = await page.evaluate(async () => {
    const state = window as unknown as {
      searchTiming: { start: number; firstCardMs?: number; imagesMs?: number }
    }
    const images = [...document.querySelectorAll<HTMLImageElement>('.pokemon-card__image')]
      .filter((image) => image.getBoundingClientRect().top < innerHeight)
    const decoded = await Promise.all(images.map((image) => image.decode().then(() => true, () => false)))
    state.searchTiming.imagesMs = performance.now() - state.searchTiming.start
    return { ...state.searchTiming, visibleImages: images.length, decodedImages: decoded.filter(Boolean).length }
  })
  expect(timing.visibleImages).toBeGreaterThan(0)
  expect(timing.decodedImages).toBe(timing.visibleImages)
  await info.attach('search-timing', { body: JSON.stringify({ ...timing, api }, null, 2), contentType: 'application/json' })
  console.log(JSON.stringify({ project: info.project.name, searchTiming: { ...timing, api } }))
  await page.screenshot({ path: info.outputPath('search.png') })
})
