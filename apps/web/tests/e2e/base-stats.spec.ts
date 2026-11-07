import { expect, test, type Page } from '@playwright/test'

test.setTimeout(60_000)

const labels = {
  'zh-Hans': ['HP', '攻击', '防御', '特攻', '特防', '速度'],
  en: ['HP', 'Attack', 'Defense', 'Sp. Atk', 'Sp. Def', 'Speed'],
}
const reference = [255, 10, 10, 75, 135, 55]
const colors = [
  'rgb(130, 189, 122)',
  'rgb(247, 207, 88)',
  'rgb(243, 176, 78)',
  'rgb(96, 184, 241)',
  'rgb(102, 169, 239)',
  'rgb(164, 87, 186)',
]

async function expectStats(page: Page, locale: keyof typeof labels) {
  await expect(page.locator('.stat-bars__row')).toHaveCount(6)
  await expect(page.locator('.stat-bars__content .stat-bars__label')).toHaveText(labels[locale])
  await expect(page.locator('.stat-bars__value')).toHaveText(reference.map(String))
  await expect(page.locator('[data-stat-total]')).toHaveText('540')
  await expect(page.locator('.stat-bars__total > .stat-bars__label')).toHaveText(
    locale === 'zh-Hans' ? '总和' : 'Total',
  )
  await expect(page.locator('.detail-sheet__stats h3')).toHaveText(
    locale === 'zh-Hans' ? '种族值' : 'Base stats',
  )
  for (const [index, label] of labels[locale].entries()) {
    await expect(page.getByRole('meter', { name: label, exact: true })).toHaveAttribute(
      'aria-valuenow',
      String(reference[index]),
    )
  }
}

async function expectGeometry(page: Page) {
  const geometry = await page.locator('.stat-bars__row').evaluateAll((elements) =>
    elements.map((row) => {
      const fill = row.querySelector<HTMLElement>('.stat-bars__fill')!
      const label = row
        .querySelector('.stat-bars__content .stat-bars__label')!
        .getBoundingClientRect()
      const number = row.querySelector('.stat-bars__value')!.getBoundingClientRect()
      return {
        width: row.getBoundingClientRect().width,
        fill: fill.getBoundingClientRect().width,
        color: getComputedStyle(fill).backgroundColor,
        backgroundImage: getComputedStyle(fill).backgroundImage,
        labelsSeparated: label.right + 8 <= number.left,
        numberCovered: fill.getBoundingClientRect().right >= number.right,
      }
    }),
  )
  geometry.forEach((row, index) => {
    expect(row.fill / row.width).toBeCloseTo(reference[index]! / 255, 3)
    expect(row.color).toBe(colors[index])
    expect(row.backgroundImage).toBe('none')
    expect(row.labelsSeparated).toBe(true)
  })
  expect(geometry[0]!.numberCovered).toBe(true)
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
}

for (const locale of ['zh-Hans', 'en'] as const) {
  for (const mode of ['day', 'night'] as const) {
    test(`base stats drawer: ${locale} ${mode} keeps reference colors, lengths, and overlaid values`, async ({
      page,
      context,
    }, info) => {
      await context.addCookies([
        {
          name: 'pokedex-appearance-v1',
          value: encodeURIComponent(JSON.stringify({ mode })),
          url: 'http://127.0.0.1:3000',
        },
      ])
      await page.goto(`/${locale}/pokemon?detail=242`, { waitUntil: 'domcontentloaded' })
      await expectStats(page, locale)
      await expectGeometry(page)
      const detail = page.locator('.detail-sheet__stats')
      await detail.scrollIntoViewIfNeeded()
      if (mode === 'night') {
        await expect(page.locator('.stat-bars__value').first()).toHaveCSS(
          'color',
          'rgb(255, 255, 255)',
        )
        const overlay = page.locator('.stat-bars__on-fill').first()
        await expect(overlay).toHaveAttribute('aria-hidden', 'true')
        expect(
          await overlay
            .locator('.stat-bars__value-copy')
            .evaluate((element) => getComputedStyle(element).color),
        ).not.toBe('rgb(255, 255, 255)')
      }
      await detail.screenshot({
        path: `../../../design/base-stats-production/${locale}-${mode}-${info.project.name}.png`,
      })
      await page.screenshot({
        path: `../../../design/base-stats-production/drawer-${locale}-${mode}-${info.project.name}.png`,
      })
      await page
        .getByRole('button', {
          name: locale === 'zh-Hans' ? '关闭详情' : 'Close details',
          exact: true,
        })
        .click()
      await expect(page.getByRole('dialog')).toHaveCount(0)
      await expect(page).not.toHaveURL(/detail=/)
    })
  }
}

test('base stats labels switch through the real language selector without reloading the page', async ({
  page,
}) => {
  await page.goto('/zh-Hans/pokemon/242', { waitUntil: 'domcontentloaded' })
  await expectStats(page, 'zh-Hans')
  await page.evaluate(() => {
    ;(window as unknown as { languageProbe: boolean }).languageProbe = true
  })
  await page.locator('.catalog-language').click()
  await page.getByRole('option', { name: 'English', exact: true }).click()
  await expect(page).toHaveURL(/\/en\/pokemon\/242/)
  await expectStats(page, 'en')
  expect(
    await page.evaluate(() => (window as unknown as { languageProbe: boolean }).languageProbe),
  ).toBe(true)
  await page.locator('.catalog-language').click()
  await page.getByRole('option', { name: '简体中文', exact: true }).click()
  await expectStats(page, 'zh-Hans')
})

test('base stats use the selected form data and recompute the total in the drawer', async ({
  page,
  request,
}) => {
  const response = await request.get('/api/v1/pokemon/6?locale=zh-Hans')
  expect(response.ok()).toBe(true)
  const original = await response.json()
  const alternative = original.formOptions.find(
    (form: { pokemonId: number }) => form.pokemonId !== 6,
  )
  expect(alternative).toBeTruthy()
  const alternateResponse = await request.get(
    `/api/v1/pokemon/${alternative.pokemonId}?locale=zh-Hans`,
  )
  expect(alternateResponse.ok()).toBe(true)
  const changed = await alternateResponse.json()
  await page.goto('/zh-Hans/pokemon?detail=6', { waitUntil: 'domcontentloaded' })
  await expect(page.locator('.stat-bars__value')).toHaveText(
    original.stats.map((stat: { baseStat: number }) => String(stat.baseStat)),
  )
  await page.locator('#drawer-form-choice').selectOption(alternative.key)
  await expect(page).toHaveURL(new RegExp(`detail=${alternative.pokemonId}`))
  await expect(page.locator('.stat-bars__value')).toHaveText(
    changed.stats.map((stat: { baseStat: number }) => String(stat.baseStat)),
  )
  await expect(page.locator('[data-stat-total]')).toHaveText(
    String(
      changed.stats.reduce((sum: number, stat: { baseStat: number }) => sum + stat.baseStat, 0),
    ),
  )
})

test('base stats English labels and three-digit values fit a 320px drawer', async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 800 })
  await page.goto('/en/pokemon?detail=242', { waitUntil: 'domcontentloaded' })
  await expectStats(page, 'en')
  await expectGeometry(page)
})
