/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { fetchApi, isApiError } from '@/lib/api-client'
import type { SearchFacets } from '@/api/domains/catalog/catalog-api'

/**
 * Empty facets payload mirroring the deployed backend shape. Returned when
 * the parallel facets fetch fails so the main search still renders.
 */
export const EMPTY_FACETS: SearchFacets = {
  item_type: [],
  status: [],
  publication_year: [],
  location: [],
  subject: [],
  author: [],
  series: [],
}

// ==================== Unified Search Types ====================

export type ContentSource = 'local' | 'palace' | 'indie'

export type ContentFormat =
  | 'book'
  | 'ebook'
  | 'audiobook'
  | 'dvd'
  | 'bluray'
  | 'cd'
  | 'vinyl'
  | 'magazine'
  | 'game'
  | 'equipment'
  | 'kit'
  | 'tool'
  | 'video_streaming'
  | 'music'

export interface RelatedSourceInfo {
  source: string
  source_id: string
  format: string
  is_available: boolean
  formats_available: string[]
}

export interface UnifiedSearchResult {
  id: string
  source: string
  source_id: string
  title: string
  author: string | null
  authors: string[]
  format: string
  format_details: string[]
  description: string | null
  cover_url: string | null
  isbn: string | null
  publisher: string | null
  publication_year: number | null
  subjects: string[]
  language: string | null
  is_available: boolean
  copies_available: number | null
  copies_total: number | null
  hold_count: number | null
  estimated_wait_days: number | null
  download_formats: string[]
  relevance_score: number
  related_sources: RelatedSourceInfo[]
}

export interface UnifiedSearchResponse {
  query: string
  total_results: number
  results: UnifiedSearchResult[]
  sources_searched: string[]
  source_counts: Record<string, number>
  search_time_ms: number
  has_more: boolean
  /**
   * True when the user's query consisted entirely of English FTS stopwords
   * (the, of, and, ...). The backend falls through to an unfiltered browse
   * in this case; the UI should show a banner explaining the query was
   * ignored rather than silently surfacing the broader result set.
   *
   * Only populated by the /catalog/search fallback path -- the unified
   * search endpoint does not currently emit this flag, so callers should
   * treat undefined as false.
   */
  query_was_all_stopwords?: boolean
}

export interface QuickSearchSuggestion {
  id: string
  title: string
  author: string | null
  format: string
  source: string
  is_available: boolean
  cover_url: string | null
}

export interface QuickSearchResponse {
  query: string
  suggestions: QuickSearchSuggestion[]
}

export interface SearchSourceInfo {
  id: string
  name: string
  description: string
  enabled: boolean
}

export interface SearchFormatInfo {
  id: string
  name: string
}

export interface AvailableSourcesResponse {
  sources: SearchSourceInfo[]
  formats: SearchFormatInfo[]
}

export interface UnifiedItemDetailsResponse {
  item: UnifiedSearchResult
  availability_summary: {
    any_available: boolean
    sources_with_item: string[]
  }
}

export interface UnifiedSearchParams {
  query: string
  sources?: ContentSource[]
  formats?: ContentFormat[]
  available_only?: boolean
  deduplicate?: boolean
  year_min?: number
  year_max?: number
  limit?: number
  offset?: number
  sort_by?: string
  sort_direction?: string
  min_lexile?: number | null
  max_lexile?: number | null
  min_pages?: number
  max_pages?: number
  // ISO 639-2/B codes (eng, spa, fre, ...). year/lexile/language are all
  // forwarded to /search/unified, which now honors them (local via BIBFRAME;
  // indie dropped when lexile/language is set).
  language?: string[]
  /** Drops indie source (large-print is a physical-book property). */
  is_large_print?: boolean
  /**
   * #889: Filter by holdability. When true, returns only items where placing a
   * hold is meaningful (i.e. not lost/withdrawn/missing/reference/restricted).
   * Forwarded to /catalog/search; the /search/unified endpoint passes it
   * through to the local source while indie/digital sources are inherently
   * holdable.
   */
  available_for_hold?: boolean
  /** Free-text publisher contains-match (local source only). */
  publisher?: string
  /** Free-text location/shelf contains-match (local source only). */
  location?: string
  /** Sidebar subject facets (local source only). Exact-label match; AND-joined across facets; capped at 20. */
  subject_facets?: string[]
  /** Sidebar author facets (local source only). Exact-match; capped at 20. */
  author_facets?: string[]
  /** Sidebar series facets (local source only). Exact-match; capped at 20. */
  series_facets?: string[]
}

export interface QuickSearchParams {
  query: string
  limit?: number
}

// ==================== Unified Search Functions ====================

export async function unifiedSearch(
  params: UnifiedSearchParams
): Promise<UnifiedSearchResponse> {
  const urlParams = new URLSearchParams()

  urlParams.set('q', params.query)

  if (params.sources && params.sources.length > 0) {
    urlParams.set('sources', params.sources.join(','))
  }

  if (params.formats && params.formats.length > 0) {
    urlParams.set('formats', params.formats.join(','))
  }

  if (params.available_only !== undefined) {
    urlParams.set('available_only', String(params.available_only))
  }

  if (params.deduplicate !== undefined) {
    urlParams.set('deduplicate', String(params.deduplicate))
  }

  if (params.limit !== undefined) {
    urlParams.set('limit', String(params.limit))
  }

  if (params.offset !== undefined) {
    urlParams.set('offset', String(params.offset))
  }

  if (params.year_min !== undefined) {
    urlParams.set('year_min', String(params.year_min))
  }

  if (params.year_max !== undefined) {
    urlParams.set('year_max', String(params.year_max))
  }

  if (params.min_lexile != null) {
    urlParams.set('min_lexile', String(params.min_lexile))
  }

  if (params.max_lexile != null) {
    urlParams.set('max_lexile', String(params.max_lexile))
  }
  if (params.min_pages !== undefined) urlParams.set('min_pages', String(params.min_pages))
  if (params.max_pages !== undefined) urlParams.set('max_pages', String(params.max_pages))

  if (params.language && params.language.length > 0) {
    // FastAPI list[str] query param: repeat the key
    for (const code of params.language) urlParams.append('language', code)
  }

  if (params.is_large_print !== undefined) {
    urlParams.set('is_large_print', String(params.is_large_print))
  }

  // #889: forward holdability filter when set.
  if (params.available_for_hold !== undefined) {
    urlParams.set('available_for_hold', String(params.available_for_hold))
  }

  if (params.publisher) urlParams.set('publisher', params.publisher)
  if (params.location) urlParams.set('location', params.location)
  if (params.subject_facets && params.subject_facets.length > 0) {
    for (const value of params.subject_facets) urlParams.append('subject_facets', value)
  }
  if (params.author_facets && params.author_facets.length > 0) {
    for (const value of params.author_facets) urlParams.append('author_facets', value)
  }
  if (params.series_facets && params.series_facets.length > 0) {
    for (const value of params.series_facets) urlParams.append('series_facets', value)
  }

  // Sort params are local-source only (indie returns relevance-ordered).
  // /search/unified ignores them when sources includes indie + multi-merge.
  if (params.sort_by) urlParams.set('sort_by', params.sort_by)
  if (params.sort_direction) urlParams.set('sort_direction', params.sort_direction)

  try {
    // /search/unified now honors year/lexile/language. A successful call is
    // authoritative, including a zero-result response (drop-source can
    // legitimately empty a source). /catalog/search remains only as an
    // outage resilience net in the catch below.
    return await fetchApi<UnifiedSearchResponse>(`/search/unified?${urlParams}`)
  } catch {
    // Unified search endpoint unavailable — fall back to catalog
  }

  // Fallback to /catalog endpoint
    const fallbackParams = new URLSearchParams()
    if (params.query && params.query !== '*') fallbackParams.set('q', params.query)
    if (params.limit !== undefined) fallbackParams.set('per_page', String(params.limit))
    if (params.offset !== undefined) {
      const page = Math.floor((params.offset) / (params.limit || 20)) + 1
      fallbackParams.set('page', String(page))
    }
    if (params.formats && params.formats.length > 0) fallbackParams.set('item_type', params.formats[0]!)
    if (params.available_only) fallbackParams.set('status', 'available')
    if (params.available_for_hold !== undefined) {
      fallbackParams.set('available_for_hold', String(params.available_for_hold))
    }
    if (params.year_min !== undefined) fallbackParams.set('year_min', String(params.year_min))
    if (params.year_max !== undefined) fallbackParams.set('year_max', String(params.year_max))
    if (params.min_lexile != null) fallbackParams.set('min_lexile', String(params.min_lexile))
    if (params.max_lexile != null) fallbackParams.set('max_lexile', String(params.max_lexile))
    if (params.min_pages !== undefined) fallbackParams.set('min_pages', String(params.min_pages))
    if (params.max_pages !== undefined) fallbackParams.set('max_pages', String(params.max_pages))
    if (params.language && params.language.length > 0) {
      // FastAPI list[str] query param: repeat the key
      for (const code of params.language) fallbackParams.append('language', code)
    }
    if (params.sort_by !== undefined) fallbackParams.set('sort_by', params.sort_by)
    if (params.sort_direction !== undefined) fallbackParams.set('sort_direction', params.sort_direction)
    if (params.subject_facets && params.subject_facets.length > 0) {
      for (const v of params.subject_facets) {
        fallbackParams.append('subject_facets', v)
      }
    }

    if (params.author_facets && params.author_facets.length > 0) {
      for (const v of params.author_facets) {
        fallbackParams.append('author_facets', v)
      }
    }

    if (params.series_facets && params.series_facets.length > 0) {
      for (const v of params.series_facets) {
        fallbackParams.append('series_facets', v)
      }
    }

    const qs = fallbackParams.toString()
    const catalogResponse = await fetchApi<{
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      items: Array<Record<string, any>>
      total: number
      page: number
      per_page: number
      pages: number
      query_was_all_stopwords?: boolean
    }>(`/catalog/search${qs ? `?${qs}` : ''}`)

    const results: UnifiedSearchResult[] = catalogResponse.items.map((item) => ({
      id: String(item.id),
      source: 'local',
      source_id: String(item.id),
      title: item.title || '',
      author: item.author || null,
      authors: item.author ? [item.author] : [],
      format: item.item_type || 'book',
      format_details: [],
      description: item.description || null,
      cover_url: item.cover_url || null,
      isbn: item.isbn || null,
      publisher: item.publisher || null,
      publication_year: item.publication_year || null,
      subjects: item.subjects ? item.subjects.split(',').map((s: string) => s.trim()) : [],
      language: null,
      is_available: item.status === 'available',
      copies_available: null,
      copies_total: null,
      hold_count: null,
      estimated_wait_days: null,
      download_formats: [],
      relevance_score: 1,
      related_sources: [],
    }))

    return {
      query: params.query,
      total_results: catalogResponse.total,
      results,
      sources_searched: ['local'],
      source_counts: { local: catalogResponse.total },
      search_time_ms: 0,
      has_more: catalogResponse.page < catalogResponse.pages,
      query_was_all_stopwords: catalogResponse.query_was_all_stopwords ?? false,
    }
}


export async function fetchCatalogFacets(
  params: UnifiedSearchParams
): Promise<SearchFacets> {
  const qp = new URLSearchParams()

  qp.set('include_facets', 'true')
  qp.set('per_page', '1')

  if (params.query && params.query !== '*') {
    qp.set('q', params.query)
  }

  // Map UnifiedSearch formats → catalog item_type. /catalog/search accepts
  // a single item_type; mirror unifiedSearch's first-format mapping.
  if (params.formats && params.formats.length > 0) {
    qp.set('item_type', params.formats[0]!)
  }

  if (params.available_only) {
    qp.set('status', 'available')
  }

  if (params.year_min !== undefined) {
    qp.set('year_min', String(params.year_min))
  }
  if (params.year_max !== undefined) {
    qp.set('year_max', String(params.year_max))
  }

  if (params.min_lexile != null) {
    qp.set('min_lexile', String(params.min_lexile))
  }
  if (params.max_lexile != null) {
    qp.set('max_lexile', String(params.max_lexile))
  }
  if (params.min_pages !== undefined) qp.set('min_pages', String(params.min_pages))
  if (params.max_pages !== undefined) qp.set('max_pages', String(params.max_pages))

  if (params.subject_facets && params.subject_facets.length > 0) {
    for (const v of params.subject_facets) {
      qp.append('subject_facets', v)
    }
  }

  if (params.author_facets && params.author_facets.length > 0) {
    for (const v of params.author_facets) {
      qp.append('author_facets', v)
    }
  }

  if (params.series_facets && params.series_facets.length > 0) {
    for (const v of params.series_facets) {
      qp.append('series_facets', v)
    }
  }

  const response = await fetchApi<{
    facets?: SearchFacets
  }>(`/catalog/search?${qp}`)

  return response.facets ?? EMPTY_FACETS
}


export async function getAvailableSources(): Promise<AvailableSourcesResponse> {
  try {
    return await fetchApi<AvailableSourcesResponse>('/search/unified/sources')
  } catch {
    // Return default empty response on error
    return {
      sources: [],
      formats: [],
    }
  }
}

export async function quickSearch(
  params: QuickSearchParams
): Promise<QuickSearchResponse> {
  const urlParams = new URLSearchParams()

  urlParams.set('q', params.query)

  if (params.limit !== undefined) {
    urlParams.set('limit', String(params.limit))
  }

  // Skip unified search for browse-all queries — catalog handles these better
  if (params.query === "*") {
    return {
      query: params.query,
      suggestions: [],
    }
  }

  try {
    return await fetchApi<QuickSearchResponse>(`/search/unified/quick?${urlParams}`)
  } catch {
    // Return empty suggestions on error
    return {
      query: params.query,
      suggestions: [],
    }
  }
}

export async function getUnifiedItemDetails(
  source: ContentSource,
  sourceId: string
): Promise<UnifiedItemDetailsResponse | null> {
  try {
    return await fetchApi<UnifiedItemDetailsResponse>(
      `/search/unified/item/${encodeURIComponent(source)}/${encodeURIComponent(sourceId)}`
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      if (error.status === 404) {
        return null
      }
      throw new Error(error.detail || 'Failed to get item details')
    }
    return null
  }
}

// ==================== Helper Functions ====================

export function getSourceLabel(source: ContentSource | string): string {
  const labels: Record<string, string> = {
    local: 'Physical Catalog',
    palace: 'Palace Project',
    indie: 'eBooks',
  }
  return labels[source] || source
}

export function getFormatLabel(format: ContentFormat | string): string {
  const labels: Record<string, string> = {
    book: 'Physical Book',
    ebook: 'eBook',
    audiobook: 'Audiobook',
    dvd: 'DVD',
    bluray: 'Blu-ray',
    cd: 'CD',
    vinyl: 'Vinyl',
    magazine: 'Magazine',
    game: 'Game',
    equipment: 'Equipment',
    kit: 'Kit',
    tool: 'Tool',
    video_streaming: 'Streaming Video',
    music: 'Music',
  }
  return labels[format] || format
}

export function getSearchResultAvailability(result: UnifiedSearchResult): {
  text: string
  variant: 'success' | 'warning' | 'error'
} {
  if (result.is_available) {
    if (result.copies_available !== null && result.copies_available > 0) {
      return {
        text: `${result.copies_available} available`,
        variant: 'success',
      }
    }
    return { text: 'Available', variant: 'success' }
  }

  if (result.hold_count !== null && result.hold_count > 0) {
    if (result.estimated_wait_days !== null) {
      return {
        text: `~${result.estimated_wait_days} day wait`,
        variant: 'warning',
      }
    }
    return {
      text: `${result.hold_count} holds`,
      variant: 'warning',
    }
  }

  return { text: 'Unavailable', variant: 'error' }
}

export function hasMultipleSources(result: UnifiedSearchResult): boolean {
  return result.related_sources.length > 0
}

export function getAvailableSourcesToList(result: UnifiedSearchResult): string[] {
  const sources: string[] = []

  if (result.is_available) {
    sources.push(result.source)
  }

  for (const related of result.related_sources) {
    if (related.is_available) {
      sources.push(related.source)
    }
  }

  return sources
}
