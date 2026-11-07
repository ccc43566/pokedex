import { expect, test } from '@playwright/test'

test('drawer and full detail show totals, breeding facts and historical stats', async ({
  page,
}) => {
  await page.goto('/zh-Hans/pokemon?q=25&detail=25')
  await expect(page.locator('[data-stat-total]')).toHaveText('320')
  await expect(page.locator('[data-egg-groups]')).toContainText('陆上 / 妖精')
  await expect(page.locator('[data-gender-ratio]')).toHaveText('雄性 50% · 雌性 50%')
  const history = page.locator('[data-stat-history]')
  await expect(history).toContainText('第 6 世代起')
  await expect(history).toContainText('30 → 40')
  await expect(history).toContainText('40 → 50')
  await expect(history).toContainText('特殊分拆')
  await page.goto('/zh-Hans/pokemon/81')
  await expect(page.locator('[data-stat-total]')).toHaveText('325')
  await expect(page.locator('[data-egg-groups]')).toHaveText('矿物')
  await expect(page.locator('[data-gender-ratio]')).toHaveText('无性别')
  await expect(page.locator('[data-stat-history]')).toContainText('特殊分拆')
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true,
  )
})
