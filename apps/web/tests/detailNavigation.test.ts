import { describe, expect, it } from 'vitest'
import {
  browseContextKey,
  relatedDetailLocation,
  safeReturnPath,
  readBrowsePosition,
  saveBrowsePosition,
} from '../utils/detailNavigation'

const browse = {
  path: '/zh-Hans/pokemon',
  fullPath: '/zh-Hans/pokemon?q=喵喵&type=normal&sort=name&detail=52',
  query: { q: '喵喵', type: 'normal', sort: 'name', detail: '52', form: 'form:1' },
}

describe('context based detail navigation', () => {
  it('keeps near, distant and filtered-out targets in the same drawer', () => {
    for (const id of [53, 863, 10161, '10161']) {
      expect(
        relatedDetailLocation(browse, { pokemonId: id }, true, `/zh-Hans/pokemon/${id}`),
      ).toEqual({
        path: browse.path,
        query: { ...browse.query, detail: String(id), form: undefined },
      })
    }
  })
  it('keeps cosmetic form parameters and complete-page return context', () => {
    const full = {
      path: '/en/pokemon/412',
      fullPath: '/en/pokemon/412?from=%2Fen%2Fpokemon%3Fq%3Dburmy',
      query: { from: '/en/pokemon?q=burmy' },
    }
    expect(
      relatedDetailLocation(
        full,
        { pokemonId: 413, formKey: 'form:10036' },
        false,
        '/en/pokemon/413',
      ),
    ).toEqual({
      path: '/en/pokemon/413',
      query: { from: full.query.from, detail: undefined, form: 'form:10036' },
    })
    const direct = { path: '/en/pokemon/133', fullPath: '/en/pokemon/133', query: {} }
    expect(relatedDetailLocation(direct, { pokemonId: 700 }, false, '/en/pokemon/700')).toEqual({
      path: '/en/pokemon/700',
      query: { from: direct.fullPath, detail: undefined, form: undefined },
    })
  })
  it('validates internal return addresses without stripping list or form parameters', () => {
    const origin = '/zh-Hans/pokemon?q=red&page=2&detail=774&form=form%3A10249'
    expect(safeReturnPath(origin)).toBe(origin)
    for (const invalid of [
      'https://evil.test',
      '//evil.test',
      '/en.evil/path',
      '/\\evil.test',
      '/api/v1/pokemon',
    ])
      expect(safeReturnPath(invalid)).toBeUndefined()
  })
  it('shares scroll positions across drawer states but separates real filter contexts', () => {
    const alternate = { ...browse, query: { ...browse.query, detail: '10161', form: 'form:99' } }
    expect(browseContextKey(alternate)).toBe(browseContextKey(browse))
    saveBrowsePosition(browse, 2345)
    expect(readBrowsePosition(alternate)).toBe(2345)
    expect(
      readBrowsePosition({ ...browse, query: { ...browse.query, q: 'other' } }),
    ).toBeUndefined()
  })
})
