/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * PostgreSQL Full-Text Search API client.
 *
 * Provides typed API calls for the native Postgres search endpoints:
 * - Full-text search with facets
 * - Search suggestions (trigram similarity)
 * - Health check
 */

import { fetchApi } from '@/lib/api-client'

// ==================== Types ====================

export interface PgSearchParams {
  q: string
  item_type?: string
  status?: string
  available_only?: boolean
  year_min?: number
  year_max?: number
  location?: string
  hybrid?: boolean
  semantic_weight?: number
  page?: number
  per_page?: number
  include_facets?: boolean
}

export interface SearchResultItem {
  id: number | null
  title: string
  author: string | null
  item_type: string | null
  status: string | null
  isbn: string | null
  publisher: string | null
  publication_year: number | null
  description: string | null
  subjects: string | null
  cover_url: string | null
  location: string | null
  is_available: boolean | null
  relevance_score: number
  matched_by: string
  highlight_title: string | null
  highlight_description: string | null
}

export interface SearchFacets {
  item_types: Record<string, number>
  statuses: Record<string, number>
  year_ranges: Record<string, number>
  locations: Record<string, number>
}

export interface PgSearchResponse {
  query: string
  results: SearchResultItem[]
  total_results: number
  facets: SearchFacets
  search_time_ms: number
  search_strategy: string
  page: number
  per_page: number
  has_more: boolean
}

export interface SearchSuggestion {
  id: number | null
  title: string | null
  author: string | null
  item_type: string | null
  cover_url: string | null
  is_available: boolean | null
  similarity: number
  suggestion_type: 'title' | 'author'
  book_count?: number
}

export interface SuggestionsResponse {
  query: string
  suggestions: SearchSuggestion[]
  search_time_ms: number
}

export interface SearchHealthResponse {
  status: string
  search_engine: string
  elasticsearch_enabled: boolean
  postgres_search_ready: boolean
  checks: Record<string, unknown>
  features: Record<string, boolean>
}

// ==================== API Functions ====================

export async function pgSearch(params: PgSearchParams): Promise<PgSearchResponse> {
  const urlParams = new URLSearchParams()

  urlParams.set('q', params.q)
  if (params.item_type) urlParams.set('item_type', params.item_type)
  if (params.status) urlParams.set('status', params.status)
  if (params.available_only) urlParams.set('available_only', 'true')
  if (params.year_min != null) urlParams.set('year_min', params.year_min.toString())
  if (params.year_max != null) urlParams.set('year_max', params.year_max.toString())
  if (params.location) urlParams.set('location', params.location)
  if (params.hybrid) urlParams.set('hybrid', 'true')
  if (params.semantic_weight != null) urlParams.set('semantic_weight', params.semantic_weight.toString())
  if (params.page) urlParams.set('page', params.page.toString())
  if (params.per_page) urlParams.set('per_page', params.per_page.toString())
  if (params.include_facets != null) urlParams.set('include_facets', params.include_facets.toString())

  return fetchApi<PgSearchResponse>(`/search/pg?${urlParams}`)
}

export async function getSearchSuggestions(
  query: string,
  limit: number = 10
): Promise<SuggestionsResponse> {
  const urlParams = new URLSearchParams()
  urlParams.set('q', query)
  urlParams.set('limit', limit.toString())

  return fetchApi<SuggestionsResponse>(`/search/pg/suggestions?${urlParams}`)
}

export async function getSearchHealth(): Promise<SearchHealthResponse> {
  return fetchApi<SearchHealthResponse>('/search/pg/health')
}
