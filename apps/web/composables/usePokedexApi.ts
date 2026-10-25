export function buildPokedexApiUrl(
  path: string,
  options: { server?: boolean; apiBase?: string; publicApiBase?: string } = {},
): string {
  const base = options.server
    ? `${String(options.apiBase || 'http://localhost:8000').replace(/\/$/, '')}/api/v1`
    : `${String(options.publicApiBase || '/api').replace(/\/$/, '')}/v1`
  return `${base}${path.startsWith('/') ? path : `/${path}`}`
}

export function usePokedexApi() {
  const config = useRuntimeConfig()

  async function fetchApi<T>(
    path: string,
    options: Parameters<typeof $fetch<T>>[1] = {},
  ): Promise<T> {
    const url = buildPokedexApiUrl(path, {
      server: import.meta.server,
      apiBase: config.apiBase,
      publicApiBase: config.public.apiBase,
    })
    return (await $fetch(url, options)) as T
  }

  return { fetchApi }
}
