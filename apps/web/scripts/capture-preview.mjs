import { mkdir } from 'node:fs/promises'
import { join } from 'node:path'
import { chromium } from '@playwright/test'

const baseURL = process.env.POKEDEX_PREVIEW_URL || 'http://127.0.0.1:3000'
const output = join(process.cwd(), 'test-results', 'visual')
await mkdir(output, { recursive: true })

const browser = await chromium.launch({ channel: 'msedge' })
try {
  const desktop = await browser.newPage({ viewport: { width: 1440, height: 900 } })
  await desktop.goto(`${baseURL}/zh-Hans/pokemon`, { waitUntil: 'domcontentloaded' })
  await desktop.getByText('已显示全部').waitFor({ timeout: 60000 })
  await desktop.screenshot({ path: join(output, 'desktop-list.png') })
  await desktop.locator('[data-pokemon-id="25"]').click()
  await desktop.getByRole('dialog').waitFor()
  await desktop.screenshot({ path: join(output, 'desktop-selected.png') })

  const mobile = await browser.newPage({ viewport: { width: 390, height: 844 }, isMobile: true })
  await mobile.goto(`${baseURL}/zh-Hans/pokemon`, { waitUntil: 'domcontentloaded' })
  await mobile.getByText('已显示全部').waitFor({ timeout: 60000 })
  await mobile.evaluate(() => window.scrollTo(0, 1600))
  await mobile.locator('.dex-filter-form--stuck').waitFor()
  await mobile.screenshot({ path: join(output, 'mobile-sticky.png') })
  await mobile.getByRole('button', { name: '更多' }).click()
  await mobile.screenshot({ path: join(output, 'mobile-expanded.png') })
} finally {
  await browser.close()
}
