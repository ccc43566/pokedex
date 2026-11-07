import { expect, test } from '@playwright/test'
test.setTimeout(90_000)

test('paper control synchronizes generation and Pokémon paper in both modes', async ({ page }) => {
  await page.goto('/zh-Hans/pokemon', { waitUntil: 'domcontentloaded' })
  await page.locator('#generation-1-trigger').click()
  await expect(page.locator('.pokemon-grid[data-ready=true]')).toBeVisible()
  for (const mode of ['day', 'night']) {
    if (mode === 'night')
      await page.getByRole('button', { name: '切换到夜间模式', exact: true }).click()
    for (const value of ['0', '60', '100']) {
      await page.locator('.card-background-trigger').click()
      await page.getByLabel('纸面不透明度', { exact: true }).fill(value)
      await page.keyboard.press('Escape')
      await expect
        .poll(() => page.evaluate(() => getComputedStyle(document.querySelector('.generation-bar')!).backgroundColor === getComputedStyle(document.querySelector('.pokemon-card')!).backgroundColor))
        .toBe(true)
    }
  }
})

test('preparing first cards never reserves a blank block', async ({ page }) => {
  await page.goto('/zh-Hans/pokemon', { waitUntil: 'domcontentloaded' })
  await page.evaluate(() => {
    ;(window as unknown as { blankHeights: number[] }).blankHeights = []
    const sample = () => {
      const element = document.querySelector('.pokemon-batch-list--preparing')
      if (element)
        (window as unknown as { blankHeights: number[] }).blankHeights.push(
          element.getBoundingClientRect().height,
        )
      if (!document.querySelector('.pokemon-grid[data-ready=true]')) requestAnimationFrame(sample)
    }
    requestAnimationFrame(sample)
  })
  await page.locator('#generation-1-trigger').click()
  await expect(page.locator('.pokemon-grid[data-ready=true]')).toBeVisible()
  const heights = await page.evaluate(
    () => (window as unknown as { blankHeights: number[] }).blankHeights,
  )
  expect(heights.length).toBeGreaterThan(0)
  expect(heights.every((height) => height === 0)).toBe(true)
})

test('checkbox draws its tick and supports keyboard and reduced motion', async ({ page }) => {
  await page.goto('/zh-Hans/pokemon', { waitUntil: 'domcontentloaded' })
  const checkbox = page.getByRole('checkbox', { name: 'Mega', exact: true })
  await checkbox.check()
  await expect(checkbox).toBeChecked()
  const path = checkbox.locator('..').locator('path')
  await expect(path).toHaveCSS('stroke-dashoffset', '0px')
  await checkbox.focus()
  await page.keyboard.press('Space')
  await expect(checkbox).not.toBeChecked()
  await page.emulateMedia({ reducedMotion: 'reduce' })
  await expect(path).toHaveCSS('transition-duration', '0s')
})

test('filter actions share press behavior across all three catalogues', async ({ page }) => {
  for (const path of ['/pokemon', '/items?q=1', '/moves?q=1']) {
    await page.goto('/zh-Hans' + path, { waitUntil: 'domcontentloaded' })
    const button = page.getByRole('button', { name: '筛选', exact: true })
    await expect(button).toBeEnabled()
    await button.hover()
    await page.mouse.down()
    await page.waitForTimeout(110)
    expect(await button.evaluate((el) => getComputedStyle(el).transform)).not.toBe('none')
    await page.mouse.move(1, 1)
    await page.mouse.up()
    await expect(button).toHaveCSS('transform', 'none')
  }
})
