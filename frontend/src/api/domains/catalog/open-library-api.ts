/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { fetchApi } from '@/lib/api-client'

// ==================== Open Library Types ====================

export interface OpenLibraryAuthor {
  name: string
  ol_id: string | null
}

export interface OpenLibraryBookSummary {
  id: number
  ol_work_id: string
  title: string
  primary_author: string | null
  cover_url: string | null
  edition_count: number
  languages: string | null
  has_fulltext: boolean
}

export interface OpenLibraryBookDetail extends OpenLibraryBookSummary {
  ol_edition_id: string | null
  authors: OpenLibraryAuthor[] | null
  subjects: string[] | null
  first_publish_year: number | null
  publisher: string | null
  isbn_13: string | null
  isbn_10: string | null
  public_scan: boolean
  availability: Record<string, string> | null
  catalog_item_id: number | null
  last_synced_at: string
  created_at: string
  read_url: string | null
  is_favorited: boolean
  download_history: OpenLibraryDownload[] | null
}

export interface OpenLibrarySearchResponse {
  count: number
  page: number
  page_size: number
  total_pages: number
  books: OpenLibraryBookSummary[]
  has_next: boolean
  has_previous: boolean
}

export interface OpenLibraryDownload {
  id: number
  user_id: number
  book_id: number
  access_type: string
  accessed_at: string
  book_title: string | null
}

export interface OpenLibraryFavorite {
  id: number
  user_id: number
  book_id: number
  notes: string | null
  created_at: string
  book: OpenLibraryBookSummary | null
}

// ==================== API Functions ====================

export async function searchOpenLibraryBooks(
  token: string | null,
  params: {
    q?: string
    author?: string
    title?: string
    subject?: string
    languages?: string
    page?: number
    source?: 'api' | 'local'
  }
): Promise<OpenLibrarySearchResponse> {
  const searchParams = new URLSearchParams()
  if (params.q) searchParams.append('q', params.q)
  if (params.author) searchParams.append('author', params.author)
  if (params.title) searchParams.append('title', params.title)
  if (params.subject) searchParams.append('subject', params.subject)
  if (params.languages) searchParams.append('languages', params.languages)
  if (params.page) searchParams.append('page', params.page.toString())
  if (params.source) searchParams.append('source', params.source)

  return fetchApi<OpenLibrarySearchResponse>(
    `/open-library/search?${searchParams.toString()}`,
    token ? { token } : {}
  )
}

export async function getOpenLibraryBook(
  token: string | null,
  bookId: number
): Promise<OpenLibraryBookDetail> {
  return fetchApi<OpenLibraryBookDetail>(`/open-library/books/${bookId}`, token ? { token } : {})
}

export async function recordOpenLibraryDownload(
  token: string,
  bookId: number,
  accessType: string = 'read_online'
): Promise<OpenLibraryDownload> {
  return fetchApi<OpenLibraryDownload>('/open-library/downloads', {
    method: 'POST',
    token,
    body: { book_id: bookId, access_type: accessType },
  })
}

export async function addOpenLibraryFavorite(
  token: string,
  bookId: number,
  notes?: string
): Promise<OpenLibraryFavorite> {
  return fetchApi<OpenLibraryFavorite>('/open-library/favorites', {
    method: 'POST',
    token,
    body: { book_id: bookId, notes },
  })
}

export async function removeOpenLibraryFavorite(
  token: string,
  bookId: number
): Promise<void> {
  return fetchApi(`/open-library/favorites/${bookId}`, { method: 'DELETE', token })
}

export async function triggerOpenLibrarySync(
  token: string,
  options?: { subject?: string; max_batches?: number }
): Promise<{ ok: boolean; message: string; books_synced: number }> {
  return fetchApi('/open-library/sync', { method: 'POST', token, body: options || {} })
}
