/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { fetchApi } from '@/lib/api-client'

export interface SiteSearchResultItem {
  id: string
  entity_type: 'catalog' | 'ebook' | 'event' | 'announcement' | 'indie_author' | 'page' | string
  title: string
  snippet: string | null
  url: string
  score: number
  source: string
}

export interface SiteSearchResponse {
  query: string
  total_results: number
  results: SiteSearchResultItem[]
  page: number
  per_page: number
  has_more: boolean
  facets?: Record<string, number>
  next_cursor?: string | null
  did_you_mean?: string | null
}

export interface SiteSearchOptions {
  page?: number
  perPage?: number
  cursor?: string | null
  entityTypes?: string[]
}

export async function siteSearch(
  query: string,
  options: SiteSearchOptions | number = {},
  perPageLegacy: number = 20,
): Promise<SiteSearchResponse> {
  // Backwards compat: previously called as siteSearch(query, page, perPage).
  const opts: SiteSearchOptions =
    typeof options === 'number' ? { page: options, perPage: perPageLegacy } : options

  const params = new URLSearchParams()
  params.set('q', query)
  params.set('page', String(opts.page ?? 1))
  params.set('per_page', String(opts.perPage ?? 20))
  if (opts.cursor) params.set('cursor', opts.cursor)
  if (opts.entityTypes && opts.entityTypes.length > 0) {
    params.set('entity_types', opts.entityTypes.join(','))
  }

  return fetchApi<SiteSearchResponse>(`/search?${params.toString()}`)
}

export interface SearchClickEvent {
  query: string
  result_id: string
  entity_type: string
  position: number
}

export async function logSearchClick(event: SearchClickEvent): Promise<void> {
  try {
    await fetchApi<void>('/search/click', {
      method: 'POST',
      body: event,
      skipJsonParse: true,
    })
  } catch {
    // Click logging is best-effort; never block navigation.
  }
}

export interface TrendingQuery {
  query: string
  count: number
  avg_results: number
}

export async function fetchTrendingQueries(limit = 10): Promise<TrendingQuery[]> {
  const params = new URLSearchParams({ limit: String(limit) })
  const data = await fetchApi<{ queries: TrendingQuery[] }>(`/search/trending?${params.toString()}`)
  return data.queries ?? []
}
