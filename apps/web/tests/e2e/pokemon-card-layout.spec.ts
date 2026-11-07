import { expect, test, type Locator } from '@playwright/test'

test.setTimeout(120_000)

async function flow(card: Locator) {
  await card.scrollIntoViewIfNeeded()
  return card.evaluate((element) => {
    const card = element.getBoundingClientRect(),
      style = getComputedStyle(element)
    const name = element.querySelector('.pokemon-card__name')!
    const types = element.querySelector('.pokemon-card__types')!
    const t = types.getBoundingClientRect()
    return {
      width: card.width - parseFloat(style.paddingLeft) - parseFloat(style.paddingRight) - 2,
      cardHeight: card.height,
      gap: t.top - name.getBoundingClientRect().bottom,
      bottom: card.bottom - t.bottom - parseFloat(style.borderBottomWidth),
      height: t.height,
      center: card.x + card.width / 2,
      bars: [...types.querySelectorAll('.type-bar')].map((bar) => {
        const rect = bar.getBoundingClientRect(),
          label = bar.querySelector('.type-bar__name')!
        return {
          width: rect.width,
          height: rect.height,
          center: rect.x + rect.width / 2,
          top: rect.top,
          overflow:
            label.scrollHeight > label.clientHeight + 1 ||
            label.scrollWidth > label.clientWidth + 1,
        }
      }),
    }
  })
}

test('grid preserves existing column counts with horizontal types and equal row heights', async ({
  page,
}) => {
  await page.goto('/zh-Hans/pokemon')
  await page.locator('#generation-1-trigger').click()
  await expect(page.locator('.pokemon-card')).toHaveCount(48, { timeout: 60_000 })
  for (const width of [320, 344, 360, 393, 768, 1024, 1280, 1366, 1920]) {
    await page.setViewportSize({ width, height: 900 })
    const first = page.locator('.pokemon-card').first()
    const layout = await flow(first)
    const columns = width >= 1280 ? 8 : width >= 1024 ? 6 : width >= 768 ? 4 : 2
    expect(
      await page
        .locator('.pokemon-grid')
        .evaluate((grid) => getComputedStyle(grid).gridTemplateColumns.split(' ').length),
    ).toBe(columns)
    expect(layout.height).toBe(30)
    expect(layout.bars).toHaveLength(2)
    expect(layout.bars[0]!.top).toBeCloseTo(layout.bars[1]!.top, 1)
    for (const bar of layout.bars) {
      expect(bar.width).toBeCloseTo((layout.width - 6) / 2, 1)
      expect(bar.height).toBe(30)
      expect(bar.overflow).toBe(false)
    }
    const row = await page.locator('.pokemon-card').evaluateAll((cards) => {
      const top = cards[0]!.getBoundingClientRect().top
      return cards
        .filter((c) => Math.abs(c.getBoundingClientRect().top - top) < 1)
        .map((c) => ({
          height: c.getBoundingClientRect().height,
          typeBottom: c.querySelector('.pokemon-card__types')!.getBoundingClientRect().bottom,
        }))
    })
    for (const card of row) {
      expect(card.height).toBeCloseTo(row[0]!.height, 1)
      expect(card.typeBottom).toBeCloseTo(row[0]!.typeBottom, 1)
    }
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  }
})

test('long form labels wrap completely while each row keeps one bottom-aligned type bar row', async ({
  page,
}) => {
  await page.setViewportSize({ width: 375, height: 900 })
  const heights = []
  for (const query of ['zygarde', 'meowth', 'charizard']) {
    await page.goto(`/en/pokemon?q=${query}`)
    await expect(page.locator('.pokemon-card').first()).toBeVisible()
    const cards = page.locator('.pokemon-card')
    for (const card of await cards.all()) {
      const layout = await flow(card)
      expect(layout.gap).toBeGreaterThanOrEqual(11.9)
      expect(layout.height).toBe(30)
      expect(layout.bottom).toBeCloseTo(12, 1)
      expect(layout.bars.every((bar) => !bar.overflow)).toBe(true)
      if (layout.bars.length === 1) expect(layout.bars[0]!.center).toBeCloseTo(layout.center, 1)
      heights.push(layout.cardHeight)
      const nameFits = await card.evaluate((c) => {
        const name = c.querySelector('.pokemon-card__name')!
        return [...name.children].every(
          (child) =>
            child.getBoundingClientRect().bottom <= name.getBoundingClientRect().bottom + 1,
        )
      })
      expect(nameFits).toBe(true)
    }
    if (query === 'zygarde') {
      // Browser-only long-label stress. Restore the original text immediately;
      // the API and database remain unchanged and real labels stay intact.
      const label = cards.first().locator('.pokemon-card__form-label')
      const original = await label.textContent()
      await label.evaluate((element) => {
        element.textContent = Array(4).fill(element.textContent).join(' · ')
      })
      const stress = await flow(cards.first())
      expect(stress.height).toBe(30)
      expect(stress.bottom).toBeCloseTo(12, 1)
      expect(
        await label.evaluate(
          (element) =>
            element.getBoundingClientRect().height >
            parseFloat(getComputedStyle(element).lineHeight) + 1,
        ),
      ).toBe(true)
      await label.evaluate((element, text) => {
        element.textContent = text
      }, original)
    }
  }
  expect(new Set(heights.map(Math.round)).size).toBeGreaterThan(1)
})

test('opening switching and closing the drawer never changes grid tracks or visible card geometry', async ({
  page,
  isMobile,
}) => {
  await page.goto('/zh-Hans/pokemon')
  await page.locator('#generation-1-trigger').click()
  await expect(page.locator('.pokemon-card')).toHaveCount(48, { timeout: 60_000 })
  for (const width of isMobile ? [393, 320] : [1280, 1366, 1024]) {
    await page.setViewportSize({ width, height: 900 })
    await page.locator('.pokemon-card').first().scrollIntoViewIfNeeded()
    const snapshot = () =>
      page.locator('.pokemon-grid').evaluate((grid) => {
        const first = grid.querySelector('.pokemon-card')!.getBoundingClientRect().top
        return {
          width: grid.getBoundingClientRect().width,
          tracks: getComputedStyle(grid).gridTemplateColumns,
          cards: [...grid.querySelectorAll('.pokemon-card')]
            .filter((c) => Math.abs(c.getBoundingClientRect().top - first) < 1)
            .map((c) => {
              const r = c.getBoundingClientRect()
              return {
                width: r.width,
                height: r.height,
                bars: [...c.querySelectorAll('.type-bar')].map((b) => {
                  const t = b.getBoundingClientRect()
                  return { width: t.width, height: t.height, top: t.top - r.top }
                }),
              }
            }),
        }
      })
    const before = await snapshot()
    await page.locator('[data-pokemon-id="1"]').click()
    await expect(page.getByRole('dialog')).toBeVisible()
    expect(await snapshot()).toEqual(before)
    await page.locator('[data-evolution-node="pokemon:2"]').click()
    await expect(page).toHaveURL(/detail=2/)
    expect(await snapshot()).toEqual(before)
    await page.getByRole('button', { name: '关闭详情', exact: true }).click()
    await expect(page.getByRole('dialog')).toHaveCount(0)
    expect(await snapshot()).toEqual(before)
  }
})

test('native list layout restores a deep position after drawer open and close', async ({
  page,
}) => {
  await page.goto('/zh-Hans/pokemon')
  await page.locator('#generation-7-trigger').click()
  await expect(page.locator('.pokemon-card')).toHaveCount(48, { timeout: 60_000 })
  const target = page.locator('.pokemon-card[data-pokemon-id="750"]')
  while (!(await target.count())) {
    const previous = await page.locator('.pokemon-card').count()
    await page.locator('.pokemon-batch-more').scrollIntoViewIfNeeded()
    await expect.poll(() => page.locator('.pokemon-card').count()).toBeGreaterThan(previous)
  }
  await target.evaluate((node) => node.scrollIntoView({ block: 'center' }))
  await target.evaluate(async () => {
    for (let frame = 0; frame < 3; frame++)
      await new Promise<void>((resolve) => requestAnimationFrame(() => resolve()))
  })
  const before = await page.evaluate(() => window.scrollY)
  const loaded = await page.locator('.pokemon-card').count()
  const image = await target.locator('.pokemon-card__image').getAttribute('src')
  await target.click()
  await expect(page.getByRole('dialog')).toBeVisible()
  await page.getByRole('button', { name: '关闭详情', exact: true }).click()
  await expect(page.getByRole('dialog')).toHaveCount(0)
  await expect
    .poll(async () => Math.abs((await page.evaluate(() => window.scrollY)) - before))
    .toBeLessThan(3)
  await expect(target.locator('.pokemon-card__image')).toHaveAttribute('src', image!)
  // Returning near the batch boundary may legitimately prefetch the next batch.
  expect(await page.locator('.pokemon-card').count()).toBeGreaterThanOrEqual(loaded)
})
