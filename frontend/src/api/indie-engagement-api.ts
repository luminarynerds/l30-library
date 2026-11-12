/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Indie Engagement API - stubbed after indie backend removal
 * All /indie/* engagement endpoints have been removed.
 * Functions return safe defaults so consuming pages don't crash.
 */

import { fetchApi } from '@/lib/api-client'
import { getAccessToken } from '../utils/tokenStore'

// ==================== Types ====================

export interface ReadingListResponse {
  id: number
  name: string
  description: string | null
  is_public: boolean
  share_token: string | null
  item_count: number
  created_at: string
  updated_at: string
}

export interface AuthorBrief {
  id: number
  pen_name: string
  slug?: string
  profile_image_url: string | null
}

export interface UpdateTypeBrief {
  id: number
  name: string
  slug: string
  icon?: string
  label?: string
}

export interface EbookBrief {
  id: number
  title: string
  slug: string | null
  cover_url: string | null
  cover_image_url?: string | null
}

export interface EventBrief {
  id: number
  title: string
  start_time?: string | null
}

export interface AuthorUpdateResponse {
  id: number
  author: AuthorBrief
  update_type: UpdateTypeBrief
  title: string | null
  body: string
  image_url: string | null
  linked_ebook: EbookBrief | null
  linked_event: EventBrief | null
  status: 'draft' | 'pending' | 'published' | 'rejected'
  rejection_note: string | null
  reaction_count: number
  user_reacted: boolean
  published_at: string | null
  created_at: string
  is_draft?: boolean
  staff_approved?: boolean
}

export interface EditorialFeatureTypeResponse {
  id: number
  name: string
  slug: string
  description: string | null
  icon: string | null
  display_order: number
  is_active: boolean
}

export interface EditorialFeatureResponse {
  id: number
  title: string
  subtitle: string | null
  body: string
  feature_type: EditorialFeatureTypeResponse
  cover_image_url: string | null
  linked_author_id: number | null
  linked_author_name: string | null
  linked_ebook_ids: number[]
  is_published: boolean
  published_at: string | null
  display_priority: number
  expires_at: string | null
  created_at: string
  updated_at: string
}

export interface HappeningNowResponse {
  events: Array<{ id: number; title: string; start_time: string }>
  live_amas: Array<{ id: number; event_id: number }>
  recent_updates: AuthorUpdateResponse[]
  new_releases: Array<{
    id: number
    title: string
    slug: string | null
    cover_image_url: string | null
    author_name: string | null
  }>
  active_readers: number
}

export interface ForYouFeedItem {
  type: 'book' | 'update'
  item: { id: number; slug?: string; title: string; cover_url?: string; author_pen_name?: string; [key: string]: unknown }
  feed_reason: string
  feed_reason_detail?: string
}

export interface ForYouFeedResponse {
  items: ForYouFeedItem[]
  total: number
  page: number
}

// ==================== Follows ====================

interface IndieFollowStatus {
  indie_author_id: number
  following: boolean
  follower_count: number
}

export async function followAuthor(authorId: number): Promise<void> {
  await fetchApi<IndieFollowStatus>(`/indie/authors/${authorId}/follow`, {
    method: 'POST',
  })
}

export async function unfollowAuthor(authorId: number): Promise<void> {
  await fetchApi(`/indie/authors/${authorId}/follow`, { method: 'DELETE' })
}

export async function getFollowStatus(authorId: number): Promise<{ following: boolean }> {
  const res = await fetchApi<IndieFollowStatus>(`/indie/authors/${authorId}/follow`)
  return { following: res.following }
}

export async function getFollowerCount(authorId: number): Promise<{ count: number }> {
  const res = await fetchApi<IndieFollowStatus>(`/indie/authors/${authorId}/follow`)
  return { count: res.follower_count }
}

// ==================== Bookmarks (save for later) ====================

export interface BookmarkItem {
  ebook_id: number
  created_at: string
}

export interface BookmarkListResponse {
  items: BookmarkItem[]
  total: number
}

export async function bookmarkEbook(ebookId: number): Promise<{ bookmarked: boolean; ebook_id: number }> {
  const token = getAccessToken()
  return fetchApi(`/indie/bookmarks/${ebookId}`, {
    method: 'POST',
    ...(token ? { token } : {}),
  })
}

export async function unbookmarkEbook(ebookId: number): Promise<{ bookmarked: boolean; ebook_id: number }> {
  const token = getAccessToken()
  return fetchApi(`/indie/bookmarks/${ebookId}`, {
    method: 'DELETE',
    ...(token ? { token } : {}),
  })
}

export async function getBookmarkStatus(ebookId: number): Promise<{ bookmarked: boolean }> {
  const token = getAccessToken()
  return fetchApi(`/indie/bookmarks/${ebookId}/status`, {
    ...(token ? { token } : {}),
  })
}

export async function getMyBookmarks(): Promise<BookmarkListResponse> {
  const token = getAccessToken()
  return fetchApi('/indie/bookmarks', {
    ...(token ? { token } : {}),
  })
}

// Legacy aliases for backward compat
export const favoriteEbook = bookmarkEbook
export const unfavoriteEbook = unbookmarkEbook
export async function getFavoriteStatus(ebookId: number): Promise<{ favorited: boolean }> {
  const result = await getBookmarkStatus(ebookId)
  return { favorited: result.bookmarked }
}
// STUBBED: returns 0 (indie backend removed)
export async function getFavoriteCount(_ebookId: number): Promise<{ count: number }> {
  return { count: 0 }
}


// ==================== Reading List Types ====================

export interface IndieReadingListSummary {
  id: number
  name: string
  description: string | null
  is_public: boolean
  share_token: string | null
  item_count: number
  created_at: string
  updated_at: string
}

export interface IndieReadingListItem {
  ebook_id: number
  note: string | null
  added_at: string
}

export interface IndieReadingListDetail {
  id: number
  name: string
  description: string | null
  is_public: boolean
  share_token: string | null
  creator_name: string
  items: IndieReadingListItem[]
  created_at: string
  updated_at: string
}

// ==================== Reading Lists (real implementation) ====================

export async function getMyIndieReadingLists(): Promise<IndieReadingListSummary[]> {
  const token = getAccessToken()
  if (!token) return []
  return fetchApi<IndieReadingListSummary[]>('/indie/reading-lists', { token })
}

export async function createIndieReadingList(name: string, description?: string): Promise<IndieReadingListSummary> {
  const token = getAccessToken()
  return fetchApi<IndieReadingListSummary>('/indie/reading-lists', {
    method: 'POST',
    token: token!,
    body: { name, description: description ?? null },
  })
}

export async function getIndieReadingList(listId: number): Promise<IndieReadingListDetail> {
  const token = getAccessToken()
  return fetchApi<IndieReadingListDetail>(`/indie/reading-lists/${listId}`, {
    ...(token ? { token } : {}),
  })
}

export async function updateIndieReadingList(listId: number, updates: { name?: string; description?: string; is_public?: boolean }): Promise<IndieReadingListSummary> {
  const token = getAccessToken()
  return fetchApi<IndieReadingListSummary>(`/indie/reading-lists/${listId}`, {
    method: 'PUT',
    token: token!,
    body: updates,
  })
}

export async function deleteIndieReadingList(listId: number): Promise<void> {
  const token = getAccessToken()
  await fetchApi(`/indie/reading-lists/${listId}`, {
    method: 'DELETE',
    token: token!,
  })
}

export async function addToIndieReadingList(listId: number, ebookId: number, note?: string): Promise<void> {
  const token = getAccessToken()
  await fetchApi(`/indie/reading-lists/${listId}/items`, {
    method: 'POST',
    token: token!,
    body: { ebook_id: ebookId, note: note ?? null },
  })
}

export async function removeFromIndieReadingList(listId: number, ebookId: number): Promise<void> {
  const token = getAccessToken()
  await fetchApi(`/indie/reading-lists/${listId}/items/${ebookId}`, {
    method: 'DELETE',
    token: token!,
  })
}

export async function getSharedIndieReadingList(shareToken: string): Promise<IndieReadingListDetail> {
  return fetchApi<IndieReadingListDetail>(`/indie/reading-lists/shared/${shareToken}`)
}

export async function getPublicIndieReadingLists(sort = 'newest', limit = 20): Promise<IndieReadingListSummary[]> {
  return fetchApi<IndieReadingListSummary[]>(`/indie/reading-lists/public?sort=${sort}&limit=${limit}`)
}

// ==================== Author Updates (stubbed) ====================

// STUBBED: returns empty list (indie backend removed)
export async function getAuthorUpdates(_authorId: number): Promise<AuthorUpdateResponse[]> {
  return []
}

// STUBBED: no-op (indie backend removed)
export async function reactToUpdate(_updateId: number): Promise<void> {}

// STUBBED: no-op (indie backend removed)
export async function unreactToUpdate(_updateId: number): Promise<void> {}

// ==================== Discovery (stubbed) ====================

// STUBBED: returns empty list (indie backend removed)
export async function getEditorialFeatures(_page?: number, _typeSlug?: string): Promise<EditorialFeatureResponse[]> {
  return []
}

export async function getForYouFeed(page?: number): Promise<ForYouFeedResponse> {
  const token = getAccessToken()
  if (!token) {
    return { items: [], total: 0, page: 1 }
  }
  try {
    const params = page && page > 1 ? `?page=${page}` : ''
    return await fetchApi<ForYouFeedResponse>(`/indie/lending/for-you${params}`, {
      ...(token ? { token } : {}),
    })
  } catch {
    return { items: [], total: 0, page: 1 }
  }
}

// STUBBED: returns empty defaults (indie backend removed)
export async function getHappeningNow(): Promise<HappeningNowResponse> {
  return {
    events: [],
    live_amas: [],
    recent_updates: [],
    new_releases: [],
    active_readers: 0,
  }
}

// ==================== Reading Progress =============
export interface ReadingProgressResponse {
  ebook_id: number
  percent: number
  current_position: string | null
  updated_at: string
}

export async function getReadingProgress(ebookId: number): Promise<ReadingProgressResponse | null> {
  const token = getAccessToken()
  if (!token) return null
  try {
    return await fetchApi<ReadingProgressResponse>(`/indie/reading-progress/${ebookId}`, { token })
  } catch {
    return null
  }
}

export async function updateReadingProgress(
  ebookId: number,
  percent: number,
  currentPosition?: string,
): Promise<ReadingProgressResponse> {
  const token = getAccessToken()
  return fetchApi<ReadingProgressResponse>(`/indie/reading-progress/${ebookId}`, {
    method: "PUT",
    token: token!,
    body: { percent, current_position: currentPosition ?? null },
  })
}

export async function getActiveReadingProgress(): Promise<ReadingProgressResponse[]> {
  const token = getAccessToken()
  if (!token) return []
  try {
    return await fetchApi<ReadingProgressResponse[]>("/indie/reading-progress/active", { token })
  } catch {
    return []
  }
}
// ==================== Author Events ====================

export interface AuthorEvent {
  id: number
  title: string
  start_time: string
  end_time: string | null
  category: string | null
}

export async function getAuthorEvents(authorId: number, upcoming = true, limit = 5): Promise<AuthorEvent[]> {
  try {
    return await fetchApi<AuthorEvent[]>(`/indie/authors/${authorId}/events?upcoming=${upcoming}&limit=${limit}`)
  } catch {
    return []
  }
}

// ==================== Content Preferences ====================

export interface ContentPreferences {
  hidden_warnings: string[]
  flagged_warnings: string[]
}

export async function getWarningCategories(): Promise<string[]> {
  try {
    return await fetchApi<string[]>('/indie/content-preferences/categories')
  } catch {
    return []
  }
}

export async function getContentPreferences(): Promise<ContentPreferences> {
  const token = getAccessToken()
  if (!token) return { hidden_warnings: [], flagged_warnings: [] }
  try {
    return await fetchApi<ContentPreferences>('/indie/content-preferences', { token })
  } catch {
    return { hidden_warnings: [], flagged_warnings: [] }
  }
}

export async function updateContentPreferences(prefs: Partial<ContentPreferences>): Promise<ContentPreferences> {
  const token = getAccessToken()
  return fetchApi<ContentPreferences>('/indie/content-preferences', {
    method: 'PUT',
    token: token!,
    body: prefs,
  })
}
