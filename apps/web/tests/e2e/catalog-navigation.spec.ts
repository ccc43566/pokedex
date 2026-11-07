import { expect, test, type Page } from '@playwright/test'
test.setTimeout(120_000)

test('first visit to Pokemon starts at the top after leaving a scrolled catalogue', async ({
  page,
}) => {
  await page.goto('/zh-Hans/items', { waitUntil: 'domcontentloaded' })
  await expect(page.locator('.reference-card').first()).toBeVisible()
  await page.evaluate(() => scrollTo(0, 1000))
  await page.locator('.catalog-nav').getByRole('link', { name: '宝可梦', exact: true }).click()
  await expect(page).toHaveURL(/\/zh-Hans\/pokemon$/)
  await expect(page.locator('.generation-bar')).toHaveCount(9)
  await expect.poll(() => page.evaluate(() => scrollY)).toBe(0)
})
async function aligned(page: Page, path: string) {
  await expect(page.locator(`.catalog-nav [data-nav-path="${path}"]`)).toHaveAttribute(
    'aria-current',
    'page',
  )
  await expect
    .poll(() =>
      page.locator('.catalog-nav__slider').evaluate((element) => {
        const r = element.getBoundingClientRect(),
          target = document
            .querySelector('.catalog-nav [aria-current=page]')!
            .getBoundingClientRect()
        return Math.max(
          Math.abs(r.x - target.x),
          Math.abs(r.y - target.y),
          Math.abs(r.width - target.width),
          Math.abs(r.height - target.height),
        )
      }),
    )
    .toBeLessThan(0.75)
}

test('shared slider follows routes, preserves the header and leaves no running layers', async ({
  page,
}) => {
  await page.goto('/zh-Hans/pokemon', { waitUntil: 'domcontentloaded' })
  await expect(page.locator('.catalog-nav--enhanced')).toBeVisible()
  await page.locator('header').evaluate((element) => element.setAttribute('data-persistent', 'yes'))
  for (const [path, label] of [
    ['/types', '属性'],
    ['/items', '道具'],
    ['/moves', '招式'],
    ['/pokemon', '宝可梦'],
  ]) {
    await page.locator('.catalog-nav').getByRole('link', { name: label!, exact: true }).click()
    await expect(page).toHaveURL(new RegExp(`/zh-Hans${path}$`))
    await aligned(page, path!)
    await expect(page.locator('header')).toHaveAttribute('data-persistent', 'yes')
  }
  await expect
    .poll(() =>
      page.evaluate(
        () =>
          document
            .getAnimations()
            .filter(
              (a) =>
                a.effect instanceof KeyframeEffect &&
                ((a.effect.target as Element)?.closest('.catalog-nav') ||
                  (a.effect.target as Element)?.closest('main')),
            ).length,
      ),
    )
    .toBe(0)
})

test('rapid clicks and delayed data settle on the latest route without hiding the old page early', async ({
  page,
}) => {
  await page.goto('/zh-Hans/pokemon', { waitUntil: 'domcontentloaded' })
  await expect(page.locator('.catalog-nav--enhanced')).toBeVisible()
  let release!: () => void, started!: () => void
  const held = new Promise<void>((resolve) => {
      release = resolve
    }),
    began = new Promise<void>((resolve) => {
      started = resolve
    })
  await page.route('**/api/v1/types?*', async (route) => {
    started()
    await held
    await route.continue()
  })
  const click = page
    .locator('.catalog-nav')
    .getByRole('link', { name: '属性', exact: true })
    .click()
  try {
    await Promise.race([
      began,
      new Promise((_, reject) =>
        setTimeout(() => reject(new Error('No delayed Types request')), 5000),
      ),
    ])
    await expect(page.locator('.pokemon-catalog')).toBeVisible()
    await page.locator('.catalog-nav').getByRole('link', { name: '招式', exact: true }).click()
  } finally {
    release()
  }
  await click
  await expect(page).toHaveURL(/\/zh-Hans\/moves$/)
  await expect(page.locator('.reference-browse h1')).toHaveText('招式')
  await aligned(page, '/moves')
  await page.goBack()
  // The Types URL was already committed while its async page was still
  // pending; normal browser history retains that entry.
  await expect(page).toHaveURL(/\/zh-Hans\/types$/)
  await aligned(page, '/types')
  await page.goBack()
  await expect(page).toHaveURL(/\/zh-Hans\/pokemon$/)
  await aligned(page, '/pokemon')
})

test('responsive English navigation and night reduced motion align immediately', async ({
  page,
}) => {
  await page.emulateMedia({ reducedMotion: 'reduce' })
  await page.goto('/en/pokemon', { waitUntil: 'domcontentloaded' })
  for (const width of [320, 393, 947, 1440]) {
    await page.setViewportSize({ width, height: 900 })
    await aligned(page, '/pokemon')
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  }
  await page.getByRole('button', { name: 'Switch to night mode', exact: true }).click()
  await expect(page.locator('.catalog-nav__slider')).toHaveCSS(
    'background-color',
    'rgb(48, 75, 75)',
  )
  const link = page.locator('.catalog-nav').getByRole('link', { name: 'Types', exact: true })
  await link.focus()
  await page.keyboard.press('Enter')
  await expect(page).toHaveURL(/\/en\/types$/)
  await aligned(page, '/types')
  expect(
    await page
      .locator('.catalog-nav__slider')
      .evaluate((element) => element.getAnimations().length),
  ).toBe(0)
})

test('returning to an expanded generation restores batches and position; drawers do not replay navigation', async ({
  page,
}) => {
  await page.goto('/zh-Hans/pokemon', { waitUntil: 'domcontentloaded' })
  await page.locator('#generation-1-trigger').click()
  await expect(page.locator('.pokemon-grid[data-ready=true]')).toBeVisible()
  await page.locator('.pokemon-batch-more').scrollIntoViewIfNeeded()
  await expect(page.locator('.pokemon-card')).toHaveCount(96)
  const card = page.locator('.pokemon-card').nth(65)
  await card.evaluate((element) => element.scrollIntoView({ block: 'center' }))
  await page.waitForTimeout(200)
  const before = await page.evaluate(() => scrollY)
  await page.locator('.catalog-nav').getByRole('link', { name: '属性', exact: true }).click()
  await expect(page).toHaveURL(/\/types$/)
  await page.goBack()
  await expect(page.locator('#generation-1-trigger')).toHaveAttribute('aria-expanded', 'true')
  await expect.poll(() => page.evaluate(() => scrollY)).toBeCloseTo(before, 0)
  await card.click()
  await expect(page.getByRole('dialog')).toBeVisible()
  await aligned(page, '/pokemon')
  await page.getByRole('button', { name: '关闭详情', exact: true }).click()
  await expect(page.getByRole('dialog')).toHaveCount(0)
  await expect.poll(() => page.evaluate(() => scrollY)).toBeCloseTo(before, 0)
})
