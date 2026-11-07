import { expect, test } from '@playwright/test'

test('groups Urshifu cards and switches the entire drawer while retaining filters', async ({
  page,
}) => {
  await page.goto('/zh-Hans/pokemon?q=武道熊师&detail=892')
  const cards = page.locator('.pokemon-card')
  await expect(cards).toHaveCount(4)
  expect(
    await cards.evaluateAll((nodes) =>
      nodes.map((node) => node.getAttribute('data-display-number')),
    ),
  ).toEqual(['892', '892.1', '892.2', '892.3'])
  expect(
    await cards.evaluateAll((nodes) => nodes.map((node) => node.getAttribute('data-pokemon-id'))),
  ).toEqual(['892', '10191', '10226', '10227'])
  const picker = page.locator('#drawer-form-choice')
  await expect(picker.locator('option')).toHaveCount(4)
  await expect(page.locator('.detail-sheet__name')).toHaveText('武道熊师（Single Strike）')
  const initialImage = await page.locator('.detail-sheet__image').getAttribute('src')
  const galleryImage = page.locator('.version-gallery__item img').first()
  await expect(galleryImage).toHaveAttribute('src', /^\/media\//)
  const initialGalleryImage = await galleryImage.getAttribute('src')
  await picker.selectOption('pokemon:10191')
  await expect(page).toHaveURL(/detail=10191/)
  await expect(page.locator('.detail-sheet__name')).toHaveText('武道熊师（Rapid Strike）')
  await expect(
    page.locator('.detail-sheet__intro').getByRole('link', { name: '水', exact: true }),
  ).toBeVisible()
  await expect(page.locator('.detail-sheet__image')).not.toHaveAttribute('src', initialImage!)
  await expect(page.locator('[data-form-key="pokemon:10191"]')).toHaveAttribute(
    'aria-pressed',
    'true',
  )
  await expect(page.locator('[data-pokemon-id="10191"]')).toHaveAttribute('aria-current', 'true')
  await expect(galleryImage).toBeAttached()
  await expect(galleryImage).not.toHaveAttribute('src', initialGalleryImage!)
  expect(new URL(page.url()).searchParams.get('q')).toBe('武道熊师')
  await page.locator('[data-form-key="pokemon:10226"]').click()
  await expect(page.locator('.detail-sheet__name')).toHaveText(
    '武道熊师（Gigantamax Single Strike）',
  )
  await expect(page.locator('#drawer-form-choice')).toHaveValue('pokemon:10226')
  await page.getByRole('button', { name: '关闭详情' }).click()
  await expect(page.getByRole('dialog')).toHaveCount(0)
  await expect(cards).toHaveCount(4)
})

test('regional variants update stats, abilities, artwork and keep old links', async ({ page }) => {
  await page.goto('/zh-Hans/pokemon/52')
  const picker = page.locator('#page-form-choice')
  await expect(picker.locator('option')).toHaveCount(4)
  await expect(page.locator('.detail-sheet__name')).toHaveText('喵喵')
  const stats = page.locator('.detail-sheet__sections section').first()
  const oldStats = await stats.innerText()
  const oldImage = await page.locator('.detail-sheet__image').getAttribute('src')
  await picker.selectOption('pokemon:10161')
  await expect(page).toHaveURL(/\/pokemon\/10161(?:\?|$)/)
  await expect(page.locator('.detail-sheet__name')).toHaveText('喵喵（Galarian）')
  await expect(
    page.locator('.detail-sheet__intro').getByRole('link', { name: '钢', exact: true }),
  ).toBeVisible()
  await expect(stats).not.toHaveText(oldStats)
  await expect(page.locator('.detail-sheet__sections')).toContainText('硬爪')
  await expect(page.locator('.detail-sheet__image')).not.toHaveAttribute('src', oldImage!)
  await page.goto('/zh-Hans/pokemon/raichu-alola')
  await expect(page.locator('.detail-sheet__name')).toHaveText('雷丘（Alolan）')
  await expect(page.locator('.detail-sheet__number')).toHaveText('#26.1')
  await expect(page.locator('#page-form-choice option')).toHaveCount(4)
  await page.locator('#page-form-choice').selectOption('pokemon:26')
  await expect(page.locator('.detail-sheet__name')).toHaveText('雷丘')
})

test('ordinary defaults merge, Alcremie cosmetics stay selectable without extra cards', async ({
  page,
}) => {
  await page.goto('/zh-Hans/pokemon/1')
  await expect(page.locator('#page-form-choice option')).toHaveCount(1)
  await expect(page.locator('#page-form-choice')).toBeDisabled()
  await expect(page.locator('[data-species-forms] button')).toHaveCount(1)
  await expect(page.locator('.version-gallery__controls select')).toHaveCount(3)
  await page.goto('/zh-Hans/pokemon?q=霜奶仙&detail=869')
  await expect(page.locator('.pokemon-card')).toHaveCount(2)
  const picker = page.locator('#drawer-form-choice')
  await expect(picker.locator('option')).toHaveCount(64)
  const choices = await picker
    .locator('option')
    .evaluateAll((nodes) =>
      nodes.map((n) => ({ value: (n as HTMLOptionElement).value, label: n.textContent })),
    )
  const cosmetic = choices.find(
    (item) => item.value.startsWith('form:') && item.label?.includes('Matcha'),
  )!
  const oldImage = await page.locator('.detail-sheet__image').getAttribute('src')
  await picker.selectOption(cosmetic.value)
  await expect(page.locator('.detail-sheet__name')).toContainText('Matcha')
  await expect(page.locator('.detail-sheet__image')).not.toHaveAttribute('src', oldImage!)
  await expect(page.locator(`[data-form-key="${cosmetic.value}"]`)).toHaveAttribute(
    'aria-pressed',
    'true',
  )
  await expect(page.locator('.pokemon-card')).toHaveCount(2)
  await page.reload()
  await expect(page.locator('#drawer-form-choice')).toHaveValue(cosmetic.value)
  await expect(page.locator('.detail-sheet__name')).toContainText('Matcha')
})

test('national and segmented number search keeps the original record IDs', async ({
  page,
  request,
}) => {
  const all = await (await request.get('/api/v1/pokemon?q=892&pageSize=100')).json()
  const filtered = await (await request.get('/api/v1/pokemon?q=892.1')).json()
  expect(filtered.items.map((p: { id: number }) => p.id)).toEqual([10191])
  expect(filtered.items[0].displayNumber).toBe(all.items[1].displayNumber)
  const internal = await (await request.get('/api/v1/pokemon?q=10191')).json()
  expect(internal.items.some((p: { id: number }) => p.id === 10191)).toBe(true)
  await page.goto('/en/pokemon/10191')
  await expect(page.locator('.detail-sheet__name')).toHaveText('Urshifu（Rapid Strike）')
  await expect(page.locator('.detail-sheet__number')).toHaveText('#892.1')
})
