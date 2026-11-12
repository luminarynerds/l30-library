/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Public Reading Lists API Service
 *
 * Handles discovery, searching, and browsing of public reading lists
 * created by library patrons. Provides search, filtering, sorting,
 * and pagination functionality.
 */

import { fetchApi, isApiError } from '@/lib/api-client'

// ==================== Types ====================

export type PublicReadingListSortBy = 'newest' | 'most_popular' | 'alphabetical' | 'most_shared'

export interface ReadingListCreator {
  id: number
  name: string
  avatar: string | null
}

export interface ReadingListShareStats {
  total_shares: number
  bluesky_shares: number
  mastodon_shares: number
  email_shares: number
}

export interface PublicReadingListPreview {
  id: number
  name: string
  description: string | null
  creator: ReadingListCreator
  item_count: number
  share_count: number
  share_stats: ReadingListShareStats | null
  created_at: string | null
  updated_at: string | null
}

export interface PaginationInfo {
  total_count: number
  page: number
  per_page: number
  total_pages: number
  has_next: boolean
  has_previous: boolean
}

export interface SearchFilters {
  search: string | null
  sort: PublicReadingListSortBy
  creator_id: number | null
}

export interface BrowsePublicListsResponse {
  success: boolean
  data: PublicReadingListPreview[]
  pagination: PaginationInfo
  filters: SearchFilters
}

export interface CreatorSearchResult {
  id: number
  name: string
  avatar: string | null
  public_lists_count: number
}

export interface SearchCreatorsResponse {
  success: boolean
  creators: CreatorSearchResult[]
  count: number
}

export interface ReadingListItem {
  id: number
  catalog_item_id: number
  title: string
  author: string | null
  isbn: string | null
  cover_image: string | null
  added_at: string | null
}

export interface PublicReadingListDetail {
  id: number
  name: string
  description: string | null
  creator: ReadingListCreator
  item_count: number
  share_count: number
  share_stats: ReadingListShareStats | null
  created_at: string | null
  updated_at: string | null
  items: ReadingListItem[]
}

export interface GetPublicListPreviewResponse {
  success: boolean
  list: PublicReadingListDetail
}

export interface TrendingListPreview {
  id: number
  name: string
  creator: ReadingListCreator
  item_count: number
  share_count: number
  created_at: string | null
}

export interface GetTrendingListsResponse {
  success: boolean
  trending: TrendingListPreview[]
  count: number
}

export interface BrowsePublicListsParams {
  search?: string
  sort?: PublicReadingListSortBy
  creator_id?: number
  page?: number
  per_page?: number
}

// ==================== API Functions ====================

export async function browsePublicReadingLists(
  params: BrowsePublicListsParams = {}
): Promise<BrowsePublicListsResponse> {
  const searchParams = new URLSearchParams()

  if (params.search) {
    searchParams.append('search', params.search)
  }
  if (params.sort) {
    searchParams.append('sort', params.sort)
  }
  if (params.creator_id !== undefined) {
    searchParams.append('creator_id', params.creator_id.toString())
  }
  if (params.page !== undefined) {
    searchParams.append('page', params.page.toString())
  }
  if (params.per_page !== undefined) {
    searchParams.append('per_page', params.per_page.toString())
  }

  const queryString = searchParams.toString()
  const endpoint = `/reading-lists/public${queryString ? `?${queryString}` : ''}`

  try {
    return await fetchApi<BrowsePublicListsResponse>(endpoint)
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to browse public reading lists')
    }
    throw error
  }
}

export async function searchReadingListCreators(
  query: string,
  limit: number = 10
): Promise<SearchCreatorsResponse> {
  if (!query || query.length < 1) {
    throw new Error('Search query must be at least 1 character')
  }
  if (limit < 1 || limit > 50) {
    throw new Error('Limit must be between 1 and 50')
  }

  const searchParams = new URLSearchParams()
  searchParams.append('query', query)
  searchParams.append('limit', limit.toString())

  try {
    return await fetchApi<SearchCreatorsResponse>(
      `/reading-lists/public/search/creators?${searchParams}`
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to search for creators')
    }
    throw error
  }
}

export async function getPublicReadingListPreview(
  listId: number
): Promise<GetPublicListPreviewResponse> {
  try {
    return await fetchApi<GetPublicListPreviewResponse>(
      `/reading-lists/public/${listId}/preview`
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      if (error.status === 404) {
        throw new Error('Public reading list not found')
      }
      throw new Error(error.detail || 'Failed to fetch reading list preview')
    }
    throw error
  }
}

export async function getTrendingReadingLists(
  limit: number = 10,
  days: number = 30
): Promise<GetTrendingListsResponse> {
  if (limit < 1 || limit > 50) {
    throw new Error('Limit must be between 1 and 50')
  }
  if (days < 1 || days > 365) {
    throw new Error('Days must be between 1 and 365')
  }

  const searchParams = new URLSearchParams()
  searchParams.append('limit', limit.toString())
  searchParams.append('days', days.toString())

  try {
    return await fetchApi<GetTrendingListsResponse>(
      `/reading-lists/public/stats/trending?${searchParams}`
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch trending reading lists')
    }
    throw error
  }
}
