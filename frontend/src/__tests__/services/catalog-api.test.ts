/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Catalog API Service Tests
 *
 * Tests for catalog API functions including:
 * - Search catalog
 * - Get catalog item details
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import * as apiClient from '@/lib/api-client'
import { searchCatalog, getCatalogItem } from '@/api/catalog-api'

// Mock the api-client module
vi.mock('@/lib/api-client', () => ({
  fetchApi: vi.fn(),
  isApiError: vi.fn(),
  // lib/api-helpers.ts imports getErrorMessage at module scope
  // (extractErrorMessage = getErrorMessage), and catalog-api.ts pulls in
  // api-helpers -- needs to exist even though this test never calls it.
  getErrorMessage: vi.fn((_err: unknown, fallback?: string) => fallback ?? 'Error'),
}))

describe('Catalog API', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  // ==================== Search Tests ====================

  describe('searchCatalog', () => {
    it('should return search results with pagination', async () => {
      const mockResults = {
        items: [
          {
            id: 1,
            title: 'The Great Gatsby',
            author: 'F. Scott Fitzgerald',
            item_type: 'book',
            status: 'available',
            isbn: '978-0743273565',
            publisher: 'Scribner',
            publication_year: 1925,
            description: 'A story of the Jazz Age',
            subjects: 'Fiction, American Literature',
            cover_url: '/covers/gatsby.jpg',
            page_count: 180,
            location: 'Fiction - F',
            barcode: '123456789',
            created_at: '2023-01-01T00:00:00Z',
          },
        ],
        total: 1,
        page: 1,
        per_page: 20,
        pages: 1,
      }
      vi.mocked(apiClient.fetchApi).mockResolvedValue(mockResults)

      const result = await searchCatalog({ query: 'gatsby' })

      expect(result).toEqual(mockResults)
      // searchCatalog builds `/catalog/${queryString}` — trailing slash before
      // the query string is intentional (backend route requires it).
      expect(apiClient.fetchApi).toHaveBeenCalledWith(expect.stringContaining('/catalog/?'))
      expect(apiClient.fetchApi).toHaveBeenCalledWith(expect.stringContaining('q=gatsby'))
    })

    it('should handle empty search query', async () => {
      const mockResults = {
        items: [],
        total: 0,
        page: 1,
        per_page: 20,
        pages: 0,
      }
      vi.mocked(apiClient.fetchApi).mockResolvedValue(mockResults)

      const result = await searchCatalog({})

      expect(result).toEqual(mockResults)
      // Empty queryString still leaves the trailing slash from the template.
      expect(apiClient.fetchApi).toHaveBeenCalledWith('/catalog/')
    })

    it('should support pagination', async () => {
      const mockResults = {
        items: [{ id: 21, title: 'Book 21' }],
        total: 50,
        page: 2,
        per_page: 20,
        pages: 3,
      }
      vi.mocked(apiClient.fetchApi).mockResolvedValue(mockResults)

      const result = await searchCatalog({ query: 'fiction', page: 2, per_page: 20 })

      expect(result).toEqual(mockResults)
      expect(apiClient.fetchApi).toHaveBeenCalledWith(expect.stringContaining('q=fiction'))
      expect(apiClient.fetchApi).toHaveBeenCalledWith(expect.stringContaining('page=2'))
    })

    it('should URL encode special characters in query', async () => {
      vi.mocked(apiClient.fetchApi).mockResolvedValue({ items: [], total: 0, page: 1, per_page: 20, pages: 0 })

      await searchCatalog({ query: 'C++ programming' })

      // URLSearchParams will encode the space and + correctly
      expect(apiClient.fetchApi).toHaveBeenCalledWith(expect.stringContaining('q=C%2B%2B+programming'))
    })

    it('should return multiple items', async () => {
      const mockResults = {
        items: [
          { id: 1, title: 'Book One', author: 'Author A' },
          { id: 2, title: 'Book Two', author: 'Author B' },
          { id: 3, title: 'Book Three', author: 'Author C' },
        ],
        total: 3,
        page: 1,
        per_page: 20,
        pages: 1,
      }
      vi.mocked(apiClient.fetchApi).mockResolvedValue(mockResults)

      const result = await searchCatalog({ query: 'book' })

      expect(result.items).toHaveLength(3)
      expect(result.total).toBe(3)
    })

    it('should throw error when search fails', async () => {
      vi.mocked(apiClient.fetchApi).mockRejectedValue(new Error('Server error'))

      await expect(searchCatalog({ query: 'test' })).rejects.toThrow('Failed to search catalog')
    })

    it('should throw error on network failure', async () => {
      vi.mocked(apiClient.fetchApi).mockRejectedValue(new Error('Network error'))

      await expect(searchCatalog({ query: 'test' })).rejects.toThrow('Failed to search catalog')
    })
  })

  // ==================== Get Item Tests ====================

  describe('getCatalogItem', () => {
    it('should return item details', async () => {
      const mockItem = {
        id: 1,
        title: 'The Great Gatsby',
        author: 'F. Scott Fitzgerald',
        item_type: 'book',
        status: 'available',
        isbn: '978-0743273565',
        publisher: 'Scribner',
        publication_year: 1925,
        description: 'A classic novel about the American Dream',
        subjects: 'Fiction, American Literature, Jazz Age',
        cover_url: '/covers/gatsby.jpg',
        page_count: 180,
        location: 'Fiction - F',
        barcode: '123456789',
        created_at: '2023-01-01T00:00:00Z',
      }
      vi.mocked(apiClient.fetchApi).mockResolvedValue(mockItem)

      const result = await getCatalogItem(1)

      expect(result).toEqual(mockItem)
      expect(apiClient.fetchApi).toHaveBeenCalledWith('/catalog/1')
    })

    it('should return item with null optional fields', async () => {
      const mockItem = {
        id: 2,
        title: 'Mystery Book',
        author: null,
        item_type: 'book',
        status: 'checked_out',
        isbn: null,
        publisher: null,
        publication_year: null,
        description: null,
        subjects: null,
        cover_url: null,
        page_count: null,
        location: null,
        barcode: '987654321',
        created_at: '2023-06-15T00:00:00Z',
      }
      vi.mocked(apiClient.fetchApi).mockResolvedValue(mockItem)

      const result = await getCatalogItem(2)

      expect(result.author).toBeNull()
      expect(result.isbn).toBeNull()
      expect(result.cover_url).toBeNull()
    })

    it('should throw "Item not found" for 404 error', async () => {
      const apiError = { status: 404, detail: 'Not found' }
      vi.mocked(apiClient.fetchApi).mockRejectedValue(apiError)
      vi.mocked(apiClient.isApiError).mockReturnValue(true)

      await expect(getCatalogItem(999)).rejects.toThrow('Item not found')
    })

    it('should throw generic error for other API errors', async () => {
      const apiError = { status: 500, detail: 'Database error' }
      vi.mocked(apiClient.fetchApi).mockRejectedValue(apiError)
      vi.mocked(apiClient.isApiError).mockReturnValue(true)

      await expect(getCatalogItem(1)).rejects.toThrow('Failed to fetch catalog item')
    })

    it('should throw generic error for non-API errors', async () => {
      vi.mocked(apiClient.fetchApi).mockRejectedValue(new Error('Network error'))
      vi.mocked(apiClient.isApiError).mockReturnValue(false)

      await expect(getCatalogItem(1)).rejects.toThrow('Failed to fetch catalog item')
    })

    it('should handle different item types', async () => {
      const itemTypes = ['book', 'dvd', 'audiobook', 'magazine', 'ebook']

      for (const itemType of itemTypes) {
        vi.mocked(apiClient.fetchApi).mockResolvedValue({
          id: 1,
          title: 'Test Item',
          item_type: itemType,
          status: 'available',
        })

        const result = await getCatalogItem(1)
        expect(result.item_type).toBe(itemType)
      }
    })

    it('should handle different item statuses', async () => {
      const statuses = ['available', 'checked_out', 'on_hold', 'in_transit', 'lost', 'damaged']

      for (const status of statuses) {
        vi.mocked(apiClient.fetchApi).mockResolvedValue({
          id: 1,
          title: 'Test Item',
          item_type: 'book',
          status: status,
        })

        const result = await getCatalogItem(1)
        expect(result.status).toBe(status)
      }
    })
  })
})
