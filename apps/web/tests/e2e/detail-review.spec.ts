import { expect, test } from '@playwright/test'

test.setTimeout(90_000)

test('opening and closing a visible generation preserves the filter gap and scroll position', async ({
  page,
}) => {
  await page.setViewportSize({ width: 947, height: 871 })
  await page.goto('/zh-Hans/pokemon', { waitUntil: 'domcontentloaded' })
  const position = () =>
    page
      .locator('.dex-filter-form')
      .evaluate((element) => ({ top: element.getBoundingClientRect().top, scroll: scrollY }))
  for (const top of [0, 16]) {
    await page.evaluate((top) => scrollTo(0, top), top)
    const before = await position()
    await page.locator('#generation-1-trigger').click()
    await expect(page.locator('.pokemon-grid[data-ready="true"]')).toBeVisible()
    expect(await position()).toEqual(before)
    await page.locator('#generation-1-trigger').click()
    await expect(page.locator('.pokemon-card')).toHaveCount(0)
    expect(await position()).toEqual(before)
  }
})

test('drawer and full detail omit removed copy while retaining facts and readable night statistics', async ({
  page,
}) => {
  await page.goto('/zh-Hans/pokemon/2', { waitUntil: 'domcontentloaded' })
  await page.getByRole('button', { name: '切换到夜间模式', exact: true }).click()
  for (const path of ['/zh-Hans/pokemon/2', '/zh-Hans/pokemon?q=2&detail=2']) {
    await page.goto(path, { waitUntil: 'domcontentloaded' })
    const detail = page.locator('.detail-sheet')
    await expect(detail.locator('.stat-bars__value')).toHaveCount(6)
    await expect(detail.locator('.detail-form-picker p')).toHaveCount(0)
    await expect(detail).not.toContainText('基础经验')
    await expect(detail).not.toContainText('蛋组与雌雄比例为物种资料')
    await expect(detail.locator('[data-evolution-version-note]')).toHaveCount(0)
    await expect(detail.locator('.detail-sheet__metrics>div')).toHaveCount(4)
    await expect(detail.locator('[data-egg-groups]')).not.toBeEmpty()
    await expect(detail.locator('[data-stat-total]')).toHaveText('405')
    expect(
      await detail
        .locator('.stat-bars__value')
        .evaluateAll((elements) =>
          elements.every((element) => getComputedStyle(element).color === 'rgb(255, 255, 255)'),
        ),
    ).toBe(true)
    await expect(detail.locator('[data-stat-total]')).toHaveCSS('color', 'rgb(255, 255, 255)')
  }
  await page.goto('/zh-Hans/pokemon/2', { waitUntil: 'domcontentloaded' })
  await page.getByRole('button', { name: '切换到日间模式', exact: true }).click()
  await expect(page.locator('.stat-bars__value').first()).toHaveCSS('color', 'rgb(117, 117, 117)')
})
