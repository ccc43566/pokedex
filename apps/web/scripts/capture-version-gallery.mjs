import { mkdir } from 'node:fs/promises'
import { join } from 'node:path'
import { chromium } from '@playwright/test'

const output = join(process.cwd(), 'test-results', 'visual')
await mkdir(output, { recursive: true })
const browser = await chromium.launch({ channel: 'msedge' })
async function captureGallery(page, filename) {
  await page.locator('.version-gallery__heading').evaluate((element) => {
    element.scrollIntoView({ block: 'start' })
    window.scrollBy(0, -78)
  })
  await page.waitForFunction(() => [...document.querySelectorAll('.version-gallery__item img')]
    .filter((image) => {
      const bounds = image.getBoundingClientRect()
      return bounds.bottom > 70 && bounds.top < innerHeight
    })
    .every((image) => image.complete && image.naturalWidth > 0))
  await page.screenshot({ path: join(output, filename), fullPage: false })
}
try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
  await page.goto('http://127.0.0.1:3000/zh-Hans/pokemon/1')
  await page.getByText('历代游戏图片', { exact: true }).waitFor()
  await page.getByText('134 张图片', { exact: true }).waitFor()
  const controls = page.locator('.version-gallery__controls select')
  if (await page.locator('.version-gallery__group').count() !== 9) throw Error('Cross-generation sections are missing')
  if (await page.locator('.version-gallery__item').count() < 20) throw Error('Game comparisons are missing')
  await captureGallery(page, 'version-gallery-desktop.png')

  await controls.nth(1).selectOption('generation-ix')
  await controls.nth(2).selectOption('scarlet-violet')
  const genNine = page.locator('.version-gallery__item img')
  await genNine.first().evaluate((img) => img.decode())
  if (!(await genNine.first().getAttribute('src'))?.endsWith('.webp')) throw Error('Generation IX WebP was not preserved')

  await controls.nth(1).selectOption('generation-v')
  await controls.nth(2).selectOption('black-white')
  await controls.nth(3).selectOption('animated/front_default')
  const gif = page.locator('.version-gallery__item img').first()
  await gif.evaluate((img) => img.decode())
  if (!(await gif.getAttribute('src'))?.endsWith('.gif')) throw Error('Animated GIF was not preserved')
  await captureGallery(page, 'version-gallery-gif.png')

  await controls.nth(1).selectOption('generation-iv')
  await controls.nth(2).selectOption('diamond-pearl')
  await controls.nth(3).selectOption('front_female')
  await page.getByText('未提供独立雌性图 · 显示本游戏默认图').waitFor()
  const femaleFallback = page.locator('.version-gallery__item img').first()
  if (!(await femaleFallback.getAttribute('src'))?.endsWith('.png')) throw Error('Same-game female fallback is missing')
  await captureGallery(page, 'version-gallery-female-fallback.png')

  const mobile = await browser.newPage({ viewport: { width: 390, height: 844 }, isMobile: true })
  await mobile.goto('http://127.0.0.1:3000/zh-Hans/pokemon/1')
  await mobile.getByText('134 张图片', { exact: true }).waitFor()
  await captureGallery(mobile, 'version-gallery-mobile.png')

  const formPage = await browser.newPage({ viewport: { width: 1280, height: 900 } })
  await formPage.goto('http://127.0.0.1:3000/zh-Hans/pokemon/25')
  await formPage.getByText('历代游戏图片', { exact: true }).waitFor()
  await formPage.locator('.version-gallery__controls select').first().selectOption('form:25')
  const formLabel = await formPage.locator('.version-gallery__controls option[value="form:25"]').textContent()
  if (formLabel !== 'pikachu （默认形态）') throw Error('Default form label is missing')
  if (await formPage.locator('.version-gallery__item').count() === 0) throw Error('Form images are missing')
  console.log('Version gallery: nine generations, WebP, animated GIF, female fallback, form selector, and mobile layout passed.')
} finally {
  await browser.close()
}
