/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'

const { fetchApiMock, isApiErrorMock } = vi.hoisted(() => ({
  fetchApiMock: vi.fn(),
  isApiErrorMock: vi.fn().mockReturnValue(false),
}))

vi.mock('@/lib/api-client', () => ({
  fetchApi: fetchApiMock,
  isApiError: isApiErrorMock,
}))

import {
  createILLRequest,
  getMyILLRequests,
  cancelILLRequest,
  searchPartnerCatalogs,
  staffListILLRequests,
  staffUpdateILLRequest,
  staffAutoSearchAndSubmit,
  staffRenewILLRequest,
  staffAddTrackingUpdate,
  getReturnShippingLabel,
  staffAddCostRecord,
  getDueReminders,
  getFillRateReport,
  getReciprocalLendingDashboard,
  staffListPartnerLibraries,
  staffCreatePartnerLibrary,
} from '@/api/interlibrary-loan-api'

const mockToken = 'test-token-123'

describe('Interlibrary Loan API', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  // ============================
  // Patron Endpoints
  // ============================

  describe('createILLRequest', () => {
    it('should submit a new ILL request', async () => {
      const mockResponse = {
        id: 1,
        title: 'The Great Gatsby',
        author: 'F. Scott Fitzgerald',
        status: 'pending',
        request_type: 'borrow',
      }
      fetchApiMock.mockResolvedValueOnce(mockResponse)

      const result = await createILLRequest(mockToken, {
        title: 'The Great Gatsby',
        author: 'F. Scott Fitzgerald',
      })

      expect(result).toEqual(mockResponse)
      expect(fetchApiMock).toHaveBeenCalledWith('/ill/requests', {
        method: 'POST',
        token: mockToken,
        body: { title: 'The Great Gatsby', author: 'F. Scott Fitzgerald' },
      })
    })

    it('should throw on failure', async () => {
      fetchApiMock.mockRejectedValueOnce(new Error('Network error'))
      await expect(
        createILLRequest(mockToken, { title: 'Test' })
      ).rejects.toThrow()
    })
  })

  describe('getMyILLRequests', () => {
    it('should fetch patron ILL requests', async () => {
      const mockRequests = [
        { id: 1, title: 'Book A', status: 'pending', status_label: 'Request submitted' },
        { id: 2, title: 'Book B', status: 'checked_out', status_label: 'Checked out to you' },
      ]
      fetchApiMock.mockResolvedValueOnce(mockRequests)

      const result = await getMyILLRequests(mockToken)

      expect(result).toEqual(mockRequests)
      expect(fetchApiMock).toHaveBeenCalledWith('/ill/requests/my', { token: mockToken })
    })

    it('should pass active_only filter', async () => {
      fetchApiMock.mockResolvedValueOnce([])

      await getMyILLRequests(mockToken, true)

      expect(fetchApiMock).toHaveBeenCalledWith('/ill/requests/my?active_only=true', {
        token: mockToken,
      })
    })

    it('should throw on failure', async () => {
      fetchApiMock.mockRejectedValueOnce(new Error('fail'))
      await expect(getMyILLRequests(mockToken)).rejects.toThrow(
        'Failed to fetch interlibrary loan requests'
      )
    })
  })

  describe('cancelILLRequest', () => {
    it('should cancel a request', async () => {
      const mockResponse = { id: 1, status: 'cancelled' }
      fetchApiMock.mockResolvedValueOnce(mockResponse)

      const result = await cancelILLRequest(mockToken, 1)

      expect(result.status).toBe('cancelled')
      expect(fetchApiMock).toHaveBeenCalledWith('/ill/requests/1/cancel', {
        method: 'POST',
        token: mockToken,
      })
    })
  })

  // ============================
  // Partner Search
  // ============================

  describe('searchPartnerCatalogs', () => {
    it('should search partners by title', async () => {
      const mockResults = [
        { partner_library_id: 1, partner_library_name: 'Elm St', available: true, lending_fee: 0 },
      ]
      fetchApiMock.mockResolvedValueOnce(mockResults)

      const result = await searchPartnerCatalogs(mockToken, 'Gatsby')

      expect(result).toEqual(mockResults)
      expect(fetchApiMock).toHaveBeenCalledWith(
        expect.stringContaining('/ill/search-partners?title=Gatsby'),
        { token: mockToken }
      )
    })

    it('should include author and isbn params', async () => {
      fetchApiMock.mockResolvedValueOnce([])

      await searchPartnerCatalogs(mockToken, 'Gatsby', 'Fitzgerald', '978-123')

      expect(fetchApiMock).toHaveBeenCalledWith(
        expect.stringMatching(/title=Gatsby.*author=Fitzgerald.*isbn=978-123/),
        { token: mockToken }
      )
    })
  })

  // ============================
  // Staff Endpoints
  // ============================

  describe('staffListILLRequests', () => {
    it('should list all requests with no filters', async () => {
      fetchApiMock.mockResolvedValueOnce([])

      await staffListILLRequests(mockToken)

      expect(fetchApiMock).toHaveBeenCalledWith('/ill/staff/requests', { token: mockToken })
    })

    it('should pass status filter', async () => {
      fetchApiMock.mockResolvedValueOnce([])

      await staffListILLRequests(mockToken, { status: 'pending' })

      expect(fetchApiMock).toHaveBeenCalledWith(
        expect.stringContaining('status=pending'),
        { token: mockToken }
      )
    })

    it('should pass active_only filter', async () => {
      fetchApiMock.mockResolvedValueOnce([])

      await staffListILLRequests(mockToken, { active_only: true })

      expect(fetchApiMock).toHaveBeenCalledWith(
        expect.stringContaining('active_only=true'),
        { token: mockToken }
      )
    })
  })

  describe('staffUpdateILLRequest', () => {
    it('should update a request status', async () => {
      const mockResponse = { id: 1, status: 'approved' }
      fetchApiMock.mockResolvedValueOnce(mockResponse)

      const result = await staffUpdateILLRequest(mockToken, 1, { status: 'approved' })

      expect(result.status).toBe('approved')
      expect(fetchApiMock).toHaveBeenCalledWith('/ill/staff/requests/1', {
        method: 'PATCH',
        token: mockToken,
        body: { status: 'approved' },
      })
    })
  })

  describe('staffAutoSearchAndSubmit', () => {
    it('should trigger auto-search', async () => {
      const mockResponse = { id: 1, status: 'submitted', partner_library_name: 'Elm St' }
      fetchApiMock.mockResolvedValueOnce(mockResponse)

      const result = await staffAutoSearchAndSubmit(mockToken, 1)

      expect(result.status).toBe('submitted')
      expect(fetchApiMock).toHaveBeenCalledWith('/ill/staff/requests/1/auto-search', {
        method: 'POST',
        token: mockToken,
      })
    })
  })

  describe('staffRenewILLRequest', () => {
    it('should renew a checkout', async () => {
      const mockResponse = { id: 1, renewal_count: 1, due_date: '2026-04-01' }
      fetchApiMock.mockResolvedValueOnce(mockResponse)

      const result = await staffRenewILLRequest(mockToken, 1)

      expect(result.renewal_count).toBe(1)
      expect(fetchApiMock).toHaveBeenCalledWith('/ill/staff/requests/1/renew', {
        method: 'POST',
        token: mockToken,
      })
    })
  })

  describe('staffAddTrackingUpdate', () => {
    it('should add a tracking update', async () => {
      const mockTracking = { id: 1, message: 'Item shipped', status: 'in_transit' }
      fetchApiMock.mockResolvedValueOnce(mockTracking)

      const result = await staffAddTrackingUpdate(mockToken, 1, { message: 'Item shipped' })

      expect(result.message).toBe('Item shipped')
      expect(fetchApiMock).toHaveBeenCalledWith('/ill/staff/requests/1/tracking', {
        method: 'POST',
        token: mockToken,
        body: { message: 'Item shipped' },
      })
    })
  })

  // ============================
  // Shipping Label
  // ============================

  describe('getReturnShippingLabel', () => {
    it('should fetch shipping label data', async () => {
      const mockLabel = {
        to_library: 'Elm Street Public Library',
        to_city: 'Springfield',
        label_format: 'pdf',
      }
      fetchApiMock.mockResolvedValueOnce(mockLabel)

      const result = await getReturnShippingLabel(mockToken, 1)

      expect(result).toEqual(mockLabel)
      expect(fetchApiMock).toHaveBeenCalledWith('/ill/staff/requests/1/shipping-label', {
        token: mockToken,
      })
    })
  })

  // ============================
  // Cost Tracking
  // ============================

  describe('staffAddCostRecord', () => {
    it('should add a cost record', async () => {
      const mockCost = { id: 1, category: 'shipping', amount: '4.50' }
      fetchApiMock.mockResolvedValueOnce(mockCost)

      const result = await staffAddCostRecord(mockToken, 1, {
        category: 'shipping',
        amount: '4.50',
        description: 'USPS',
      })

      expect(result.category).toBe('shipping')
      expect(fetchApiMock).toHaveBeenCalledWith('/ill/staff/requests/1/costs', {
        method: 'POST',
        token: mockToken,
        body: { category: 'shipping', amount: '4.50', description: 'USPS' },
      })
    })
  })

  // ============================
  // Due Date Reminders
  // ============================

  describe('getDueReminders', () => {
    it('should fetch due date reminders', async () => {
      const mockReminders = { upcoming: [], overdue: [], upcoming_count: 0, overdue_count: 0 }
      fetchApiMock.mockResolvedValueOnce(mockReminders)

      const result = await getDueReminders(mockToken)

      expect(result.upcoming_count).toBe(0)
      expect(fetchApiMock).toHaveBeenCalledWith('/ill/staff/due-reminders?days_ahead=7', {
        token: mockToken,
      })
    })
  })

  // ============================
  // Reporting
  // ============================

  describe('getFillRateReport', () => {
    it('should fetch fill rate report', async () => {
      const mockReport = {
        total_requests: 100,
        filled_requests: 85,
        fill_rate_percent: 85.0,
      }
      fetchApiMock.mockResolvedValueOnce(mockReport)

      const result = await getFillRateReport(mockToken)

      expect(result.fill_rate_percent).toBe(85.0)
      expect(fetchApiMock).toHaveBeenCalledWith('/ill/staff/reports/fill-rate', {
        token: mockToken,
      })
    })

    it('should pass period params', async () => {
      fetchApiMock.mockResolvedValueOnce({})

      await getFillRateReport(mockToken, '2025-01-01', '2025-12-31')

      expect(fetchApiMock).toHaveBeenCalledWith(
        expect.stringContaining('period_start=2025-01-01'),
        { token: mockToken }
      )
    })
  })

  describe('getReciprocalLendingDashboard', () => {
    it('should fetch reciprocal lending dashboard', async () => {
      const mockDashboard = {
        total_partners: 5,
        active_partners: 4,
        total_items_borrowed: 50,
        total_items_lent: 40,
        partner_stats: [],
      }
      fetchApiMock.mockResolvedValueOnce(mockDashboard)

      const result = await getReciprocalLendingDashboard(mockToken)

      expect(result.total_partners).toBe(5)
      expect(fetchApiMock).toHaveBeenCalledWith(
        '/ill/staff/reports/reciprocal-dashboard',
        { token: mockToken }
      )
    })
  })

  // ============================
  // Partner Library Management
  // ============================

  describe('staffListPartnerLibraries', () => {
    it('should list partner libraries', async () => {
      const mockPartners = [
        { id: 1, name: 'Elm Street Library', code: 'ESPL', status: 'active' },
      ]
      fetchApiMock.mockResolvedValueOnce(mockPartners)

      const result = await staffListPartnerLibraries(mockToken)

      expect(result).toHaveLength(1)
      expect(fetchApiMock).toHaveBeenCalledWith('/ill/staff/partners', { token: mockToken })
    })

    it('should pass search filter', async () => {
      fetchApiMock.mockResolvedValueOnce([])

      await staffListPartnerLibraries(mockToken, { search: 'Elm' })

      expect(fetchApiMock).toHaveBeenCalledWith(
        expect.stringContaining('search=Elm'),
        { token: mockToken }
      )
    })
  })

  describe('staffCreatePartnerLibrary', () => {
    it('should create a partner library', async () => {
      const mockPartner = { id: 1, name: 'New Library', code: 'NL' }
      fetchApiMock.mockResolvedValueOnce(mockPartner)

      const result = await staffCreatePartnerLibrary(mockToken, {
        name: 'New Library',
        code: 'NL',
      })

      expect(result.name).toBe('New Library')
      expect(fetchApiMock).toHaveBeenCalledWith('/ill/staff/partners', {
        method: 'POST',
        token: mockToken,
        body: { name: 'New Library', code: 'NL' },
      })
    })
  })
})
