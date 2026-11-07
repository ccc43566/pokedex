import { expect, test } from '@playwright/test'

test('serves the themed homepage with neutral navigation, real media and full-width footer', async ({
  page,
  isMobile,
}) => {
  const errors: string[] = [],
    sources: string[] = []
  page.on('pageerror', (error) => errors.push(error.message))
  page.on('console', (message) => {
    if (/hydration/i.test(message.text())) errors.push(message.text())
  })
  page.on('request', (request) => {
    if (/\.gif(?:\?|$)/.test(request.url())) sources.push(request.url())
  })
  await page.goto('/zh-Hans')
  await expect(page.locator('.visitor')).toHaveCount(28)
  await expect(page.locator('header')).toHaveCount(1)
  await expect(page.locator('footer')).toHaveCount(1)
  await expect(
    page.locator('.nav-links a[aria-current],.nav-links .active,.preview-tools'),
  ).toHaveCount(0)
  expect(
    await page
      .locator('.nav-links a')
      .evaluateAll((links) => links.map((link) => link.getAttribute('href'))),
  ).toEqual(['/zh-Hans/pokemon', '/zh-Hans/moves', '/zh-Hans/items', '/zh-Hans/types'])
  await expect(page.locator('.scene')).toBeVisible()
  await expect
    .poll(() => page.locator('.night-home').getAttribute('data-motion-engine'))
    .toMatch(/native|compatible/)
  const ids = await page
    .locator('.visitor')
    .evaluateAll((links) => links.map((link) => link.getAttribute('data-id')))
  expect(new Set(ids).size).toBe(28)
  for (const width of isMobile ? [320, 390] : [768, 1366, 1920, 3440]) {
    await page.setViewportSize({ width, height: isMobile ? 844 : 1000 })
    await page.locator('.page-footer').scrollIntoViewIfNeeded()
    await expect
      .poll(() => page.evaluate(() => document.documentElement.scrollWidth <= innerWidth))
      .toBe(true)
    const edges = await page
      .locator('.page-footer')
      .evaluate((element) => ({
        left: element.getBoundingClientRect().left,
        right: element.getBoundingClientRect().right,
        width: document.documentElement.clientWidth,
      }))
    expect(edges.left).toBe(0)
    expect(edges.right).toBe(edges.width)
  }
  if (isMobile) expect(sources).toHaveLength(0)
  expect(errors).toEqual([])
})

test('homepage visitor drawer preserves the route, browser history, scroll and original links', async ({
  page,
}) => {
  test.setTimeout(60000)
  await page.goto('/zh-Hans')
  const visitor = page.locator('.visitor[data-id="708"]')
  await visitor.scrollIntoViewIfNeeded()
  const before = await page.evaluate(() => scrollY)
  await visitor.click()
  await expect(page).toHaveURL(/\/zh-Hans\?detail=708$/)
  await expect(page.getByRole('dialog')).toContainText('小木灵', { timeout: 30000 })
  await page.reload()
  await expect(page.getByRole('dialog')).toContainText('小木灵', { timeout: 30000 })
  await page.getByRole('button', { name: '关闭详情', exact: true }).click()
  await expect(page.getByRole('dialog')).toHaveCount(0)
  await expect(page.locator('.night-home')).toBeVisible()
  await visitor.scrollIntoViewIfNeeded()
  await visitor.click()
  await expect(page.getByRole('dialog')).toBeVisible()
  await page.goBack()
  await expect(page.getByRole('dialog')).toHaveCount(0)
  expect(Math.abs((await page.evaluate(() => scrollY)) - before)).toBeLessThan(80)
  await page.goForward()
  await expect(page.getByRole('dialog')).toBeVisible()
})

test('search uses the complete Pokédex and SPA return does not leak homepage styling', async ({
  page,
}) => {
  test.setTimeout(90000)
  await page.goto('/zh-Hans')
  await page.locator('#home-search').fill('25')
  await page.getByRole('button', { name: '搜索', exact: true }).click()
  await expect(page).toHaveURL(/\/zh-Hans\/pokemon\?q=25$/)
  await expect(page.locator('.pokemon-card[data-pokemon-id="25"]')).toBeVisible({ timeout: 60000 })
  await expect(page.locator('.night-home')).toHaveCount(0)
  await expect(page.locator('header')).toHaveCount(1)
  const appearance = await page
    .locator('header')
    .evaluate((element) => ({
      background: getComputedStyle(element).backgroundColor,
      color: getComputedStyle(element).color,
    }))
  expect(appearance.background).not.toBe('rgb(23, 26, 51)')
  await page.locator('header a').first().click()
  await expect(page).toHaveURL(/\/zh-Hans$/)
  await expect(page.locator('.visitor')).toHaveCount(28)
  await page.locator('.nav-links a[href="/zh-Hans/types"]').click()
  await expect(page).toHaveURL(/\/zh-Hans\/types$/)
  await expect(page.locator('.night-home')).toHaveCount(0)
  await page.goBack()
  await expect(page.locator('.visitor')).toHaveCount(28)
})

test('lantern controls, locale switch and animation preferences work without preview controls', async ({
  page,
  isMobile,
}) => {
  await page.goto('/zh-Hans')
  await page.locator('.jack').first().scrollIntoViewIfNeeded()
  const footerTop = await page
    .locator('.page-footer')
    .evaluate((element) => element.getBoundingClientRect().top + scrollY)
  await page.locator('.jack').first().focus()
  await page.keyboard.press('Enter')
  await expect(page.locator('.lantern-guest')).toContainText('南瓜怪人')
  await expect(page.locator('.lantern-guest')).toHaveAttribute('href', '/zh-Hans?detail=711')
  await page.locator('.reset-lamps').click()
  await expect(page.locator('.lantern-guest')).toHaveCount(0)
  expect(
    await page
      .locator('.page-footer')
      .evaluate((element) => element.getBoundingClientRect().top + scrollY),
  ).toBe(footerTop)
  await page.locator('#home-ambient').uncheck()
  await expect(page.locator('.visitor-image[data-playing="true"]')).toHaveCount(0)
  await page.locator('#home-ambient').check()
  await page.emulateMedia({ reducedMotion: 'reduce' })
  await expect(page.locator('.visitor-image[data-playing="true"]')).toHaveCount(0)
  await expect(page.locator('.story')).toHaveCount(0)
  await page.locator('.home-language select').selectOption('en')
  await expect(page).toHaveURL(/\/en$/)
  await expect(page.locator('.visitor[data-id="711"]')).toContainText('Gourgeist')
  await expect(page.locator('.nav-links a').first()).toHaveAttribute('href', '/en/pokemon')
  await expect(page.locator('.nav-links a[aria-current]')).toHaveCount(0)
  if (isMobile) await expect(page.locator('.visitor-image[data-playing="true"]')).toHaveCount(0)
})

test('finite enlarged stories run automatically and fallback cleans up after navigation', async ({
  page,
}) => {
  await page.addInitScript(() => {
    Object.defineProperty(window, 'ScrollTimeline', { value: undefined, configurable: true })
  })
  await page.clock.install()
  await page.goto('/zh-Hans')
  await expect(page.locator('.night-home')).toHaveAttribute('data-motion-engine', 'compatible')
  await page.clock.runFor(8200)
  await expect(page.locator('.story-flight')).toHaveCount(1)
  const width = await page
    .locator('.story-flight')
    .evaluate((element) => element.getBoundingClientRect().width)
  expect([72, 96]).toContain(width)
  await page.locator('#home-search').focus()
  await expect(page.locator('.story')).toHaveCount(0)
  await page.locator('#home-ambient').uncheck()
  await page.clock.runFor(60000)
  await expect(page.locator('.story')).toHaveCount(0)
  await page.locator('.nav-links a[href="/zh-Hans/types"]').click()
  await expect(page.locator('.night-home')).toHaveCount(0)
  await page.clock.runFor(60000)
  await expect(page.locator('.story')).toHaveCount(0)
})
