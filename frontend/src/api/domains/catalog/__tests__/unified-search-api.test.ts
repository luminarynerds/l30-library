import { describe, it, expect, vi, beforeEach } from 'vitest'
import { unifiedSearch } from '../unified-search-api'

const fetchApi = vi.hoisted(() => vi.fn())
vi.mock('@/lib/api-client', () => ({ fetchApi, isApiError: vi.fn() }))

describe('unifiedSearch fallback behavior', () => {
  beforeEach(() => fetchApi.mockReset())

  it('does not throw or fall back when lexile is requested', async () => {
    fetchApi.mockResolvedValueOnce({ query: 'x', total_results: 0, results: [], sources_searched: ['local'], source_counts: {}, search_time_ms: 1, has_more: false })
    await unifiedSearch({ query: 'x', min_lexile: 500 })
    expect(fetchApi).toHaveBeenCalledTimes(1)
    expect(fetchApi.mock.calls[0]![0]).toContain('/search/unified')
  })

  it('returns zero-result unified response without re-querying /catalog/search', async () => {
    fetchApi.mockResolvedValueOnce({ query: 'x', total_results: 0, results: [], sources_searched: ['local'], source_counts: {}, search_time_ms: 1, has_more: false })
    const res = await unifiedSearch({ query: 'x' })
    expect(fetchApi).toHaveBeenCalledTimes(1)
    expect(res.total_results).toBe(0)
  })

  it('falls back to /catalog/search on a genuine failure', async () => {
    fetchApi.mockRejectedValueOnce(new Error('network'))
    fetchApi.mockResolvedValueOnce({ items: [], total: 0, page: 1, per_page: 20, pages: 0 })
    await unifiedSearch({ query: 'x' })
    expect(fetchApi).toHaveBeenCalledTimes(2)
    expect(fetchApi.mock.calls[1]![0]).toContain('/catalog/search')
  })

  it('forwards language to /search/unified and does not fall back', async () => {
    fetchApi.mockResolvedValueOnce({ query: 'x', total_results: 0, results: [], sources_searched: ['local'], source_counts: {}, search_time_ms: 1, has_more: false })
    await unifiedSearch({ query: 'x', language: ['eng'] })
    expect(fetchApi).toHaveBeenCalledTimes(1)
    const calledUrl = fetchApi.mock.calls[0]![0] as string
    expect(calledUrl).toContain('/search/unified')
    expect(calledUrl).toContain('language=eng')
  })

  it('forwards repeated facets to the primary unified search request', async () => {
    fetchApi.mockResolvedValueOnce({ query: 'x', total_results: 0, results: [], sources_searched: ['local'], source_counts: {}, search_time_ms: 1, has_more: false })
    await unifiedSearch({
      query: 'x',
      subject_facets: ['Fiction', 'Memoir'],
      author_facets: ['Morrison, Toni'],
      series_facets: ['Earthsea', 'Hainish'],
    })

    expect(fetchApi).toHaveBeenCalledTimes(1)
    const calledUrl = new URL(fetchApi.mock.calls[0]![0] as string, 'https://example.test')
    expect(calledUrl.pathname).toBe('/search/unified')
    expect(calledUrl.searchParams.getAll('subject_facets')).toEqual(['Fiction', 'Memoir'])
    expect(calledUrl.searchParams.getAll('author_facets')).toEqual(['Morrison, Toni'])
    expect(calledUrl.searchParams.getAll('series_facets')).toEqual(['Earthsea', 'Hainish'])
  })

  it('forwards page-count bounds to primary and fallback search requests', async () => {
    fetchApi.mockRejectedValueOnce(new Error('network'))
    fetchApi.mockResolvedValueOnce({ items: [], total: 0, page: 1, per_page: 20, pages: 0 })

    await unifiedSearch({ query: 'x', min_pages: 150, max_pages: 299 })

    for (const call of fetchApi.mock.calls) {
      const url = new URL(call[0] as string, 'https://example.test')
      expect(url.searchParams.get('min_pages')).toBe('150')
      expect(url.searchParams.get('max_pages')).toBe('299')
    }
  })
})
