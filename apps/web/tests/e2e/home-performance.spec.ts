import { expect, test } from '@playwright/test'

test('homepage scrolling keeps the idle story host untouched and persists position after settling', async ({
  page,
}) => {
  await page.addInitScript(() => {
    const writes: { key: string; at: number }[] = []
    const original = Storage.prototype.setItem
    Storage.prototype.setItem = function (key, value) {
      writes.push({ key, at: performance.now() })
      return original.call(this, key, value)
    }
    Object.assign(window, { scrollWrites: writes })
  })
  await page.goto('/zh-Hans')
  await expect(page.locator('#home-search')).toBeEnabled()
  await page.evaluate(
    () =>
      new Promise<void>((resolve) =>
        requestAnimationFrame(() => requestAnimationFrame(() => resolve())),
      ),
  )
  const result = await page.evaluate(async () => {
    const state = window as unknown as { scrollWrites: { key: string; at: number }[] }
    state.scrollWrites.length = 0
    const host = document.querySelector('.scene-stories')!
    let mutations = 0
    const observer = new MutationObserver((entries) => {
      mutations += entries.length
    })
    observer.observe(host, { childList: true, subtree: true })
    const until = performance.now() + 650
    await new Promise<void>((resolve) => {
      function tick() {
        scrollTo(0, 400 + Math.round((performance.now() % 100) * 2))
        dispatchEvent(new Event('scroll'))
        if (performance.now() < until) requestAnimationFrame(tick)
        else resolve()
      }
      tick()
    })
    const during = state.scrollWrites.filter((row) => row.key.startsWith('pokedex:scroll:')).length
    await new Promise((resolve) => setTimeout(resolve, 220))
    const stored = sessionStorage.getItem('pokedex:scroll:/zh-Hans?')
    observer.disconnect()
    return { mutations, during, stored: Number(stored), top: scrollY }
  })
  expect(result.mutations).toBe(0)
  expect(result.during).toBe(0)
  expect(result.stored).toBe(result.top)
  // Leave immediately after a scroll: the route guard must flush the pending save.
  const top = await page.evaluate(() => {
    scrollTo(0, 750)
    return scrollY
  })
  await page.locator('.nav-links a[href="/zh-Hans/types"]').click()
  await expect(page).toHaveURL(/\/zh-Hans\/types$/)
  await page.goBack()
  await expect(page.locator('.night-home')).toBeVisible()
  await expect.poll(() => page.evaluate(() => scrollY)).toBe(top)
})

test('real visible animations retain their sources and repaint isolation without changing mobile policy', async ({
  page,
  isMobile,
}) => {
  await page.goto('/zh-Hans')
  await expect(page.locator('#home-search')).toBeEnabled()
  await page.locator('.visitor[data-id="708"]').scrollIntoViewIfNeeded()
  if (isMobile) {
    await expect(page.locator('.visitor-image[data-playing="true"]')).toHaveCount(0)
  } else {
    await expect
      .poll(() => page.locator('.visitor-image[data-playing="true"]').count())
      .toBeGreaterThan(0)
    const images = await page.locator('.visitor-image[data-playing="true"]').evaluateAll((nodes) =>
      nodes.map((node) => {
        const image = node as HTMLImageElement
        return {
          source: image.getAttribute('src'),
          layer: getComputedStyle(image).willChange,
          render: getComputedStyle(image).imageRendering,
        }
      }),
    )
    expect(
      images.every(
        (image) =>
          image.source?.endsWith('.gif') &&
          image.layer === 'transform' &&
          image.render === 'pixelated',
      ),
    ).toBe(true)
    await page.locator('.page-footer').scrollIntoViewIfNeeded()
    await page.locator('#home-ambient').uncheck()
    await expect(page.locator('.visitor-image[data-playing="true"]')).toHaveCount(0)
    expect(
      await page
        .locator('.visitor-image')
        .evaluateAll((nodes) =>
          nodes.every((node) => getComputedStyle(node).willChange === 'auto'),
        ),
    ).toBe(true)
  }
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
})
