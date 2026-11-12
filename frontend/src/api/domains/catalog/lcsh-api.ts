/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * LCSH (Library of Congress Subject Headings) API Service
 *
 * Provides access to controlled vocabulary subject headings for cataloging.
 * Staff-only endpoints for autocomplete, validation, and browsing of LCSH terms.
 */

import { fetchApi, isApiError } from '@/lib/api-client'
import { getAccessToken } from '../../../utils/tokenStore'

// ==================== Types ====================

export interface LcshSuggestion {
  heading: string
  uri?: string
  broader_term?: string
  narrower_terms?: string[]
  related_terms?: string[]
  scope_note?: string
}

export interface LcshAutocompleteResponse {
  ok: boolean
  query: string
  count: number
  suggestions: string[]
}

export interface LcshValidateResponse {
  ok: boolean
  subject: string
  is_valid: boolean
  suggestions?: string[]
}

export interface LcshBrowseResponse {
  ok: boolean
  prefix: string | null
  count: number
  subjects: string[]
}

export interface LcshAutocompleteParams {
  q: string
  limit?: number
}

export interface LcshBrowseParams {
  prefix?: string
  limit?: number
}

// ==================== API Functions ====================

const BASE_PATH = '/cataloging/subjects'

export async function autocompleteLcshSubjects(
  params: LcshAutocompleteParams
): Promise<LcshAutocompleteResponse> {
  const token = getAccessToken()
  const searchParams = new URLSearchParams()

  searchParams.set('q', params.q)
  if (params.limit !== undefined) {
    searchParams.set('limit', params.limit.toString())
  }

  try {
    return await fetchApi<LcshAutocompleteResponse>(
      `${BASE_PATH}/autocomplete?${searchParams}`,
      { ...(token ? { token } : {}) }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      if (error.status === 403) {
        throw new Error('Staff or admin role required for cataloging')
      }
      if (error.status === 422) {
        throw new Error('Search query must be at least 1 character')
      }
      throw new Error(error.detail || 'Failed to autocomplete subject headings')
    }
    throw error
  }
}

export async function validateLcshSubject(
  subject: string
): Promise<LcshValidateResponse> {
  const token = getAccessToken()
  const searchParams = new URLSearchParams()
  searchParams.set('subject', subject)

  try {
    return await fetchApi<LcshValidateResponse>(
      `${BASE_PATH}/validate?${searchParams}`,
      { ...(token ? { token } : {}) }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      if (error.status === 403) {
        throw new Error('Staff or admin role required for cataloging')
      }
      if (error.status === 422) {
        throw new Error('Subject heading must be at least 1 character')
      }
      throw new Error(error.detail || 'Failed to validate subject heading')
    }
    throw error
  }
}

export async function browseLcshSubjects(
  params: LcshBrowseParams = {}
): Promise<LcshBrowseResponse> {
  const token = getAccessToken()
  const searchParams = new URLSearchParams()

  if (params.prefix) {
    searchParams.set('prefix', params.prefix)
  }
  if (params.limit !== undefined) {
    searchParams.set('limit', params.limit.toString())
  }

  const query = searchParams.toString() ? `?${searchParams}` : ''

  try {
    return await fetchApi<LcshBrowseResponse>(
      `${BASE_PATH}/browse${query}`,
      { ...(token ? { token } : {}) }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      if (error.status === 403) {
        throw new Error('Staff or admin role required for cataloging')
      }
      throw new Error(error.detail || 'Failed to browse subject headings')
    }
    throw error
  }
}

// ==================== Utility Functions ====================

export function getLcshUri(heading: string): string {
  // Convert heading to URI-safe format (replace spaces with underscores, etc.)
  const encoded = encodeURIComponent(heading.replace(/\s+/g, '_'))
  return `https://id.loc.gov/authorities/subjects/${encoded}`
}

export function formatLcshHeading(heading: string, scopeNote?: string): string {
  if (scopeNote) {
    return `${heading} (${scopeNote})`
  }
  return heading
}

export function parseLcshSubdivisions(heading: string): {
  mainHeading: string
  subdivisions: string[]
} {
  const parts = heading.split('--').map((part) => part.trim())
  return {
    mainHeading: parts[0] ?? '',
    subdivisions: parts.slice(1),
  }
}

export function buildLcshHeading(
  mainHeading: string,
  subdivisions: string[] = []
): string {
  if (subdivisions.length === 0) {
    return mainHeading
  }
  return [mainHeading, ...subdivisions].join('--')
}
