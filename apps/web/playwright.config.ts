import { defineConfig, devices } from '@playwright/test'

const localBrowser = process.env.PLAYWRIGHT_USE_EDGE ? { channel: 'msedge' as const } : {}

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: false,
  workers: 1,
  retries: process.env.CI ? 2 : 0,
  use: {
    baseURL: 'http://127.0.0.1:3000',
    trace: 'on-first-retry',
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'], ...localBrowser } },
    { name: 'mobile', use: { ...devices['Pixel 7'], ...localBrowser } },
  ],
  webServer: {
    command: 'pnpm dev',
    url: 'http://127.0.0.1:3000/zh-Hans',
    reuseExistingServer: !process.env.CI,
    timeout: 120000,
  },
})
