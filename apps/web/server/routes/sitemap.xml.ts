import type { PaginatedPokemon, TypeSummary } from '~/types/api'

export default defineEventHandler(async (event) => {
  const config = useRuntimeConfig(event)
  const apiBase = String(config.apiBase).replace(/\/$/, '')
  const siteUrl = String(config.public.siteUrl).replace(/\/$/, '')
  const urls: string[] = []

  for (const locale of ['zh-Hans', 'en']) {
    urls.push(`${siteUrl}/${locale}`)
    urls.push(`${siteUrl}/${locale}/pokemon`)
    urls.push(`${siteUrl}/${locale}/types`)
    let page = 1
    let hasNext = true
    while (hasNext) {
      const data = await $fetch<PaginatedPokemon>(`${apiBase}/api/v1/pokemon`, {
        params: { locale, page, pageSize: 100 },
      })
      urls.push(...data.items.map((item) => `${siteUrl}/${locale}/pokemon/${item.id}`))
      hasNext = data.hasNext
      page += 1
    }
    const types = await $fetch<TypeSummary[]>(`${apiBase}/api/v1/types`, { params: { locale } })
    urls.push(...types.map((type) => `${siteUrl}/${locale}/types/${type.name}`))
  }

  setHeader(event, 'content-type', 'application/xml; charset=utf-8')
  return [
    '<?xml version="1.0" encoding="UTF-8"?>',
    '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ...urls.map((url) => `<url><loc>${url}</loc></url>`),
    '</urlset>',
  ].join('')
})
