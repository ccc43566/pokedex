import { expect, test } from '@playwright/test'

test('item evolution associations target exact regional and cosmetic forms with a return context', async ({
  page,
}) => {
  await page.goto('/zh-Hans/items?q=80&detail=80&rel=evolutions')
  const dialog = page.getByRole('dialog')
  const regional = dialog.getByRole('link', { name: /裙儿小姐（Hisuian）/ })
  await expect(regional).toHaveAttribute('href', /\/pokemon\/10237\?from=/)
  await regional.click()
  await expect(page.getByRole('heading', { level: 1 })).toContainText('裙儿小姐（Hisuian）')
  await page.getByRole('link', { name: '返回道具列表' }).click()
  await expect(page).toHaveURL(/items\?q=80&detail=80&rel=evolutions/)
  await page.goto('/zh-Hans/items?detail=1167&rel=evolutions')
  const cosmetic = dialog.locator('a[href*="/pokemon/869?"][href*="form="]').first()
  await expect(cosmetic).toBeVisible()
  const href = await cosmetic.getAttribute('href')
  const form = new URL(href!, 'http://127.0.0.1:3000').searchParams.get('form')
  expect(form).toMatch(/^form:\d+$/)
  await cosmetic.click()
  await expect.poll(() => new URL(page.url()).searchParams.get('form')).toBe(form)
  await page.getByRole('link', { name: '返回道具列表' }).click()
  await expect(page.locator('.reference-detail')).toHaveAttribute('data-record-id', '1167')
})

test('missing and failed item images keep the correct name and operable drawer', async ({
  page,
}) => {
  const response = await page.request.get('/api/v1/items/1?locale=zh-Hans')
  expect(response.ok()).toBe(true)
  const json = await response.json()
  json.record.imageUrl = null
  json.record.imageStatus = 'missing'
  await page.route('**/media/**', (route) => route.abort())
  await page.route('**/api/v1/items/1?*', (route) => route.fulfill({ json }))
  await page.goto('/zh-Hans/items?q=1')
  await expect(page.locator('.reference-card .item-image__missing')).toBeVisible()
  await page.getByRole('button', { name: /道具 #1 / }).click()
  const dialog = page.getByRole('dialog')
  await expect(dialog.getByRole('heading', { level: 2 })).toHaveText('大师球')
  await expect(dialog.locator('.item-image__missing')).toBeVisible()
  await expect(dialog.locator('img')).toHaveCount(0)
  await page.keyboard.press('Escape')
  await expect(page.locator('.reference-card')).toBeFocused()
})

test('an aborted earlier detail cannot overwrite a later item selection', async ({ page }) => {
  let started!: () => void
  let finished!: () => void
  const oldStarted = new Promise<void>((resolve) => {
    started = resolve
  })
  const oldFinished = new Promise<void>((resolve) => {
    finished = resolve
  })
  await page.route('**/api/v1/items/1?*', async (route) => {
    started()
    try {
      const response = await route.fetch()
      await new Promise((resolve) => setTimeout(resolve, 800))
      await route.fulfill({ response })
    } catch {
      /* The browser deliberately cancelled this request. */
    } finally {
      finished()
    }
  })
  await page.goto('/zh-Hans/items')
  await page.getByRole('button', { name: /道具 #1 / }).click()
  await oldStarted
  await page.getByRole('button', { name: '关闭详情', exact: true }).click()
  await page.getByRole('button', { name: /道具 #2 / }).click()
  await expect(page.locator('.reference-detail')).toHaveAttribute('data-record-id', '2')
  await oldFinished
  await expect(page.locator('.reference-detail')).toHaveAttribute('data-record-id', '2')
  await expect(page.getByRole('heading', { level: 2 })).toHaveText('高级球')
})

test('move search filters sorting pagination and upstream English fallback', async ({ page }) => {
  await page.goto('/zh-Hans/moves')
  await expect(page.locator('.reference-card')).toHaveCount(937)
  await page.getByRole('combobox', { name: '属性', exact: true }).click()
  await page.getByRole('option', { name: '电', exact: true }).click()
  await page.getByLabel('伤害类别', { exact: true }).selectOption('3')
  await page.getByLabel('引入世代', { exact: true }).selectOption('1')
  await page.getByLabel('排序', { exact: true }).selectOption('power_desc')
  await page.getByRole('button', { name: '筛选', exact: true }).click()
  await expect(page).toHaveURL(/type=13&damage_class=3&generation=1/)
  await expect(page.locator('.reference-card').first()).toContainText('打雷')
  await page.getByLabel('名称或 ID', { exact: true }).fill('Thunderbolt')
  await page.getByRole('button', { name: '筛选', exact: true }).click()
  await expect(page.locator('.reference-card')).toHaveCount(1)
  await expect(page.locator('.reference-card')).toContainText('十万伏特')
  await page.getByRole('button', { name: '清除', exact: true }).click()
  await expect(page.locator('.reference-card')).toHaveCount(937)
  await expect(page.getByRole('button', { name: '下一页', exact: true })).toHaveCount(0)
  await page.goto('/en/moves?q=85&detail=85')
  await expect(page.getByRole('heading', { level: 2 })).toHaveText('Thunderbolt')
  await page.goto('/zh-Hans/items?q=114&detail=114')
  await expect(page.getByRole('heading', { level: 2 })).toHaveText('Grass Mail')
  await expect(page.getByText('名称回退：en', { exact: true })).toBeVisible()
})

test('item navigation, compact cards, official pockets and berry detail', async ({
  page,
}, info) => {
  await page.goto('/zh-Hans/items')
  await expect(page.getByRole('heading', { name: '道具', exact: true })).toBeVisible()
  await expect(page.locator('.reference-card')).toHaveCount(2223)
  const card = page.locator('.reference-card').first()
  await expect(card.locator('img')).toBeVisible()
  expect(
    await card.locator('img').evaluate((el: HTMLImageElement) => el.naturalWidth),
  ).toBeGreaterThan(0)
  expect((await card.boundingBox())!.width).toBeLessThan(190)
  await page.getByLabel('口袋', { exact: true }).selectOption('3')
  await page.getByRole('button', { name: '筛选', exact: true }).click()
  await expect(page).toHaveURL(/pocket=3/)
  await expect(page.locator('.reference-card').first()).toContainText('大师球')
  await page.getByLabel('口袋', { exact: true }).selectOption('5')
  await page.getByRole('button', { name: '筛选', exact: true }).click()
  await expect(page.locator('.reference-card').first()).toContainText('樱子果')
  await page.locator('.reference-card').first().click()
  const dialog = page.getByRole('dialog')
  await expect(dialog.getByRole('heading', { name: /树果资料/ })).toBeVisible()
  await expect(dialog.getByRole('link', { name: '查看完整页面' })).toHaveCount(0)
  await expect(dialog.locator('.item-image img')).toHaveAttribute('data-item-id', '126')
  await page.screenshot({ path: `../../../migration-audit/items-${info.project.name}.png` })
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
})

test('duplicate item identifiers stay independent with shared media and restorable URLs', async ({
  page,
}) => {
  await page.goto('/zh-Hans/items?q=roseli-berry')
  await expect(page.locator('[data-list-ready="true"]')).toBeVisible()
  await expect(page.locator('.reference-card')).toHaveCount(2)
  const images = await page
    .locator('.reference-card img')
    .evaluateAll((els) => els.map((el) => el.getAttribute('src')))
  expect(images[0]).toBeTruthy()
  expect(images[0]).toBe(images[1])
  await page.getByRole('button', { name: /道具 #723 / }).click()
  await expect(page.locator('.reference-detail')).toHaveAttribute('data-record-id', '723')
  await expect(page.getByRole('heading', { name: /树果资料/ })).toHaveCount(0)
  await page.getByRole('button', { name: '关闭详情', exact: true }).click()
  await page.getByRole('button', { name: /道具 #2279 / }).click()
  await expect(page.locator('.reference-detail')).toHaveAttribute('data-record-id', '2279')
  await expect(page.getByRole('heading', { name: /树果资料/ })).toBeVisible()
  await page.reload()
  await expect(page.locator('.reference-detail')).toHaveAttribute('data-record-id', '2279')
  await page.goBack()
  await expect(page.getByRole('dialog')).toHaveCount(0)
  await page.goForward()
  await expect(page.locator('.reference-detail')).toHaveAttribute('data-record-id', '2279')
})

test('prices distinguish version currency null zero and missing records', async ({ page }) => {
  await page.goto('/zh-Hans/items?detail=1')
  const dialog = page.getByRole('dialog')
  await expect(dialog.getByRole('heading', { name: '游戏价格' })).toBeVisible()
  const price = dialog.locator('.ref-price-row').first()
  await expect(price).toContainText('Pokémon Dollar')
  await expect(price).toContainText('不可购买')
  await expect(price.locator('dd').last()).toHaveText('0')
  await dialog.getByLabel('版本组', { exact: true }).selectOption('2')
  await expect(dialog.locator('.ref-price-row')).toHaveCount(1)
  await page.goto('/zh-Hans/items?detail=723')
  await expect(dialog.getByText('暂无价格资料', { exact: true })).toBeVisible()
})

test('moves retain null values history and versioned machine navigation', async ({
  page,
}, info) => {
  await page.goto('/zh-Hans/moves?q=85&detail=85')
  const dialog = page.getByRole('dialog')
  await expect(dialog.getByRole('heading', { level: 2 })).toHaveText('十万伏特')
  await expect(dialog.getByRole('heading', { name: '历代数值变化' })).toBeVisible()
  await expect(dialog.locator('.ref-history-row').first()).toContainText('95')
  await page.screenshot({ path: `../../../migration-audit/moves-${info.project.name}.png` })
  await dialog.getByRole('button', { name: /招式机器 \(/ }).click()
  const link = dialog.locator('.ref-history-row a').filter({ hasText: /#\d+/ }).first()
  await expect(link).toBeVisible()
  await link.click()
  await expect(page).toHaveURL(/\/items\?detail=/)
  await expect(page.locator('.reference-detail')).toHaveAttribute('data-kind', 'items')
  await page.getByRole('link', { name: '返回来源' }).click()
  await expect(page).toHaveURL(/\/moves\?q=85&detail=85&rel=machines/)
  await expect(page.locator('.reference-detail')).toHaveAttribute('data-record-id', '85')
  await page.goto('/zh-Hans/moves?detail=14')
  await expect(dialog.getByRole('heading', { level: 2 })).toHaveText('剑舞')
  await expect(
    dialog
      .locator('dt')
      .filter({ hasText: /^威力$/ })
      .first()
      .locator('..')
      .locator('dd'),
  ).toHaveText('未提供')
  await expect(dialog.getByText('攻击 +2', { exact: true })).toBeVisible()
})

test('continuous drawer close keyboard and history restore list position', async ({ page }) => {
  await page.goto('/zh-Hans/items?page=2')
  await expect(page.locator('.reference-card')).toHaveCount(2223)
  const card = page.locator('.reference-card').nth(50)
  await card.scrollIntoViewIfNeeded()
  const top = await page.evaluate(() => scrollY)
  expect(top).toBeGreaterThan(200)
  await card.click()
  await expect(page.getByRole('dialog')).toBeVisible()
  await page.keyboard.press('Escape')
  await expect(page.getByRole('dialog')).toHaveCount(0)
  await expect.poll(() => page.evaluate(() => scrollY)).toBeCloseTo(top, -1)
  await expect(card).toBeFocused()
  await expect(page).not.toHaveURL(/page=/)
  await page
    .getByRole('navigation')
    .first()
    .getByRole('link', { name: '招式', exact: true })
    .click()
  await expect(page.locator('.reference-card')).toHaveCount(937)
  await page.goBack()
  await expect(page.locator('.reference-card')).toHaveCount(2223)
  await expect.poll(() => page.evaluate(() => scrollY)).toBeCloseTo(top, -1)
})

test('learner links keep independent Pokémon ID and return to the move drawer', async ({
  page,
}) => {
  await page.goto('/zh-Hans/moves?detail=85&rel=learners&rel_vg=20&rel_method=4')
  const dialog = page.getByRole('dialog')
  const learner = dialog.locator('.ref-history-row a').first()
  await expect(learner).toBeVisible()
  const href = await learner.getAttribute('href')
  expect(href).toMatch(/\/pokemon\/\d+\?from=/)
  await learner.click()
  await expect(page.getByRole('link', { name: '返回招式列表' })).toBeVisible()
  await page.getByRole('link', { name: '返回招式列表' }).click()
  await expect(page).toHaveURL(/detail=85&rel=learners&rel_vg=20&rel_method=4/)
  await expect(page.locator('.reference-detail')).toHaveAttribute('data-record-id', '85')
  await expect(dialog.getByLabel('学习方式', { exact: true })).toHaveValue('4')
})
