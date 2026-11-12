/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { fetchCatalogFacets, EMPTY_FACETS } from '@/api/domains/catalog/unified-search-api'
import { fetchApi } from '@/lib/api-client'

vi.mock('@/lib/api-client', () => ({
  fetchApi: vi.fn(),
  isApiError: () => false,
}))

describe('fetchCatalogFacets', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('hits /catalog/search with include_facets=true and per_page=1', async () => {
    vi.mocked(fetchApi).mockResolvedValue({
      facets: {
        item_type: [],
        status: [],
        publication_year: [],
        location: [],
        subject: [{ value: 'Fiction', count: 12 }],
      },
    })

    const result = await fetchCatalogFacets({ query: 'cats' })

    expect(fetchApi).toHaveBeenCalledTimes(1)
    const url = vi.mocked(fetchApi).mock.calls[0]![0] as string
    expect(url.startsWith('/catalog/search?')).toBe(true)
    expect(url).toContain('include_facets=true')
    expect(url).toContain('per_page=1')
    expect(url).toContain('q=cats')
    expect(result.subject).toEqual([{ value: 'Fiction', count: 12 }])
  })

  it('omits q for the wildcard browse query', async () => {
    vi.mocked(fetchApi).mockResolvedValue({ facets: EMPTY_FACETS })

    await fetchCatalogFacets({ query: '*' })

    const url = vi.mocked(fetchApi).mock.calls[0]![0] as string
    expect(url).not.toContain('q=')
  })

  it('forwards filters that influence facet counts', async () => {
    vi.mocked(fetchApi).mockResolvedValue({ facets: EMPTY_FACETS })

    await fetchCatalogFacets({
      query: 'space',
      formats: ['book'],
      available_only: true,
      year_min: 2000,
      year_max: 2020,
      min_lexile: 400,
      max_lexile: 800,
      subject_facets: ['Fiction', 'History'],
      author_facets: ['Spiegelman', 'Satrapi'],
      series_facets: ['Maus', 'Persepolis'],
    })

    const url = vi.mocked(fetchApi).mock.calls[0]![0] as string
    expect(url).toContain('item_type=book')
    expect(url).toContain('status=available')
    expect(url).toContain('year_min=2000')
    expect(url).toContain('year_max=2020')
    expect(url).toContain('min_lexile=400')
    expect(url).toContain('max_lexile=800')
    // Repeated params for multi-select subjects
    expect(url).toContain('subject_facets=Fiction')
    expect(url).toContain('subject_facets=History')
    // Repeated params for author + series multi-select
    expect(url).toContain('author_facets=Spiegelman')
    expect(url).toContain('author_facets=Satrapi')
    expect(url).toContain('series_facets=Maus')
    expect(url).toContain('series_facets=Persepolis')
  })

  it('returns EMPTY_FACETS when backend omits facets field', async () => {
    vi.mocked(fetchApi).mockResolvedValue({})

    const result = await fetchCatalogFacets({ query: 'x' })

    expect(result).toEqual(EMPTY_FACETS)
  })

  it('does NOT set available_only when false/undefined', async () => {
    vi.mocked(fetchApi).mockResolvedValue({ facets: EMPTY_FACETS })

    await fetchCatalogFacets({ query: 'x', available_only: false })

    const url = vi.mocked(fetchApi).mock.calls[0]![0] as string
    expect(url).not.toContain('status=available')
  })
})
