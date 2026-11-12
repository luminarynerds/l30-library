/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Reports API Service Tests
 *
 * Tests for reports API functions including:
 * - Daily statistics
 * - Hold statistics
 * - Fine statistics
 * - Popular items
 * - Overdue items
 * - Circulation trends
 * - Daily details
 * - Inventory summary
 * - Aggregate report fetching
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import * as apiClient from '@/lib/api-client'
import * as tokenStore from '@/utils/tokenStore'
import {
  getDailyStats,
  getHoldsStats,
  getFineStats,
  getPopularItemsFromReports,
  getOverdueItems,
  getCirculationTrendsFromReports,
  getDailyDetails,
  getCirculationTrendsWithComparison,
  getInventorySummary,
  fetchAllCirculationReports,
} from '@/api/reports-api'

// Mock the api-client module
vi.mock('@/lib/api-client', () => ({
  fetchApi: vi.fn(),
  isApiError: vi.fn(),
}))

// Mock the tokenStore module
vi.mock('@/utils/tokenStore', () => ({
  getAccessToken: vi.fn(),
}))

describe('Reports API', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(tokenStore.getAccessToken).mockReturnValue('test-token')
  })

  // ==================== Daily Stats Tests ====================

  describe('getDailyStats', () => {
    it('should return daily statistics', async () => {
      const mockStats = {
        date: '2024-01-15',
        checkouts_today: 45,
        returns_today: 38,
        active_checkouts: 1250,
        overdue_count: 23,
      }
      vi.mocked(apiClient.fetchApi).mockResolvedValue(mockStats)

      const result = await getDailyStats()

      expect(result).toEqual(mockStats)
      expect(apiClient.fetchApi).toHaveBeenCalledWith('/reports/circulation/daily', {
        token: 'test-token',
      })
    })

    it('should handle zero values', async () => {
      const mockStats = {
        date: '2024-01-01',
        checkouts_today: 0,
        returns_today: 0,
        active_checkouts: 0,
        overdue_count: 0,
      }
      vi.mocked(apiClient.fetchApi).mockResolvedValue(mockStats)

      const result = await getDailyStats()

      expect(result.checkouts_today).toBe(0)
      expect(result.returns_today).toBe(0)
    })

    it('should work without token', async () => {
      vi.mocked(tokenStore.getAccessToken).mockReturnValue(null)
      vi.mocked(apiClient.fetchApi).mockResolvedValue({ date: '2024-01-15' })

      await getDailyStats()

      expect(apiClient.fetchApi).toHaveBeenCalledWith('/reports/circulation/daily', {
        token: undefined,
      })
    })

    it('should throw error with detail on API error', async () => {
      const apiError = { status: 403, detail: 'Access denied' }
      vi.mocked(apiClient.fetchApi).mockRejectedValue(apiError)
      vi.mocked(apiClient.isApiError).mockReturnValue(true)

      await expect(getDailyStats()).rejects.toThrow('Access denied')
    })

    it('should throw generic error when no detail', async () => {
      const apiError = { status: 500 }
      vi.mocked(apiClient.fetchApi).mockRejectedValue(apiError)
      vi.mocked(apiClient.isApiError).mockReturnValue(true)

      await expect(getDailyStats()).rejects.toThrow('Request failed with status 500')
    })

    it('should re-throw non-API errors', async () => {
      vi.mocked(apiClient.fetchApi).mockRejectedValue(new Error('Network error'))
      vi.mocked(apiClient.isApiError).mockReturnValue(false)

      await expect(getDailyStats()).rejects.toThrow('Network error')
    })
  })

  // ==================== Holds Stats Tests ====================

  describe('getHoldsStats', () => {
    it('should return hold statistics', async () => {
      const mockStats = {
        pending_holds: 156,
        ready_for_pickup: 42,
        avg_wait_days: 4.5,
      }
      vi.mocked(apiClient.fetchApi).mockResolvedValue(mockStats)

      const result = await getHoldsStats()

      expect(result).toEqual(mockStats)
      expect(apiClient.fetchApi).toHaveBeenCalledWith('/reports/circulation/holds', {
        token: 'test-token',
      })
    })

    it('should handle null avg_wait_days', async () => {
      const mockStats = {
        pending_holds: 0,
        ready_for_pickup: 0,
        avg_wait_days: null,
      }
      vi.mocked(apiClient.fetchApi).mockResolvedValue(mockStats)

      const result = await getHoldsStats()

      expect(result.avg_wait_days).toBeNull()
    })

    it('should throw error on failure', async () => {
      const apiError = { status: 500, detail: 'Database error' }
      vi.mocked(apiClient.fetchApi).mockRejectedValue(apiError)
      vi.mocked(apiClient.isApiError).mockReturnValue(true)

      await expect(getHoldsStats()).rejects.toThrow('Database error')
    })
  })

  // ==================== Fine Stats Tests ====================

  describe('getFineStats', () => {
    it('should return fine statistics', async () => {
      const mockStats = {
        outstanding_total: 1250.5,
        paid_this_month: 450.25,
        waived_this_month: 75.0,
        patrons_with_fines: 89,
      }
      vi.mocked(apiClient.fetchApi).mockResolvedValue(mockStats)

      const result = await getFineStats()

      expect(result).toEqual(mockStats)
      expect(apiClient.fetchApi).toHaveBeenCalledWith('/reports/circulation/fines', {
        token: 'test-token',
      })
    })

    it('should handle zero fines', async () => {
      const mockStats = {
        outstanding_total: 0,
        paid_this_month: 0,
        waived_this_month: 0,
        patrons_with_fines: 0,
      }
      vi.mocked(apiClient.fetchApi).mockResolvedValue(mockStats)

      const result = await getFineStats()

      expect(result.outstanding_total).toBe(0)
      expect(result.patrons_with_fines).toBe(0)
    })

    it('should throw error on failure', async () => {
      const apiError = { status: 403, detail: 'Insufficient permissions' }
      vi.mocked(apiClient.fetchApi).mockRejectedValue(apiError)
      vi.mocked(apiClient.isApiError).mockReturnValue(true)

      await expect(getFineStats()).rejects.toThrow('Insufficient permissions')
    })
  })

  // ==================== Popular Items Tests ====================

  describe('getPopularItemsFromReports', () => {
    it('should return popular items', async () => {
      const mockResponse = {
        items: [
          { catalog_item_id: 1, title: 'Book One', author: 'Author A', checkout_count: 150 },
          { catalog_item_id: 2, title: 'Book Two', author: 'Author B', checkout_count: 120 },
        ],
      }
      vi.mocked(apiClient.fetchApi).mockResolvedValue(mockResponse)

      const result = await getPopularItemsFromReports()

      expect(result).toEqual(mockResponse.items)
      expect(apiClient.fetchApi).toHaveBeenCalledWith('/reports/circulation/popular', {
        token: 'test-token',
      })
    })

    it('should support days parameter', async () => {
      vi.mocked(apiClient.fetchApi).mockResolvedValue({ items: [] })

      await getPopularItemsFromReports({ days: 7 })

      expect(apiClient.fetchApi).toHaveBeenCalledWith('/reports/circulation/popular?days=7', {
        token: 'test-token',
      })
    })

    it('should support limit parameter', async () => {
      vi.mocked(apiClient.fetchApi).mockResolvedValue({ items: [] })

      await getPopularItemsFromReports({ limit: 5 })

      expect(apiClient.fetchApi).toHaveBeenCalledWith('/reports/circulation/popular?limit=5', {
        token: 'test-token',
      })
    })

    it('should support both parameters', async () => {
      vi.mocked(apiClient.fetchApi).mockResolvedValue({ items: [] })

      await getPopularItemsFromReports({ days: 30, limit: 10 })

      expect(apiClient.fetchApi).toHaveBeenCalledWith(
        expect.stringContaining('days=30'),
        expect.anything()
      )
      expect(apiClient.fetchApi).toHaveBeenCalledWith(
        expect.stringContaining('limit=10'),
        expect.anything()
      )
    })

    it('should return empty array when response has no items', async () => {
      vi.mocked(apiClient.fetchApi).mockResolvedValue({})

      const result = await getPopularItemsFromReports()

      expect(result).toEqual([])
    })

    it('should throw error on failure', async () => {
      const apiError = { status: 500, detail: 'Query timeout' }
      vi.mocked(apiClient.fetchApi).mockRejectedValue(apiError)
      vi.mocked(apiClient.isApiError).mockReturnValue(true)

      await expect(getPopularItemsFromReports()).rejects.toThrow('Query timeout')
    })
  })

  // ==================== Overdue Items Tests ====================

  describe('getOverdueItems', () => {
    it('should return overdue items', async () => {
      const mockResponse = {
        items: [
          {
            checkout_id: 1,
            patron_name: 'John Doe',
            patron_email: 'john@example.com',
            item_title: 'Overdue Book',
            due_date: '2024-01-01',
            days_overdue: 14,
          },
        ],
      }
      vi.mocked(apiClient.fetchApi).mockResolvedValue(mockResponse)

      const result = await getOverdueItems()

      expect(result).toEqual(mockResponse.items)
      expect(apiClient.fetchApi).toHaveBeenCalledWith('/reports/circulation/overdue', {
        token: 'test-token',
      })
    })

    it('should support pagination parameters', async () => {
      vi.mocked(apiClient.fetchApi).mockResolvedValue({ items: [] })

      await getOverdueItems({ per_page: 25, page: 2 })

      expect(apiClient.fetchApi).toHaveBeenCalledWith(
        expect.stringContaining('per_page=25'),
        expect.anything()
      )
      expect(apiClient.fetchApi).toHaveBeenCalledWith(
        expect.stringContaining('page=2'),
        expect.anything()
      )
    })

    it('should return empty array when no overdue items', async () => {
      vi.mocked(apiClient.fetchApi).mockResolvedValue({ items: [] })

      const result = await getOverdueItems()

      expect(result).toEqual([])
    })

    it('should throw error on failure', async () => {
      const apiError = { status: 403, detail: 'Access denied' }
      vi.mocked(apiClient.fetchApi).mockRejectedValue(apiError)
      vi.mocked(apiClient.isApiError).mockReturnValue(true)

      await expect(getOverdueItems()).rejects.toThrow('Access denied')
    })
  })

  // ==================== Circulation Trends Tests ====================

  describe('getCirculationTrendsFromReports', () => {
    it('should return trend data', async () => {
      const mockResponse = {
        data: [
          { date: '2024-01-01', checkouts: 45 },
          { date: '2024-01-02', checkouts: 52 },
          { date: '2024-01-03', checkouts: 38 },
        ],
      }
      vi.mocked(apiClient.fetchApi).mockResolvedValue(mockResponse)

      const result = await getCirculationTrendsFromReports()

      expect(result).toEqual(mockResponse.data)
      expect(apiClient.fetchApi).toHaveBeenCalledWith('/reports/circulation/trends', {
        token: 'test-token',
      })
    })

    it('should support days parameter', async () => {
      vi.mocked(apiClient.fetchApi).mockResolvedValue({ data: [] })

      await getCirculationTrendsFromReports({ days: 7 })

      expect(apiClient.fetchApi).toHaveBeenCalledWith('/reports/circulation/trends?days=7', {
        token: 'test-token',
      })
    })

    it('should support comparison parameters', async () => {
      vi.mocked(apiClient.fetchApi).mockResolvedValue({ data: [] })

      await getCirculationTrendsFromReports({ compare_previous_period: true, compare_previous_year: true })

      expect(apiClient.fetchApi).toHaveBeenCalledWith(
        expect.stringContaining('compare_previous_period=true'),
        expect.anything()
      )
      expect(apiClient.fetchApi).toHaveBeenCalledWith(
        expect.stringContaining('compare_previous_year=true'),
        expect.anything()
      )
    })

    it('should return empty array when no data', async () => {
      vi.mocked(apiClient.fetchApi).mockResolvedValue({})

      const result = await getCirculationTrendsFromReports()

      expect(result).toEqual([])
    })

    it('should throw error on failure', async () => {
      const apiError = { status: 500, detail: 'Database timeout' }
      vi.mocked(apiClient.fetchApi).mockRejectedValue(apiError)
      vi.mocked(apiClient.isApiError).mockReturnValue(true)

      await expect(getCirculationTrendsFromReports()).rejects.toThrow('Database timeout')
    })
  })

  // ==================== Daily Details Tests ====================

  describe('getDailyDetails', () => {
    it('should return daily drill-down data', async () => {
      const mockData = {
        date: '2024-01-15',
        checkouts: [
          {
            checkout_id: 1,
            item_title: 'Book One',
            item_author: 'Author A',
            patron_name: 'John Doe',
            checked_out_at: '2024-01-15T10:30:00Z',
          },
        ],
        returns: [
          {
            checkout_id: 2,
            item_title: 'Book Two',
            item_author: 'Author B',
            patron_name: 'Jane Smith',
            returned_at: '2024-01-15T14:00:00Z',
          },
        ],
        patron_count: 25,
      }
      vi.mocked(apiClient.fetchApi).mockResolvedValue(mockData)

      const result = await getDailyDetails({ date: '2024-01-15' })

      expect(result).toEqual(mockData)
      expect(apiClient.fetchApi).toHaveBeenCalledWith(
        '/reports/circulation/daily-details?date=2024-01-15',
        { token: 'test-token' }
      )
    })

    it('should handle empty day', async () => {
      const mockData = {
        date: '2024-01-01',
        checkouts: [],
        returns: [],
        patron_count: 0,
      }
      vi.mocked(apiClient.fetchApi).mockResolvedValue(mockData)

      const result = await getDailyDetails({ date: '2024-01-01' })

      expect(result.checkouts).toEqual([])
      expect(result.returns).toEqual([])
      expect(result.patron_count).toBe(0)
    })

    it('should throw error on failure', async () => {
      const apiError = { status: 400, detail: 'Invalid date format' }
      vi.mocked(apiClient.fetchApi).mockRejectedValue(apiError)
      vi.mocked(apiClient.isApiError).mockReturnValue(true)

      await expect(getDailyDetails({ date: 'invalid' })).rejects.toThrow('Invalid date format')
    })
  })

  // ==================== Trends with Comparison Tests ====================

  describe('getCirculationTrendsWithComparison', () => {
    it('should return comparison trend data', async () => {
      const mockResponse = {
        data: [
          { date: '2024-01-01', checkouts: 45, checkouts_previous: 40, checkouts_previous_year: 35 },
          { date: '2024-01-02', checkouts: 52, checkouts_previous: 48, checkouts_previous_year: 42 },
        ],
      }
      vi.mocked(apiClient.fetchApi).mockResolvedValue(mockResponse)

      const result = await getCirculationTrendsWithComparison({
        compare_previous_period: true,
        compare_previous_year: true,
      })

      expect(result).toEqual(mockResponse.data)
      expect(result[0]!.checkouts_previous).toBe(40)
      expect(result[0]!.checkouts_previous_year).toBe(35)
    })

    it('should return empty array when no data', async () => {
      vi.mocked(apiClient.fetchApi).mockResolvedValue({})

      const result = await getCirculationTrendsWithComparison()

      expect(result).toEqual([])
    })
  })

  // ==================== Inventory Summary Tests ====================

  describe('getInventorySummary', () => {
    it('should return inventory summary', async () => {
      const mockSummary = {
        total_copies: 15000,
        total_titles: 8500,
        by_condition: {
          excellent: 10000,
          good: 3500,
          fair: 1000,
          poor: 500,
        },
      }
      vi.mocked(apiClient.fetchApi).mockResolvedValue(mockSummary)

      const result = await getInventorySummary()

      expect(result).toEqual(mockSummary)
      expect(apiClient.fetchApi).toHaveBeenCalledWith('/reports/inventory/summary', {
        token: 'test-token',
      })
    })

    it('should handle empty inventory', async () => {
      const mockSummary = {
        total_copies: 0,
        total_titles: 0,
        by_condition: {},
      }
      vi.mocked(apiClient.fetchApi).mockResolvedValue(mockSummary)

      const result = await getInventorySummary()

      expect(result.total_copies).toBe(0)
      expect(result.by_condition).toEqual({})
    })

    it('should throw error on failure', async () => {
      const apiError = { status: 500, detail: 'Server error' }
      vi.mocked(apiClient.fetchApi).mockRejectedValue(apiError)
      vi.mocked(apiClient.isApiError).mockReturnValue(true)

      await expect(getInventorySummary()).rejects.toThrow('Server error')
    })
  })

  // ==================== Fetch All Reports Tests ====================

  describe('fetchAllCirculationReports', () => {
    it('should fetch all reports in parallel', async () => {
      const mockDaily = { date: '2024-01-15', checkouts_today: 45 }
      const mockHolds = { pending_holds: 100 }
      const mockFines = { outstanding_total: 500 }
      const mockPopular = { items: [{ title: 'Popular Book' }] }
      const mockOverdue = { items: [{ patron_name: 'John' }] }
      const mockTrends = { data: [{ date: '2024-01-15', checkouts: 45 }] }
      const mockInventory = { total_copies: 15000 }

      vi.mocked(apiClient.fetchApi)
        .mockResolvedValueOnce(mockDaily)
        .mockResolvedValueOnce(mockHolds)
        .mockResolvedValueOnce(mockFines)
        .mockResolvedValueOnce(mockPopular)
        .mockResolvedValueOnce(mockOverdue)
        .mockResolvedValueOnce(mockTrends)
        .mockResolvedValueOnce(mockInventory)

      const result = await fetchAllCirculationReports()

      expect(result.daily).toEqual(mockDaily)
      expect(result.holds).toEqual(mockHolds)
      expect(result.fines).toEqual(mockFines)
      expect(result.popular).toEqual(mockPopular.items)
      expect(result.overdue).toEqual(mockOverdue.items)
      expect(result.trends).toEqual(mockTrends.data)
      expect(result.inventory).toEqual(mockInventory)
    })

    it('should use custom trendDays parameter', async () => {
      vi.mocked(apiClient.fetchApi).mockResolvedValue({ items: [], data: [] })

      await fetchAllCirculationReports(7)

      // Check that popular items uses the custom days
      expect(apiClient.fetchApi).toHaveBeenCalledWith(
        expect.stringContaining('days=7'),
        expect.anything()
      )
    })

    it('should use default trendDays of 30', async () => {
      vi.mocked(apiClient.fetchApi).mockResolvedValue({ items: [], data: [] })

      await fetchAllCirculationReports()

      // Check that popular items uses default 30 days
      expect(apiClient.fetchApi).toHaveBeenCalledWith(
        expect.stringContaining('days=30'),
        expect.anything()
      )
    })

    it('should degrade gracefully (not throw) if one report request fails', async () => {
      // fetchAllCirculationReports runs the 7 report calls through
      // Promise.allSettled and falls back to a sane default per field (#54)
      // so one flaky endpoint doesn't blank the whole staff dashboard.
      vi.mocked(apiClient.fetchApi)
        .mockResolvedValueOnce({ date: '2024-01-15' }) // daily succeeds
        .mockRejectedValueOnce({ status: 500, detail: 'Database error' }) // holds fails
        .mockResolvedValue({ items: [], data: [] }) // remaining calls succeed
      vi.mocked(apiClient.isApiError).mockReturnValue(true)

      const result = await fetchAllCirculationReports()

      expect(result.daily).toEqual({ date: '2024-01-15' })
      expect(result.holds).toEqual({ pending_holds: 0, ready_for_pickup: 0, avg_wait_days: null })
    })
  })
})
