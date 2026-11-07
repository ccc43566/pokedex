import { expect, test } from '@playwright/test'

test('Totem records stay addressable and selectable but never consume list slots', async ({
  page,
  request,
}) => {
  const all = await (await request.get('/api/v1/pokemon?pageSize=1')).json()
  expect(all.total).toBe(1339)
  const family = await (await request.get('/api/v1/pokemon?q=20&pageSize=100')).json()
  const rats = family.items.filter((p: { speciesId: number }) => p.speciesId === 20)
  expect(rats.map((p: { displayNumber: string }) => p.displayNumber)).toEqual(['20', '20.1'])
  expect((await (await request.get('/api/v1/pokemon?q=totem')).json()).total).toBe(0)
  await page.goto('/zh-Hans/pokemon/raticate-totem-alola')
  await expect(page.locator('.detail-sheet__number')).toHaveText('#20')
  await expect(page.locator('#page-form-choice option')).toHaveCount(3)
  await expect(page.locator('[data-form-key="pokemon:10093"]')).toHaveAttribute(
    'aria-pressed',
    'true',
  )
  await expect(page.locator('[data-evolution-edge]')).toHaveCount(0)
  await page.locator('[data-form-key="pokemon:10092"]').click()
  await expect(page.locator('.detail-sheet__number')).toHaveText('#20.1')
  await expect(page.locator('[data-evolution-edge]')).toHaveAttribute(
    'data-source',
    'pokemon:10091',
  )
})

test('both form entrances, drawer URL and browser history share the complete selection', async ({
  page,
}) => {
  await page.goto('/zh-Hans/pokemon?q=喵喵&detail=52')
  await expect(page.locator('.detail-sheet__name')).toHaveText('喵喵')
  await expect(page.locator('.version-gallery__controls select')).toHaveCount(3)
  await expect(page.locator('[data-evolution-edge]')).toHaveAttribute('data-target', 'pokemon:53')
  await page.locator('[data-form-key="pokemon:10161"]').click()
  await expect(page.locator('#drawer-form-choice')).toHaveValue('pokemon:10161')
  await expect(page.locator('[data-evolution-edge]')).toHaveAttribute('data-target', 'pokemon:863')
  await expect(page.locator('.detail-sheet__name')).toHaveText('喵喵（Galarian）')
  await expect(page.locator('[data-evolution-node="pokemon:10161"]')).toHaveAttribute(
    'aria-current',
    'true',
  )
  const galarImage = await page.locator('.detail-sheet__image').getAttribute('src')
  await page.reload()
  await expect(page.locator('#drawer-form-choice')).toHaveValue('pokemon:10161')
  await expect(page.locator('.detail-sheet__image')).toHaveAttribute('src', galarImage!)
  await page.locator('#drawer-form-choice').selectOption('pokemon:10107')
  await expect(page.locator('[data-evolution-edge]')).toHaveAttribute(
    'data-target',
    'pokemon:10108',
  )
  await page.goBack()
  await expect(page.locator('#drawer-form-choice')).toHaveValue('pokemon:10161')
  await expect(page.locator('[data-evolution-edge]')).toHaveAttribute('data-target', 'pokemon:863')
  await page.goForward()
  await expect(page.locator('#drawer-form-choice')).toHaveValue('pokemon:10107')
  await expect(page.locator('[data-form-key="pokemon:10107"]')).toHaveAttribute(
    'aria-pressed',
    'true',
  )
  await expect(page.locator('[data-evolution-edge]')).toHaveAttribute(
    'data-target',
    'pokemon:10108',
  )
})

test('branching lines point from the shared parent and keep alternate methods intact', async ({
  page,
}) => {
  await page.goto('/zh-Hans/pokemon/133')
  const lines = page.locator('[data-evolution-edge]')
  await expect(lines).toHaveCount(8)
  const sources = await lines.evaluateAll((nodes) =>
    nodes.map((n) => n.getAttribute('data-source')),
  )
  expect(new Set(sources)).toEqual(new Set(['pokemon:133']))
  const leaf = page.locator('[data-target="pokemon:470"]')
  await expect(leaf.locator('[data-evolution-method]')).toHaveCount(6)
  await leaf.locator('summary').first().click()
  await expect(leaf).toContainText('叶之石')
  await expect(leaf).toContainText('eterna forest')
  await expect(page.locator('[data-evolution-node="pokemon:470"]')).toHaveAttribute(
    'href',
    /^\/zh-Hans\/pokemon\/470\?from=/,
  )
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true,
  )
  await expect(page.locator('.evolution-lines > g')).toHaveCount(8)
  await page.goto('/zh-Hans/pokemon/414')
  await expect(page.locator('[data-evolution-node="pokemon:414"]')).toHaveCount(1)
  await expect(page.locator('[data-evolution-node][aria-current="true"]')).toHaveCount(1)
})

test('cosmetic links keep form queries, full choices and current evolution after reload and history', async ({
  page,
}) => {
  await page.goto('/zh-Hans/pokemon/664?form=form%3A10271')
  const lines = page.locator('[data-evolution-edge]')
  await expect(lines).toHaveCount(2)
  await expect(page.locator('[data-evolution-node="form:10290"]')).toHaveAttribute(
    'href',
    /^\/zh-Hans\/pokemon\/665\?form=form:10290&from=/,
  )
  await page.locator('[data-evolution-node="form:10290"]').click()
  await expect(page.locator('#page-form-choice')).toHaveValue('form:10290')
  await expect(page.locator('[data-evolution-node="form:10290"]')).toHaveAttribute(
    'aria-current',
    'true',
  )
  await page.goto('/zh-Hans/pokemon?q=霜奶仙&detail=869&form=form%3A10449')
  await expect(page.locator('.pokemon-card')).toHaveCount(2)
  await expect(page.locator('[data-species-forms] button')).toHaveCount(64)
  await expect(page.locator('[data-species-forms] img').first()).toHaveAttribute('loading', 'lazy')
  await expect(page.locator('[data-evolution-edge]')).toHaveAttribute('data-target', 'form:10449')
  await page.locator('[data-form-key="pokemon:869"]').click()
  await expect(page.locator('#drawer-form-choice')).toHaveValue('pokemon:869')
  await expect(page.locator('[data-evolution-edge]')).toHaveAttribute('data-target', 'pokemon:869')
  await page.goBack()
  await expect(page.locator('#drawer-form-choice')).toHaveValue('form:10449')
  await expect(page.locator('[data-evolution-edge]')).toHaveAttribute('data-target', 'form:10449')
  await page.reload()
  await expect(page.locator('[data-form-key="form:10449"]')).toHaveAttribute('aria-pressed', 'true')
})
