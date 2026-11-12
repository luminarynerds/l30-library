/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { fetchApi } from '@/lib/api-client'

// ==================== Unified Free Ebooks Types ====================

export type FreeEbookSource =
  | 'gutenberg'
  | 'open_library'
  | 'standard_ebooks'
  | 'librivox'
  | 'feedbooks'
  | 'manybooks'
  | 'all'

export interface UnifiedBookResult {
  source: string
  source_id: string
  title: string
  author: string | null
  cover_url: string | null
  language: string | null
  media_type: 'ebook' | 'audiobook'
  detail_url: string
  formats: string[]
}

export interface UnifiedSearchResponse {
  query: string | null
  total_results: number
  sources_searched: string[]
  sources_failed: string[]
  results: UnifiedBookResult[]
}

export interface FreeEbookSourceInfo {
  name: string
  key: string
  description: string
  cached_count: number
  media_type: 'ebook' | 'audiobook'
  api_prefix: string
}

export interface FreeEbooksOverview {
  sources: FreeEbookSourceInfo[]
  total_cached_books: number
  total_cached_audiobooks: number
}

// ==================== API Functions ====================

export async function searchFreeEbooks(
  token: string | null,
  params: {
    q: string
    sources?: FreeEbookSource
    page?: number
  }
): Promise<UnifiedSearchResponse> {
  const searchParams = new URLSearchParams()
  searchParams.append('q', params.q)
  if (params.sources) searchParams.append('sources', params.sources)
  if (params.page) searchParams.append('page', params.page.toString())

  return fetchApi<UnifiedSearchResponse>(
    `/free-ebooks/search?${searchParams.toString()}`,
    token ? { token } : {}
  )
}

export async function getFreeEbooksOverview(
  token: string | null
): Promise<FreeEbooksOverview> {
  return fetchApi<FreeEbooksOverview>('/free-ebooks/overview', token ? { token } : {})
}

// ==================== Catalog Ingestion ====================

export interface IngestionResult {
  ok: boolean
  message: string
  results: Record<string, { ingested: number; status: string; error?: string }>
}

export interface IngestionStatus {
  sources: Record<
    string,
    { total_cached: number; ingested_to_catalog: number; pending: number }
  >
  total_cached: number
  total_ingested_to_catalog: number
  total_pending: number
}

export async function ingestFreeEbooksToCatalog(
  token: string,
  options?: { sources?: string; limit_per_source?: number }
): Promise<IngestionResult> {
  return fetchApi<IngestionResult>('/free-ebooks/ingest', {
    method: 'POST',
    token,
    body: options || {},
  })
}

export async function getFreeEbooksIngestionStatus(
  token: string
): Promise<IngestionStatus> {
  return fetchApi<IngestionStatus>('/free-ebooks/ingestion-status', { token })
}
