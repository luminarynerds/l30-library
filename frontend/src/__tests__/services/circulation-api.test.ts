/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Circulation API Service Tests
 *
 * Tests for circulation API functions including:
 * - Checkouts (fetch, renew)
 * - Holds (fetch, place, cancel)
 * - History
 * - Fines
 * - Self-checkout
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import * as apiClient from '@/lib/api-client'
import {
  getMyCheckouts,
  getMyHolds,
  renewCheckout,
  cancelHold,
  getMyHistory,
  getMyFines,
  getMyFinesSummary,
  placeHold,
  lookupItemByBarcode,
  selfCheckoutItem,
} from '@/api/circulation-api'

// Mock the api-client module
vi.mock('@/lib/api-client', () => ({
  fetchApi: vi.fn(),
  isApiError: vi.fn(),
}))

describe('Circulation API', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  // ==================== Checkouts Tests ====================

  describe('getMyCheckouts', () => {
    it('should return list of checkouts', async () => {
      const mockCheckouts = [
        {
          id: 1,
          user_id: 1,
          item_id: 101,
          status: 'active',
          checked_out_at: '2024-01-01T10:00:00Z',
          due_date: '2024-01-15T23:59:59Z',
          returned_at: null,
          item_title: 'The Great Gatsby',
          item_author: 'F. Scott Fitzgerald',
        },
        {
          id: 2,
          user_id: 1,
          item_id: 102,
          status: 'overdue',
          checked_out_at: '2023-12-01T10:00:00Z',
          due_date: '2023-12-15T23:59:59Z',
          returned_at: null,
          item_title: '1984',
          item_author: 'George Orwell',
        },
      ]
      vi.mocked(apiClient.fetchApi).mockResolvedValue({
        data: mockCheckouts,
        pagination: { page: 1, per_page: 20, total: 2, total_pages: 1, has_next: false, has_previous: false },
      })

      const result = await getMyCheckouts('auth-token')

      expect(result).toEqual(mockCheckouts)
      expect(apiClient.fetchApi).toHaveBeenCalledWith('/circulation/checkouts', { token: 'auth-token' })
    })

    it('should return empty array when no checkouts', async () => {
      vi.mocked(apiClient.fetchApi).mockResolvedValue({
        data: [],
        pagination: { page: 1, per_page: 20, total: 0, total_pages: 0, has_next: false, has_previous: false },
      })

      const result = await getMyCheckouts('auth-token')

      expect(result).toEqual([])
    })

    it('should throw error when fetch fails', async () => {
      vi.mocked(apiClient.fetchApi).mockRejectedValue(new Error('Server error'))

      await expect(getMyCheckouts('token')).rejects.toThrow('Failed to fetch checkouts')
    })
  })

  describe('renewCheckout', () => {
    it('should successfully renew a checkout', async () => {
      const mockRenewedCheckout = {
        id: 1,
        user_id: 1,
        item_id: 101,
        status: 'active',
        checked_out_at: '2024-01-01T10:00:00Z',
        due_date: '2024-01-29T23:59:59Z', // Extended due date
        returned_at: null,
        item_title: 'The Great Gatsby',
        item_author: 'F. Scott Fitzgerald',
      }
      vi.mocked(apiClient.fetchApi).mockResolvedValue(mockRenewedCheckout)

      const result = await renewCheckout('auth-token', 1)

      expect(result).toEqual(mockRenewedCheckout)
      expect(apiClient.fetchApi).toHaveBeenCalledWith('/circulation/renew/1', {
        method: 'POST',
        token: 'auth-token',
      })
    })

    it('should throw error when renewal limit reached', async () => {
      const apiError = { status: 400, detail: 'Maximum renewals reached' }
      vi.mocked(apiClient.fetchApi).mockRejectedValue(apiError)
      vi.mocked(apiClient.isApiError).mockReturnValue(true)

      await expect(renewCheckout('token', 1)).rejects.toThrow('Maximum renewals reached')
    })

    it('should throw error when item has holds', async () => {
      const apiError = { status: 400, detail: 'Item has pending holds' }
      vi.mocked(apiClient.fetchApi).mockRejectedValue(apiError)
      vi.mocked(apiClient.isApiError).mockReturnValue(true)

      await expect(renewCheckout('token', 1)).rejects.toThrow('Item has pending holds')
    })

    it('should throw error when checkout not found', async () => {
      const apiError = { status: 404, detail: 'Checkout not found' }
      vi.mocked(apiClient.fetchApi).mockRejectedValue(apiError)
      vi.mocked(apiClient.isApiError).mockReturnValue(true)

      await expect(renewCheckout('token', 999)).rejects.toThrow('Checkout not found')
    })

    it('should throw "Renewal failed" when no detail', async () => {
      const apiError = { status: 500 }
      vi.mocked(apiClient.fetchApi).mockRejectedValue(apiError)
      vi.mocked(apiClient.isApiError).mockReturnValue(true)

      await expect(renewCheckout('token', 1)).rejects.toThrow('Renewal failed')
    })

    it('should re-throw non-API errors', async () => {
      vi.mocked(apiClient.fetchApi).mockRejectedValue(new Error('Network error'))
      vi.mocked(apiClient.isApiError).mockReturnValue(false)

      await expect(renewCheckout('token', 1)).rejects.toThrow('Network error')
    })
  })

  // ==================== Holds Tests ====================

  describe('getMyHolds', () => {
    it('should return list of holds', async () => {
      const mockHolds = [
        {
          id: 1,
          user_id: 1,
          item_id: 101,
          status: 'pending',
          position: 3,
          created_at: '2024-01-01T10:00:00Z',
          notified_at: null,
          expires_at: null,
          item_title: 'Dune',
          item_author: 'Frank Herbert',
        },
        {
          id: 2,
          user_id: 1,
          item_id: 102,
          status: 'ready',
          position: 0,
          created_at: '2023-12-15T10:00:00Z',
          notified_at: '2024-01-05T09:00:00Z',
          expires_at: '2024-01-12T23:59:59Z',
          item_title: 'Foundation',
          item_author: 'Isaac Asimov',
        },
      ]
      vi.mocked(apiClient.fetchApi).mockResolvedValue({
        data: mockHolds,
        pagination: { page: 1, per_page: 20, total: 2, total_pages: 1, has_next: false, has_previous: false },
      })

      const result = await getMyHolds('auth-token')

      expect(result).toEqual(mockHolds)
      expect(apiClient.fetchApi).toHaveBeenCalledWith('/circulation/holds', { token: 'auth-token' })
    })

    it('should return empty array when no holds', async () => {
      vi.mocked(apiClient.fetchApi).mockResolvedValue({
        data: [],
        pagination: { page: 1, per_page: 20, total: 0, total_pages: 0, has_next: false, has_previous: false },
      })

      const result = await getMyHolds('auth-token')

      expect(result).toEqual([])
    })

    it('should throw error when fetch fails', async () => {
      vi.mocked(apiClient.fetchApi).mockRejectedValue(new Error('Server error'))

      await expect(getMyHolds('token')).rejects.toThrow('Failed to fetch holds')
    })
  })

  describe('placeHold', () => {
    it('should successfully place a hold', async () => {
      const mockResponse = {
        message: 'Hold placed successfully',
        item_id: 101,
      }
      vi.mocked(apiClient.fetchApi).mockResolvedValue(mockResponse)

      const result = await placeHold('auth-token', 101)

      expect(result).toEqual(mockResponse)
      expect(apiClient.fetchApi).toHaveBeenCalledWith('/circulation/holds', {
        method: 'POST',
        token: 'auth-token',
        // pickup_location_id defaults to null when the caller doesn't pass one (#1567)
        body: { item_id: 101, pickup_location_id: null },
      })
    })

    it('should throw error when already on hold', async () => {
      const apiError = { status: 400, detail: 'You already have a hold on this item' }
      vi.mocked(apiClient.fetchApi).mockRejectedValue(apiError)
      vi.mocked(apiClient.isApiError).mockReturnValue(true)

      await expect(placeHold('token', 101)).rejects.toThrow('You already have a hold on this item')
    })

    it('should throw error when item not available for holds', async () => {
      const apiError = { status: 400, detail: 'Item is not available for holds' }
      vi.mocked(apiClient.fetchApi).mockRejectedValue(apiError)
      vi.mocked(apiClient.isApiError).mockReturnValue(true)

      await expect(placeHold('token', 101)).rejects.toThrow('Item is not available for holds')
    })

    it('should throw error when hold limit reached', async () => {
      const apiError = { status: 400, detail: 'Hold limit reached' }
      vi.mocked(apiClient.fetchApi).mockRejectedValue(apiError)
      vi.mocked(apiClient.isApiError).mockReturnValue(true)

      await expect(placeHold('token', 101)).rejects.toThrow('Hold limit reached')
    })

    it('preserves the patron-safe eligibility detail for a 403 hold block', async () => {
      const apiError = { status: 403, detail: 'Your library card has expired. Please contact the library to renew it.' }
      vi.mocked(apiClient.fetchApi).mockRejectedValue(apiError)
      vi.mocked(apiClient.isApiError).mockReturnValue(true)

      await expect(placeHold('token', 101)).rejects.toThrow('Your library card has expired')
    })

    it('should throw "Failed to place hold" when no detail', async () => {
      const apiError = { status: 500 }
      vi.mocked(apiClient.fetchApi).mockRejectedValue(apiError)
      vi.mocked(apiClient.isApiError).mockReturnValue(true)

      await expect(placeHold('token', 101)).rejects.toThrow('Failed to place hold')
    })

    it('should re-throw non-API errors', async () => {
      vi.mocked(apiClient.fetchApi).mockRejectedValue(new Error('Connection refused'))
      vi.mocked(apiClient.isApiError).mockReturnValue(false)

      await expect(placeHold('token', 101)).rejects.toThrow('Connection refused')
    })
  })

  describe('cancelHold', () => {
    it('should successfully cancel a hold', async () => {
      vi.mocked(apiClient.fetchApi).mockResolvedValue(undefined)

      await expect(cancelHold('auth-token', 1)).resolves.toBeUndefined()

      expect(apiClient.fetchApi).toHaveBeenCalledWith('/circulation/holds/1', {
        method: 'DELETE',
        token: 'auth-token',
        body: undefined,
        skipJsonParse: true,
      })
    })

    it('should send reason when provided', async () => {
      vi.mocked(apiClient.fetchApi).mockResolvedValue(undefined)

      await expect(cancelHold('auth-token', 1, 'No longer needed')).resolves.toBeUndefined()

      expect(apiClient.fetchApi).toHaveBeenCalledWith('/circulation/holds/1', {
        method: 'DELETE',
        token: 'auth-token',
        body: { reason: 'No longer needed' },
        skipJsonParse: true,
      })
    })

    it('should throw error when hold not found', async () => {
      const apiError = { status: 404, detail: 'Hold not found' }
      vi.mocked(apiClient.fetchApi).mockRejectedValue(apiError)
      vi.mocked(apiClient.isApiError).mockReturnValue(true)

      await expect(cancelHold('token', 999)).rejects.toThrow('This hold was not found. It may have already been cancelled.')
    })

    it('should throw error when hold already fulfilled', async () => {
      const apiError = { status: 400, detail: 'Hold has already been fulfilled' }
      vi.mocked(apiClient.fetchApi).mockRejectedValue(apiError)
      vi.mocked(apiClient.isApiError).mockReturnValue(true)

      await expect(cancelHold('token', 1)).rejects.toThrow('Hold has already been fulfilled')
    })

    it('should throw "Failed to cancel hold" when no detail', async () => {
      const apiError = { status: 500 }
      vi.mocked(apiClient.fetchApi).mockRejectedValue(apiError)
      vi.mocked(apiClient.isApiError).mockReturnValue(true)

      await expect(cancelHold('token', 1)).rejects.toThrow('Failed to cancel hold')
    })

    it('should re-throw non-API errors', async () => {
      vi.mocked(apiClient.fetchApi).mockRejectedValue(new Error('Timeout'))
      vi.mocked(apiClient.isApiError).mockReturnValue(false)

      await expect(cancelHold('token', 1)).rejects.toThrow('Timeout')
    })
  })

  // ==================== History Tests ====================

  describe('getMyHistory', () => {
    it('should return checkout history', async () => {
      const mockHistory = [
        {
          id: 10,
          user_id: 1,
          item_id: 101,
          status: 'returned',
          checked_out_at: '2023-11-01T10:00:00Z',
          due_date: '2023-11-15T23:59:59Z',
          returned_at: '2023-11-10T14:30:00Z',
          item_title: 'Pride and Prejudice',
          item_author: 'Jane Austen',
        },
      ]
      vi.mocked(apiClient.fetchApi).mockResolvedValue({
        data: mockHistory,
        pagination: { page: 1, per_page: 20, total: 1, total_pages: 1, has_next: false, has_previous: false },
      })

      const result = await getMyHistory('auth-token')

      expect(result).toEqual(mockHistory)
      expect(apiClient.fetchApi).toHaveBeenCalledWith('/circulation/history', { token: 'auth-token' })
    })

    it('should return empty array when no history', async () => {
      vi.mocked(apiClient.fetchApi).mockResolvedValue({
        data: [],
        pagination: { page: 1, per_page: 20, total: 0, total_pages: 0, has_next: false, has_previous: false },
      })

      const result = await getMyHistory('auth-token')

      expect(result).toEqual([])
    })

    it('should throw error when fetch fails', async () => {
      vi.mocked(apiClient.fetchApi).mockRejectedValue(new Error('Server error'))

      await expect(getMyHistory('token')).rejects.toThrow('Failed to fetch history')
    })
  })

  // ==================== Fines Tests ====================

  describe('getMyFines', () => {
    it('should return list of fines', async () => {
      const mockFines = [
        {
          id: 1,
          amount: '5.00',
          reason: 'overdue',
          description: 'Overdue fee for The Great Gatsby',
          created_at: '2024-01-01T00:00:00Z',
          item_title: 'The Great Gatsby',
        },
        {
          id: 2,
          amount: '25.00',
          reason: 'lost',
          description: 'Lost item replacement fee',
          created_at: '2024-01-05T00:00:00Z',
          paid_at: '2024-01-10T14:00:00Z',
          item_title: '1984',
        },
      ]
      vi.mocked(apiClient.fetchApi).mockResolvedValue({
        data: mockFines,
        pagination: { page: 1, per_page: 20, total: 2, total_pages: 1, has_next: false, has_previous: false },
      })

      const result = await getMyFines('auth-token')

      expect(result).toEqual(mockFines)
      expect(apiClient.fetchApi).toHaveBeenCalledWith('/circulation/fines', { token: 'auth-token' })
    })

    it('should return empty array when no fines', async () => {
      vi.mocked(apiClient.fetchApi).mockResolvedValue({
        data: [],
        pagination: { page: 1, per_page: 20, total: 0, total_pages: 0, has_next: false, has_previous: false },
      })

      const result = await getMyFines('auth-token')

      expect(result).toEqual([])
    })

    it('should throw error when fetch fails', async () => {
      vi.mocked(apiClient.fetchApi).mockRejectedValue(new Error('Server error'))

      await expect(getMyFines('token')).rejects.toThrow('Failed to fetch fines')
    })
  })

  describe('getMyFinesSummary', () => {
    it('should return fines summary', async () => {
      const mockSummary = {
        total_outstanding: 30.0,
        total_paid: 15.0,
        outstanding_count: 2,
        paid_count: 1,
      }
      vi.mocked(apiClient.fetchApi).mockResolvedValue(mockSummary)

      const result = await getMyFinesSummary('auth-token')

      expect(result).toEqual(mockSummary)
      expect(apiClient.fetchApi).toHaveBeenCalledWith('/circulation/fines/summary', { token: 'auth-token' })
    })

    it('should return zero values when no fines', async () => {
      const mockSummary = {
        total_outstanding: 0,
        total_paid: 0,
        outstanding_count: 0,
        paid_count: 0,
      }
      vi.mocked(apiClient.fetchApi).mockResolvedValue(mockSummary)

      const result = await getMyFinesSummary('auth-token')

      expect(result).toEqual(mockSummary)
    })

    it('should throw error when fetch fails', async () => {
      vi.mocked(apiClient.fetchApi).mockRejectedValue(new Error('Server error'))

      await expect(getMyFinesSummary('token')).rejects.toThrow('Failed to fetch fines summary')
    })
  })

  // ==================== Self-Checkout Tests ====================

  describe('lookupItemByBarcode', () => {
    it('should return item details for valid barcode', async () => {
      const mockItem = {
        id: 101,
        title: 'The Great Gatsby',
        author: 'F. Scott Fitzgerald',
        item_type: 'book',
        status: 'available',
        isbn: '978-0743273565',
        publisher: 'Scribner',
        publication_year: 1925,
        description: 'A story of the Jazz Age',
        location: 'Fiction - F',
        barcode: '123456789',
      }
      vi.mocked(apiClient.fetchApi).mockResolvedValue(mockItem)

      const result = await lookupItemByBarcode('123456789')

      expect(result).toEqual(mockItem)
      expect(apiClient.fetchApi).toHaveBeenCalledWith('/catalog/barcode/123456789')
    })

    it('should encode barcode in URL', async () => {
      vi.mocked(apiClient.fetchApi).mockResolvedValue({ id: 1 })

      await lookupItemByBarcode('ABC 123')

      expect(apiClient.fetchApi).toHaveBeenCalledWith('/catalog/barcode/ABC%20123')
    })

    it('should throw error when item not found (404)', async () => {
      const apiError = { status: 404, detail: 'Not found' }
      vi.mocked(apiClient.fetchApi).mockRejectedValue(apiError)
      vi.mocked(apiClient.isApiError).mockReturnValue(true)

      await expect(lookupItemByBarcode('invalid-barcode')).rejects.toThrow(
        'Item not found with that barcode'
      )
    })

    it('should throw API error detail for other errors', async () => {
      const apiError = { status: 500, detail: 'Database error' }
      vi.mocked(apiClient.fetchApi).mockRejectedValue(apiError)
      vi.mocked(apiClient.isApiError).mockReturnValue(true)

      await expect(lookupItemByBarcode('123')).rejects.toThrow('Database error')
    })

    it('should throw "Failed to look up item" when no detail', async () => {
      const apiError = { status: 500 }
      vi.mocked(apiClient.fetchApi).mockRejectedValue(apiError)
      vi.mocked(apiClient.isApiError).mockReturnValue(true)

      await expect(lookupItemByBarcode('123')).rejects.toThrow('Failed to look up item')
    })

    it('should re-throw non-API errors', async () => {
      vi.mocked(apiClient.fetchApi).mockRejectedValue(new Error('Network error'))
      vi.mocked(apiClient.isApiError).mockReturnValue(false)

      await expect(lookupItemByBarcode('123')).rejects.toThrow('Network error')
    })
  })

  describe('selfCheckoutItem', () => {
    it('should successfully checkout an item', async () => {
      const mockCheckout = {
        id: 1,
        user_id: 1,
        item_id: 101,
        status: 'active',
        checked_out_at: '2024-01-15T10:00:00Z',
        due_date: '2024-01-29T23:59:59Z',
        returned_at: null,
        item_title: 'The Great Gatsby',
        item_author: 'F. Scott Fitzgerald',
      }
      vi.mocked(apiClient.fetchApi).mockResolvedValue(mockCheckout)

      const result = await selfCheckoutItem('auth-token', 101)

      expect(result).toEqual(mockCheckout)
      expect(apiClient.fetchApi).toHaveBeenCalledWith('/circulation/checkout', {
        method: 'POST',
        token: 'auth-token',
        body: { item_id: 101 },
      })
    })

    it('should throw error when item not available', async () => {
      const apiError = { status: 400, detail: 'Item is not available for checkout' }
      vi.mocked(apiClient.fetchApi).mockRejectedValue(apiError)
      vi.mocked(apiClient.isApiError).mockReturnValue(true)

      await expect(selfCheckoutItem('token', 101)).rejects.toThrow('Item is not available for checkout')
    })

    it('should throw error when checkout limit reached', async () => {
      const apiError = { status: 400, detail: 'Checkout limit reached' }
      vi.mocked(apiClient.fetchApi).mockRejectedValue(apiError)
      vi.mocked(apiClient.isApiError).mockReturnValue(true)

      await expect(selfCheckoutItem('token', 101)).rejects.toThrow('Checkout limit reached')
    })

    it('should throw error when patron has blocks', async () => {
      const apiError = { status: 403, detail: 'Account has outstanding fines' }
      vi.mocked(apiClient.fetchApi).mockRejectedValue(apiError)
      vi.mocked(apiClient.isApiError).mockReturnValue(true)

      await expect(selfCheckoutItem('token', 101)).rejects.toThrow('Account has outstanding fines')
    })

    it('should throw "Checkout failed" when no detail', async () => {
      const apiError = { status: 500 }
      vi.mocked(apiClient.fetchApi).mockRejectedValue(apiError)
      vi.mocked(apiClient.isApiError).mockReturnValue(true)

      await expect(selfCheckoutItem('token', 101)).rejects.toThrow('Checkout failed')
    })

    it('should re-throw non-API errors', async () => {
      vi.mocked(apiClient.fetchApi).mockRejectedValue(new Error('Connection lost'))
      vi.mocked(apiClient.isApiError).mockReturnValue(false)

      await expect(selfCheckoutItem('token', 101)).rejects.toThrow('Connection lost')
    })
  })
})
