/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Staff API Service Tests
 *
 * Tests for staff API functions including:
 * - Dashboard stats and activity
 * - Patron management (search, view, update)
 * - Patron checkouts and holds
 * - Staff checkout/checkin operations
 * - Catalog management
 * - User management
 * - Fine management
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import * as apiClient from '@/lib/api-client'
import {
  getStaffDashboardStats,
  getStaffActivityFeed,
  getPatronStatistics,
  searchPatrons,
  searchPatronsSuggestions,
  getPatron,
  togglePatronBlock,
  getPatronCheckouts,
  getPatronHolds,
  staffCheckoutItem,
  staffCheckinItem,
  getOverdueItems,
  createCatalogItem,
  updateCatalogItem,
  deleteCatalogItem,
  getUserStats,
  searchUsers,
  getUser,
  createUser,
  updateUser,
  deleteUser,
  lockUser,
  unlockUser,
  bulkBlockPatrons,
  bulkWaiveFines,
  listFines,
  createFine,
  payFine,
  waiveFine,
  getPatronFineHistory,
  makePartialPayment,
  createPaymentPlan,
  getPaymentPlan,
} from '@/api/staff-api'

// Mock the api-client module
vi.mock('@/lib/api-client', () => ({
  fetchApi: vi.fn(),
  isApiError: vi.fn(),
  getErrorMessage: vi.fn((err: unknown, fallback?: string) => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    if (err && typeof err === 'object' && 'message' in err) return (err as any).message
    return fallback || 'Unknown error'
  }),
  getUserMessage: vi.fn((_err: unknown, fallback: string) => fallback),
}))

describe('Staff API', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  // ==================== Dashboard Tests ====================

  describe('getStaffDashboardStats', () => {
    it('should return dashboard statistics', async () => {
      const mockStats = {
        checkouts_today: 45,
        returns_today: 38,
        overdue_items: 23,
        active_holds: 156,
        new_patrons_this_week: 12,
        total_patrons: 5432,
      }
      vi.mocked(apiClient.fetchApi).mockResolvedValue(mockStats)

      const result = await getStaffDashboardStats('auth-token')

      expect(result).toEqual(mockStats)
      expect(apiClient.fetchApi).toHaveBeenCalledWith('/staff/dashboard/stats', { token: 'auth-token' })
    })

    it('should propagate the error rather than mask it with fake stats', async () => {
      // #1558 deliberately removed the silent try/catch fallback here —
      // showing made-up dashboard numbers when the real request fails
      // hides the failure from staff instead of surfacing it.
      vi.mocked(apiClient.fetchApi).mockRejectedValue(new Error('Server error'))

      await expect(getStaffDashboardStats('token')).rejects.toThrow('Server error')
    })
  })

  describe('getStaffActivityFeed', () => {
    it('should return activity items', async () => {
      const mockActivity = [
        { id: 1, type: 'checkout', description: 'John Doe checked out "The Great Gatsby"', timestamp: '2024-01-15T10:00:00Z' },
        { id: 2, type: 'return', description: 'Jane Smith returned "1984"', timestamp: '2024-01-15T09:45:00Z' },
      ]
      vi.mocked(apiClient.fetchApi).mockResolvedValue(mockActivity)

      const result = await getStaffActivityFeed('auth-token')

      expect(result).toEqual(mockActivity)
      expect(apiClient.fetchApi).toHaveBeenCalledWith('/staff/dashboard/activity?limit=10', { token: 'auth-token' })
    })

    it('should support custom limit', async () => {
      vi.mocked(apiClient.fetchApi).mockResolvedValue([])

      await getStaffActivityFeed('token', 20)

      expect(apiClient.fetchApi).toHaveBeenCalledWith('/staff/dashboard/activity?limit=20', { token: 'token' })
    })

    it('should handle wrapped response format', async () => {
      vi.mocked(apiClient.fetchApi).mockResolvedValue({ data: [{ id: 1, type: 'checkout' }] })

      const result = await getStaffActivityFeed('token')

      expect(result).toEqual([{ id: 1, type: 'checkout' }])
    })

    it('should propagate the error rather than mask it with an empty feed', async () => {
      // Same #1558 change as getStaffDashboardStats above.
      vi.mocked(apiClient.fetchApi).mockRejectedValue(new Error('Server error'))

      await expect(getStaffActivityFeed('token')).rejects.toThrow('Server error')
    })
  })

  describe('getPatronStatistics', () => {
    it('should return patron statistics', async () => {
      const mockStats = {
        total_patrons: 5000,
        active_patrons: 4500,
        blocked_patrons: 50,
        new_this_week: 25,
        new_this_month: 100,
        total_fines_outstanding: 2500.5,
        total_overdue_items: 150,
        at_risk_counts: {
          patrons_with_many_overdue: 10,
          patrons_with_high_fines: 15,
          inactive_patrons: 200,
        },
        patrons_with_many_overdue: [],
        patrons_with_high_fines: [],
        inactive_patrons: [],
      }
      vi.mocked(apiClient.fetchApi).mockResolvedValue(mockStats)

      const result = await getPatronStatistics('auth-token')

      expect(result).toEqual(mockStats)
      expect(apiClient.fetchApi).toHaveBeenCalledWith('/staff/patrons/statistics', { token: 'auth-token' })
    })

    it('should throw error on failure', async () => {
      vi.mocked(apiClient.fetchApi).mockRejectedValue(new Error('Server error'))

      await expect(getPatronStatistics('token')).rejects.toThrow('Server error')
    })
  })

  // ==================== Patron Search Tests ====================

  describe('searchPatrons', () => {
    it('should search patrons with query', async () => {
      const mockResponse = {
        patrons: [
          { id: 1, email: 'john@example.com', first_name: 'John', last_name: 'Doe' },
        ],
        total_count: 1,
      }
      vi.mocked(apiClient.fetchApi).mockResolvedValue(mockResponse)

      const result = await searchPatrons('auth-token', 'john')

      expect(result.patrons).toHaveLength(1)
      expect(result.total).toBe(1)
      expect(apiClient.fetchApi).toHaveBeenCalledWith(
        expect.stringContaining('search=john'),
        { token: 'auth-token' }
      )
    })

    it('should support pagination', async () => {
      vi.mocked(apiClient.fetchApi).mockResolvedValue({ patrons: [], total_count: 0 })

      await searchPatrons('token', 'test', 2)

      expect(apiClient.fetchApi).toHaveBeenCalledWith(
        expect.stringContaining('offset=20'),
        expect.anything()
      )
    })

    it('should support status filter', async () => {
      vi.mocked(apiClient.fetchApi).mockResolvedValue({ patrons: [], total_count: 0 })

      await searchPatrons('token', '', 1, undefined, 'blocked')

      expect(apiClient.fetchApi).toHaveBeenCalledWith(
        expect.stringContaining('is_active=false'),
        expect.anything()
      )
    })

    it('should support advanced filters', async () => {
      vi.mocked(apiClient.fetchApi).mockResolvedValue({ patrons: [], total_count: 0 })

      await searchPatrons('token', '', 1, {
        finesMin: 10,
        finesMax: 100,
        hasOverdue: 'has_overdue',
        sortBy: 'fines_balance',
        sortDirection: 'desc',
      })

      const call = vi.mocked(apiClient.fetchApi).mock.calls[0]![0]
      expect(call).toContain('fines_min=10')
      expect(call).toContain('fines_max=100')
      expect(call).toContain('has_overdue=has_overdue')
      expect(call).toContain('sort_by=fines_balance')
    })

    it('should propagate errors instead of silently returning empty', async () => {
      vi.mocked(apiClient.fetchApi).mockRejectedValue(new Error('Server error'))

      await expect(searchPatrons('token', 'test')).rejects.toThrow('Server error')
    })
  })

  describe('searchPatronsSuggestions', () => {
    it('should return suggestions for query', async () => {
      vi.mocked(apiClient.fetchApi).mockResolvedValue({
        patrons: [{ id: 1, first_name: 'John', last_name: 'Doe' }],
        total_count: 1,
      })

      const result = await searchPatronsSuggestions('token', 'john')

      expect(result).toHaveLength(1)
    })

    it('should return empty array for short query', async () => {
      const result = await searchPatronsSuggestions('token', 'a')

      expect(result).toEqual([])
      expect(apiClient.fetchApi).not.toHaveBeenCalled()
    })

    it('should return empty array for empty query', async () => {
      const result = await searchPatronsSuggestions('token', '')

      expect(result).toEqual([])
    })
  })

  // ==================== Patron Management Tests ====================

  describe('getPatron', () => {
    it('should return patron details', async () => {
      const mockPatron = {
        id: 1,
        email: 'john@example.com',
        first_name: 'John',
        last_name: 'Doe',
        role: 'PATRON',
        is_active: true,
        library_card: 'LIB001',
        fines_balance: 5.5,
        total_checkouts: 50,
        current_checkouts: 3,
        current_holds: 2,
      }
      vi.mocked(apiClient.fetchApi).mockResolvedValue(mockPatron)

      const result = await getPatron('auth-token', 1)

      expect(result).toEqual(mockPatron)
      expect(apiClient.fetchApi).toHaveBeenCalledWith('/staff/patrons/1', { token: 'auth-token' })
    })

    it('should throw error when patron not found', async () => {
      vi.mocked(apiClient.fetchApi).mockRejectedValue(new Error('Not found'))

      await expect(getPatron('token', 999)).rejects.toThrow('Failed to fetch patron')
    })
  })

describe('togglePatronBlock', () => {
    it('should block patron', async () => {
      const mockPatron = { id: 1, is_active: false }
      vi.mocked(apiClient.fetchApi).mockResolvedValue(mockPatron)

      const result = await togglePatronBlock('auth-token', 1, true)

      expect(result.is_active).toBe(false)
      expect(apiClient.fetchApi).toHaveBeenCalledWith('/staff/patrons/1/block', {
        method: 'POST',
        token: 'auth-token',
        body: { blocked: true },
      })
    })

    it('should unblock patron', async () => {
      const mockPatron = { id: 1, is_active: true }
      vi.mocked(apiClient.fetchApi).mockResolvedValue(mockPatron)

      const result = await togglePatronBlock('auth-token', 1, false)

      expect(result.is_active).toBe(true)
    })
  })

  describe('getPatronCheckouts', () => {
    it('should return patron checkouts', async () => {
      const mockCheckouts = [
        { id: 1, item_title: 'Book 1', due_date: '2024-01-20' },
        { id: 2, item_title: 'Book 2', due_date: '2024-01-25' },
      ]
      vi.mocked(apiClient.fetchApi).mockResolvedValue(mockCheckouts)

      const result = await getPatronCheckouts('auth-token', 1)

      expect(result).toEqual(mockCheckouts)
      expect(apiClient.fetchApi).toHaveBeenCalledWith('/staff/patrons/1/checkouts', { token: 'auth-token' })
    })

    it('should throw error when fetch fails', async () => {
      vi.mocked(apiClient.fetchApi).mockRejectedValue(new Error('Server error'))

      await expect(getPatronCheckouts('token', 1)).rejects.toThrow('Failed to fetch patron checkouts')
    })
  })

  describe('getPatronHolds', () => {
    it('should return patron holds', async () => {
      const mockHolds = [
        { id: 1, item_title: 'Book 1', status: 'pending', position: 3 },
      ]
      vi.mocked(apiClient.fetchApi).mockResolvedValue(mockHolds)

      const result = await getPatronHolds('auth-token', 1)

      expect(result).toEqual(mockHolds)
      expect(apiClient.fetchApi).toHaveBeenCalledWith('/staff/patrons/1/holds', { token: 'auth-token' })
    })
  })

  // ==================== Staff Checkout/Checkin Tests ====================

  describe('staffCheckoutItem', () => {
    it('should checkout item for patron', async () => {
      const mockCheckout = {
        id: 1,
        user_id: 1,
        item_id: 101,
        status: 'active',
        due_date: '2024-01-29',
      }
      vi.mocked(apiClient.fetchApi).mockResolvedValue(mockCheckout)

      vi.mocked(apiClient.fetchApi).mockResolvedValue({ checkout: mockCheckout })

      const result = await staffCheckoutItem('auth-token', 1, '123456')

      expect(result).toEqual(mockCheckout)
      expect(apiClient.fetchApi).toHaveBeenCalledWith('/staff/patrons/1/quick-checkout', {
        method: 'POST',
        token: 'auth-token',
        body: { barcode: '123456' },
      })
    })

    it('should throw error when item not available', async () => {
      const apiError = { status: 400, detail: 'Item is already checked out' }
      vi.mocked(apiClient.fetchApi).mockRejectedValue(apiError)
      vi.mocked(apiClient.isApiError).mockReturnValue(true)

      await expect(staffCheckoutItem('token', 1, '123456')).rejects.toThrow('Item is already checked out')
    })

    it('should throw "Checkout failed" when no detail', async () => {
      const apiError = { status: 500 }
      vi.mocked(apiClient.fetchApi).mockRejectedValue(apiError)
      vi.mocked(apiClient.isApiError).mockReturnValue(true)

      await expect(staffCheckoutItem('token', 1, '123456')).rejects.toThrow('Checkout failed')
    })
  })

  describe('staffCheckinItem', () => {
    it('should checkin item by barcode (legacy shape: no next_hold field)', async () => {
      // Old backends returned a bare Checkout; the helper now normalises it
      // into {message, checkout, next_hold:null} for FE consumers.
      const mockCheckout = { id: 1, status: 'returned', returned_at: '2024-01-15T10:00:00Z' }
      const backendResponse = { message: 'Checked in Book Title', checkout: mockCheckout }
      vi.mocked(apiClient.fetchApi).mockResolvedValue(backendResponse)

      const result = await staffCheckinItem('auth-token', '123456')

      expect(result).toEqual({
        message: 'Checked in Book Title',
        checkout: mockCheckout,
        next_hold: null,
      })
      expect(apiClient.fetchApi).toHaveBeenCalledWith('/staff/checkin-barcode?barcode=123456', {
        method: 'POST',
        token: 'auth-token',
      })
    })

    it('surfaces next_hold when backend returns structured response', async () => {
      const mockCheckout = { id: 2, status: 'returned' }
      const nextHold = {
        hold_id: 7,
        patron_first_name: 'Felicity',
        patron_last_initial: 'T.',
        shelf_slot: 'A-12',
        expires_at: '2026-06-01T00:00:00Z',
        item_title: 'Sample Title',
      }
      vi.mocked(apiClient.fetchApi).mockResolvedValue({
        message: 'Checked in Sample Title',
        checkout: mockCheckout,
        next_hold: nextHold,
      })

      const result = await staffCheckinItem('auth-token', '999')

      expect(result.next_hold).toEqual(nextHold)
      expect(result.checkout).toEqual(mockCheckout)
      expect(result.message).toBe('Checked in Sample Title')
    })

    it('should throw error when barcode not found', async () => {
      const apiError = { status: 404, detail: 'No active checkout found for this barcode' }
      vi.mocked(apiClient.fetchApi).mockRejectedValue(apiError)
      vi.mocked(apiClient.isApiError).mockReturnValue(true)

      await expect(staffCheckinItem('token', 'invalid')).rejects.toThrow('No active checkout found for this barcode')
      expect(apiClient.fetchApi).toHaveBeenCalledWith(
        expect.stringContaining('/staff/checkin-barcode'),
        expect.anything()
      )
    })
  })

  describe('getOverdueItems', () => {
    it('should return overdue items', async () => {
      const mockItems = [
        { id: 1, patron_name: 'John Doe', item_title: 'Book 1', days_overdue: 5 },
      ]
      vi.mocked(apiClient.fetchApi).mockResolvedValue(mockItems)

      const result = await getOverdueItems('auth-token')

      expect(result).toEqual(mockItems)
      expect(apiClient.fetchApi).toHaveBeenCalledWith('/staff/circulation/overdue', { token: 'auth-token' })
    })

    it('should return empty array on error', async () => {
      vi.mocked(apiClient.fetchApi).mockRejectedValue(new Error('Server error'))

      const result = await getOverdueItems('token')

      expect(result).toEqual([])
    })
  })

  // ==================== Catalog Management Tests ====================

  describe('createCatalogItem', () => {
    it('should create new catalog item', async () => {
      const mockItem = {
        id: 1,
        title: 'New Book',
        author: 'John Author',
        item_type: 'book',
        isbn: '978-1234567890',
        status: 'available',
      }
      vi.mocked(apiClient.fetchApi).mockResolvedValue(mockItem)

      const itemData = {
        title: 'New Book',
        author: 'John Author',
        item_type: 'book',
        isbn: '978-1234567890',
      }
      const result = await createCatalogItem('auth-token', itemData)

      expect(result).toEqual(mockItem)
      expect(apiClient.fetchApi).toHaveBeenCalledWith('/staff/catalog', {
        method: 'POST',
        token: 'auth-token',
        body: itemData,
      })
    })

    it('should throw error on validation failure', async () => {
      const apiError = { status: 422, detail: 'Title is required' }
      vi.mocked(apiClient.fetchApi).mockRejectedValue(apiError)
      vi.mocked(apiClient.isApiError).mockReturnValue(true)

      await expect(createCatalogItem('token', { item_type: 'book', title: '' })).rejects.toThrow('Title is required')
    })
  })

  describe('updateCatalogItem', () => {
    it('should update catalog item', async () => {
      const mockItem = { id: 1, title: 'Updated Title' }
      vi.mocked(apiClient.fetchApi).mockResolvedValue(mockItem)

      const result = await updateCatalogItem('auth-token', 1, { title: 'Updated Title' })

      expect(result).toEqual(mockItem)
      expect(apiClient.fetchApi).toHaveBeenCalledWith('/staff/catalog/1', {
        method: 'PUT',
        token: 'auth-token',
        body: { title: 'Updated Title' },
      })
    })
  })

  describe('deleteCatalogItem', () => {
    it('should delete catalog item', async () => {
      vi.mocked(apiClient.fetchApi).mockResolvedValue(undefined)

      await expect(deleteCatalogItem('auth-token', 1)).resolves.toBeUndefined()

      expect(apiClient.fetchApi).toHaveBeenCalledWith('/staff/catalog/1', {
        method: 'DELETE',
        token: 'auth-token',
        skipJsonParse: true,
      })
    })

    it('should throw error when item has active checkouts', async () => {
      const apiError = { status: 400, detail: 'Cannot delete item with active checkouts' }
      vi.mocked(apiClient.fetchApi).mockRejectedValue(apiError)
      vi.mocked(apiClient.isApiError).mockReturnValue(true)

      await expect(deleteCatalogItem('token', 1)).rejects.toThrow('Cannot delete item with active checkouts')
    })
  })

  // ==================== User Management Tests ====================

  describe('getUserStats', () => {
    it('should return user statistics', async () => {
      const mockStats = {
        total_users: 100,
        active_users: 90,
        new_this_month: 5,
        locked_accounts: 3,
      }
      vi.mocked(apiClient.fetchApi).mockResolvedValue(mockStats)

      const result = await getUserStats('auth-token')

      expect(result).toEqual(mockStats)
      expect(apiClient.fetchApi).toHaveBeenCalledWith('/users/stats', { token: 'auth-token' })
    })
  })

  describe('searchUsers', () => {
    it('should search users with filters', async () => {
      const mockResponse = {
        users: [{ id: 1, email: 'staff@example.com', role: 'staff' }],
        total: 1,
        page: 1,
        per_page: 20,
      }
      vi.mocked(apiClient.fetchApi).mockResolvedValue(mockResponse)

      const result = await searchUsers('auth-token', { search: 'staff', role: 'staff' })

      expect(result).toEqual(mockResponse)
      expect(apiClient.fetchApi).toHaveBeenCalledWith(
        expect.stringContaining('search=staff'),
        { token: 'auth-token' }
      )
    })
  })

  describe('getUser', () => {
    it('should return user details', async () => {
      const mockUser = { id: 1, email: 'user@example.com', role: 'staff' }
      vi.mocked(apiClient.fetchApi).mockResolvedValue(mockUser)

      const result = await getUser('auth-token', 1)

      expect(result).toEqual(mockUser)
      expect(apiClient.fetchApi).toHaveBeenCalledWith('/users/1', { token: 'auth-token' })
    })
  })

  describe('createUser', () => {
    it('should create new user', async () => {
      const mockUser = { id: 1, email: 'new@example.com', role: 'staff' }
      vi.mocked(apiClient.fetchApi).mockResolvedValue(mockUser)

      const userData = { email: 'new@example.com', password: 'Password123!', role: 'staff' }
      const result = await createUser('auth-token', userData)

      expect(result).toEqual(mockUser)
      expect(apiClient.fetchApi).toHaveBeenCalledWith('/users', {
        method: 'POST',
        token: 'auth-token',
        body: userData,
      })
    })
  })

  describe('updateUser', () => {
    it('should update user data', async () => {
      const mockUser = { id: 1, role: 'ADMIN' }
      vi.mocked(apiClient.fetchApi).mockResolvedValue(mockUser)

      const result = await updateUser('auth-token', 1, { role: 'ADMIN' })

      expect(result).toEqual(mockUser)
    })
  })

  describe('deleteUser', () => {
    it('should delete user', async () => {
      vi.mocked(apiClient.fetchApi).mockResolvedValue(undefined)

      await expect(deleteUser('auth-token', 1)).resolves.toBeUndefined()

      expect(apiClient.fetchApi).toHaveBeenCalledWith('/users/1', {
        method: 'DELETE',
        token: 'auth-token',
        skipJsonParse: true,
      })
    })
  })

  describe('lockUser', () => {
    it('should lock user account', async () => {
      const mockUser = { id: 1, is_locked: true }
      vi.mocked(apiClient.fetchApi).mockResolvedValue(mockUser)

      const result = await lockUser('auth-token', 1)

      expect(result.is_locked).toBe(true)
      expect(apiClient.fetchApi).toHaveBeenCalledWith('/users/1/lock', {
        method: 'POST',
        token: 'auth-token',
      })
    })
  })

  describe('unlockUser', () => {
    it('should unlock user account', async () => {
      const mockUser = { id: 1, is_locked: false }
      vi.mocked(apiClient.fetchApi).mockResolvedValue(mockUser)

      const result = await unlockUser('auth-token', 1)

      expect(result.is_locked).toBe(false)
    })
  })

  // ==================== Bulk Operations Tests ====================

  describe('bulkBlockPatrons', () => {
    it('should block multiple patrons', async () => {
      const mockResponse = {
        success: true,
        processed_count: 3,
        failed_ids: [],
        message: '3 patrons blocked successfully',
      }
      vi.mocked(apiClient.fetchApi).mockResolvedValue(mockResponse)

      const result = await bulkBlockPatrons('auth-token', {
        patron_ids: [1, 2, 3],
        blocked: true,
        reason: 'Policy violation',
      })

      expect(result).toEqual(mockResponse)
      expect(apiClient.fetchApi).toHaveBeenCalledWith('/staff/patrons/bulk-block', {
        method: 'POST',
        token: 'auth-token',
        body: { patron_ids: [1, 2, 3], blocked: true, reason: 'Policy violation' },
      })
    })
  })

  describe('bulkWaiveFines', () => {
    it('should waive fines for multiple patrons', async () => {
      const mockResponse = {
        success: true,
        patrons_processed: 5,
        fines_waived: 12,
        total_amount_waived: 150.5,
        failed_ids: [],
        message: 'Fines waived successfully',
      }
      vi.mocked(apiClient.fetchApi).mockResolvedValue(mockResponse)

      const result = await bulkWaiveFines('auth-token', {
        patron_ids: [1, 2, 3, 4, 5],
        reason: 'Fee forgiveness program',
      })

      expect(result).toEqual(mockResponse)
    })
  })

  // ==================== Fine Management Tests ====================

  describe('listFines', () => {
    it('should list fines for a patron', async () => {
      const mockResponse = {
        fines: [{ id: 10, user_id: 1, amount: 12.5, amount_paid: 0, status: 'unpaid' }],
        total_count: 1,
        total_unpaid: 12.5,
      }
      vi.mocked(apiClient.fetchApi).mockResolvedValue(mockResponse)

      const result = await listFines('auth-token', { patron_id: 1, unpaid_only: true, limit: 20, offset: 0 })

      expect(result).toEqual(mockResponse)
      expect(apiClient.fetchApi).toHaveBeenCalledWith('/staff/fines?patron_id=1&unpaid_only=true&limit=20&offset=0', {
        token: 'auth-token',
      })
    })
  })

  describe('createFine', () => {
    it('should create a fine', async () => {
      const mockFine = { id: 11, user_id: 1, amount: 8.5, fine_type: 'overdue', status: 'unpaid' }
      vi.mocked(apiClient.fetchApi).mockResolvedValue(mockFine)

      const result = await createFine('auth-token', {
        user_id: 1,
        fine_type: 'overdue',
        amount: 8.5,
        description: 'Late return',
      })

      expect(result).toEqual(mockFine)
      expect(apiClient.fetchApi).toHaveBeenCalledWith('/staff/fines', {
        method: 'POST',
        token: 'auth-token',
        body: {
          user_id: 1,
          fine_type: 'overdue',
          amount: 8.5,
          description: 'Late return',
        },
      })
    })
  })

  describe('payFine', () => {
    it('should pay a fine', async () => {
      const mockFine = { id: 12, amount: 20, amount_paid: 20, status: 'paid' }
      vi.mocked(apiClient.fetchApi).mockResolvedValue(mockFine)

      const result = await payFine('auth-token', 12, { amount: 20 })

      expect(result).toEqual(mockFine)
      expect(apiClient.fetchApi).toHaveBeenCalledWith('/staff/fines/12/pay', {
        method: 'POST',
        token: 'auth-token',
        body: { amount: 20 },
      })
    })
  })

  describe('waiveFine', () => {
    it('should waive a fine', async () => {
      const mockFine = { id: 13, amount: 15, amount_paid: 0, status: 'waived' }
      vi.mocked(apiClient.fetchApi).mockResolvedValue(mockFine)

      const result = await waiveFine('auth-token', 13, { reason: 'Hardship program' })

      expect(result).toEqual(mockFine)
      expect(apiClient.fetchApi).toHaveBeenCalledWith('/staff/fines/13/waive', {
        method: 'POST',
        token: 'auth-token',
        body: { reason: 'Hardship program' },
      })
    })
  })

  describe('getPatronFineHistory', () => {
    it('should return patron fine history', async () => {
      const mockHistory = {
        patron_id: 1,
        patron_name: 'John Doe',
        fines: [{ id: 1, amount: 5.0, status: 'unpaid' }],
        payments: [],
        total_count: 1,
        total_fines_amount: 5.0,
        total_paid_amount: 0,
        current_balance: 5.0,
      }
      vi.mocked(apiClient.fetchApi).mockResolvedValue(mockHistory)

      const result = await getPatronFineHistory('auth-token', 1)

      expect(result).toEqual(mockHistory)
      expect(apiClient.fetchApi).toHaveBeenCalledWith('/staff/patrons/1/fines/history', { token: 'auth-token' })
    })
  })

  describe('makePartialPayment', () => {
    it('should process partial payment', async () => {
      const mockResponse = {
        fine: { id: 1, amount: 10.0, amount_paid: 5.0, balance: 5.0 },
        payment: { id: 1, amount: 5.0, payment_method: 'cash' },
        receipt_number: 'RCP-001',
      }
      vi.mocked(apiClient.fetchApi).mockResolvedValue(mockResponse)

      const result = await makePartialPayment('auth-token', 1, {
        amount: 5.0,
        payment_method: 'cash',
      })

      expect(result).toEqual(mockResponse)
      expect(apiClient.fetchApi).toHaveBeenCalledWith('/staff/fines/1/partial-payment', {
        method: 'POST',
        token: 'auth-token',
        body: { amount: 5.0, payment_method: 'cash' },
      })
    })
  })

  describe('createPaymentPlan', () => {
    it('should create payment plan', async () => {
      const mockPlan = {
        id: 1,
        user_id: 1,
        total_amount: 100.0,
        installment_amount: 25.0,
        frequency: 'monthly',
        status: 'active',
      }
      vi.mocked(apiClient.fetchApi).mockResolvedValue(mockPlan)

      const result = await createPaymentPlan('auth-token', 1, {
        total_amount: 100.0,
        installment_amount: 25.0,
        frequency: 'monthly',
      })

      expect(result).toEqual(mockPlan)
    })
  })

  describe('getPaymentPlan', () => {
    it('should return active payment plan', async () => {
      const mockPlan = { id: 1, status: 'active', remaining_balance: 75.0 }
      vi.mocked(apiClient.fetchApi).mockResolvedValue(mockPlan)

      const result = await getPaymentPlan('auth-token', 1)

      expect(result).toEqual(mockPlan)
    })

    it('should return null when no active plan (404)', async () => {
      const apiError = { status: 404, detail: 'No active plan' }
      vi.mocked(apiClient.fetchApi).mockRejectedValue(apiError)
      vi.mocked(apiClient.isApiError).mockReturnValue(true)

      const result = await getPaymentPlan('auth-token', 1)

      expect(result).toBeNull()
    })
  })
})
