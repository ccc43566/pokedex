import { mkdir } from 'node:fs/promises'
import { join } from 'node:path'
import { chromium } from '@playwright/test'

const output = join(process.cwd(), 'test-results', 'visual')
await mkdir(output, { recursive: true })
const browser = await chromium.launch({ channel: 'msedge' })
try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
  await page.goto('http://127.0.0.1:3000/image-review/')
  await page.getByText('11,475', { exact: true }).waitFor()
  try {
    await page.waitForFunction(() => [...document.querySelectorAll('#venusaur-base img')].length === 8 && [...document.querySelectorAll('#venusaur-base img')].every((img) => img.complete && img.naturalWidth > 0))
  } catch (error) {
    console.error(await page.locator('#venusaur-base img').evaluateAll((images) => images.map((img) => ({ src: img.src, complete: img.complete, width: img.naturalWidth }))))
    throw error
  }
  if (await page.locator('#venusaur-base .feature-card').count() !== 4) throw Error('Venusaur comparison is incomplete')
  if (await page.locator('#generation-gallery .generation-panel').count() !== 9) throw Error('Generation gallery did not render all nine generations')
  for (let generation = 1; generation <= 9; generation++) {
    if (await page.locator(`#generation-gallery [data-generation="${generation}"] .generation-sample`).count() !== 8) throw Error(`Generation ${generation} does not show eight samples`)
  }
  await page.locator('#generation-gallery .generation-panel[data-generation="1"]').scrollIntoViewIfNeeded()
  await page.locator('#generation-gallery [data-generation="1"] img').evaluateAll((images) => Promise.all(images.map((img) => img.decode())))
  await page.screenshot({ path: join(output, 'image-review-generations.png'), fullPage: false })
  await page.locator('#generation-gallery .generation-panel[data-generation="9"]').scrollIntoViewIfNeeded()
  await page.locator('#generation-gallery [data-generation="9"] img').evaluateAll((images) => Promise.all(images.map((img) => img.decode())))
  await page.screenshot({ path: join(output, 'image-review-generation-9.png'), fullPage: false })
  await page.locator('#generation-gallery [data-generation="9"] .generation-open').click()
  if (!(await page.locator('#result-count').textContent())?.includes('1,142 张')) throw Error('Generation 9 filter did not show 1,142 files')
  await page.locator('#generation').selectOption('all')
  if (await page.locator('#catalog-grid .image-card').count() !== 96) throw Error('Catalog did not render 96 initial images')
  await page.screenshot({ path: join(output, 'image-review-desktop.png'), fullPage: false })
  await page.locator('#show-more').click()
  if (await page.locator('#catalog-grid .image-card').count() !== 192) throw Error('Catalog did not append the next 96 images')

  await page.locator('#sort').selectOption('asc')
  if (await page.locator('#catalog-grid .image-card').count() !== 96) throw Error('Sorting did not reset the visible catalog')
  if (!(await page.locator('#catalog-grid .image-card').first().textContent())?.includes('274 B')) throw Error('Ascending size sort failed')
  await page.locator('#search').fill('妙蛙花')
  if (!(await page.locator('#result-count').textContent())?.includes('24 张')) throw Error('Venusaur search did not find 24 files')
  await page.locator('#search').fill('')
  await page.locator('#sort').selectOption('desc')
  await page.locator('#venusaur-base .compare-add').first().click()
  await page.locator('#venusaur-base .compare-add').nth(1).click()
  if (await page.locator('#compare-grid .compare-card').count() !== 2) throw Error('Comparison selection failed')
  await page.screenshot({ path: join(output, 'image-review-compare.png'), fullPage: false })
  await page.close()

  const mobile = await browser.newPage({ viewport: { width: 390, height: 844 }, isMobile: true })
  await mobile.goto('http://127.0.0.1:3000/image-review/')
  await mobile.getByText('11,475', { exact: true }).waitFor()
  try {
    await mobile.waitForFunction(() => [...document.querySelectorAll('#venusaur-base img')].length === 8 && [...document.querySelectorAll('#venusaur-base img')].every((img) => img.complete && img.naturalWidth > 0), null, { timeout: 45000 })
  } catch (error) {
    console.error(await mobile.locator('#venusaur-base img').evaluateAll((images) => images.map((img) => ({ src: img.src, complete: img.complete, width: img.naturalWidth }))))
    throw error
  }
  await mobile.screenshot({ path: join(output, 'image-review-mobile.png'), fullPage: false })
  await mobile.locator('#generation-gallery .generation-panel[data-generation="9"]').scrollIntoViewIfNeeded()
  await mobile.locator('#generation-gallery [data-generation="9"] img').evaluateAll((images) => Promise.all(images.map((img) => img.decode())))
  await mobile.screenshot({ path: join(output, 'image-review-generation-9-mobile.png'), fullPage: false })
  console.log('Image review: nine generations with eight samples each, 4 Venusaur visuals, 96 catalog cards, sorting, search, and compare passed.')
} finally {
  await browser.close()
}
