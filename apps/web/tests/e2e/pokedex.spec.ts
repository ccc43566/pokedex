import { expect, test } from '@playwright/test'

test('shows every result without pagination or duplicate cards', async ({ page }) => {
  test.setTimeout(60000)
  await page.goto('/zh-Hans/pokemon')
  const result = page.getByText(/共 \d+ 条结果/)
  await expect(result).toBeVisible({ timeout: 60000 })
  const total = Number((await result.textContent())?.match(/\d+/)?.[0])
  expect(total).toBeGreaterThan(100)
  const cards = page.locator('.pokemon-card')
  await expect(cards).toHaveCount(total, { timeout: 60000 })
  const ids = await cards.evaluateAll((elements) =>
    elements.map((element) => element.getAttribute('data-pokemon-id')),
  )
  expect(new Set(ids).size).toBe(total)
  await expect(page.getByRole('button', { name: '下一页' })).toHaveCount(0)
})

test('keeps draft filters unapplied and marks the selected card when the drawer opens', async ({
  page,
}) => {
  test.setTimeout(60000)
  await page.goto('/zh-Hans/pokemon')
  await expect(page.locator('.pokemon-card').first()).toBeVisible({ timeout: 60000 })
  const search = page.getByPlaceholder('名称或编号')
  await search.fill('皮卡丘')
  await expect(page).not.toHaveURL(/q=/)
  expect(await page.locator('.pokemon-card').count()).toBeGreaterThanOrEqual(100)
  await page.getByRole('button', { name: '筛选' }).click()
  await expect(page).toHaveURL(/q=/, { timeout: 20000 })
  const pikachu = page.getByRole('link', { name: /#0025 皮卡丘/ })
  await expect(pikachu).toBeVisible()
  await pikachu.click()
  await expect(pikachu).toHaveAttribute('aria-current', 'true')
  await expect(page.getByRole('dialog')).toContainText('皮卡丘')
  await page.getByRole('button', { name: '关闭详情' }).click()
  await expect(pikachu).not.toHaveAttribute('aria-current', 'true')
  await expect(page).toHaveURL(/q=/)
})

test('keeps search controls below the main menu while scrolling', async ({ page, isMobile }) => {
  await page.goto('/zh-Hans/pokemon')
  await expect(page.locator('.pokemon-card').first()).toBeVisible({ timeout: 60000 })
  await page.evaluate(() => window.scrollTo(0, 1600))
  const form = page.locator('.dex-filter-form')
  await expect(form).toHaveClass(/dex-filter-form--stuck/)
  const header = page.locator('header')
  const headerBox = await header.boundingBox()
  const formBox = await form.boundingBox()
  expect(formBox!.y).toBeGreaterThanOrEqual(headerBox!.y + headerBox!.height - 3)
  expect(formBox!.y).toBeLessThan(headerBox!.y + headerBox!.height + 8)
  await expect(page.getByPlaceholder('名称或编号')).toBeVisible()
  if (isMobile) {
    await page.getByRole('button', { name: '更多' }).click()
    await expect(page.getByRole('checkbox', { name: '传说的宝可梦' })).toBeVisible()
  }
})

test('normalizes an old page URL after returning from a direct detail page', async ({ page }) => {
  test.setTimeout(60000)
  await page.goto('/zh-Hans/pokemon/25?from=%2Fzh-Hans%2Fpokemon%3Fpage%3D2')
  await expect(page.getByRole('heading', { level: 1 })).toContainText('皮卡丘')
  await page.getByRole('link', { name: '返回图鉴' }).click()
  await expect(page).toHaveURL(/\/zh-Hans\/pokemon$/)
  await expect(page.locator('.pokemon-card').first()).toBeVisible({ timeout: 60000 })
  await expect(page.getByText('已显示全部')).toBeVisible({ timeout: 60000 })
  expect(await page.locator('.pokemon-card').count()).toBeGreaterThan(100)
})
