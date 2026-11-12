/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Z39.50 Copy Cataloging API Service
 *
 * Provides functions for searching and retrieving MARC records from Z39.50 sources
 * (Library of Congress, OCLC WorldCat) for copy cataloging.
 * All endpoints require STAFF or ADMIN role.
 */

import { fetchApi, isApiError } from '@/lib/api-client'
import { getAccessToken } from '../../../utils/tokenStore'

// ==================== Types ====================

export interface Z3950Source {
  id: string
  name: string
  host: string
  port: number
  database: string
  requires_auth: boolean
  available: boolean
}

export interface Z3950SearchResult {
  title: string | null
  author: string | null
  isbn: string | null
  publisher: string | null
  publication_year: number | null
  description: string | null
  subjects: string[]
  lc_call_number: string | null
  dewey_decimal: string | null
  edition: string | null
  page_count: number | null
  control_number: string | null
  source: string
}

export interface Z3950SearchParams {
  isbn?: string
  title?: string
  author?: string
  source?: 'loc' | 'oclc'
  max_results?: number
}

export interface Z3950SearchResponse {
  ok: boolean
  source: string
  query: {
    isbn: string | null
    title: string | null
    author: string | null
  }
  count: number
  results: Z3950SearchResult[]
  hint?: string
}

export interface Z3950SourcesResponse {
  ok: boolean
  available: boolean
  sources: Z3950Source[]
}

export interface Z3950RecordResponse {
  ok: boolean
  source: string
  control_number: string
  record: Z3950SearchResult
}

// ==================== API Functions ====================

export async function searchZ3950Records(
  params: Z3950SearchParams
): Promise<Z3950SearchResponse> {
  const token = getAccessToken()
  const searchParams = new URLSearchParams()

  if (params.isbn) searchParams.set('isbn', params.isbn)
  if (params.title) searchParams.set('title', params.title)
  if (params.author) searchParams.set('author', params.author)
  if (params.source) searchParams.set('source', params.source)
  if (params.max_results) searchParams.set('max_results', params.max_results.toString())

  const query = searchParams.toString() ? `?${searchParams}` : ''

  try {
    return await fetchApi<Z3950SearchResponse>(`/cataloging/z3950/search${query}`, {
      method: 'POST',
      ...(token ? { token } : {}),
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      if (error.status === 503) {
        throw new Error('Z39.50 service is unavailable. PyZ3950 library may not be installed.')
      }
      if (error.status === 400) {
        throw new Error(error.detail || 'Invalid search parameters. Provide at least one criterion.')
      }
      if (error.status === 403) {
        throw new Error('Staff or admin role required for cataloging')
      }
      throw new Error(error.detail || 'Z39.50 search failed')
    }
    throw error
  }
}

export async function getZ3950Sources(): Promise<Z3950SourcesResponse> {
  const token = getAccessToken()

  try {
    return await fetchApi<Z3950SourcesResponse>('/cataloging/z3950/sources', {
      ...(token ? { token } : {}),
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      if (error.status === 503) {
        throw new Error('Z39.50 service is unavailable')
      }
      if (error.status === 403) {
        throw new Error('Staff or admin role required')
      }
      throw new Error(error.detail || 'Failed to get Z39.50 sources')
    }
    throw error
  }
}

export async function getZ3950RecordByControlNumber(
  controlNumber: string,
  source: 'loc' | 'oclc' = 'loc'
): Promise<Z3950RecordResponse> {
  const token = getAccessToken()
  const searchParams = new URLSearchParams()
  searchParams.set('source', source)

  try {
    return await fetchApi<Z3950RecordResponse>(
      `/cataloging/z3950/record/${encodeURIComponent(controlNumber)}?${searchParams}`,
      { ...(token ? { token } : {}) }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      if (error.status === 404) {
        throw new Error(`Record not found: ${controlNumber}`)
      }
      if (error.status === 503) {
        throw new Error('Z39.50 service is unavailable')
      }
      if (error.status === 400) {
        throw new Error('Invalid source. Use "loc" or "oclc"')
      }
      if (error.status === 403) {
        throw new Error('Staff or admin role required')
      }
      throw new Error(error.detail || 'Failed to retrieve MARC record')
    }
    throw error
  }
}

// ==================== Helper Functions ====================

export function calculateZ3950MatchConfidence(record: Z3950SearchResult): number {
  let score = 0
  const weights = {
    title: 20,
    author: 15,
    isbn: 20,
    publisher: 10,
    publication_year: 10,
    lc_call_number: 10,
    dewey_decimal: 5,
    description: 5,
    subjects: 5,
  }

  if (record.title) score += weights.title
  if (record.author) score += weights.author
  if (record.isbn) score += weights.isbn
  if (record.publisher) score += weights.publisher
  if (record.publication_year) score += weights.publication_year
  if (record.lc_call_number) score += weights.lc_call_number
  if (record.dewey_decimal) score += weights.dewey_decimal
  if (record.description) score += weights.description
  if (record.subjects && record.subjects.length > 0) score += weights.subjects

  return score
}

export function getZ3950MatchQualityLabel(confidence: number): {
  label: string
  color: 'green' | 'yellow' | 'orange' | 'red'
} {
  if (confidence >= 80) {
    return { label: 'Excellent', color: 'green' }
  } else if (confidence >= 60) {
    return { label: 'Good', color: 'yellow' }
  } else if (confidence >= 40) {
    return { label: 'Fair', color: 'orange' }
  } else {
    return { label: 'Minimal', color: 'red' }
  }
}

/**
 * Available Z39.50 sources for UI selection
 */
export const Z3950_SOURCES = [
  { value: 'loc', label: 'Library of Congress', description: 'US national library' },
  { value: 'oclc', label: 'OCLC WorldCat', description: 'Global library catalog (requires auth)' },
] as const

export function formatZ3950SourceName(sourceId: string): string {
  const source = Z3950_SOURCES.find((s) => s.value === sourceId)
  return source?.label || sourceId.toUpperCase()
}
