import { expect, test } from '@playwright/test'

test('logo replays automatically two seconds after the full animation finishes', async ({
  page,
}) => {
  await page.clock.install()
  await page.goto('/zh-Hans')
  const logo = page.locator('.night-logo')
  await expect(logo).toHaveAttribute('data-playing', 'true')
  await page.clock.pauseAt(new Date(Date.now() + 1000))
  for (let cycle = 0; cycle < 2; cycle++) {
    await logo.evaluate((element) =>
      element.getAnimations({ subtree: true }).forEach((animation) => animation.finish()),
    )
    await expect(logo).toHaveAttribute('data-playing', 'false')
    await page.clock.runFor(1990)
    await expect(logo).toHaveAttribute('data-playing', 'false')
    await page.clock.runFor(30)
    await expect(logo).toHaveAttribute('data-playing', 'true')
  }
  // A manual restart cancels the old run without leaving an extra automatic timer.
  await page.locator('.brand-trigger').click()
  await expect(logo).toHaveAttribute('data-playing', 'true')
  await page.clock.runFor(2050)
  await expect(logo).toHaveAttribute('data-playing', 'true')
})

test('offscreen and reduced motion suppress automatic replays and resume without catch-up loops', async ({
  page,
}) => {
  await page.clock.install()
  await page.goto('/zh-Hans')
  const logo = page.locator('.night-logo')
  await expect(logo).toHaveAttribute('data-playing', 'true')
  await page.clock.pauseAt(new Date(Date.now() + 1000))
  await logo.evaluate((element) =>
    element.getAnimations({ subtree: true }).forEach((animation) => animation.finish()),
  )
  await expect(logo).toHaveAttribute('data-playing', 'false')
  await page.locator('.page-footer').scrollIntoViewIfNeeded()
  await expect
    .poll(() => logo.evaluate((element) => element.style.getPropertyValue('--logo-play-state')))
    .toBe('paused')
  await page.clock.runFor(10000)
  await expect(logo).toHaveAttribute('data-playing', 'false')
  await page.evaluate(() => scrollTo(0, 0))
  await expect
    .poll(() => logo.evaluate((element) => element.style.getPropertyValue('--logo-play-state')))
    .toBe('running')
  await page.clock.runFor(1990)
  await expect(logo).toHaveAttribute('data-playing', 'false')
  await page.clock.runFor(30)
  await expect(logo).toHaveAttribute('data-playing', 'true')
  await page.emulateMedia({ reducedMotion: 'reduce' })
  await expect(logo).toHaveAttribute('data-playing', 'false')
  await page.clock.runFor(10000)
  await expect(logo).toHaveAttribute('data-playing', 'false')
  await page.emulateMedia({ reducedMotion: 'no-preference' })
  await expect
    .poll(() => logo.evaluate((element) => element.style.getPropertyValue('--logo-play-state')))
    .toBe('running')
  await page.clock.runFor(2020)
  await expect(logo).toHaveAttribute('data-playing', 'true')
})

test('background suspension pauses the logo and leaving the homepage cancels replay tasks', async ({
  page,
}) => {
  await page.clock.install()
  await page.goto('/zh-Hans')
  const logo = page.locator('.night-logo')
  await expect(logo).toHaveAttribute('data-playing', 'true')
  await page.clock.pauseAt(new Date(Date.now() + 1000))
  // Exercise the same visibility event received when the host backgrounds this tab.
  await page.evaluate(() => {
    Object.defineProperty(document, 'hidden', { configurable: true, value: true })
    document.dispatchEvent(new Event('visibilitychange'))
  })
  await expect
    .poll(() => logo.evaluate((element) => element.style.getPropertyValue('--logo-play-state')))
    .toBe('paused')
  await page.clock.runFor(10000)
  await page.evaluate(() => {
    Reflect.deleteProperty(document, 'hidden')
    document.dispatchEvent(new Event('visibilitychange'))
  })
  await expect
    .poll(() => logo.evaluate((element) => element.style.getPropertyValue('--logo-play-state')))
    .toBe('running')
  await logo.evaluate((element) =>
    element.getAnimations({ subtree: true }).forEach((animation) => animation.finish()),
  )
  await expect(logo).toHaveAttribute('data-playing', 'false')
  // Nuxt's route transition needs rAF after asynchronous page data resolves.
  await page.clock.resume()
  await page.locator('.nav-links a[href="/zh-Hans/types"]').click()
  await expect(page.locator('.night-home')).toHaveCount(0)
  await page.clock.runFor(10000)
  await expect(logo).toHaveCount(0)
})
