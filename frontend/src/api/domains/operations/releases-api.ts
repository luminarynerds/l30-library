/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { fetchApi, isApiError } from '@/lib/api-client'
import { getAccessToken } from '@/utils/tokenStore'

// ==================== Types ====================

export interface Author {
  id: string
  name: string
  google_id: string | null
  image_url: string | null
  bio: string | null
  website: string | null
  follower_count: number
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface Book {
  id: string
  title: string
  subtitle: string | null
  release_date: string | null
  is_date_exact: boolean
  isbn_10: string | null
  isbn_13: string | null
  asin: string | null
  age_rating: 'child' | 'teen' | 'adult'
  cover_url: string | null
  description: string | null
  publisher: string | null
  page_count: number | null
  list_price: number | null
  status: 'upcoming' | 'released' | 'cancelled'
  author_id: string
}

export interface AuthorSearchResultItem {
  id: string | null
  name: string
  source: 'local' | 'google_books'
  source_id?: string
  follower_count: number
  image_url: string | null
}

export interface AuthorSearchResultsResponse {
  results: AuthorSearchResultItem[]
}

export interface FollowedAuthorItem {
  follow_id: number
  author: Author
  profile_type: 'parent' | 'child'
  notify_on_release: boolean
}

export interface FollowedAuthorsResponse {
  items: FollowedAuthorItem[]
  total: number
}

export interface FollowResponse {
  id: number
  user_id: number
  author_id: string
  profile_type: string
  notify_on_release: boolean
}

export interface CreateAndFollowAuthorResponse {
  author: Author
  status: string
}

export interface ReleaseFeedItem {
  book: Book
  author: Author | null
  days_until_release: number | null
  is_followed: boolean
}

export interface ReleaseFeedResponse {
  items: ReleaseFeedItem[]
  total: number
}

export interface LibrarianReleaseItem {
  book: Book
  author_name: string
  library_status: 'new' | 'owned' | 'on_order'
  demand_score: number
  catalog_item_id: number | null
}

export interface LibrarianReleasesResponse {
  items: LibrarianReleaseItem[]
  total: number
  page: number
  per_page: number
}

export interface CreatePOFromReleasesRequest {
  tracker_book_ids: string[]
  vendor_id: number
  fund_id: number
  use_existing_draft: boolean
}

export interface CreatePOFromReleasesResponse {
  purchase_order_id: number
  po_number: string
  items_added: number
  catalog_items_created: number
}

export interface IngestionStats {
  authors_processed: number
  books_added: number
  books_updated: number
  errors: string[]
}

export interface StaffAuthorsResponse {
  items: Author[]
  total: number
  page: number
  per_page: number
}

export interface AuthorCreate {
  name: string
  google_id?: string
  image_url?: string
  bio?: string
  website?: string
}

export interface FollowCreate {
  profile_type?: 'parent' | 'child'
  notify_on_release?: boolean
}

// ==================== Author Search & Discovery ====================

export async function searchAuthors(query: string): Promise<AuthorSearchResultsResponse> {
  const token = getAccessToken()
  try {
    return await fetchApi<AuthorSearchResultsResponse>(
      `/releases/authors/search?q=${encodeURIComponent(query)}`,
      { ...(token ? { token } : {}) }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Author search failed')
    }
    throw error
  }
}

export async function getFollowedAuthors(): Promise<FollowedAuthorsResponse> {
  const token = getAccessToken()
  try {
    return await fetchApi<FollowedAuthorsResponse>('/releases/authors', {
      ...(token ? { token } : {}),
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to get followed authors')
    }
    throw error
  }
}

export async function followAuthor(
  authorId: string,
  data?: FollowCreate
): Promise<FollowResponse> {
  const token = getAccessToken()
  try {
    return await fetchApi<FollowResponse>(`/releases/authors/${authorId}/follow`, {
      method: 'POST',
      ...(token ? { token } : {}),
      ...(data ? { body: data } : {}),
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to follow author')
    }
    throw error
  }
}

export async function unfollowAuthor(authorId: string): Promise<void> {
  const token = getAccessToken()
  try {
    await fetchApi<void>(`/releases/authors/${authorId}/follow`, {
      method: 'DELETE',
      ...(token ? { token } : {}),
      skipJsonParse: true,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to unfollow author')
    }
    throw error
  }
}

export async function createAndFollowAuthor(
  name: string,
  googleId?: string,
  profileType: string = 'parent'
): Promise<CreateAndFollowAuthorResponse> {
  const token = getAccessToken()
  const params = new URLSearchParams()
  params.set('name', name)
  if (googleId) params.set('google_id', googleId)
  params.set('profile_type', profileType)

  try {
    return await fetchApi<CreateAndFollowAuthorResponse>(
      `/releases/authors/create-and-follow?${params}`,
      {
        method: 'POST',
        ...(token ? { token } : {}),
      }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to create and follow author')
    }
    throw error
  }
}

// ==================== Patron Release Feed ====================

export async function getMyReleases(params?: {
  profile?: 'parent' | 'child'
  status?: 'upcoming' | 'released'
  days_ahead?: number
  page?: number
  per_page?: number
}): Promise<ReleaseFeedResponse> {
  const token = getAccessToken()
  const searchParams = new URLSearchParams()
  if (params?.profile) searchParams.set('profile', params.profile)
  if (params?.status) searchParams.set('status', params.status)
  if (params?.days_ahead) searchParams.set('days_ahead', params.days_ahead.toString())
  if (params?.page) searchParams.set('page', params.page.toString())
  if (params?.per_page) searchParams.set('per_page', params.per_page.toString())
  const query = searchParams.toString() ? `?${searchParams}` : ''

  try {
    return await fetchApi<ReleaseFeedResponse>(`/releases/my-releases${query}`, {
      ...(token ? { token } : {}),
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to get releases')
    }
    throw error
  }
}

// ==================== Librarian Endpoints ====================

export async function getLibrarianReleases(params?: {
  status?: 'upcoming' | 'released'
  library_status?: 'new' | 'owned' | 'on_order'
  age_rating?: 'child' | 'teen' | 'adult'
  min_demand?: number
  page?: number
  per_page?: number
}): Promise<LibrarianReleasesResponse> {
  const token = getAccessToken()
  const searchParams = new URLSearchParams()
  if (params?.status) searchParams.set('status', params.status)
  if (params?.library_status) searchParams.set('library_status', params.library_status)
  if (params?.age_rating) searchParams.set('age_rating', params.age_rating)
  if (params?.min_demand !== undefined) searchParams.set('min_demand', params.min_demand.toString())
  if (params?.page) searchParams.set('page', params.page.toString())
  if (params?.per_page) searchParams.set('per_page', params.per_page.toString())
  const query = searchParams.toString() ? `?${searchParams}` : ''

  try {
    return await fetchApi<LibrarianReleasesResponse>(`/releases/librarian/releases${query}`, {
      ...(token ? { token } : {}),
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to get librarian releases')
    }
    throw error
  }
}

export async function createPOFromReleases(
  data: CreatePOFromReleasesRequest
): Promise<CreatePOFromReleasesResponse> {
  const token = getAccessToken()
  try {
    return await fetchApi<CreatePOFromReleasesResponse>('/releases/librarian/create-po', {
      method: 'POST',
      ...(token ? { token } : {}),
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to create purchase order')
    }
    throw error
  }
}

export async function refreshAuthor(authorId: string): Promise<IngestionStats> {
  const token = getAccessToken()
  try {
    return await fetchApi<IngestionStats>(`/releases/librarian/refresh-author/${authorId}`, {
      method: 'POST',
      ...(token ? { token } : {}),
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to refresh author')
    }
    throw error
  }
}

export async function refreshAllAuthors(force: boolean = false): Promise<{ status: string; message: string }> {
  const token = getAccessToken()
  try {
    return await fetchApi<{ status: string; message: string }>('/releases/librarian/refresh-all', {
      method: 'POST',
      ...(token ? { token } : {}),
      body: { force },
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to refresh all authors')
    }
    throw error
  }
}

// ==================== Staff Author Management ====================

export async function createAuthor(data: AuthorCreate): Promise<Author> {
  const token = getAccessToken()
  try {
    return await fetchApi<Author>('/releases/staff/authors', {
      method: 'POST',
      ...(token ? { token } : {}),
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to create author')
    }
    throw error
  }
}

export async function getStaffAuthors(params?: {
  q?: string
  active_only?: boolean
  page?: number
  per_page?: number
}): Promise<StaffAuthorsResponse> {
  const token = getAccessToken()
  const searchParams = new URLSearchParams()
  if (params?.q) searchParams.set('q', params.q)
  if (params?.active_only !== undefined) searchParams.set('active_only', params.active_only.toString())
  if (params?.page) searchParams.set('page', params.page.toString())
  if (params?.per_page) searchParams.set('per_page', params.per_page.toString())
  const query = searchParams.toString() ? `?${searchParams}` : ''

  try {
    return await fetchApi<StaffAuthorsResponse>(`/releases/staff/authors${query}`, {
      ...(token ? { token } : {}),
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to get staff authors')
    }
    throw error
  }
}

// ==================== Patron Featured Upcoming ====================

export interface FeaturedUpcomingItem {
  tracker_book_id: string
  title: string
  author_name?: string | null
  isbn_13?: string | null
  release_date?: string | null
  is_date_exact?: boolean
  source: string
  source_url?: string | null
  blurb?: string | null
  blurb_credit?: string | null
  library_status: string
  catalog_item_id?: number | null
}

export interface FeaturedUpcomingResponse {
  items: FeaturedUpcomingItem[]
  total: number
  page: number
  per_page: number
}

export async function getFeaturedUpcoming(): Promise<FeaturedUpcomingResponse> {
  try {
    return await fetchApi<FeaturedUpcomingResponse>('/releases/featured-upcoming')
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to load upcoming titles')
    }
    throw error
  }
}
