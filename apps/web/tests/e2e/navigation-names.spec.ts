import { expect, test, type Page } from '@playwright/test'

async function openScrolledMeowth(page: Page) {
  await page.goto('/zh-Hans/pokemon?type=normal&sort=id')
  await expect(page.getByText('已显示全部')).toBeVisible({ timeout: 60000 })
  const card = page.locator('[data-pokemon-id="52"]')
  await card.evaluate((node) => node.scrollIntoView({ block: 'center' }))
  await expect(page.locator('.dex-filter-form')).toHaveClass(/--stuck/)
  const top = await page.evaluate(() => window.scrollY)
  const count = await page.locator('.pokemon-card').count()
  await card.click()
  await expect(page.locator('#drawer-form-choice')).toHaveValue('pokemon:52')
  return { top, count }
}

test('distant and filtered-out evolution targets stay in the drawer and restore list position', async ({
  page,
}) => {
  test.setTimeout(90000)
  const { top, count } = await openScrolledMeowth(page)
  await page.locator('[data-form-key="pokemon:10161"]').click()
  await expect(page.locator('.detail-sheet__name')).toHaveText('喵喵（Galarian）')
  await expect(page.locator('[data-pokemon-id="10161"]')).toHaveCount(0)
  await page.locator('[data-evolution-node="pokemon:863"]').click()
  await expect(page).toHaveURL(/\/pokemon\?type=normal&sort=id&detail=863/)
  await expect(page.getByRole('dialog')).toContainText('喵头目')
  await expect(page.locator('[data-pokemon-id="863"]')).toHaveCount(0)
  await expect(page.locator('.pokemon-card')).toHaveCount(count)
  await page.goBack()
  await expect(page.locator('#drawer-form-choice')).toHaveValue('pokemon:10161')
  await page.goBack()
  await expect(page.locator('#drawer-form-choice')).toHaveValue('pokemon:52')
  await page.goForward()
  await expect(page.locator('#drawer-form-choice')).toHaveValue('pokemon:10161')
  await page.reload()
  await expect(page.locator('#drawer-form-choice')).toHaveValue('pokemon:10161')
  await expect(page.locator('.pokemon-card')).toHaveCount(count)
  await page.getByRole('button', { name: '关闭详情' }).click()
  await expect(page.getByRole('dialog')).toHaveCount(0)
  await expect.poll(() => page.evaluate(() => window.scrollY)).toBeCloseTo(top, 0)
  expect(new URL(page.url()).searchParams.get('type')).toBe('normal')
  expect(new URL(page.url()).searchParams.get('sort')).toBe('id')
})

test('only the full-page entrance changes modes and keeps its return context across related pages', async ({
  page,
}) => {
  test.setTimeout(90000)
  const { top } = await openScrolledMeowth(page)
  await page.locator('#drawer-form-choice').selectOption('pokemon:10161')
  await page.getByRole('link', { name: '完整页面' }).click()
  await expect(page.getByRole('dialog')).toHaveCount(0)
  await expect(page.locator('#page-form-choice')).toHaveValue('pokemon:10161')
  const from = new URL(page.url()).searchParams.get('from')
  expect(from).toContain('type=normal&sort=id&detail=10161')
  await page.locator('#page-form-choice').selectOption('pokemon:10107')
  await page.locator('[data-evolution-node="pokemon:10108"]').click()
  await expect(page.locator('.detail-sheet__name')).toHaveText('猫老大（Alolan）')
  await expect(page.getByRole('dialog')).toHaveCount(0)
  expect(new URL(page.url()).searchParams.get('from')).toBe(from)
  await page.goBack()
  await expect(page.locator('#page-form-choice')).toHaveValue('pokemon:10107')
  await page.goForward()
  await expect(page.locator('#page-form-choice')).toHaveValue('pokemon:10108')
  expect(new URL(page.url()).searchParams.get('from')).toBe(from)
  await page.reload()
  await expect(page.locator('#page-form-choice')).toHaveValue('pokemon:10108')
  await page.getByRole('link', { name: '返回图鉴' }).click()
  await expect(page.locator('#drawer-form-choice')).toHaveValue('pokemon:10161')
  await page.getByRole('button', { name: '关闭详情' }).click()
  await expect.poll(() => page.evaluate(() => window.scrollY)).toBeCloseTo(top, 0)
})

test('direct full-page related links preserve their previous-detail context and old slugs', async ({
  page,
}) => {
  await page.goto('/zh-Hans/pokemon/eevee')
  await expect(page.locator('.detail-sheet__name')).toHaveText('伊布')
  await page.locator('[data-evolution-node="pokemon:700"]').click()
  await expect(page.locator('#page-form-choice')).toHaveValue('pokemon:700')
  await expect(page.getByRole('dialog')).toHaveCount(0)
  expect(new URL(page.url()).searchParams.get('from')).toBe('/zh-Hans/pokemon/eevee')
  await page.getByRole('link', { name: '返回上一个详情' }).click()
  await expect(page).toHaveURL(/\/pokemon\/eevee$/)
  await expect(page.locator('#page-form-choice')).toHaveValue('pokemon:133')
})

test('evolution form queries and browser history use the same drawer navigation', async ({
  page,
}) => {
  await page.goto('/zh-Hans/pokemon?q=粉蝶虫&detail=664&form=form:10271')
  const node = page.locator('[data-evolution-node="form:10290"]')
  await expect(node).toHaveAttribute('href', /detail=665&form=form:10290/)
  await node.click()
  await expect(page.locator('#drawer-form-choice')).toHaveValue('form:10290')
  await expect(page.getByRole('dialog')).toHaveAttribute('aria-label', '粉蝶蛹（Polar）')
  await page.goBack()
  await expect(page.locator('#drawer-form-choice')).toHaveValue('form:10271')
  await page.goForward()
  await expect(page.locator('#drawer-form-choice')).toHaveValue('form:10290')
  await page.reload()
  await expect(page.locator('#drawer-form-choice')).toHaveValue('form:10290')
  await expect(page.locator('[data-form-key="form:10290"]')).toHaveAttribute('aria-pressed', 'true')
})

for (const [sid, count] of [
  [678, 4],
  [718, 6],
  [774, 14],
  [555, 4],
]) {
  test(`names stay identical in every position for species ${sid}`, async ({ page, request }) => {
    test.setTimeout(90000)
    const result = await (await request.get(`/api/v1/pokemon?q=${sid}&pageSize=100`)).json()
    expect(result.total).toBe(count)
    await page.goto(`/zh-Hans/pokemon?q=${sid}&detail=${sid}`)
    await expect(page.locator('.pokemon-card')).toHaveCount(count)
    expect(new Set(result.items.map((p: { displayName: string }) => p.displayName)).size).toBe(
      count,
    )
    for (const item of result.items) {
      const card = page.locator(`[data-pokemon-id="${item.id}"]`)
      await expect(card).toHaveAttribute('title', item.displayName)
      expect(await card.getAttribute('aria-label')).toContain(item.displayName)
      const picker = page.locator('#drawer-form-choice')
      await expect(picker.locator(`option[value="pokemon:${item.id}"]`)).toHaveText(
        `${item.displayNumber} ${item.displayName}`,
      )
      await expect(page.locator(`[data-form-key="pokemon:${item.id}"] strong`)).toHaveText(
        item.displayName,
      )
      await picker.selectOption(`pokemon:${item.id}`)
      await expect(page.locator('.detail-sheet__name')).toHaveText(item.displayName)
      await expect(page.getByRole('dialog')).toHaveAttribute('aria-label', item.displayName)
      await expect(page.locator(`[data-evolution-node="pokemon:${item.id}"]`)).toHaveAttribute(
        'aria-label',
        `#${item.displayNumber} ${item.displayName}`,
      )
    }
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  })
}
