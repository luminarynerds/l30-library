/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { fetchApi, isApiError } from '@/lib/api-client'

// ==================== BIBFRAME Types ====================

export interface BibframeWork {
  id: number
  title: string
  subtitle: string | null
  summary: string | null
  genre_form: string | null
  language: string | null
  origin_date: string | null
  dewey_classification: string | null
  lc_classification: string | null
  series_title: string | null
  series_number: string | null
  /** Number of Instances (editions/formats) linked to this Work */
  instance_count?: number
  /** Total number of physical/digital Items linked to this Work */
  item_count?: number
}

export interface BibframeInstance {
  id: number
  title: string | null
  instance_type: string | null
  carrier_type: string | null
  media_type: string | null
  publisher: string | null
  publication_date: string | null
  isbn_13: string | null
  isbn_10: string | null
  items: BibframeItemRecord[]
}

export interface BibframeItemRecord {
  id: number
  barcode: string | null
  call_number: string | null
  library_branch: string | null
  circulation_status: string | null
}

export interface BibframeWorkDetail extends BibframeWork {
  instances: BibframeInstance[]
}

// ==================== Search / List Types ====================

export interface BibframeSearchParams {
  q?: string
  title?: string
  author?: string
  subject?: string
  genre?: string
  language?: string
  publication_year?: number
  year_min?: number
  year_max?: number
  sort_by?: 'relevance' | 'title' | 'author' | 'year'
  sort_direction?: 'asc' | 'desc'
  page?: number
  per_page?: number
}

export interface BibframeSearchResult {
  items: BibframeWork[]
  total: number
  page: number
  per_page: number
  pages: number
}

// ==================== API Functions ====================

const BASE = '/bibframe-catalog'

export async function searchBibframeCatalog(
  params: BibframeSearchParams = {}
): Promise<BibframeSearchResult> {
  const urlParams = new URLSearchParams()

  if (params.q) urlParams.set('q', params.q)
  if (params.title) urlParams.set('title', params.title)
  if (params.author) urlParams.set('author', params.author)
  if (params.subject) urlParams.set('subject', params.subject)
  if (params.genre) urlParams.set('genre', params.genre)
  if (params.language) urlParams.set('language', params.language)
  if (params.publication_year != null) urlParams.set('publication_year', params.publication_year.toString())
  if (params.year_min != null) urlParams.set('year_min', params.year_min.toString())
  if (params.year_max != null) urlParams.set('year_max', params.year_max.toString())
  if (params.sort_by) urlParams.set('sort_by', params.sort_by)
  if (params.sort_direction) urlParams.set('sort_direction', params.sort_direction)
  if (params.page) urlParams.set('page', params.page.toString())
  if (params.per_page) urlParams.set('per_page', params.per_page.toString())

  const qs = urlParams.toString()
  try {
    return await fetchApi<BibframeSearchResult>(`${BASE}/search${qs ? '?' + qs : ''}`)
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to search BIBFRAME catalog')
    }
    throw new Error('Failed to search BIBFRAME catalog')
  }
}

export async function listBibframeWorks(
  page: number = 1,
  perPage: number = 20
): Promise<BibframeSearchResult> {
  const urlParams = new URLSearchParams()
  urlParams.set('page', page.toString())
  urlParams.set('per_page', perPage.toString())

  try {
    return await fetchApi<BibframeSearchResult>(`${BASE}/?${urlParams.toString()}`)
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to list BIBFRAME works')
    }
    throw new Error('Failed to list BIBFRAME works')
  }
}

export async function getBibframeWork(workId: number): Promise<BibframeWorkDetail> {
  try {
    return await fetchApi<BibframeWorkDetail>(`${BASE}/${workId}`)
  } catch (error: unknown) {
    if (isApiError(error)) {
      if (error.status === 404) throw new Error('Work not found')
      throw new Error(error.detail || 'Failed to fetch BIBFRAME work')
    }
    throw new Error('Failed to fetch BIBFRAME work')
  }
}
