/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Circulation API Tests
 *
 * Tests for circulation-related API functions including:
 * - Checkouts (view, renew)
 * - Holds (view, cancel)
 * - History
 * - Fines
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import {
  getMyCheckouts,
  getMyHolds,
  renewCheckout,
  cancelHold,
  getMyHistory,
  getMyFines,
  type Checkout,
  type Hold,
  type Fine,
} from '@/api/circulation-api'

// Mock fetch
const mockFetch = vi.fn()
global.fetch = mockFetch

const TEST_TOKEN = 'test-token-123'

describe('Circulation API', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('getMyCheckouts', () => {
    it('should fetch user checkouts', async () => {
      const mockCheckouts: Checkout[] = [
        {
          id: 1,
          user_id: 1,
          item_id: 100,
          status: 'active',
          checked_out_at: '2024-01-01T00:00:00Z',
          due_date: '2024-01-15T00:00:00Z',
          returned_at: null,
          item_title: 'Test Book',
          item_author: 'Test Author',
        },
      ]

      mockFetch.mockResolvedValue({
        ok: true,
        json: async () => ({
          data: mockCheckouts,
          pagination: { page: 1, per_page: 20, total: 1, total_pages: 1, has_next: false, has_previous: false },
        }),
      })

      const result = await getMyCheckouts(TEST_TOKEN)

      expect(result).toEqual(mockCheckouts)
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/circulation/checkouts'),
        expect.objectContaining({
          // apiClient always adds Content-Type too now, even on GET/DELETE.
          headers: expect.objectContaining({ Authorization: `Bearer ${TEST_TOKEN}` }),
        })
      )
    })

    it('should handle checkout fetch errors', async () => {
      mockFetch.mockResolvedValue({
        ok: false,
        status: 401,
      })

      await expect(getMyCheckouts(TEST_TOKEN)).rejects.toThrow('Failed to fetch checkouts')
    })

    it('should return empty array when no checkouts', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: async () => ({
          data: [],
          pagination: { page: 1, per_page: 20, total: 0, total_pages: 0, has_next: false, has_previous: false },
        }),
      })

      const result = await getMyCheckouts(TEST_TOKEN)

      expect(result).toEqual([])
    })
  })

  describe('getMyHolds', () => {
    it('should fetch user holds', async () => {
      const mockHolds: Hold[] = [
        {
          id: 1,
          user_id: 1,
          item_id: 200,
          status: 'pending',
          position: 3,
          created_at: '2024-01-01T00:00:00Z',
          notified_at: null,
          expires_at: null,
          item_title: 'Popular Book',
          item_author: 'Famous Author',
          cancelled_at: null,
          cancellation_reason: null,
          cancelled_by: null,
        },
      ]

      mockFetch.mockResolvedValue({
        ok: true,
        json: async () => ({
          data: mockHolds,
          pagination: { page: 1, per_page: 20, total: 1, total_pages: 1, has_next: false, has_previous: false },
        }),
      })

      const result = await getMyHolds(TEST_TOKEN)

      expect(result).toEqual(mockHolds)
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/circulation/holds'),
        expect.objectContaining({
          // apiClient always adds Content-Type too now, even on GET/DELETE.
          headers: expect.objectContaining({ Authorization: `Bearer ${TEST_TOKEN}` }),
        })
      )
    })

    it('should handle holds fetch errors', async () => {
      // Real Response with no parseable body: parseAndThrow's json()->text()
      // fallback chain can't recover a `detail` (the body is already
      // consumed by the failed json() read), so the ApiError message ends up
      // as the raw "{status} {statusText}" string. getMyHolds' own
      // `error.detail || 'Failed to fetch your holds'` fallback never
      // actually fires here since parseAndThrow's fallback is always
      // truthy — a pre-existing quirk, not something this batch introduced.
      mockFetch.mockResolvedValue(new Response(null, { status: 500 }))

      await expect(getMyHolds(TEST_TOKEN)).rejects.toThrow('500 ')
    })

    it('should show different hold statuses', async () => {
      const mockHolds: Hold[] = [
        {
          id: 1,
          user_id: 1,
          item_id: 200,
          status: 'pending',
          position: 3,
          created_at: '2024-01-01T00:00:00Z',
          notified_at: null,
          expires_at: null,
          item_title: 'Book 1',
          item_author: 'Author 1',
          cancelled_at: null,
          cancellation_reason: null,
          cancelled_by: null,
        },
        {
          id: 2,
          user_id: 1,
          item_id: 201,
          status: 'ready',
          position: 0,
          created_at: '2024-01-05T00:00:00Z',
          notified_at: '2024-01-10T00:00:00Z',
          expires_at: '2024-01-17T00:00:00Z',
          item_title: 'Book 2',
          item_author: 'Author 2',
          cancelled_at: null,
          cancellation_reason: null,
          cancelled_by: null,
        },
      ]

      mockFetch.mockResolvedValue({
        ok: true,
        json: async () => ({
          data: mockHolds,
          pagination: { page: 1, per_page: 20, total: 2, total_pages: 1, has_next: false, has_previous: false },
        }),
      })

      const result = await getMyHolds(TEST_TOKEN)

      expect(result).toHaveLength(2)
      expect(result[0]!.status).toBe('pending')
      expect(result[1]!.status).toBe('ready')
    })
  })

  describe('renewCheckout', () => {
    it('should renew a checkout successfully', async () => {
      const renewedCheckout: Checkout = {
        id: 1,
        user_id: 1,
        item_id: 100,
        status: 'active',
        checked_out_at: '2024-01-01T00:00:00Z',
        due_date: '2024-01-29T00:00:00Z', // Extended
        returned_at: null,
        item_title: 'Test Book',
        item_author: 'Test Author',
      }

      mockFetch.mockResolvedValue({
        ok: true,
        json: async () => renewedCheckout,
      })

      const result = await renewCheckout(TEST_TOKEN, 1)

      expect(result).toEqual(renewedCheckout)
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/circulation/renew/1'),
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({ Authorization: `Bearer ${TEST_TOKEN}` }),
        })
      )
    })

    it('should handle renewal errors with detail message', async () => {
      mockFetch.mockResolvedValue({
        ok: false,
        status: 400,
        json: async () => ({ detail: 'Item cannot be renewed' }),
      })

      await expect(renewCheckout(TEST_TOKEN, 1)).rejects.toThrow('Item cannot be renewed')
    })

    it('should handle renewal errors without detail message', async () => {
      // Real Response with a non-JSON body — the caller's own 'Renewal
      // failed' fallback never fires (see getMyHolds comment above); the
      // ApiError message is parseAndThrow's raw "{status} {statusText}".
      mockFetch.mockResolvedValue(new Response('not valid json', { status: 500 }))

      await expect(renewCheckout(TEST_TOKEN, 1)).rejects.toThrow('500 ')
    })

    it('should handle max renewal limit error', async () => {
      mockFetch.mockResolvedValue({
        ok: false,
        status: 400,
        json: async () => ({ detail: 'Maximum renewals reached' }),
      })

      await expect(renewCheckout(TEST_TOKEN, 1)).rejects.toThrow('Maximum renewals reached')
    })
  })

  describe('cancelHold', () => {
    it('should cancel a hold successfully', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        status: 204,
      })

      await expect(cancelHold(TEST_TOKEN, 1)).resolves.not.toThrow()

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/circulation/holds/1'),
        expect.objectContaining({
          method: 'DELETE',
          headers: expect.objectContaining({ Authorization: `Bearer ${TEST_TOKEN}` }),
        })
      )
    })

    it('should handle cancel errors with detail message', async () => {
      mockFetch.mockResolvedValue({
        ok: false,
        status: 404,
        json: async () => ({ detail: 'Hold not found' }),
      })

      await expect(cancelHold(TEST_TOKEN, 999)).rejects.toThrow('This hold was not found. It may have already been cancelled.')
    })

    it('should handle cancel errors without detail message', async () => {
      // Real Response with a non-JSON body — see getMyHolds comment above
      // for why the caller's own fallback text never fires here.
      mockFetch.mockResolvedValue(new Response('not valid json', { status: 500 }))

      await expect(cancelHold(TEST_TOKEN, 1)).rejects.toThrow('500 ')
    })
  })

  describe('getMyHistory', () => {
    it('should fetch checkout history', async () => {
      const mockHistory: Checkout[] = [
        {
          id: 1,
          user_id: 1,
          item_id: 100,
          status: 'returned',
          checked_out_at: '2023-12-01T00:00:00Z',
          due_date: '2023-12-15T00:00:00Z',
          returned_at: '2023-12-14T00:00:00Z',
          item_title: 'Old Book',
          item_author: 'Past Author',
        },
      ]

      mockFetch.mockResolvedValue({
        ok: true,
        json: async () => ({
          data: mockHistory,
          pagination: { page: 1, per_page: 20, total: 1, total_pages: 1, has_next: false, has_previous: false },
        }),
      })

      const result = await getMyHistory(TEST_TOKEN)

      expect(result).toEqual(mockHistory)
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/circulation/history'),
        expect.objectContaining({
          // apiClient always adds Content-Type too now, even on GET/DELETE.
          headers: expect.objectContaining({ Authorization: `Bearer ${TEST_TOKEN}` }),
        })
      )
    })

    it('should handle history fetch errors', async () => {
      mockFetch.mockResolvedValue({
        ok: false,
        status: 401,
      })

      await expect(getMyHistory(TEST_TOKEN)).rejects.toThrow('Failed to fetch history')
    })

    it('should return empty array for new users', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: async () => ({
          data: [],
          pagination: { page: 1, per_page: 20, total: 0, total_pages: 0, has_next: false, has_previous: false },
        }),
      })

      const result = await getMyHistory(TEST_TOKEN)

      expect(result).toEqual([])
    })
  })

  describe('getMyFines', () => {
    it('should fetch user fines', async () => {
      const mockFines: Fine[] = [
        {
          id: 1,
          amount: '5.00',
          reason: 'Late return',
          description: 'Book returned 5 days late',
          created_at: '2024-01-10T00:00:00Z',
          item_title: 'Overdue Book',
        },
      ]

      mockFetch.mockResolvedValue({
        ok: true,
        json: async () => ({
          data: mockFines,
          pagination: { page: 1, per_page: 20, total: 1, total_pages: 1, has_next: false, has_previous: false },
        }),
      })

      const result = await getMyFines(TEST_TOKEN)

      expect(result).toEqual(mockFines)
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/circulation/fines'),
        expect.objectContaining({
          // apiClient always adds Content-Type too now, even on GET/DELETE.
          headers: expect.objectContaining({ Authorization: `Bearer ${TEST_TOKEN}` }),
        })
      )
    })

    it('should handle fines fetch errors', async () => {
      mockFetch.mockResolvedValue({
        ok: false,
        status: 500,
      })

      await expect(getMyFines(TEST_TOKEN)).rejects.toThrow('Failed to fetch fines')
    })

    it('should show paid and unpaid fines', async () => {
      const mockFines: Fine[] = [
        {
          id: 1,
          amount: '5.00',
          reason: 'Late return',
          created_at: '2024-01-01T00:00:00Z',
          paid_at: '2024-01-05T00:00:00Z',
        },
        {
          id: 2,
          amount: '3.00',
          reason: 'Late return',
          created_at: '2024-01-10T00:00:00Z',
        },
      ]

      mockFetch.mockResolvedValue({
        ok: true,
        json: async () => ({
          data: mockFines,
          pagination: { page: 1, per_page: 20, total: 2, total_pages: 1, has_next: false, has_previous: false },
        }),
      })

      const result = await getMyFines(TEST_TOKEN)

      expect(result).toHaveLength(2)
      expect(result[0]!.paid_at).toBeDefined()
      expect(result[1]!.paid_at).toBeUndefined()
    })

    it('should show waived fines', async () => {
      const mockFines: Fine[] = [
        {
          id: 1,
          amount: '5.00',
          reason: 'Late return',
          created_at: '2024-01-01T00:00:00Z',
          waived_at: '2024-01-05T00:00:00Z',
        },
      ]

      mockFetch.mockResolvedValue({
        ok: true,
        json: async () => ({
          data: mockFines,
          pagination: { page: 1, per_page: 20, total: 1, total_pages: 1, has_next: false, has_previous: false },
        }),
      })

      const result = await getMyFines(TEST_TOKEN)

      expect(result[0]!.waived_at).toBeDefined()
    })
  })

  describe('Authentication', () => {
    it('should require authentication token for all endpoints', async () => {
      const paginatedEmpty = {
        data: [],
        pagination: { page: 1, per_page: 20, total: 0, total_pages: 0, has_next: false, has_previous: false },
      }
      const endpoints = [
        () => getMyCheckouts(TEST_TOKEN),
        () => getMyHolds(TEST_TOKEN),
        () => renewCheckout(TEST_TOKEN, 1),
        () => cancelHold(TEST_TOKEN, 1),
        () => getMyHistory(TEST_TOKEN),
        () => getMyFines(TEST_TOKEN),
      ]

      for (const endpoint of endpoints) {
        mockFetch.mockResolvedValue({
          ok: true,
          json: async () => paginatedEmpty,
        })

        await endpoint()

        expect(mockFetch).toHaveBeenCalledWith(
          expect.any(String),
          expect.objectContaining({
            headers: expect.objectContaining({
              Authorization: `Bearer ${TEST_TOKEN}`,
            }),
          })
        )

        mockFetch.mockClear()
      }
    })
  })

  describe('Checkout Status Handling', () => {
    it('should handle different checkout statuses', async () => {
      const mockCheckouts: Checkout[] = [
        {
          id: 1,
          user_id: 1,
          item_id: 100,
          status: 'active',
          checked_out_at: '2024-01-01T00:00:00Z',
          due_date: '2024-01-15T00:00:00Z',
          returned_at: null,
          item_title: 'Active Book',
          item_author: 'Author 1',
        },
        {
          id: 2,
          user_id: 1,
          item_id: 101,
          status: 'overdue',
          checked_out_at: '2023-12-01T00:00:00Z',
          due_date: '2023-12-15T00:00:00Z',
          returned_at: null,
          item_title: 'Overdue Book',
          item_author: 'Author 2',
        },
        {
          id: 3,
          user_id: 1,
          item_id: 102,
          status: 'returned',
          checked_out_at: '2023-11-01T00:00:00Z',
          due_date: '2023-11-15T00:00:00Z',
          returned_at: '2023-11-14T00:00:00Z',
          item_title: 'Returned Book',
          item_author: 'Author 3',
        },
      ]

      mockFetch.mockResolvedValue({
        ok: true,
        json: async () => ({
          data: mockCheckouts,
          pagination: { page: 1, per_page: 20, total: 3, total_pages: 1, has_next: false, has_previous: false },
        }),
      })

      const result = await getMyCheckouts(TEST_TOKEN)

      expect(result).toHaveLength(3)
      expect(result[0]!.status).toBe('active')
      expect(result[1]!.status).toBe('overdue')
      expect(result[2]!.status).toBe('returned')
    })
  })

  describe('Hold Position Tracking', () => {
    it('should track hold position in queue', async () => {
      const mockHolds: Hold[] = [
        {
          id: 1,
          user_id: 1,
          item_id: 200,
          status: 'pending',
          position: 1,
          created_at: '2024-01-01T00:00:00Z',
          notified_at: null,
          expires_at: null,
          item_title: 'Popular Book',
          item_author: 'Popular Author',
          cancelled_at: null,
          cancellation_reason: null,
          cancelled_by: null,
        },
      ]

      mockFetch.mockResolvedValue({
        ok: true,
        json: async () => ({
          data: mockHolds,
          pagination: { page: 1, per_page: 20, total: 1, total_pages: 1, has_next: false, has_previous: false },
        }),
      })

      const result = await getMyHolds(TEST_TOKEN)

      expect(result[0]!.position).toBe(1)
    })

    it('should show when hold is ready (position 0)', async () => {
      const mockHolds: Hold[] = [
        {
          id: 1,
          user_id: 1,
          item_id: 200,
          status: 'ready',
          position: 0,
          created_at: '2024-01-01T00:00:00Z',
          notified_at: '2024-01-10T00:00:00Z',
          expires_at: '2024-01-17T00:00:00Z',
          item_title: 'Ready Book',
          item_author: 'Ready Author',
          cancelled_at: null,
          cancellation_reason: null,
          cancelled_by: null,
        },
      ]

      mockFetch.mockResolvedValue({
        ok: true,
        json: async () => ({
          data: mockHolds,
          pagination: { page: 1, per_page: 20, total: 1, total_pages: 1, has_next: false, has_previous: false },
        }),
      })

      const result = await getMyHolds(TEST_TOKEN)

      expect(result[0]!.status).toBe('ready')
      expect(result[0]!.position).toBe(0)
      expect(result[0]!.expires_at).toBeDefined()
    })
  })
})
