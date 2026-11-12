/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, expect, it } from 'vitest'
import {
  hasAnyFilterUrlParam,
  parseFiltersFromUrl,
  parseSiblingBoolsFromUrl,
  serializeFiltersToUrl,
  serializeSiblingBoolsToUrl,
} from '../url'
import { EMPTY_FILTERS, EMPTY_SIBLING_BOOLS } from '../types'

const sp = (init: Record<string, string>) => new URLSearchParams(init)

describe('parseFiltersFromUrl', () => {
  it('reads item_type from the canonical `item_type` key', () => {
    expect(parseFiltersFromUrl(sp({ item_type: 'audiobook' }))).toEqual({ item_type: 'audiobook' })
  })

  it('ignores the legacy `type` alias (dropped in #886)', () => {
    expect(parseFiltersFromUrl(sp({ type: 'ebook' }))).toEqual({})
  })

  it('parses available_only=true; treats anything else as URL-absent (#887)', () => {
    expect(parseFiltersFromUrl(sp({ available_only: 'true' }))).toEqual({ available_only: true })
    expect(parseFiltersFromUrl(sp({ available_only: 'false' }))).toEqual({})
    expect(parseFiltersFromUrl(sp({ available_only: '1' }))).toEqual({})
    expect(parseFiltersFromUrl(sp({ available_only: '' }))).toEqual({})
  })

  it('parses available_for_hold=true; anything else URL-absent (#889)', () => {
    expect(parseFiltersFromUrl(sp({ available_for_hold: 'true' })))
      .toEqual({ available_for_hold: true })
    expect(parseFiltersFromUrl(sp({ available_for_hold: 'false' }))).toEqual({})
  })

  it('parseInt-round-trips year and lexile fields, dropping NaN', () => {
    expect(parseFiltersFromUrl(sp({
      year_min: '2010',
      year_max: '2020.5',
      min_lexile: '500',
      max_lexile: 'bogus',
    }))).toEqual({
      year_min: '2010',
      year_max: '2020',
      min_lexile: 500,
    })
  })

  it('caps language at 10 chars', () => {
    expect(parseFiltersFromUrl(sp({ language: 'engxxxxxxxxxxxxx' })))
      .toEqual({ language: 'engxxxxxxx' })
  })

  it('round-trips reading_time / access / topic through the URL (#888)', () => {
    expect(parseFiltersFromUrl(sp({
      reading_time: 'short',
      access: 'audio',
      topic: 'young_adult',
    }))).toEqual({
      reading_time: 'short',
      access: 'audio',
      topic: 'young_adult',
    })
  })

  it('round-trips location through the URL (PR #941 / issue #884)', () => {
    expect(parseFiltersFromUrl(sp({ location: 'Adult Fiction' })))
      .toEqual({ location: 'Adult Fiction' })
  })

  it('round-trips publisher through the URL (PR #945 / issue #885)', () => {
    expect(parseFiltersFromUrl(sp({ publisher: 'Penguin' })))
      .toEqual({ publisher: 'Penguin' })
  })

  it('returns an empty partial when no filter params are present', () => {
    expect(parseFiltersFromUrl(sp({ q: 'hello', sort: 'title' }))).toEqual({})
  })
})

describe('parseSiblingBoolsFromUrl', () => {
  it('reads showNewArrivals from is_new=true', () => {
    expect(parseSiblingBoolsFromUrl(sp({ is_new: 'true' }))).toEqual({ showNewArrivals: true })
  })

  it('treats any non-`true` is_new value as false', () => {
    expect(parseSiblingBoolsFromUrl(sp({ is_new: '1' }))).toEqual({ showNewArrivals: false })
    expect(parseSiblingBoolsFromUrl(sp({ is_new: 'yes' }))).toEqual({ showNewArrivals: false })
  })

  it('reads showLargePrintOnly from is_large_print=true (#888)', () => {
    expect(parseSiblingBoolsFromUrl(sp({ is_large_print: 'true' })))
      .toEqual({ showLargePrintOnly: true })
  })
})

describe('hasAnyFilterUrlParam', () => {
  it('returns true for filter keys, sibling bool keys, and non-filter sentinel keys', () => {
    expect(hasAnyFilterUrlParam(sp({ item_type: 'ebook' }))).toBe(true)
    expect(hasAnyFilterUrlParam(sp({ is_new: 'true' }))).toBe(true)
    expect(hasAnyFilterUrlParam(sp({ q: 'cats' }))).toBe(true)
    expect(hasAnyFilterUrlParam(sp({ sort: 'title' }))).toBe(true)
    expect(hasAnyFilterUrlParam(sp({ sort_dir: 'asc' }))).toBe(true)
  })

  it('returns false for unrelated keys', () => {
    expect(hasAnyFilterUrlParam(sp({ subject: 'cats' }))).toBe(false)
    expect(hasAnyFilterUrlParam(sp({ saved: '42' }))).toBe(false)
    expect(hasAnyFilterUrlParam(sp({}))).toBe(false)
  })
})

describe('serializeFiltersToUrl', () => {
  it('writes only filters with non-default values and url config', () => {
    const params = new URLSearchParams()
    serializeFiltersToUrl({
      ...EMPTY_FILTERS,
      item_type: 'ebook',
      available_only: true,
      year_min: '2010',
      min_lexile: 500,
      language: 'eng',
      location: 'Adult',
      publisher: 'Penguin',
      // #888: reading_time / access / topic now serialize too.
      topic: 'young_adult',
    }, params)
    expect(Array.from(params.entries()).sort()).toEqual([
      ['available_only', 'true'],
      ['item_type', 'ebook'],
      ['language', 'eng'],
      ['location', 'Adult'],
      ['min_lexile', '500'],
      ['publisher', 'Penguin'],
      ['topic', 'young_adult'],
      ['year_min', '2010'],
    ])
  })

  it('writes item_type under its canonical key (#886)', () => {
    const params = new URLSearchParams()
    serializeFiltersToUrl({ ...EMPTY_FILTERS, item_type: 'audiobook' }, params)
    expect(params.get('item_type')).toBe('audiobook')
    expect(params.has('type')).toBe(false)
  })

  it('omits available_only when false (#887)', () => {
    const a = new URLSearchParams()
    serializeFiltersToUrl({ ...EMPTY_FILTERS, available_only: false }, a)
    expect(a.has('available_only')).toBe(false)

    const b = new URLSearchParams()
    serializeFiltersToUrl({ ...EMPTY_FILTERS, available_only: true }, b)
    expect(b.get('available_only')).toBe('true')
  })

  it('omits null/empty numeric and string fields', () => {
    const params = new URLSearchParams()
    serializeFiltersToUrl(EMPTY_FILTERS, params)
    expect(Array.from(params.entries())).toEqual([])
  })
})

describe('serializeSiblingBoolsToUrl', () => {
  it('writes is_new=true only when showNewArrivals is true', () => {
    const params = new URLSearchParams()
    serializeSiblingBoolsToUrl({ ...EMPTY_SIBLING_BOOLS, showNewArrivals: true }, params)
    expect(params.get('is_new')).toBe('true')
  })

  it('omits is_new when false', () => {
    const params = new URLSearchParams()
    serializeSiblingBoolsToUrl(EMPTY_SIBLING_BOOLS, params)
    expect(params.has('is_new')).toBe(false)
  })

  it('writes is_large_print=true when showLargePrintOnly is true (#888)', () => {
    const params = new URLSearchParams()
    serializeSiblingBoolsToUrl({ showNewArrivals: false, showLargePrintOnly: true }, params)
    expect(params.get('is_large_print')).toBe('true')
  })

  it('omits is_large_print when false', () => {
    const params = new URLSearchParams()
    serializeSiblingBoolsToUrl(EMPTY_SIBLING_BOOLS, params)
    expect(params.has('is_large_print')).toBe(false)
  })
})

describe('round-trip', () => {
  it('parse(serialize(x)) preserves URL-serializable filters', () => {
    const original: typeof EMPTY_FILTERS = {
      ...EMPTY_FILTERS,
      item_type: 'ebook',
      available_only: true,
      year_min: '2010',
      year_max: '2020',
      language: 'eng',
      min_lexile: 500,
      max_lexile: 1200,
    }
    const params = new URLSearchParams()
    serializeFiltersToUrl(original, params)
    const reparsed = parseFiltersFromUrl(params)
    expect({ ...EMPTY_FILTERS, ...reparsed }).toEqual(original)
  })

  // ---------- string-array (multi-select facets) ----------
  //
  // Pre-fix, ``useCatalogSearch`` wrote ``subject_facets`` / ``author_facets``
  // / ``series_facets`` to the URL as repeated params but the codec never
  // parsed them back, so a reload or deep-link share silently emptied the
  // chip set even though the URL still carried the values. Slice C added
  // a ``string-array`` value type to the schema and wired ``getAll`` /
  // ``append`` round-tripping through the codec.

  it('parses multi-select subject_facets via repeated params', () => {
    const params = new URLSearchParams()
    params.append('subject_facets', 'Fiction')
    params.append('subject_facets', 'Memoir')
    expect(parseFiltersFromUrl(params)).toEqual({
      subject_facets: ['Fiction', 'Memoir'],
    })
  })

  it('parses author_facets and series_facets independently', () => {
    const params = new URLSearchParams()
    params.append('author_facets', 'Le Guin, Ursula K.')
    params.append('series_facets', 'Earthsea')
    params.append('series_facets', 'Hainish')
    expect(parseFiltersFromUrl(params)).toEqual({
      author_facets: ['Le Guin, Ursula K.'],
      series_facets: ['Earthsea', 'Hainish'],
    })
  })

  it('drops blank facet values', () => {
    const params = new URLSearchParams()
    params.append('subject_facets', '')
    params.append('subject_facets', 'Fiction')
    params.append('subject_facets', '')
    expect(parseFiltersFromUrl(params)).toEqual({
      subject_facets: ['Fiction'],
    })
  })

  it('omits the facet key entirely when no values are present', () => {
    expect(parseFiltersFromUrl(sp({}))).toEqual({})
  })

  it('round-trips a multi-select facet selection through serialize+parse', () => {
    const original: typeof EMPTY_FILTERS = {
      ...EMPTY_FILTERS,
      subject_facets: ['Fiction', 'Memoir', 'History'],
      author_facets: ['Morrison, Toni'],
      series_facets: ['Earthsea', 'Hainish'],
    }
    const params = new URLSearchParams()
    serializeFiltersToUrl(original, params)
    // Confirm the URL really contains repeated params -- not a comma-joined
    // single value -- since OPDS readers, server logs, and shared links all
    // depend on the standard repeated-param shape.
    expect(params.getAll('subject_facets')).toEqual(['Fiction', 'Memoir', 'History'])
    expect(params.getAll('series_facets')).toEqual(['Earthsea', 'Hainish'])
    const reparsed = parseFiltersFromUrl(params)
    expect({ ...EMPTY_FILTERS, ...reparsed }).toEqual(original)
  })

  it('serializing twice does not duplicate facet values', () => {
    const filters: typeof EMPTY_FILTERS = {
      ...EMPTY_FILTERS,
      subject_facets: ['Fiction'],
    }
    const params = new URLSearchParams()
    serializeFiltersToUrl(filters, params)
    serializeFiltersToUrl(filters, params)
    expect(params.getAll('subject_facets')).toEqual(['Fiction'])
  })
})
