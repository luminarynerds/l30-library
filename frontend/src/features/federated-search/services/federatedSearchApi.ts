/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Federated Search API Service
 *
 * Handles communication with the federated search backend API.
 * Provides methods for executing searches, managing sources, and handling caching.
 */

import { fetchApi, isApiError } from '@/lib/api-client'
import type {
  FederatedSearchQuery,
  FederatedSearchResponse,
  SearchSourceConfig,
  SearchSource,
  FederatedSearchError,
} from '../types/federated-search.types'

// ==================== Constants ====================

const API_BASE_PATH = '/federated-search'
const REQUEST_TIMEOUT = 30000 // 30 seconds

let searchAbortController: AbortController | null = null

// ==================== Types ====================

// Shape returned by backend to_dict()
interface BackendSearchResponse {
  ok: boolean
  results: FederatedSearchResponse['results']
  total_results: number
  sources_queried: number
  sources_succeeded: number
  source_statuses: { source_id: string; source_name: string; status: string; result_count: number; elapsed_ms: number }[]
  deduplicated_count: number
  elapsed_ms: number
}

function normalizeResponse(raw: BackendSearchResponse, query: FederatedSearchQuery): FederatedSearchResponse {
  // Pass through whatever source ids the backend actually returns — no hardcoded allowlist
  const queriedSources = raw.source_statuses.map(s => s.source_id as SearchSource)

  return {
    results: raw.results,
    total: raw.total_results,
    page: query.page ?? 1,
    perPage: query.perPage ?? 20,
    pages: Math.ceil(raw.total_results / (query.perPage ?? 20)),
    query: query.q,
    queriedSources,
    sourcesWithResults: raw.sources_succeeded,
    searchedAt: new Date().toISOString(),
    executionTimeMs: raw.elapsed_ms,
  }
}

// ==================== API Methods ====================

export async function executeFederatedSearch(
  query: FederatedSearchQuery,
  token?: string
): Promise<FederatedSearchResponse> {
  try {
    // Cancel any previous search
    if (searchAbortController) {
      searchAbortController.abort()
    }

    searchAbortController = new AbortController()
    const { signal } = searchAbortController
    const timeout = query.timeout || REQUEST_TIMEOUT

    // Build query params for the POST — backend reads these from Query() not body
    const params: Record<string, unknown> = {
      q: query.q,
      max_results: query.perPage ?? 20,
      include_local: true,
    }
    if (query.sources && query.sources.length > 0) {
      params.sources = query.sources.join(',')
    }

    const raw = await Promise.race([
      fetchApi<BackendSearchResponse>(`${API_BASE_PATH}/search`, {
        method: 'POST',
        params,
        ...(token ? { token } : {}),
        signal,
      }),
      new Promise<never>((_, reject) =>
        setTimeout(
          () => reject(createFederatedSearchError('timeout', 'Search request timed out')),
          timeout
        )
      ),
    ])

    return normalizeResponse(raw, query)
  } catch (error: unknown) {
    if (error instanceof Error && error.message === 'AbortError') {
      throw createFederatedSearchError('timeout', 'Search was cancelled')
    }

    if (isApiError(error)) {
      if (error.status === 400) {
        throw createFederatedSearchError('invalid-query', error.detail || 'Invalid search query')
      }
      if (error.status === 403) {
        throw createFederatedSearchError('permission-denied', 'You do not have permission to search these sources')
      }
      if (error.status >= 500) {
        throw createFederatedSearchError('network', 'Search service is temporarily unavailable')
      }
    }

    throw createFederatedSearchError('unknown', 'An unexpected error occurred during search')
  }
}

export async function getAvailableSources(token?: string): Promise<SearchSourceConfig[]> {
  try {
    return await fetchApi<SearchSourceConfig[]>(`${API_BASE_PATH}/sources`, token ? { token } : {})
  } catch (error: unknown) {
    if (isApiError(error) && error.status === 404) {
      return getDefaultSources()
    }
    throw createFederatedSearchError('network', 'Failed to fetch available sources')
  }
}

export async function getSourceConfig(source: SearchSource, token?: string): Promise<SearchSourceConfig> {
  try {
    return await fetchApi<SearchSourceConfig>(`${API_BASE_PATH}/sources/${source}`, token ? { token } : {})
  } catch (_error: unknown) {
    throw createFederatedSearchError('network', `Failed to fetch configuration for source: ${source}`)
  }
}

export async function testSourceHealth(
  source: SearchSource,
  token?: string
): Promise<{ source: SearchSource; status: 'healthy' | 'degraded' | 'unhealthy'; responseTimeMs: number }> {
  try {
    const start = performance.now()
    await fetchApi(`${API_BASE_PATH}/sources/${source}/health`, token ? { token } : {})
    const responseTimeMs = Math.round(performance.now() - start)

    return { source, status: 'healthy', responseTimeMs }
  } catch (_error: unknown) {
    return { source, status: 'unhealthy', responseTimeMs: REQUEST_TIMEOUT }
  }
}

export async function getPopularSearches(limit = 10, token?: string): Promise<string[]> {
  try {
    const result = await fetchApi<{ searches: string[] }>(
      `${API_BASE_PATH}/popular?limit=${limit}`, token ? { token } : {})
    return result.searches
  } catch (_error: unknown) {
    return []
  }
}

export async function getSearchSuggestions(
  partial: string,
  sources?: SearchSource[],
  token?: string
): Promise<string[]> {
  try {
    const params = new URLSearchParams()
    params.set('q', partial)
    if (sources && sources.length > 0) {
      params.set('sources', sources.join(','))
    }

    const result = await fetchApi<{ suggestions: string[] }>(
      `${API_BASE_PATH}/suggestions?${params}`, token ? { token } : {})
    return result.suggestions
  } catch (_error: unknown) {
    return []
  }
}

export async function getSearchFilters(
  sources: SearchSource[],
  token?: string
): Promise<{
  years: { min: number; max: number }
  itemTypes: { value: string; label: string; count: number }[]
  languages: { value: string; label: string; count: number }[]
}> {
  try {
    const params = new URLSearchParams()
    if (sources.length > 0) {
      params.set('sources', sources.join(','))
    }

    return await fetchApi(
      `${API_BASE_PATH}/filters?${params}`, token ? { token } : {})
  } catch (_error: unknown) {
    return {
      years: { min: 1900, max: new Date().getFullYear() },
      itemTypes: [],
      languages: [],
    }
  }
}

export function cancelCurrentSearch(): void {
  if (searchAbortController) {
    searchAbortController.abort()
    searchAbortController = null
  }
}

// ==================== Utility Functions ====================

function createFederatedSearchError(
  code: FederatedSearchError['code'],
  message: string,
  details?: Record<string, unknown>
): FederatedSearchError {
  return { code, message, ...(details !== undefined ? { details } : {}) }
}

function getDefaultSources(): SearchSourceConfig[] {
  return [
    {
      id: 'local-catalog',
      name: 'Local Catalog',
      description: 'Search your library catalog',
      icon: 'database',
      enabled: true,
      requiresAuth: false,
      averageConfidence: 95,
      estimatedResponseTime: 200,
    },
    {
      id: 'open-library',
      name: 'Open Library',
      description: 'Open Library (community-maintained catalog)',
      icon: 'globe',
      enabled: true,
      requiresAuth: false,
      averageConfidence: 85,
      estimatedResponseTime: 1000,
    },
    {
      id: 'google-books',
      name: 'Google Books',
      description: 'Google Books metadata and previews',
      icon: 'book',
      enabled: true,
      requiresAuth: false,
      averageConfidence: 90,
      estimatedResponseTime: 800,
    },
    {
      id: 'worldcat',
      name: 'WorldCat',
      description: 'WorldCat library federation',
      icon: 'network',
      enabled: false,
      requiresAuth: true,
      averageConfidence: 92,
      estimatedResponseTime: 2000,
    },
    {
      id: 'isbn-search',
      name: 'ISBN Search',
      description: 'ISBN-based search and metadata',
      icon: 'barcode',
      enabled: false,
      requiresAuth: false,
      averageConfidence: 98,
      estimatedResponseTime: 500,
    },
  ]
}

// ==================== Type Exports ====================

export type { FederatedSearchQuery, FederatedSearchResponse, SearchSourceConfig, SearchSource }