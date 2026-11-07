export function genderRatio(rate: number | null | undefined, locale: string): string {
  const zh = locale === 'zh-Hans'
  if (rate === -1) return zh ? '无性别' : 'Genderless'
  if (rate == null || !Number.isInteger(rate) || rate < 0 || rate > 8) return '—'
  return zh
    ? `雄性 ${(8 - rate) * 12.5}% · 雌性 ${rate * 12.5}%`
    : `Male ${(8 - rate) * 12.5}% · Female ${rate * 12.5}%`
}
