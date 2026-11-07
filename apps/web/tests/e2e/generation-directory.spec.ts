import { expect, test } from '@playwright/test'

test.setTimeout(120_000)

test('compact directory is fixed and appearance controls remain available', async ({ page }) => {
  await page.goto('/zh-Hans/pokemon', { waitUntil: 'domcontentloaded' })
  await expect(page.locator('.generation-style-picker')).toHaveCount(0)
  await expect(page.locator('.generation-bar').first()).toHaveCSS(
    'min-height',
    (page.viewportSize()?.width || 0) <= 700 ? '78px' : '76px',
  )
  for (const width of [320, 393, 947, 1440]) {
    await page.setViewportSize({ width, height: 900 })
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  }
  await expect(page.locator('.card-background-trigger')).toBeVisible()
  await page.getByRole('button', { name: '切换到夜间模式', exact: true }).click()
  await expect(page.locator('.site-shell')).toHaveAttribute('data-mode', 'night')
  await expect(page.locator('.card-background-trigger')).toBeVisible()
})

test('slow first load has no white skeleton and slides in once without replaying on pagination', async ({
  page,
}) => {
  await page.emulateMedia({ reducedMotion: 'no-preference' })
  let release!: () => void
  const held = new Promise<void>((resolve) => {
    release = resolve
  })
  await page.route('**/api/v1/pokemon?*', async (route) => {
    const url = new URL(route.request().url())
    if (url.searchParams.get('generation') === '1' && url.searchParams.get('page') === '1')
      await held
    await route.continue()
  })
  const entrances: string[] = []
  await page.exposeFunction('captureEntrance', (name: string) => entrances.push(name))
  await page.goto('/zh-Hans/pokemon', { waitUntil: 'domcontentloaded' })
  await page.evaluate(() =>
    document.addEventListener('animationstart', (event) => {
      const animation = event as AnimationEvent
      if (animation.animationName.startsWith('pokemon-entry'))
        void (
          window as unknown as { captureEntrance: (name: string) => Promise<void> }
        ).captureEntrance('pokemon-entry')
    }),
  )
  await page.locator('#generation-1-trigger').click()
  await expect(page.locator('#generation-1-trigger')).toHaveAttribute('aria-busy', 'true')
  await page.waitForTimeout(200)
  await expect(page.locator('.pokemon-grid')).toHaveCount(0)
  release()
  await expect(page.locator('.pokemon-grid[data-ready="true"]')).toBeVisible()
  await expect(page.locator('.pokemon-card')).toHaveCount(48)
  await expect.poll(() => entrances.length).toBe(1)
  await expect(page.locator('.pokemon-entry-group')).not.toHaveClass(/--enter/)
  await expect(page.locator('.pokemon-batch-list')).not.toContainText(/共\s*\d+\s*条结果|已显示/)
  await page.locator('.pokemon-batch-more').scrollIntoViewIfNeeded()
  await expect(page.locator('.pokemon-card')).toHaveCount(96)
  expect(entrances).toEqual(['pokemon-entry'])
})

test('reduced motion shows the generation without an entrance animation', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' })
  await page.goto('/zh-Hans/pokemon', { waitUntil: 'domcontentloaded' })
  await page.locator('#generation-1-trigger').click()
  await expect(page.locator('.pokemon-grid[data-ready="true"]')).toBeVisible()
  await expect(page.locator('.pokemon-entry-group')).toHaveCSS('animation-name', 'none')
  await expect(page.locator('.pokemon-card')).toHaveCount(48)
})

test('fresh directory has nine collapsed generations and no Pokémon list requests', async ({
  page,
}) => {
  const requests: string[] = []
  page.on('request', (request) => {
    if (/\/api\/v1\/pokemon\?/.test(request.url())) requests.push(request.url())
  })
  await page.goto('/zh-Hans/pokemon', { waitUntil: 'domcontentloaded' })
  await expect(page.locator('.generation-bar')).toHaveCount(9)
  await expect(page.locator('.generation-bar[aria-expanded="true"]')).toHaveCount(0)
  await expect(page.locator('.pokemon-card')).toHaveCount(0)
  await expect(page.locator('.generation-bar__starters img')).toHaveCount(27)
  await expect(page.getByRole('combobox', { name: '世代', exact: true })).toHaveCount(0)
  await expect(page.getByText('传说宝可梦', { exact: true })).toBeVisible()
  await expect(page.locator('.dex-filter-flags')).toHaveCSS('border-top-width', '0px')
  await page.waitForTimeout(500)
  expect(requests).toEqual([])
  expect(
    await page
      .locator('.generation-bar__starters img')
      .evaluateAll((images) =>
        images.every(
          (image) =>
            (image as HTMLImageElement).complete && (image as HTMLImageElement).naturalWidth > 0,
        ),
      ),
  ).toBe(true)
})

test('generation batches load only on demand, cache on reopen, and stay below the filter', async ({
  page,
}) => {
  await page.goto('/zh-Hans/pokemon', { waitUntil: 'domcontentloaded' })
  await page.locator('#generation-1-trigger').click()
  await expect(page.locator('.pokemon-card')).toHaveCount(48)
  await expect(page.locator('.generation-section--open')).toHaveCount(1)
  await page.evaluate(() => window.scrollTo({ top: 750, behavior: 'instant' }))
  await expect
    .poll(async () =>
      page.locator('.generation-section--open>.generation-bar').evaluate((element) => {
        const form = document.querySelector('.dex-filter-form')!.getBoundingClientRect()
        return Math.round(element.getBoundingClientRect().top - form.bottom)
      }),
    )
    .toBeGreaterThanOrEqual(7)
  await expect
    .poll(async () =>
      page.locator('.generation-section--open>.generation-bar').evaluate((element) => {
        const form = document.querySelector('.dex-filter-form')!.getBoundingClientRect()
        return Math.round(element.getBoundingClientRect().top - form.bottom)
      }),
    )
    .toBeLessThanOrEqual(9)
  await page.locator('.pokemon-batch-more').scrollIntoViewIfNeeded()
  await expect(page.locator('.pokemon-card')).toHaveCount(96)
  // Stop requesting more pages before taking the cache snapshot. A fast API
  // can satisfy another sentinel demand while Playwright reads the cards.
  await page.evaluate(() => window.scrollTo({ top: 0, behavior: 'instant' }))
  await expect(page.locator('.pokemon-batch-list')).toHaveAttribute('aria-busy', 'false')
  const ids = await page
    .locator('.pokemon-card')
    .evaluateAll((cards) => cards.map((card) => card.getAttribute('data-pokemon-id')))
  expect(new Set(ids).size).toBe(ids.length)
  await page.locator('#generation-1-trigger').click()
  await expect(page.locator('.pokemon-card')).toHaveCount(0)
  const requests: string[] = []
  page.on('request', (request) => {
    if (/\/api\/v1\/pokemon\?/.test(request.url())) requests.push(request.url())
  })
  await page.locator('#generation-1-trigger').click()
  await expect(page.locator('.pokemon-card')).toHaveCount(ids.length)
  expect(requests).toEqual([])
  await page.locator('#generation-9-trigger').click()
  await expect(page.locator('.generation-bar[aria-expanded="true"]')).toHaveCount(1)
  await expect(page.locator('.pokemon-card')).toHaveCount(48)
  await expect(page.locator('.pokemon-card').first()).toHaveAttribute('data-display-number', '906')
})

test('filters bypass generation groups and combine form tags on the server', async ({ page }) => {
  await page.goto('/zh-Hans/pokemon', { waitUntil: 'domcontentloaded' })
  await page.getByRole('checkbox', { name: 'Mega', exact: true }).check()
  await page.getByRole('button', { name: '筛选', exact: true }).click()
  await expect(page).toHaveURL(/isMega=true/)
  await expect(page.locator('.generation-bar')).toHaveCount(0)
  await expect(page.locator('.pokemon-card').first()).toBeVisible()
  await expect(page.locator('.pokemon-card__form-label').first()).toContainText('Mega')
  await page.getByRole('checkbox', { name: '超极巨化', exact: true }).check()
  await page.getByRole('button', { name: '筛选', exact: true }).click()
  await expect(page).toHaveURL(/isGigantamax=true/)
  await expect
    .poll(async () => page.locator('.pokemon-card__form-label').allTextContents())
    .toContainEqual('（Gigantamax）')
  await page.getByRole('combobox', { name: '属性', exact: true }).click()
  await page.getByRole('option', { name: '火', exact: true }).click()
  await page.getByRole('button', { name: '筛选', exact: true }).click()
  await expect(page).toHaveURL(/type=fire/)
  await expect.poll(async () => page.locator('.pokemon-card').count()).toBeGreaterThan(0)
  await expect
    .poll(async () =>
      page
        .locator('.pokemon-card')
        .evaluateAll((cards) =>
          cards.every((card) =>
            [...card.querySelectorAll('.type-bar__name')].some(
              (type) => type.textContent?.trim() === '火',
            ),
          ),
        ),
    )
    .toBe(true)
  await page.getByRole('button', { name: '清除', exact: true }).click()
  await expect(page.locator('.generation-bar')).toHaveCount(9)
  await expect(page.locator('.pokemon-card')).toHaveCount(0)
})

test('detail close and reload retain generation, loaded batches and reading position', async ({
  page,
}) => {
  await page.goto('/zh-Hans/pokemon', { waitUntil: 'domcontentloaded' })
  await page.locator('#generation-3-trigger').click()
  await expect(page.locator('.pokemon-card')).toHaveCount(48)
  await page.locator('.pokemon-batch-more').scrollIntoViewIfNeeded()
  await expect(page.locator('.pokemon-card')).toHaveCount(96)
  const target = page.locator('.pokemon-card').nth(70)
  await target.evaluate((element) => element.scrollIntoView({ block: 'center' }))
  await page.waitForTimeout(250)
  const before = await page.evaluate(() => scrollY)
  const id = await target.getAttribute('data-pokemon-id')
  await target.click()
  await expect(page.getByRole('dialog')).toBeVisible()
  await page.getByRole('button', { name: '关闭详情', exact: true }).click()
  await expect(page.getByRole('dialog')).toHaveCount(0)
  await expect
    .poll(async () => Math.abs((await page.evaluate(() => scrollY)) - before))
    .toBeLessThan(3)
  await expect(page.locator('#generation-3-trigger')).toHaveAttribute('aria-expanded', 'true')
  await page.reload({ waitUntil: 'domcontentloaded' })
  // A restored position near the boundary can also bring a further batch into range.
  await expect.poll(() => page.locator('.pokemon-card').count()).toBeGreaterThanOrEqual(96)
  await expect(page.locator(`.pokemon-card[data-pokemon-id="${id}"]`)).toBeVisible()
  await expect
    .poll(async () => Math.abs((await page.evaluate(() => scrollY)) - before))
    .toBeLessThan(3)
})

test('a delayed generation cannot replace a newer selection', async ({ page }) => {
  let release!: () => void
  const held = new Promise<void>((resolve) => {
    release = resolve
  })
  let markStarted!: () => void
  const started = new Promise<void>((resolve) => {
    markStarted = resolve
  })
  await page.route('**/api/v1/pokemon?*', async (route) => {
    if (new URL(route.request().url()).searchParams.get('generation') === '1') {
      markStarted()
      await held
    }
    await route.continue()
  })
  await page.goto('/zh-Hans/pokemon', { waitUntil: 'domcontentloaded' })
  await page.locator('#generation-1-trigger').click()
  await started
  await page.locator('#generation-9-trigger').click()
  await expect(page.locator('.pokemon-card').first()).toHaveAttribute('data-display-number', '906')
  release()
  await expect(page.locator('#generation-9-trigger')).toHaveAttribute('aria-expanded', 'true')
  await expect(page.locator('.pokemon-card')).toHaveCount(48)
  await expect(page.locator('.pokemon-card').first()).toHaveAttribute('data-display-number', '906')
})

test('a failed later batch keeps the displayed cards and can retry', async ({ page }) => {
  let fail = true
  await page.route('**/api/v1/pokemon?*', async (route) => {
    if (new URL(route.request().url()).searchParams.get('page') === '2' && fail) {
      await route.fulfill({ status: 400, body: 'temporary' })
    } else await route.continue()
  })
  await page.goto('/zh-Hans/pokemon', { waitUntil: 'domcontentloaded' })
  await page.locator('#generation-1-trigger').click()
  await expect(page.locator('.pokemon-card')).toHaveCount(48)
  await page.locator('.pokemon-batch-more').scrollIntoViewIfNeeded()
  await expect(page.getByRole('alert')).toBeVisible()
  await expect(page.locator('.pokemon-card')).toHaveCount(48)
  fail = false
  await page.getByRole('button', { name: '请重试', exact: true }).click()
  await expect(page.getByRole('alert')).toHaveCount(0)
  await expect(page.locator('.pokemon-card')).toHaveCount(96)
})

test('prepares one next page before scrolling and mounts it in small groups without moving existing cards', async ({
  page,
}) => {
  const requested: number[] = []
  page.on('request', (request) => {
    const url = new URL(request.url())
    if (url.pathname === '/api/v1/pokemon') requested.push(Number(url.searchParams.get('page')))
  })
  await page.goto('/zh-Hans/pokemon', { waitUntil: 'domcontentloaded' })
  await page.locator('#generation-1-trigger').click()
  await expect(page.locator('.pokemon-card')).toHaveCount(48)
  await expect.poll(() => requested.includes(2)).toBe(true)
  // Speculation is bounded: no DOM growth or third-page request without demand.
  await page.waitForTimeout(400)
  await expect(page.locator('.pokemon-card')).toHaveCount(48)
  expect(requested.includes(3)).toBe(false)
  const geometry = () =>
    page
      .locator('.pokemon-card')
      .first()
      .evaluate((element) => {
        const rect = element.getBoundingClientRect()
        // Mobile filters shrink on scroll. Compare within the generation so
        // that expected sticky-toolbar movement is not counted as append shift.
        const section = element.closest('.generation-section')!.getBoundingClientRect()
        return [rect.width, rect.height, rect.top - section.top]
      })
  const before = await geometry()
  const commits: number[] = [48]
  await page.exposeFunction('capturePokemonCount', (count: number) => commits.push(count))
  await page.locator('.pokemon-grid').evaluate((element) => {
    const observer = new MutationObserver(() => {
      const count = element.querySelectorAll('.pokemon-card').length
      void (
        window as unknown as { capturePokemonCount: (count: number) => Promise<void> }
      ).capturePokemonCount(count)
      if (count >= 96) observer.disconnect()
    })
    observer.observe(element, { childList: true })
  })
  await page.locator('.pokemon-batch-more').scrollIntoViewIfNeeded()
  await expect(page.locator('.pokemon-card')).toHaveCount(96)
  await expect.poll(() => commits.at(-1)).toBe(96)
  expect(commits.length).toBeGreaterThan(3)
  expect(commits.every((count, index) => !index || count - commits[index - 1]! <= 8)).toBe(true)
  expect(await geometry()).toEqual(before)
})

test('night browsing keeps five-column rows aligned across partial batches and return to top', async ({
  page,
}) => {
  await page.setViewportSize({ width: 900, height: 900 })
  await page.goto('/zh-Hans/pokemon', { waitUntil: 'domcontentloaded' })
  await page.locator('#generation-1-trigger').click()
  await expect(page.locator('.pokemon-card')).toHaveCount(48)
  await expect(page.locator('.pokemon-batch-list')).toHaveAttribute('aria-busy', 'false')
  await page.getByRole('button', { name: '切换到夜间模式', exact: true }).click()
  const initialHeight = await page
    .locator('.pokemon-card')
    .first()
    .evaluate((element) => element.getBoundingClientRect().height)
  for (let batch = 0; batch < 4; batch++) {
    const before = await page.locator('.pokemon-card').count()
    await page.locator('.pokemon-batch-more').scrollIntoViewIfNeeded()
    await expect.poll(() => page.locator('.pokemon-card').count()).toBeGreaterThan(before)
    await expect(page.locator('.pokemon-batch-list')).toHaveAttribute('aria-busy', 'false')
  }
  await expect(page.locator('.pokemon-card')).toHaveCount(236)
  const aligned = await page.locator('.pokemon-grid').evaluate((grid) => {
    const columns = getComputedStyle(grid).gridTemplateColumns.split(' ').length
    const cards = [...grid.querySelectorAll('.pokemon-card')]
    const rows = new Map<number, number[]>()
    for (const card of cards) {
      const rect = card.getBoundingClientRect()
      const top = Math.round(rect.top)
      rows.set(top, [...(rows.get(top) || []), rect.height])
    }
    return {
      columns,
      equal: [...rows.values()].every(
        (heights) => Math.max(...heights) - Math.min(...heights) < 0.1,
      ),
    }
  })
  expect(aligned).toEqual({ columns: 5, equal: true })
  await page.evaluate(() => scrollTo(0, 0))
  await expect(page.locator('.pokemon-card').first()).toHaveCSS('content-visibility', 'visible')
  expect(
    await page
      .locator('.pokemon-card')
      .first()
      .evaluate((element) => element.getBoundingClientRect().height),
  ).toBeCloseTo(initialHeight, 2)
})
