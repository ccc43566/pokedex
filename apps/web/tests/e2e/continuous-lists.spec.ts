import { expect, test, type Page } from '@playwright/test'

test.setTimeout(90_000)
const cards = (page: Page) => page.locator('.reference-card')
async function apply(page: Page, query: string) {
  await expect(page.locator('[data-list-ready="true"]')).toBeVisible()
  await page.getByLabel('名称或 ID', { exact: true }).fill(query)
  await page.getByRole('button', { name: '筛选', exact: true }).click()
}
test('complete ordered unique lists, lazy media and legacy URLs', async ({ page }, info) => {
  const requests: URL[] = []
  page.on('request', (r) => {
    const url = new URL(r.url())
    if (/^\/api\/v1\/(items|moves)$/.test(url.pathname)) requests.push(url)
  })
  for (const [kind, total] of [
    ['items', 2223],
    ['moves', 937],
  ] as const) {
    await page.goto(`/zh-Hans/${kind}?page=9`)
    await expect(page).not.toHaveURL(/page=/)
    await expect(cards(page)).toHaveCount(total, { timeout: 60_000 })
    const ids = await cards(page).evaluateAll((els) =>
      els.map((el) =>
        Number(el.querySelector('.reference-card__id')!.textContent!.replace('#', '')),
      ),
    )
    expect(new Set(ids).size).toBe(total)
    expect(ids).toEqual([...ids].sort((a, b) => a - b))
    const batches = requests.filter((url) => url.pathname.endsWith(`/${kind}`))
    expect(batches).toHaveLength(Math.ceil(total / 100) - 1)
    expect(new Set(batches.map((url) => url.searchParams.get('page'))).size).toBe(batches.length)
    expect(batches.every((url) => url.searchParams.get('page_size') === '100')).toBe(true)
    await expect(page.getByRole('button', { name: '下一页', exact: true })).toHaveCount(0)
    await expect(page.getByText(`已显示全部 ${total} / ${total}`, { exact: true })).toBeVisible()
    if (kind === 'items')
      await expect(cards(page).first().locator('img')).toHaveAttribute('loading', 'lazy')
    await page.screenshot({
      path: `../../../migration-audit/continuous-${kind}-${info.project.name}.png`,
    })
  }
})
test('background failure keeps first batch operable and retries only missing pages', async ({
  page,
}) => {
  const calls: number[] = []
  let failed = false
  await page.route('**/api/v1/moves?*', async (route) => {
    const url = new URL(route.request().url()),
      n = Number(url.searchParams.get('page'))
    calls.push(n)
    if (n === 2 && !failed) {
      failed = true
      await route.fulfill({ status: 503, body: 'temporary' })
      return
    }
    await route.continue()
  })
  await page.goto('/zh-Hans/moves')
  await expect(page.getByRole('button', { name: '重试剩余批次' })).toBeVisible({ timeout: 30_000 })
  await expect(cards(page)).toHaveCount(100)
  await cards(page).first().click()
  await expect(page.locator('.reference-detail')).toHaveAttribute('data-record-id', '1')
  await page.getByRole('button', { name: '关闭详情', exact: true }).click()
  const before = [...calls]
  await page.getByRole('button', { name: '重试剩余批次' }).click()
  await expect(cards(page)).toHaveCount(937)
  expect(calls.slice(before.length)).toEqual([2])
  expect(new Set(before).size).toBe(before.length)
})
test('cache hits and drawer changes avoid list requests, deep return and refresh restore context', async ({
  page,
}) => {
  const lists: string[] = []
  page.on('request', (r) => {
    if (/^\/api\/v1\/(items|moves)$/.test(new URL(r.url()).pathname)) lists.push(r.url())
  })
  await page.goto('/zh-Hans/items')
  await expect(cards(page)).toHaveCount(2223, { timeout: 60_000 })
  const card = cards(page).nth(1800)
  await card.scrollIntoViewIfNeeded()
  const top = await page.evaluate(() => scrollY),
    before = lists.length
  await card.click()
  await expect(page.getByRole('dialog')).toBeVisible()
  await page.getByRole('button', { name: '关闭详情', exact: true }).click()
  await expect.poll(() => page.evaluate(() => scrollY)).toBeCloseTo(top, -1)
  expect(lists.length).toBe(before)
  await page
    .getByRole('navigation')
    .first()
    .getByRole('link', { name: '招式', exact: true })
    .click()
  await expect(cards(page)).toHaveCount(937)
  const beforeBack = lists.length
  await page.goBack()
  await expect(cards(page)).toHaveCount(2223)
  await expect.poll(() => page.evaluate(() => scrollY)).toBeCloseTo(top, -1)
  expect(lists.length).toBe(beforeBack)
  await card.click()
  await expect(page.locator('.reference-detail')).toBeVisible()
  const detail = new URL(page.url()).searchParams.get('detail')
  await page.reload()
  await expect(page.locator('.reference-detail')).toHaveAttribute('data-record-id', detail!)
  await expect(cards(page)).toHaveCount(2223, { timeout: 60_000 })
  await page.getByRole('button', { name: '关闭详情', exact: true }).click()
  await expect.poll(() => page.evaluate(() => scrollY)).toBeCloseTo(top, -1)
})
test('equivalent query hits, LRU eviction and explicit reload are observable on network', async ({
  page,
}) => {
  const requests: string[] = []
  page.on('request', (r) => {
    if (new URL(r.url()).pathname === '/api/v1/moves') requests.push(r.url())
  })
  await page.goto('/zh-Hans/moves?q=85')
  await expect(cards(page)).toHaveCount(1)
  await apply(page, ' 85 ')
  await expect(cards(page)).toHaveCount(1)
  expect(requests).toHaveLength(0) // first batch was SSR; equivalent query reuses memory
  for (const q of ['86', '87', '88']) {
    await apply(page, q)
    await expect(cards(page).first()).toContainText(`#${q}`)
  }
  const before = requests.length
  await apply(page, '85')
  await expect(cards(page).first()).toContainText('#85')
  expect(requests.length).toBe(before + 1)
  await page.getByRole('button', { name: '重新加载列表', exact: true }).click()
  await expect.poll(() => requests.length).toBe(before + 2)
  await expect(cards(page)).toHaveCount(1)
  await apply(page, 'no-results-xyz')
  await expect(page.getByText('没有符合条件的记录', { exact: true })).toBeVisible()
  await page.goto('/en/moves?q=85')
  await expect(cards(page).first()).toContainText('Thunderbolt')
  await page.goto('/zh-Hans/items?pocket=005&sort=')
  await expect(page.getByLabel('口袋', { exact: true })).toHaveValue('5')
  await expect(page.getByLabel('排序', { exact: true })).toHaveValue('id')
  await expect(cards(page)).toHaveCount(74)
})
test('late query responses cannot overwrite a newer applied query', async ({ page }) => {
  let release!: () => void
  const held = new Promise<void>((resolve) => {
    release = resolve
  })
  let started!: () => void
  const began = new Promise<void>((resolve) => {
    started = resolve
  })
  await page.route('**/api/v1/moves?*', async (route) => {
    if (new URL(route.request().url()).searchParams.get('q') === '85') {
      started()
      await held
    }
    await route.continue()
  })
  await page.goto('/zh-Hans/moves?q=14')
  await apply(page, '85')
  await expect(page).toHaveURL(/q=85/)
  await Promise.race([
    began,
    new Promise((_, reject) => setTimeout(() => reject(new Error('No old-query request')), 5000)),
  ])
  await apply(page, '86')
  await expect(cards(page).first()).toContainText('#86')
  release()
  await expect(page).toHaveURL(/q=86/)
  await expect(cards(page).first()).toContainText('#86')
  await page.goBack()
  await expect(cards(page).first()).toContainText('#85')
  await page.goForward()
  await expect(cards(page).first()).toContainText('#86')
})
