/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { toDisplayItem } from '@/pages/catalog/utils/catalogDisplayItem'
import type { UnifiedSearchResult } from '@/api/domains/catalog/unified-search-api'

vi.mock('@/lib/api-client', () => ({
  fetchApi: vi.fn(),
}))

import { fetchApi } from '@/lib/api-client'
import { getPublicBookDetail, getIndieCatalogRails, getIndieCatalogGenres, getDiscoveryPage } from '@/api/indie-catalog-api'

const mockFetchApi = vi.mocked(fetchApi)

function makeIndieResult(overrides: Partial<UnifiedSearchResult> = {}): UnifiedSearchResult {
  return {
    id: 'indie:83',
    source: 'indie',
    source_id: 'indie:83',
    title: 'Test Book',
    author: 'Test Author',
    authors: ['Test Author'],
    format: 'ebook',
    format_details: [],
    description: null,
    cover_url: null,
    isbn: null,
    publisher: null,
    publication_year: null,
    subjects: [],
    language: 'en',
    is_available: true,
    copies_available: 2,
    copies_total: 3,
    hold_count: null,
    estimated_wait_days: null,
    download_formats: [],
    relevance_score: 1,
    related_sources: [],
    ...overrides,
  }
}

describe('Tier-3 indie cutover', () => {
  beforeEach(() => {
    mockFetchApi.mockReset()
  })

  describe('toDisplayItem — indie source_id parsing', () => {
    it('parses "indie:83" source_id to numeric id 83', () => {
      const result = makeIndieResult({ source_id: 'indie:83' })
      const item = toDisplayItem(result)
      expect(item.id).toBe(83)
    })

    it('parses "indie:1" correctly', () => {
      const result = makeIndieResult({ source_id: 'indie:1' })
      const item = toDisplayItem(result)
      expect(item.id).toBe(1)
    })

    it('falls back to numeric parse for non-indie source', () => {
      const result = makeIndieResult({ source: 'local', source_id: '42' })
      const item = toDisplayItem(result)
      expect(item.id).toBe(42)
    })

    it('preserves source field', () => {
      const result = makeIndieResult()
      const item = toDisplayItem(result)
      expect(item.source).toBe('indie')
    })
  })

  describe('getPublicBookDetail', () => {
    it('fetches from /indie/catalog/{id} not /ebooks/', async () => {
      mockFetchApi.mockResolvedValue({
        id: 42,
        title: 'Local Title',
        author_pen_name: 'Pen Name',
        description: 'A good book',
        cover_url: null,
        genre: 'fiction',
        language: 'en',
        content_warnings: [],
        available_copies: 1,
        total_copies: 2,
        publication_year: 2024,
        subjects: ['subject1', 'subject2'],
        word_count: 50000,
        page_count: 200,
        isbn: '978-0-000-00000-0',
        content_rating: 'g',
        author_id: 7,
        average_rating: 4.2,
        rating_count: 15,
        total_borrows: 30,
      })

      await getPublicBookDetail('42')

      expect(mockFetchApi).toHaveBeenCalledWith('/indie/catalog/42')
      expect(mockFetchApi).not.toHaveBeenCalledWith(expect.stringContaining('/ebooks/'))
    })

    it('maps subjects, word_count, page_count, rating fields', async () => {
      mockFetchApi.mockResolvedValue({
        id: 42,
        title: 'Test',
        author_pen_name: 'Author',
        description: null,
        cover_url: null,
        genre: null,
        language: 'en',
        content_warnings: [],
        available_copies: 1,
        total_copies: 1,
        publication_year: null,
        subjects: ['sci-fi', 'space'],
        word_count: 75000,
        page_count: 300,
        isbn: null,
        content_rating: 'pg',
        author_id: 5,
        average_rating: 3.8,
        rating_count: 22,
        total_borrows: 44,
      })

      const detail = await getPublicBookDetail('local-title-42')

      expect(detail.subjects).toEqual(['sci-fi', 'space'])
      expect(detail.word_count).toBe(75000)
      expect(detail.page_count).toBe(300)
      expect(detail.rating_count).toBe(22)
      expect(detail.total_borrows).toBe(44)
      expect(detail.average_rating).toBe(3.8)
      expect(detail.content_rating).toBe('pg')
      expect(detail.borrow_duration_days).toBe(21)
    })

    it('extracts id from slug before fetching', async () => {
      mockFetchApi.mockResolvedValue({
        id: 83, title: 'T', author_pen_name: 'A', description: null, cover_url: null,
        genre: null, language: 'en', content_warnings: [], available_copies: 0, total_copies: 1,
        publication_year: null, subjects: [], word_count: null, page_count: null, isbn: null,
        content_rating: 'unrated', author_id: null, average_rating: null, rating_count: 0, total_borrows: 0,
      })

      await getPublicBookDetail('some-title-83')
      expect(mockFetchApi).toHaveBeenCalledWith('/indie/catalog/83')
    })

    it('sets author_id to 0 regardless of backend value (plain name, no link)', async () => {
      mockFetchApi.mockResolvedValue({
        id: 10, title: 'T', author_pen_name: 'A', description: null, cover_url: null,
        genre: null, language: 'en', content_warnings: [], available_copies: 1, total_copies: 1,
        publication_year: null, subjects: [], word_count: null, page_count: null, isbn: null,
        content_rating: 'g', author_id: 99, average_rating: null, rating_count: 0, total_borrows: 0,
      })

      const detail = await getPublicBookDetail('10')
      expect(detail.author_id).toBe(0)
    })
  })

  describe('getIndieCatalogRails', () => {
    it('fetches from /indie/catalog/rails', async () => {
      mockFetchApi.mockResolvedValue({ featured: [], popular: [], new: [] })
      await getIndieCatalogRails()
      expect(mockFetchApi).toHaveBeenCalledWith('/indie/catalog/rails?limit=12')
    })
  })

  describe('getIndieCatalogGenres', () => {
    it('fetches from /indie/catalog/genres', async () => {
      mockFetchApi.mockResolvedValue([{ genre: 'fiction', count: 10 }])
      await getIndieCatalogGenres()
      expect(mockFetchApi).toHaveBeenCalledWith('/indie/catalog/genres')
    })
  })

  describe('getDiscoveryPage', () => {
    it('populates featured from rails endpoint', async () => {
      const railsData = {
        featured: [{ id: 1, title: 'Featured', author_pen_name: 'Auth', description: null, cover_url: null, genre: 'fiction', language: 'en', content_warnings: [], available_copies: 1, total_copies: 1, publication_year: null }],
        popular: [],
        new: [],
      }
      mockFetchApi
        .mockResolvedValueOnce(railsData)
        .mockResolvedValueOnce([{ genre: 'fiction', count: 5 }])

      const data = await getDiscoveryPage()
      expect(data.featured).toHaveLength(1)
      expect(data.featured[0]?.title).toBe('Featured')
      expect(data.popular_genres).toHaveLength(1)
      expect(data.popular_genres[0]?.name).toBe('fiction')
    })

    it('handles rails failure gracefully', async () => {
      mockFetchApi
        .mockRejectedValueOnce(new Error('network error'))
        .mockResolvedValueOnce([{ genre: 'mystery', count: 3 }])

      const data = await getDiscoveryPage()
      expect(data.featured).toHaveLength(0)
      expect(data.trending).toHaveLength(0)
      expect(data.new_arrivals).toHaveLength(0)
    })
  })
})
