/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, expect, it } from 'vitest'
import {
  getCatalogResultWindow,
  getInitialLargePrintOnly,
  getSemanticFilterInput,
  getSelectedFacetInput,
  hasClientPostFilters,
} from '@/pages/catalog/hooks/useCatalogSearch'
import { EMPTY_FILTERS } from '@/pages/catalog/utils/catalogFilters'

describe('useCatalogSearch correctness helpers', () => {
  it('forwards selected subject, author, and series facets', () => {
    expect(getSelectedFacetInput({
      ...EMPTY_FILTERS,
      subject_facets: ['Fiction', 'Memoir'],
      author_facets: ['Morrison, Toni'],
      series_facets: ['Earthsea'],
    })).toEqual({
      subject_facets: ['Fiction', 'Memoir'],
      author_facets: ['Morrison, Toni'],
      series_facets: ['Earthsea'],
    })
  })

  it('omits empty facet arrays from the API input', () => {
    expect(getSelectedFacetInput(EMPTY_FILTERS)).toEqual({
      subject_facets: undefined,
      author_facets: undefined,
      series_facets: undefined,
    })
  })

  it('hydrates the large-print toggle from a shared URL', () => {
    expect(getInitialLargePrintOnly(new URLSearchParams('is_large_print=true'))).toBe(true)
    expect(getInitialLargePrintOnly(new URLSearchParams())).toBe(false)
  })

  it('maps reading-time and topic filters to authoritative backend inputs', () => {
    expect(getSemanticFilterInput({
      ...EMPTY_FILTERS,
      reading_time: '2_to_4h',
      topic: 'scifi',
    })).toEqual({ min_pages: 150, max_pages: 299, subject_facets: ['Science Fiction'] })
  })

  it('maps supported access filters and does not treat them as client-only', () => {
    expect(getSemanticFilterInput({ ...EMPTY_FILTERS, access: 'short_gentle' }))
      .toEqual({ min_pages: undefined, max_pages: 200, subject_facets: undefined })
    expect(hasClientPostFilters({ ...EMPTY_FILTERS, access: 'short_gentle' })).toBe(false)
  })

  it('preserves normal backend pagination without client-side filters', () => {
    expect(hasClientPostFilters(EMPTY_FILTERS)).toBe(false)
    expect(getCatalogResultWindow(false, true, 4)).toEqual({ limit: 20, offset: 60 })
    expect(getCatalogResultWindow(false, false, 4)).toEqual({ limit: 100, offset: 0 })
  })
})
