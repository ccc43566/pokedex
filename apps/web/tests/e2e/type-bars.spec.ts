import { expect, test, type Locator } from '@playwright/test'
import { typePalette } from '../../utils/typePalette'

test.setTimeout(120_000)
async function dimensions(bars: Locator) {
  return bars.evaluateAll((els) =>
    els.map((el) => {
      const box = el.getBoundingClientRect(),
        style = getComputedStyle(el)
      const name = el.querySelector('.type-bar__name')!,
        image = el.querySelector('img')!
      const text = document.createRange()
      text.selectNodeContents(name)
      return {
        width: box.width,
        height: box.height,
        font: getComputedStyle(name).fontSize,
        color: getComputedStyle(name).color,
        icon: image.getBoundingClientRect().width,
        overflow:
          name.scrollHeight > name.clientHeight + 1 || name.scrollWidth > name.clientWidth + 1,
        lines: text.getClientRects().length,
        animation: style.animationName,
      }
    }),
  )
}

test('all nineteen bars keep palette, white text, fixed boxes and glyph transparency', async ({
  page,
}, info) => {
  await page.goto('/zh-Hans/types')
  const bars = page.locator('main .type-bar')
  await expect(bars).toHaveCount(19)
  const sizes = await dimensions(bars)
  for (const s of sizes)
    expect(s).toMatchObject({
      width: 104,
      height: 32,
      color: 'rgb(255, 255, 255)',
      icon: 23,
      overflow: false,
      animation: 'none',
    })
  const styles = await bars.evaluateAll((els) =>
    els.map((el) => ({
      name: el.getAttribute('data-type')!,
      left: getComputedStyle(el).getPropertyValue('--type-icon-bg').trim(),
      right: getComputedStyle(el).getPropertyValue('--type-label-bg').trim(),
    })),
  )
  for (const s of styles) {
    expect(s.left).toBe(typePalette[s.name]!.icon)
    expect(s.right).toBe(typePalette[s.name]!.label)
  }
  await expect(page.locator('[data-type="dark"]')).toHaveCount(1)
  await expect(page.locator('[data-type="shadow"], [data-type="unknown"]')).toHaveCount(0)
  const alpha = await page.evaluate(async () => {
    const result: number[] = []
    for (const type of ['normal', 'psychic']) {
      const image = new Image()
      image.src = `/type-icons/${type}.svg`
      await image.decode()
      const canvas = document.createElement('canvas')
      canvas.width = canvas.height = 64
      const c = canvas.getContext('2d')!
      c.drawImage(image, 0, 0, 64, 64)
      result.push(c.getImageData(32, 32, 1, 1).data[3]!)
    }
    return result
  })
  expect(alpha).toEqual([0, 0])
  await page.screenshot({
    path: `../../../migration-audit/type-bars-index-${info.project.name}.png`,
  })
  await page.goto('/en/types')
  await expect(page.locator('main .type-bar')).toHaveCount(19)
  for (const box of await dimensions(page.locator('main .type-bar')))
    expect(box).toMatchObject({ width: 104, height: 32, overflow: false })
})

test('cards retain adaptive two-bar sizing, centered singles and long labels in both languages', async ({
  page,
}, info) => {
  const originalViewport = page.viewportSize()!
  for (const locale of ['zh-Hans', 'en']) {
    await page.setViewportSize(originalViewport)
    await page.goto(`/${locale}/pokemon`)
    await expect(page.locator('.pokemon-card')).toHaveCount(1339, { timeout: 60000 })
    const dual = page.locator('.pokemon-card[data-pokemon-id="1"]')
    const single = page.locator('.pokemon-card[data-pokemon-id="4"]')
    await dual.scrollIntoViewIfNeeded()
    const d = await dimensions(dual.locator('.type-bar'))
    const s = await dimensions(single.locator('.type-bar'))
    expect(d).toHaveLength(2)
    expect(s).toHaveLength(1)
    expect(s[0]!.width).toBeCloseTo(d[0]!.width, 1)
    for (const box of [...d, ...s])
      expect(box).toMatchObject({
        height: 30,
        font: '13px',
        icon: 22,
        overflow: false,
        color: 'rgb(255, 255, 255)',
      })
    for (const box of [...d, ...s]) expect(box.lines).toBeLessThanOrEqual(2)
    const card = await single.boundingBox(),
      bar = await single.locator('.type-bar').boundingBox()
    expect(bar!.x + bar!.width / 2).toBeCloseTo(card!.x + card!.width / 2, 0)
    for (const item of [single, dual]) {
      await item.scrollIntoViewIfNeeded()
      const box = await item.boundingBox()
      const row = await item.locator('.pokemon-card__types').boundingBox()
      expect(row!.height).toBe(30)
      expect(box!.y + box!.height - row!.y - row!.height).toBeCloseTo(13, 0)
    }
    const psychic = page.locator('.pokemon-card[data-pokemon-id="177"]')
    await psychic.scrollIntoViewIfNeeded()
    for (const box of await dimensions(psychic.locator('.type-bar')))
      expect(box).toMatchObject({ overflow: false })
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
    await dual.scrollIntoViewIfNeeded()
    await page.screenshot({
      path: `../../../migration-audit/type-bars-cards-${locale}-${info.project.name}.png`,
    })
    // At the existing three-column breakpoint this is narrower per card than
    // 320px/two columns, so it also covers the worst ordinary mobile label box.
    await page.setViewportSize({ width: 432, height: 800 })
    await single.scrollIntoViewIfNeeded()
    const narrowSingle = await dimensions(single.locator('.type-bar'))
    await dual.scrollIntoViewIfNeeded()
    const narrowDual = await dimensions(dual.locator('.type-bar'))
    expect(narrowDual[0]!.width).toBeCloseTo(narrowSingle[0]!.width, 1)
    const rows = await dual
      .locator('.type-bar')
      .evaluateAll((els) => els.map((el) => el.getBoundingClientRect().y))
    expect(rows[1]! - rows[0]!).toBeCloseTo(0, 0)
    for (const type of Object.keys(typePalette).filter((name) => name !== 'stellar')) {
      const card = page.locator('.pokemon-card').filter({ has: page.locator(`[data-type="${type}"]`) }).first()
      await card.scrollIntoViewIfNeeded()
      const badge = card.locator(`[data-type="${type}"]`)
      await expect(badge).toBeVisible()
      for (const box of await dimensions(badge)) {
        expect(box).toMatchObject({ height: 30, icon: 22, font: '13px', overflow: false })
        expect(box.lines).toBeLessThanOrEqual(locale === 'zh-Hans' ? 1 : 2)
      }
    }
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  }
})

test('Psychic is abbreviated only on Chinese Pokemon cards', async ({ page }) => {
  await page.goto('/zh-Hans/pokemon?q=177&detail=177')
  await expect(page.locator('.pokemon-card [data-type="psychic"] .type-bar__name')).toHaveText('超能')
  await expect(page.locator('.detail-sheet [data-type="psychic"] .type-bar__name')).toHaveText('超能力')
  await page.getByRole('button', { name: '关闭详情', exact: true }).click()
  // The filter shares the original dictionary name, not the card-only label.
  const trigger = page.getByRole('combobox', { name: '属性', exact: true })
  await page.evaluate(() => window.scrollTo(0, 0))
  await trigger.click()
  await expect(page.getByRole('listbox').getByRole('option', { name: '超能力', exact: true })).toBeVisible()
  await page.keyboard.press('Escape')
  await page.goto('/zh-Hans/types/psychic')
  await expect(page.locator('main [data-type="psychic"] .type-bar__name').first()).toHaveText('超能力')
  await page.goto('/en/pokemon?q=177')
  await expect(page.locator('.pokemon-card [data-type="psychic"] .type-bar__name')).toHaveText('Psychic')
})

test('type picker keeps draft/apply semantics, equal options and keyboard focus', async ({
  page,
}) => {
  await page.goto('/zh-Hans/moves?q=85')
  await expect(page.locator('[data-list-ready="true"]')).toBeVisible()
  const trigger = page.getByRole('combobox', { name: '属性', exact: true })
  await trigger.focus()
  await page.keyboard.press('ArrowDown')
  await expect(page.getByRole('listbox', { name: '属性', exact: true })).toBeVisible()
  await expect(
    page.getByRole('listbox', { name: '属性', exact: true }).getByRole('option'),
  ).toHaveCount(20)
  const boxes = await dimensions(page.locator('[role="option"] .type-bar'))
  for (const box of boxes)
    expect(box).toMatchObject({
      width: 84,
      height: 24,
      color: 'rgb(255, 255, 255)',
      icon: 18,
      overflow: false,
    })
  await expect(
    page
      .getByRole('listbox', { name: '属性', exact: true })
      .getByRole('option', { name: '暗', exact: true }),
  ).toHaveCount(0)
  await expect(
    page
      .getByRole('listbox', { name: '属性', exact: true })
      .getByRole('option', { name: '???', exact: true }),
  ).toHaveCount(0)
  await expect(
    page
      .getByRole('listbox', { name: '属性', exact: true })
      .getByRole('option', { name: '恶', exact: true }),
  ).toHaveCount(1)
  await page.keyboard.press('End')
  await expect(
    page
      .getByRole('listbox', { name: '属性', exact: true })
      .getByRole('option', { name: '星晶', exact: true }),
  ).toBeFocused()
  await page.keyboard.press('ArrowUp')
  await expect(
    page
      .getByRole('listbox', { name: '属性', exact: true })
      .getByRole('option', { name: '妖精', exact: true }),
  ).toBeFocused()
  await page.keyboard.press('Home')
  await page.keyboard.press('Escape')
  await expect(trigger).toBeFocused()
  await expect(trigger).toHaveAttribute('aria-expanded', 'false')
  await trigger.click()
  await page.keyboard.press('Home')
  await page.keyboard.press('Space')
  await expect(trigger).toBeFocused()
  await expect(trigger).toHaveAttribute('aria-expanded', 'false')
  await trigger.click()
  await page
    .getByRole('listbox', { name: '属性', exact: true })
    .getByRole('option', { name: '电', exact: true })
    .focus()
  await page.keyboard.press('Enter')
  await expect(trigger).toBeFocused()
  await expect(page).not.toHaveURL(/type=/)
  await page.getByRole('button', { name: '筛选', exact: true }).click()
  await expect(page).toHaveURL(/type=13/)
  await expect(page.locator('.reference-card')).toHaveCount(1)
  await page.goBack()
  await expect(page).not.toHaveURL(/type=/)
  await expect(trigger.locator('.type-bar')).toHaveCount(0)
  await page.setViewportSize({ width: 320, height: 800 })
  await trigger.click()
  const popup = await page.getByRole('listbox', { name: '属性', exact: true }).boundingBox()
  expect(popup!.x).toBeGreaterThanOrEqual(0)
  expect(popup!.x + popup!.width).toBeLessThanOrEqual(320)
  await page.keyboard.press('Tab')
  await expect(trigger).toHaveAttribute('aria-expanded', 'false')
  await expect(page.getByLabel('伤害类别', { exact: true })).toBeFocused()
})

test('Pokemon picker uses the same bars while old type links and relations still navigate', async ({
  page,
  isMobile,
}) => {
  await page.goto('/zh-Hans/pokemon?q=25')
  await expect(page.locator('.pokemon-card').first()).toBeVisible()
  if (isMobile) {
    await page.evaluate(() => window.scrollTo(0, 1200))
    await page.getByRole('button', { name: '更多', exact: true }).click()
  }
  const trigger = page.getByRole('combobox', { name: '属性', exact: true })
  await trigger.click()
  await page
    .getByRole('listbox', { name: '属性', exact: true })
    .getByRole('option', { name: '电', exact: true })
    .click()
  await expect(page).not.toHaveURL(/type=/)
  await page.getByRole('button', { name: '筛选', exact: true }).click()
  await expect(page).toHaveURL(/type=electric/)
  await page.goto('/zh-Hans/pokemon/6')
  const bars = page.locator('.detail-sheet .type-bar')
  await expect(bars).toHaveCount(2)
  for (const box of await dimensions(bars))
    expect(box).toMatchObject({ width: 104, height: 32, icon: 23 })
  await bars.filter({ hasText: '飞行' }).click()
  await expect(page).toHaveURL(/\/types\/flying/)
  await expect(page.locator('main .type-bar').first()).toHaveText('飞行')
  await page.locator('main a.type-bar[data-type="electric"]').first().click()
  await expect(page).toHaveURL(/\/types\/electric/)
  await expect(page.locator('main .type-bar').first()).toHaveText('电')
})

test('moves, historical types and berries reuse bars; shadow records stay accessible', async ({
  page,
}) => {
  await page.goto('/zh-Hans/moves?q=16&detail=16')
  await expect(page.locator('.reference-detail .type-bar[data-type="flying"]')).toHaveCount(1)
  await expect(page.locator('.ref-history-row .type-bar[data-type="normal"]')).toHaveCount(1)
  await page.goto('/zh-Hans/items?detail=126')
  await expect(page.locator('.reference-detail .type-bar[data-type="fire"]')).toHaveCount(1)
  await page.goto('/zh-Hans/moves?q=10001&detail=10001')
  await expect(page.locator('.reference-card')).toHaveCount(1)
  await expect(page.locator('.reference-detail')).toHaveAttribute('data-record-id', '10001')
  await expect(page.locator('[data-type="shadow"], [data-type="unknown"]')).toHaveCount(0)
  const source = await (await page.request.get('/api/v1/moves/10001?locale=zh-Hans')).json()
  for (const fixtureType of [{ id: 10001, name: 'unknown', localizedName: '???' }, null]) {
    await page.route('**/api/v1/moves/10001?*', (route) =>
      route.fulfill({ json: { ...source, record: { ...source.record, type: fixtureType } } }),
    )
    await page.goto('/zh-Hans/moves?q=10001&detail=10001')
    await expect(page.locator('.reference-detail')).toHaveAttribute('data-record-id', '10001')
    const label = page.locator('.reference-detail dt').filter({ hasText: /^属性$/ })
    if (fixtureType) await expect(label).toHaveCount(0)
    else await expect(label.locator('..').locator('dd')).toHaveText('未提供')
    await page.unrouteAll({ behavior: 'wait' })
  }
  await page.goto('/zh-Hans/types/unknown')
  await expect(page.getByText('此属性不在当前展示集合中。', { exact: true })).toBeVisible()
  await expect(page.locator('main .type-bar')).toHaveCount(0)
})

test('stellar matches other header bars exactly including English and its colored PNG', async ({
  page,
}) => {
  // Local Pokemon records do not assign stellar. Inject only a browser fixture to exercise that header.
  for (const locale of ['zh-Hans', 'en']) {
    const types = [
      { id: 13, name: 'electric', localizedName: locale === 'en' ? 'Electric' : '电' },
      { id: 19, name: 'stellar', localizedName: locale === 'en' ? 'Stellar' : '星晶' },
    ]
    await page.route('**/api/v1/pokemon/25?*', async (route) => {
      const response = await route.fetch(),
        json = await response.json()
      json.types = types
      for (const option of json.formOptions || []) option.types = types
      await route.fulfill({ response, json })
    })
    await page.goto(`/${locale}/pokemon?q=25&detail=25`)
    const bars = page.locator('[role="dialog"] .detail-sheet .type-bar')
    await expect(bars).toHaveCount(2)
    for (const s of await dimensions(bars))
      expect(s).toMatchObject({ width: 104, height: 32, icon: 23, overflow: false })
    await expect(bars.locator('img[src="/type-icons/stellar.png"]')).toBeVisible()
    await page.getByRole('dialog').locator('.detail-drawer__close').click()
    await page.route('**/api/v1/pokemon?*', async (route) => {
      const response = await route.fetch(),
        json = await response.json()
      for (const record of json.items) record.types = types
      await route.fulfill({ response, json })
    })
    await page.getByPlaceholder(locale === 'en' ? 'Name or number' : '名称或编号').fill('26')
    await page.locator('.dex-filter-actions button[type="submit"]').click()
    const cardBars = page.locator('.pokemon-card[data-pokemon-id="26"] .type-bar')
    await expect(cardBars).toHaveCount(2)
    const box = await dimensions(cardBars)
    expect(box[1]).toMatchObject({ height: 30, icon: 22, font: '13px', overflow: false })
    expect(box[0]!.width).toBeCloseTo(box[1]!.width, 1)
    await expect(cardBars.locator('img[src="/type-icons/stellar.png"]')).toHaveCount(1)
    await page.unrouteAll({ behavior: 'wait' })
  }
})
