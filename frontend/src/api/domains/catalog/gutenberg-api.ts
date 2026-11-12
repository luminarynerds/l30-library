/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { fetchApi } from '@/lib/api-client'

// ==================== Gutenberg Types ====================

export type GutenbergFormat = 'epub' | 'kindle' | 'html' | 'plain_text' | 'pdf'

export interface GutenbergAuthor {
  name: string
  birth_year: number | null
  death_year: number | null
}

export interface GutenbergBookSummary {
  id: number
  gutenberg_id: number
  title: string
  primary_author: string | null
  cover_url: string | null
  download_count: number
  languages: string | null
}

export interface GutenbergBookDetail {
  id: number
  gutenberg_id: number
  title: string
  authors: GutenbergAuthor[] | null
  subjects: string[] | null
  bookshelves: string[] | null
  languages: string | null
  copyright_status: boolean
  media_type: string
  download_count: number
  formats: Record<string, string> | null
  cover_url: string | null
  catalog_item_id: number | null
  last_synced_at: string
  created_at: string
  epub_url: string | null
  kindle_url: string | null
  html_url: string | null
  text_url: string | null
  pdf_url: string | null
  is_favorited: boolean
  download_history: GutenbergDownload[] | null
}

export interface GutenbergSearchResponse {
  count: number
  page: number
  page_size: number
  total_pages: number
  books: GutenbergBookSummary[]
  has_next: boolean
  has_previous: boolean
}

export interface GutenbergDownload {
  id: number
  user_id: number
  book_id: number
  format: GutenbergFormat
  downloaded_at: string
  book_title: string | null
}

export interface GutenbergFavorite {
  id: number
  user_id: number
  book_id: number
  notes: string | null
  created_at: string
  book: GutenbergBookSummary | null
}

export interface GutenbergPatronDashboard {
  recent_downloads: GutenbergDownload[]
  favorites: GutenbergFavorite[]
  total_downloads: number
  total_favorites: number
  recommended_books: GutenbergBookSummary[]
}

export interface GutenbergStats {
  total_books: number
  total_downloads: number
  total_favorites: number
  unique_patrons_downloaded: number
  popular_books: GutenbergBookSummary[]
  popular_subjects: Record<string, number>[]
  downloads_by_format: Record<string, number>
  recent_downloads: GutenbergDownload[]
}

export interface GutenbergSyncStatus {
  id: number
  last_full_sync_at: string | null
  last_incremental_sync_at: string | null
  total_books_synced: number
  last_synced_page: number
  is_syncing: boolean
  sync_started_at: string | null
  sync_error: string | null
  created_at: string
  updated_at: string
}

// ==================== API Functions ====================

export async function searchGutenbergBooks(
  token: string | null,
  params: {
    q?: string
    author?: string
    title?: string
    topic?: string
    languages?: string
    page?: number
    source?: 'api' | 'local'
  }
): Promise<GutenbergSearchResponse> {
  const searchParams = new URLSearchParams()
  if (params.q) searchParams.append('q', params.q)
  if (params.author) searchParams.append('author', params.author)
  if (params.title) searchParams.append('title', params.title)
  if (params.topic) searchParams.append('topic', params.topic)
  if (params.languages) searchParams.append('languages', params.languages)
  if (params.page) searchParams.append('page', params.page.toString())
  if (params.source) searchParams.append('source', params.source)

  return fetchApi<GutenbergSearchResponse>(
    `/gutenberg/search?${searchParams.toString()}`,
    token ? { token } : {}
  )
}

export async function getGutenbergBook(
  token: string | null,
  bookId: number
): Promise<GutenbergBookDetail> {
  return fetchApi<GutenbergBookDetail>(`/gutenberg/books/${bookId}`, token ? { token } : {})
}

export async function getGutenbergBookByGutenbergId(
  token: string | null,
  gutenbergId: number
): Promise<GutenbergBookDetail> {
  return fetchApi<GutenbergBookDetail>(
    `/gutenberg/books/gutenberg/${gutenbergId}`,
    token ? { token } : {}
  )
}

export async function getPopularBooks(
  token: string | null,
  params?: { languages?: string; limit?: number }
): Promise<GutenbergBookSummary[]> {
  const searchParams = new URLSearchParams()
  if (params?.languages) searchParams.append('languages', params.languages)
  if (params?.limit) searchParams.append('limit', params.limit.toString())

  const query = searchParams.toString()
  return fetchApi<GutenbergBookSummary[]>(
    `/gutenberg/popular${query ? `?${query}` : ''}`,
    token ? { token } : {}
  )
}

export async function recordDownload(
  token: string,
  bookId: number,
  format: GutenbergFormat
): Promise<GutenbergDownload> {
  return fetchApi<GutenbergDownload>('/gutenberg/downloads', {
    method: 'POST',
    token,
    body: { book_id: bookId, format },
  })
}

export async function getMyDownloads(
  token: string,
  limit?: number
): Promise<GutenbergDownload[]> {
  const query = limit ? `?limit=${limit}` : ''
  return fetchApi<GutenbergDownload[]>(`/gutenberg/downloads${query}`, { token })
}

async function addFavoriteGutenberg(
  token: string,
  bookId: number,
  notes?: string
): Promise<GutenbergFavorite> {
  return fetchApi<GutenbergFavorite>('/gutenberg/favorites', {
    method: 'POST',
    token,
    body: { book_id: bookId, notes },
  })
}

async function removeFavoriteGutenberg(
  token: string,
  bookId: number
): Promise<{ ok: boolean; message: string }> {
  return fetchApi(`/gutenberg/favorites/${bookId}`, {
    method: 'DELETE',
    token,
  })
}

export { addFavoriteGutenberg, removeFavoriteGutenberg }

async function getMyFavoritesGutenberg(
  token: string,
  limit?: number
): Promise<GutenbergFavorite[]> {
  const query = limit ? `?limit=${limit}` : ''
  return fetchApi<GutenbergFavorite[]>(`/gutenberg/favorites${query}`, { token })
}

export { getMyFavoritesGutenberg }

export async function getPatronDashboard(
  token: string
): Promise<GutenbergPatronDashboard> {
  return fetchApi<GutenbergPatronDashboard>('/gutenberg/dashboard', { token })
}

export async function getGutenbergStats(
  token: string
): Promise<GutenbergStats> {
  return fetchApi<GutenbergStats>('/gutenberg/stats', { token })
}

export async function getSyncStatus(
  token: string
): Promise<GutenbergSyncStatus | null> {
  return fetchApi<GutenbergSyncStatus | null>('/gutenberg/sync/status', { token })
}

export async function triggerSync(
  token: string,
  options?: {
    full_sync?: boolean
    max_pages?: number
    languages?: string[]
  }
): Promise<{
  ok: boolean
  message: string
  books_synced: number
  pages_synced: number
}> {
  return fetchApi('/gutenberg/sync', {
    method: 'POST',
    token,
    body: options || {},
  })
}

// ==================== Utility Functions ====================

export function formatDownloadCount(count: number): string {
  if (count >= 1000000) {
    return `${(count / 1000000).toFixed(1)}M`
  }
  if (count >= 1000) {
    return `${(count / 1000).toFixed(1)}K`
  }
  return count.toString()
}

export function getFormatIcon(format: GutenbergFormat): string {
  switch (format) {
    case 'epub':
      return '📱'
    case 'kindle':
      return '📚'
    case 'html':
      return '🌐'
    case 'plain_text':
      return '📄'
    case 'pdf':
      return '📑'
    default:
      return '📖'
  }
}

export function getFormatLabel(format: GutenbergFormat): string {
  switch (format) {
    case 'epub':
      return 'EPUB'
    case 'kindle':
      return 'Kindle'
    case 'html':
      return 'Read Online'
    case 'plain_text':
      return 'Plain Text'
    case 'pdf':
      return 'PDF'
    default:
      return format
  }
}

export function getLanguageName(code: string): string {
  const languages: Record<string, string> = {
    en: 'English',
    fr: 'French',
    de: 'German',
    es: 'Spanish',
    it: 'Italian',
    pt: 'Portuguese',
    nl: 'Dutch',
    la: 'Latin',
    zh: 'Chinese',
    ja: 'Japanese',
    ru: 'Russian',
  }
  return languages[code] || code.toUpperCase()
}
