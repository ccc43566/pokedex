import { expect, test } from '@playwright/test'
import path from 'node:path'

test('Nincada has separate level-up and shed conditions with scoped sourced notes', async ({
  page,
}, info) => {
  await page.goto('/zh-Hans/pokemon/290')
  const ninja = page.locator('[data-evolution-edge][data-target="pokemon:291"]')
  const shell = page.locator('[data-evolution-edge][data-target="pokemon:292"]')
  await expect(ninja.locator('.evolution-method > ul')).toHaveText('等级达到 20 后升级进化')
  await expect(ninja.locator('[data-evolution-supplement]')).toHaveCount(0)
  await expect(shell.locator('.evolution-method > ul')).toHaveText(
    '土居忍士进化为铁面忍者时，蜕壳产生的额外宝可梦',
  )
  await expect(shell.locator('[data-evolution-supplement]')).toContainText(
    '不需要额外准备普通精灵球',
  )
  await expect(shell.locator('[data-evolution-supplement]')).toContainText('会消耗该球')
  await expect(shell.locator('[data-evolution-supplement] a')).toHaveCount(2)
  await expect(shell.locator('[data-evolution-evidence] pre')).not.toBeVisible()
  await expect(shell.locator('[data-explanation-origin]')).toHaveText('项目条件释义')
  await expect(page.locator('[data-evolution-version-note]')).toHaveCount(0)
  await page.locator('[data-evolution-graph]').screenshot({
    style: 'header { visibility: hidden !important; }',
    path: path.resolve(
      `../../../migration-audit/evolution-conditions-nincada-${info.project.name}.png`,
    ),
  })
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true,
  )
})

for (const example of [
  {
    id: 206,
    common: 'pokemon:982',
    rare: 'pokemon:10255',
    commonText: '二节形态',
    rareText: '三节形态',
    extra: '强力钻',
  },
  {
    id: 924,
    common: 'pokemon:925',
    rare: 'pokemon:10257',
    commonText: '四只家庭',
    rareText: '三只家庭',
    extra: '等级达到 25 后在对战中提升等级',
  },
]) {
  test(`stored-value branch ${example.id} keeps every condition and drawer navigation`, async ({
    page,
  }) => {
    await page.goto(`/zh-Hans/pokemon?q=${example.id}&detail=${example.id}`)
    const common = page.locator(`[data-evolution-edge][data-target="${example.common}"]`)
    const rare = page.locator(`[data-evolution-edge][data-target="${example.rare}"]`)
    await expect(common.locator('.evolution-method > ul')).toContainText(
      `${example.commonText}：约 99%`,
    )
    await expect(rare.locator('.evolution-method > ul')).toContainText(`${example.rareText}：约 1%`)
    await expect(rare.locator('.evolution-method > ul')).toContainText(example.extra)
    await expect(rare.locator('.evolution-method > ul')).toContainText('由个体内部值决定')
    await expect(rare.locator('[data-evolution-note]')).toContainText('并非每次进化重新抽取概率')
    await expect(rare.locator('.evolution-method > ul')).not.toContainText('EC 100 %')
    await page.locator(`[data-evolution-node="${example.rare}"]`).click()
    await expect(page).toHaveURL(new RegExp(`detail=${example.rare.split(':')[1]}`))
    await expect(page.locator('.detail-drawer')).toBeVisible()
    await expect(page.locator('[data-evolution-edge]')).toHaveCount(1)
    await page.goBack()
    await expect(page.locator('[data-evolution-edge]')).toHaveCount(2)
    await expect(page).toHaveURL(new RegExp(`q=${example.id}.*detail=${example.id}`))
  })
}

test('Wurmple keeps two introduced-version methods per branch without probability guessing', async ({
  page,
  request,
}) => {
  await page.goto('/zh-Hans/pokemon/265')
  for (const target of [266, 268]) {
    const edge = page.locator(`[data-evolution-edge][data-target="pokemon:${target}"]`)
    await expect(edge.locator('[data-evolution-method]')).toHaveCount(2)
    for (const method of await edge.locator('[data-evolution-method]').all()) {
      await expect(method.locator(':scope > ul')).toContainText('等级达到 7 后升级进化')
      await expect(method.locator(':scope > ul')).toContainText('约 50%')
      await expect(method.locator('[data-evolution-version]')).not.toHaveText('')
      await expect(method.locator('[data-evolution-evidence] pre')).not.toBeVisible()
    }
  }
  const data = await (await request.get('/api/v1/pokemon/265?locale=zh-Hans')).json()
  const branch = data.evolutionGraph.edges.find(
    (e: { target: string }) => e.target === 'pokemon:266',
  )
  expect(
    branch.methods.map((m: { version_group: { name: string } }) => m.version_group.name),
  ).toEqual(['ruby-sapphire', 'x-y'])
  expect(branch.methods.map((m: { is_default: boolean }) => m.is_default)).toEqual([false, true])
  expect(
    branch.methodExplanations.map(
      (m: { variables: { raw_payload: { symbol: string } }[] }) =>
        m.variables[0]?.raw_payload.symbol,
    ),
  ).toEqual(['PID', 'EC'])
})

test('Alcremie directions, seconds, time and sweets follow exact form selection and history', async ({
  page,
}, info) => {
  await page.goto('/zh-Hans/pokemon/869')
  const conditions = page.locator('.evolution-method > ul')
  await expect(conditions).toContainText('顺时针旋转')
  await expect(conditions).toContainText('旋转持续少于 5 秒')
  await expect(conditions).toContainText('时间：白天')
  await expect(conditions).toContainText('草莓糖饰')
  for (const example of [
    {
      key: 'form:10346',
      direction: '逆时针旋转',
      duration: '少于 5 秒',
      time: '白天',
      sweet: '草莓糖饰',
    },
    {
      key: 'form:10348',
      direction: '逆时针旋转',
      duration: '至少 5 秒',
      time: '夜晚',
      sweet: '草莓糖饰',
    },
    { key: 'form:10353', direction: '', duration: '至少 10 秒', time: '黄昏', sweet: '草莓糖饰' },
    {
      key: 'form:10449',
      direction: '顺时针旋转',
      duration: '少于 5 秒',
      time: '白天',
      sweet: '野莓糖饰',
    },
  ]) {
    await page.locator('#page-form-choice').selectOption(example.key)
    await expect(page.locator('[data-evolution-edge]')).toHaveAttribute('data-target', example.key)
    await expect(conditions).toContainText(example.duration)
    await expect(conditions).toContainText(`时间：${example.time}`)
    await expect(conditions).toContainText(example.sweet)
    if (example.direction) await expect(conditions).toContainText(example.direction)
    else await expect(conditions).not.toContainText('时针')
    await expect(conditions).not.toContainText('%')
  }
  await page.locator('[data-evolution-graph]').screenshot({
    style: 'header { visibility: hidden !important; }',
    path: path.resolve(
      `../../../migration-audit/evolution-conditions-alcremie-${info.project.name}.png`,
    ),
  })
  await page.reload()
  await expect(page.locator('#page-form-choice')).toHaveValue('form:10449')
  await expect(conditions).toContainText('野莓糖饰')
  await page.goBack()
  await expect(conditions).toContainText('黄昏')
  await page.goForward()
  await expect(conditions).toContainText('野莓糖饰')
  await page.locator('[data-form-key="pokemon:869"]').click()
  await expect(conditions).toContainText('草莓糖饰')
  await expect(page.locator('[data-evolution-edge]')).toHaveAttribute('data-target', 'pokemon:869')
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true,
  )
})

test('ordinary item, trade and English conditions remain usable with preserved IDs', async ({
  page,
  request,
}) => {
  await page.goto('/zh-Hans/pokemon/95')
  await expect(page.locator('.evolution-method > ul')).toContainText('交换')
  await expect(page.locator('.evolution-method > ul')).toContainText('金属膜')
  await page.goto('/zh-Hans/pokemon/133')
  const leaf = page.locator('[data-evolution-edge][data-target="pokemon:470"]')
  await leaf.locator('summary').first().click()
  await expect(leaf).toContainText('叶之石')
  await page.goto('/en/pokemon/290')
  await expect(page.locator('[data-target="pokemon:291"] .evolution-method > ul')).toContainText(
    'Level up at level 20 or higher',
  )
  const all = await (await request.get('/api/v1/pokemon?pageSize=1')).json()
  expect(all.total).toBe(1339)
})
