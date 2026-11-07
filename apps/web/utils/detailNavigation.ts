import type { LocationQuery, RouteLocationRaw } from 'vue-router'
import { referenceListKey, referenceListQuery } from './referenceListCache'

export interface DetailTarget {
  pokemonId: number | string
  formKey?: string | null
}

export interface DetailRoute {
  path: string
  fullPath: string
  query: LocationQuery
}

export function safeReturnPath(value: unknown): string | undefined {
  if (typeof value !== 'string' || !value.startsWith('/') || value.startsWith('//')) return
  const url = new URL(value, 'http://pokedex.local')
  if (url.origin !== 'http://pokedex.local' || !/^\/(zh-Hans|en)(?:\/|$)/.test(url.pathname)) return
  return `${url.pathname}${url.search}${url.hash}`
}

export function relatedDetailLocation(
  route: DetailRoute,
  target: DetailTarget,
  compact: boolean,
  detailPath: string,
): RouteLocationRaw {
  const form = target.formKey?.startsWith('form:') ? target.formKey : undefined
  if (compact) {
    return { path: route.path, query: { ...route.query, detail: String(target.pokemonId), form } }
  }
  return {
    path: detailPath,
    query: {
      ...route.query,
      detail: undefined,
      form,
      from: safeReturnPath(route.query.from) || route.fullPath,
    },
  }
}

export function browseContextKey(route: Pick<DetailRoute, 'path' | 'query'>): string {
  const match = route.path.match(/^\/(zh-Hans|en)\/(items|moves)\/?$/)
  if (match) {
    const kind = match[2] as 'items' | 'moves'
    return `${route.path}?${referenceListKey(kind, referenceListQuery(kind, match[1]!, route.query))}`
  }
  const query = new URLSearchParams()
  for (const key of Object.keys(route.query).sort()) {
    if (['detail', 'form', 'page'].includes(key)) continue
    if (/\/(items|moves)\/?$/.test(route.path) && (key === 'rel' || key.startsWith('rel_')))
      continue
    const value = route.query[key]
    for (const item of Array.isArray(value) ? value : [value]) {
      if (item != null) query.append(key, item)
    }
  }
  return `${route.path}?${query}`
}

export function isBrowsePath(path: string): boolean {
  return /^\/(zh-Hans|en)\/?(?:(?:pokemon|items|moves)\/?)?$/.test(path)
}

export function saveBrowsePosition(route: Pick<DetailRoute, 'path' | 'query'>, top: number): void {
  if (typeof window === 'undefined') return
  try {
    sessionStorage.setItem(`pokedex:scroll:${browseContextKey(route)}`, String(Math.max(0, top)))
  } catch {
    /* Storage may be disabled. */
  }
}

export function readBrowsePosition(route: Pick<DetailRoute, 'path' | 'query'>): number | undefined {
  if (typeof window === 'undefined') return
  try {
    const stored = sessionStorage.getItem(`pokedex:scroll:${browseContextKey(route)}`)
    const top = stored == null ? NaN : Number(stored)
    return Number.isFinite(top) && top >= 0 ? top : undefined
  } catch {
    return undefined
  }
}
