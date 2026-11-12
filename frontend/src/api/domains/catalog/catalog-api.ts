/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { fetchApi, isApiError } from '@/lib/api-client'
import { buildQueryString } from '@/lib/api-helpers'
import { getAccessToken } from '../../../utils/tokenStore'
import { API_BASE } from '@/api/types'

// ==================== Catalog Types ====================

// Item types supported by the catalog
export type ItemType =
  | 'book'
  | 'audiobook'
  | 'ebook'
  | 'dvd'
  | 'bluray'
  | 'cd'
  | 'vinyl'
  | 'magazine'
  | 'game'
  | 'equipment'
  | 'kit'
  | 'other'

// Media format for audio/video items
export type MediaFormat =
  | 'dvd'
  | 'bluray'
  | 'cd'
  | 'vinyl_lp'
  | 'vinyl_45'
  | 'cassette'
  | 'vhs'
  | 'laserdisc'
  | 'other'

// Content ratings (MPAA, ESRB, Music)
export type ContentRating =
  | 'G'
  | 'PG'
  | 'PG-13'
  | 'R'
  | 'NC-17'  // MPAA
  | 'E'
  | 'E10+'
  | 'T'
  | 'M'
  | 'AO'     // ESRB
  | 'Explicit'
  | 'Clean'  // Music
  | 'Unrated'
  | 'Not Rated'

// Catalog image attached to an item
export interface CatalogImage {
  id: number
  catalog_item_id: number
  image_url: string
  is_primary: boolean
  caption: string | null
  display_order: number
  file_size: number | null
  content_type: string | null
  uploaded_at: string
  uploaded_by_id: number | null
}

export interface CatalogImageListResponse {
  images: CatalogImage[]
  total: number
}

export interface CatalogImageUploadResponse {
  success: boolean
  message: string
  image: CatalogImage
}

export interface CatalogItem {
  id: number
  title: string
  author: string | null
  item_type: ItemType
  status: string
  isbn: string | null
  publisher: string | null
  publication_year: number | null
  description: string | null
  subjects: string | null
  cover_url: string | null
  page_count: number | null
  location: string | null
  barcode: string | null
  created_at: string | null
  updated_at: string | null
  is_large_print: boolean
  /**
   * UX hint derived server-side from item status. True when placing a hold
   * is meaningful (i.e. not lost/withdrawn/missing/reference/restricted).
   */
  available_for_hold: boolean
  images: CatalogImage[]

  // Catalog metadata
  series_name: string | null
  series_number: string | null
  /**
   * Numeric reading-order position derived server-side from series_number
   * (MARC 490 $v). Null when the freeform enumeration is missing or
   * unparseable. Drives the "Book N in [series]" + prev/next block.
   */
  series_position: number | null
  call_number: string | null
  dewey_decimal: string | null
  total_checkouts: number

  // Multimedia fields - DVD/Blu-ray/Video
  director: string | null
  actors: string | null
  runtime_minutes: number | null
  media_format: MediaFormat | null
  content_rating: ContentRating | null
  disc_count: number | null
  studio: string | null

  // Multimedia fields - CD/Vinyl/Audio
  artist: string | null
  track_count: number | null
  music_genre: string | null

  // Multimedia fields - Games
  platform: string | null
  player_count: string | null
  game_genre: string | null

  // Multimedia fields - Equipment/Kits
  brand: string | null
  model_number: string | null
  dimensions: string | null
  material: string | null
  kit_contents: string | null

  // Additional metadata
  category?: string | null
  language?: string | null
  pages?: number | null
  content_notes?: string | null
  lexile_measure?: string | null
  lexile_number?: number | null

  // Recognition flag — surfaces a "Staff Pick" badge on catalog cards.
  staff_pick?: boolean
}

// ==================== Suggestion Types ====================

export interface SuggestionItem {
  text: string
  type: 'title' | 'author'
  item_id?: number
}

export interface SuggestResponse {
  suggestions: SuggestionItem[]
}

// ==================== Facet Types ====================

export interface FacetValue {
  value: string
  count: number
}

export interface SearchFacets {
  item_type: FacetValue[]
  status: FacetValue[]
  publication_year: FacetValue[]
  location: FacetValue[]
  character?: FacetValue[]
  publisher?: FacetValue[]
  subject?: FacetValue[]
  author?: FacetValue[]
  series?: FacetValue[]
}

export interface CatalogSearchResult {
  items: CatalogItem[]
  total: number
  page: number
  per_page: number
  pages: number
  facets?: SearchFacets
}

export type CatalogSortBy = 'relevance' | 'title' | 'author' | 'year' | 'rating' | 'popularity' | 'recently_added'
export type CatalogSortDirection = 'asc' | 'desc'

export interface CatalogSearchParams {
  query?: string
  item_type?: string
  status?: string
  year_min?: string
  year_max?: string
  location?: string
  is_new?: boolean
  is_large_print?: boolean
  availableForHold?: boolean
  character?: string
  publisher?: string
  page?: number
  per_page?: number
  sort_by?: CatalogSortBy
  sort_direction?: CatalogSortDirection
  include_facets?: boolean
}


// Random item response
export interface RandomItemResponse {
  item: CatalogItem | null
}

// New arrivals response
export interface NewArrivalsResponse {
  items: CatalogItem[]
  total: number
  days: number
  period: 'week' | 'month'
}

// ==================== Catalog Functions ====================

export async function searchCatalog(
  params: CatalogSearchParams = {}
): Promise<CatalogSearchResult> {
  try {
    const queryParams = {
      q: params.query,
      item_type: params.item_type,
      status: params.status,
      year_min: params.year_min,
      year_max: params.year_max,
      location: params.location,
      character: params.character,
      publisher: params.publisher,
      is_new: params.is_new ? 'true' : undefined,
      is_large_print: params.is_large_print ? 'true' : undefined,
      available_for_hold:
        params.availableForHold === undefined
          ? undefined
          : params.availableForHold
            ? 'true'
            : 'false',
      page: params.page,
      per_page: params.per_page,
      sort_by: params.sort_by,
      sort_direction: params.sort_direction,
      include_facets: params.include_facets ? 'true' : undefined,
    }
    const queryString = buildQueryString(queryParams)
    return await fetchApi<CatalogSearchResult>(`/catalog/${queryString}`)
  } catch {
    throw new Error('Failed to search catalog')
  }
}

export async function fetchSuggestions(query: string): Promise<SuggestResponse> {
  try {
    const queryString = buildQueryString({ q: query })
    return await fetchApi<SuggestResponse>(`/catalog/suggest${queryString}`)
  } catch {
    // Return empty suggestions on error to avoid disrupting the search experience
    return { suggestions: [] }
  }
}

export async function getCatalogItem(id: number): Promise<CatalogItem> {
  try {
    return await fetchApi<CatalogItem>(`/catalog/${id}`)
  } catch (error: unknown) {
    if (isApiError(error)) {
      if (error.status === 404) throw new Error('Item not found')
    }
    throw new Error('Failed to fetch catalog item')
  }
}

// ==================== Series reading order ====================

export interface SeriesMember {
  id: number
  title: string
  author: string | null
  item_type: ItemType
  series_position: number | null
  series_number: string | null
  cover_url: string | null
  status: string
}

export interface SeriesReadingOrder {
  series_name: string
  /** How many titles in this series we hold -- NOT the published series length. */
  total_held: number
  current_position: number | null
  prev_id: number | null
  next_id: number | null
  items: SeriesMember[]
}

export async function getSeriesReadingOrder(itemId: number): Promise<SeriesReadingOrder> {
  return await fetchApi<SeriesReadingOrder>(`/catalog/${itemId}/series`)
}

// ==================== Item Recommendations (read-alikes) ====================

export interface ItemRecommendation {
  id: number
  title: string
  author: string | null
  is_pinned: boolean
  cover_image: string | null
  available: boolean
}

export interface ItemRecommendationsResponse {
  items: ItemRecommendation[]
  total_pinned: number
  algorithm_used: string
}

export async function getItemRecommendations(itemId: number): Promise<ItemRecommendationsResponse> {
  return fetchApi<ItemRecommendationsResponse>(`/catalog/${itemId}/recommendations`)
}

// ==================== Cover Image Types ====================

export interface CoverStats {
  total_items: number
  with_covers: number
  without_covers: number
  with_isbn_no_cover: number
  coverage_percent: number
}

export interface CoverPopulateResult {
  id: number
  title: string
  status: 'updated' | 'no_cover_found' | 'error'
  cover_url?: string
  error?: string
}

export interface CoverPopulateResponse {
  processed: number
  updated: number
  skipped: number
  failed: number
  results: CoverPopulateResult[]
}

// ==================== Cover Image Functions ====================

export async function getCoverStats(): Promise<CoverStats> {
  try {
    return await fetchApi<CoverStats>('/catalog/covers/stats')
  } catch {
    throw new Error('Failed to fetch cover statistics')
  }
}

export async function fetchCoverForItem(
  token: string,
  itemId: number
): Promise<CatalogItem> {
  try {
    return await fetchApi<CatalogItem>(`/catalog/${itemId}/fetch-cover`, {
      method: 'POST',
      token,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch cover')
    }
    throw new Error('Failed to fetch cover')
  }
}

export async function populateCovers(
  token: string,
  options?: { limit?: number; overwrite?: boolean }
): Promise<CoverPopulateResponse> {
  try {
    const queryParams = {
      limit: options?.limit,
      overwrite: options?.overwrite ? 'true' : undefined,
    }
    const queryString = buildQueryString(queryParams)

    return await fetchApi<CoverPopulateResponse>(`/catalog/covers/populate${queryString}`, {
      method: 'POST',
      token,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to populate covers')
    }
    throw new Error('Failed to populate covers')
  }
}

// ==================== Duplicate Detection Types ====================

export interface DuplicateCandidate {
  id: number
  title: string
  author: string | null
  isbn: string | null
  item_type: ItemType
  publication_year: number | null
  match_type: 'isbn' | 'title_author' | 'title'
  match_confidence: number
}

export interface DuplicateCheckRequest {
  isbn?: string
  title?: string
  author?: string
  exclude_id?: number
}

export interface DuplicateCheckResponse {
  has_duplicates: boolean
  duplicates: DuplicateCandidate[]
  message: string | null
}

// ==================== Bulk Update Types ====================

export interface BulkUpdateRequest {
  item_ids: number[]
  updates: Record<string, string>
}

export interface BulkUpdateResponse {
  success_count: number
  failure_count: number
  errors: Array<{ id: number; error: string }>
}

// ==================== Duplicate Detection Functions ====================

export async function checkDuplicates(
  token: string,
  request: DuplicateCheckRequest
): Promise<DuplicateCheckResponse> {
  try {
    return await fetchApi<DuplicateCheckResponse>('/catalog/check-duplicates', {
      method: 'POST',
      token,
      body: JSON.stringify(request),
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to check for duplicates')
    }
    throw new Error('Failed to check for duplicates')
  }
}

// ==================== Bulk Update Functions ====================

export async function bulkUpdateCatalogItems(
  token: string,
  itemIds: number[],
  updates: Record<string, string>
): Promise<BulkUpdateResponse> {
  try {
    return await fetchApi<BulkUpdateResponse>('/catalog/bulk-update', {
      method: 'POST',
      token,
      body: JSON.stringify({ item_ids: itemIds, updates }),
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to bulk update items')
    }
    throw new Error('Failed to bulk update items')
  }
}

// ==================== Catalog Item Creation Types ====================

export interface CatalogItemCreateRequest {
  title: string
  author?: string | null
  item_type: ItemType
  isbn?: string | null
  publisher?: string | null
  publication_year?: number | null
  description?: string | null
  subjects?: string | null
  cover_url?: string | null
  page_count?: number | null
  location?: string | null
  barcode?: string | null
  is_large_print?: boolean
  // Multimedia fields
  director?: string | null
  actors?: string | null
  runtime_minutes?: number | null
  media_format?: MediaFormat | null
  content_rating?: ContentRating | null
  disc_count?: number | null
  studio?: string | null
  artist?: string | null
  track_count?: number | null
  music_genre?: string | null
  platform?: string | null
  player_count?: string | null
  game_genre?: string | null
  brand?: string | null
  model_number?: string | null
  dimensions?: string | null
  material?: string | null
  kit_contents?: string | null
}

// ==================== Catalog Item Creation Functions ====================

export async function createCatalogItem(
  token: string,
  item: CatalogItemCreateRequest
): Promise<CatalogItem> {
  try {
    return await fetchApi<CatalogItem>('/catalog', {
      method: 'POST',
      token,
      body: JSON.stringify(item),
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to create catalog item')
    }
    throw new Error('Failed to create catalog item')
  }
}

// ==================== Advanced Search Types ====================

export interface AdvancedSearchQuery {
  field: 'title' | 'author' | 'artist' | 'director' | 'subject' | 'isbn' | 'publisher' | 'brand' | 'platform'
  value: string
  operator: 'AND' | 'OR' | 'NOT'
}

export interface AdvancedSearchFilters {
  item_type?: ItemType
  status?: string
  publication_year_min?: number
  publication_year_max?: number
  location?: string
}

export interface AdvancedSearchRequest {
  queries: AdvancedSearchQuery[]
  filters?: AdvancedSearchFilters
}

export interface AdvancedSearchResponse {
  items: CatalogItem[]
  total: number
  page: number
  per_page: number
  pages: number
  search_params: AdvancedSearchRequest
}

export interface SimpleAdvancedSearchRequest {
  title?: string
  author?: string
  subject?: string
  isbn?: string
  publisher?: string
  operator?: 'AND' | 'OR'
  exclude_subject?: string
  item_type?: ItemType
  status?: string
  year_min?: number
  year_max?: number
  location?: string
  page?: number
  per_page?: number
}

export interface SimpleAdvancedSearchResponse {
  results: CatalogItem[]
  total: number
  page: number
  per_page: number
  pages: number
}

// ==================== Advanced Search Functions ====================

export async function advancedSearch(
  request: AdvancedSearchRequest,
  page: number = 1,
  perPage: number = 20
): Promise<AdvancedSearchResponse> {
  const token = getAccessToken()
  const queryString = buildQueryString({ page, per_page: perPage })

  try {
    return await fetchApi<AdvancedSearchResponse>(`/catalog/advanced-search${queryString}`, {
      method: 'POST',
      ...(token ? { token } : {}),
      body: JSON.stringify(request),
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Advanced search failed')
    }
    throw new Error('Advanced search failed')
  }
}

export async function searchAdvanced(
  request: SimpleAdvancedSearchRequest
): Promise<SimpleAdvancedSearchResponse> {
  const token = getAccessToken()

  try {
    return await fetchApi<SimpleAdvancedSearchResponse>('/catalog/search/advanced', {
      method: 'POST',
      ...(token ? { token } : {}),
      body: JSON.stringify(request),
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Search failed')
    }
    throw new Error('Search failed')
  }
}

// ==================== Staff Catalog Functions ====================

export async function staffCreateCatalogItem(
  token: string,
  item: CatalogItemCreateRequest
): Promise<CatalogItem> {
  try {
    return await fetchApi<CatalogItem>('/staff/catalog', {
      method: 'POST',
      token,
      body: JSON.stringify(item),
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to create catalog item')
    }
    throw new Error('Failed to create catalog item')
  }
}

// ==================== Catalog Image Functions ====================

export async function listCatalogImages(
  itemId: number
): Promise<CatalogImageListResponse> {
  try {
    return await fetchApi<CatalogImageListResponse>(`/catalog/${itemId}/images`)
  } catch {
    throw new Error('Failed to list catalog images')
  }
}

export async function uploadCatalogImage(
  token: string,
  itemId: number,
  file: File,
  options?: { is_primary?: boolean; caption?: string }
): Promise<CatalogImageUploadResponse> {
  const params = new URLSearchParams()
  if (options?.is_primary) params.set('is_primary', 'true')
  if (options?.caption) params.set('caption', options.caption)
  const qs = params.toString() ? `?${params.toString()}` : ''

  const formData = new FormData()
  formData.append('file', file)

  const response = await fetch(`${API_BASE}/catalog/${itemId}/images${qs}`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
    body: formData,
  })

  if (!response.ok) {
    const err = await response.json().catch(() => ({}))
    throw new Error(err.detail || 'Failed to upload image')
  }

  return response.json()
}

export async function deleteCatalogImage(
  token: string,
  itemId: number,
  imageId: number
): Promise<void> {
  try {
    await fetchApi<void>(`/catalog/${itemId}/images/${imageId}`, {
      method: 'DELETE',
      token,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to delete image')
    }
    throw new Error('Failed to delete image')
  }
}

export async function updateCatalogImage(
  token: string,
  itemId: number,
  imageId: number,
  options: { is_primary?: boolean; caption?: string }
): Promise<CatalogImage> {
  const params = new URLSearchParams()
  if (options.is_primary !== undefined) params.set('is_primary', String(options.is_primary))
  if (options.caption !== undefined) params.set('caption', options.caption)
  const qs = params.toString() ? `?${params.toString()}` : ''

  try {
    return await fetchApi<CatalogImage>(`/catalog/${itemId}/images/${imageId}${qs}`, {
      method: 'PATCH',
      token,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to update image')
    }
    throw new Error('Failed to update image')
  }
}

export async function reorderCatalogImages(
  token: string,
  itemId: number,
  imageIds: number[]
): Promise<void> {
  try {
    await fetchApi<void>(`/catalog/${itemId}/images/reorder`, {
      method: 'PUT',
      token,
      body: JSON.stringify({ image_ids: imageIds }),
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to reorder images')
    }
    throw new Error('Failed to reorder images')
  }
}

// ==================== Special Collection Functions ====================

export async function getRandomItem(params?: {
  item_type?: string
  status?: string
  year_min?: number
  year_max?: number
  is_large_print?: boolean
  min_lexile?: number
  max_lexile?: number
}): Promise<RandomItemResponse> {
  const queryString = buildQueryString(params)
  return await fetchApi<RandomItemResponse>(`/catalog/special/random${queryString}`)
}

export async function getNewArrivals(params?: {
  days?: number
  limit?: number
}): Promise<NewArrivalsResponse> {
  const queryString = buildQueryString(params)
  return await fetchApi<NewArrivalsResponse>(`/catalog/special/new-arrivals${queryString}`)
}

