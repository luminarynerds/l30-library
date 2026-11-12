/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Inventory API Service Tests
 *
 * Tests the inventory scanning workflow through the API layer:
 * - Start inventory session
 * - Scan items / barcode lookup
 * - Detect misplaced items
 * - Complete audit
 * - Condition changes and repairs
 * - Withdraw items
 * - List audits (history)
 * - Export / report data
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import * as apiClient from '@/lib/api-client'
import * as tokenStore from '@/utils/tokenStore'
import {
  getInventoryCopies,
  getInventoryCopy,
  withdrawCopy,
  getCopyConditionHistory,
  logConditionChange,
  lookupByBarcode,
  getInventoryAudits,
  getInventoryAudit,
  startInventoryAudit,
  scanAuditItem,
  completeInventoryAudit,
  repairCopy,
} from '@/api/inventory-api'

vi.mock('@/lib/api-client', () => ({
  fetchApi: vi.fn(),
  isApiError: vi.fn(),
}))

vi.mock('@/utils/tokenStore', () => ({
  getAccessToken: vi.fn(),
}))

describe('Inventory API', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(tokenStore.getAccessToken).mockReturnValue('test-staff-token')
  })

  // ==================== Start Inventory Session ====================

  describe('startInventoryAudit', () => {
    it('should create a new audit session for a section', async () => {
      const mockAudit = {
        id: 1,
        name: 'Adult Fiction A-1 Q1 Audit',
        description: null,
        location_filter: 'Adult Fiction A-1',
        started_at: '2026-02-25T10:00:00Z',
        completed_at: null,
        items_expected: 42,
        items_found: 0,
        items_missing: 0,
        items_misplaced: 0,
        created_by_id: 5,
      }
      vi.mocked(apiClient.fetchApi).mockResolvedValue(mockAudit)

      const result = await startInventoryAudit({
        name: 'Adult Fiction A-1 Q1 Audit',
        location_filter: 'Adult Fiction A-1',
      })

      expect(result).toEqual(mockAudit)
      expect(apiClient.fetchApi).toHaveBeenCalledWith('/inventory/audits', {
        method: 'POST',
        token: 'test-staff-token',
        body: { name: 'Adult Fiction A-1 Q1 Audit', location_filter: 'Adult Fiction A-1' },
      })
    })

    it('should create audit without location filter (full inventory)', async () => {
      const mockAudit = {
        id: 2,
        name: 'Full Library Inventory',
        description: null,
        location_filter: null,
        started_at: '2026-02-25T10:00:00Z',
        completed_at: null,
        items_expected: 500,
        items_found: 0,
        items_missing: 0,
        items_misplaced: 0,
        created_by_id: 5,
      }
      vi.mocked(apiClient.fetchApi).mockResolvedValue(mockAudit)

      const result = await startInventoryAudit({ name: 'Full Library Inventory' })

      expect(result).toEqual(mockAudit)
    })
  })

  // ==================== Scan Items ====================

  describe('scanAuditItem', () => {
    it('should scan an item by barcode during audit', async () => {
      const mockScanResult = {
        copy_id: 10,
        barcode: 'LSC-ABC12345',
        title: 'The Great Gatsby',
        status: 'found',
        message: 'Item found at expected location',
      }
      vi.mocked(apiClient.fetchApi).mockResolvedValue(mockScanResult)

      const result = await scanAuditItem(1, 'LSC-ABC12345')

      expect(result).toEqual(mockScanResult)
      expect(apiClient.fetchApi).toHaveBeenCalledWith('/inventory/audits/1/scan', {
        method: 'POST',
        token: 'test-staff-token',
        body: { barcode: 'LSC-ABC12345' },
      })
    })

    it('should handle already-scanned item', async () => {
      vi.mocked(apiClient.isApiError).mockReturnValue(true)
      vi.mocked(apiClient.fetchApi).mockRejectedValue({
        detail: 'Item already scanned in this audit',
      })

      await expect(scanAuditItem(1, 'LSC-DUP00001')).rejects.toThrow(
        'Item already scanned in this audit'
      )
    })

    it('should handle unknown barcode', async () => {
      vi.mocked(apiClient.isApiError).mockReturnValue(true)
      vi.mocked(apiClient.fetchApi).mockRejectedValue({
        detail: 'Item not found with this barcode',
      })

      await expect(scanAuditItem(1, 'UNKNOWN-999')).rejects.toThrow(
        'Item not found with this barcode'
      )
    })
  })

  // ==================== Barcode Lookup ====================

  describe('lookupByBarcode', () => {
    it('should find item by barcode', async () => {
      const mockCopy = {
        id: 10,
        catalog_item_id: 1,
        barcode: 'LSC-ABC12345',
        call_number: 'FIC-F5',
        location: 'Adult Fiction A-1',
        condition: 'good',
        status: 'available',
        acquisition_date: '2024-03-01',
        acquisition_price: 24.99,
        notes: null,
        created_at: '2024-03-01T00:00:00Z',
        updated_at: '2024-03-01T00:00:00Z',
      }
      vi.mocked(apiClient.fetchApi).mockResolvedValue(mockCopy)

      const result = await lookupByBarcode('LSC-ABC12345')

      expect(result.barcode).toBe('LSC-ABC12345')
      expect(apiClient.fetchApi).toHaveBeenCalledWith(
        '/inventory/lookup/LSC-ABC12345',
        { token: 'test-staff-token' }
      )
    })

    it('should encode special characters in barcode', async () => {
      vi.mocked(apiClient.fetchApi).mockResolvedValue({
        id: 1,
        barcode: 'LSC/2024+001',
      })

      await lookupByBarcode('LSC/2024+001')

      expect(apiClient.fetchApi).toHaveBeenCalledWith(
        '/inventory/lookup/LSC%2F2024%2B001',
        expect.any(Object)
      )
    })
  })

  // ==================== Misplaced Items (Wrong Shelf) ====================

  describe('misplaced item detection', () => {
    it('should flag item found at unexpected location', async () => {
      const mockScanResult = {
        copy_id: 10,
        barcode: 'LSC-MISPLACED',
        title: 'Misplaced Book',
        status: 'unexpected',
        message: 'Item found at wrong location',
      }
      vi.mocked(apiClient.fetchApi).mockResolvedValue(mockScanResult)

      const result = await scanAuditItem(1, 'LSC-MISPLACED')

      expect(result.status).toBe('unexpected')
    })
  })

  // ==================== Complete Audit / Mark Section Complete ====================

  describe('completeInventoryAudit', () => {
    it('should complete an audit and return final stats', async () => {
      const mockCompleted = {
        id: 1,
        name: 'Adult Fiction Scan',
        description: null,
        location_filter: 'Adult Fiction A-1',
        started_at: '2026-02-25T10:00:00Z',
        completed_at: '2026-02-25T14:30:00Z',
        items_expected: 42,
        items_found: 39,
        items_missing: 3,
        items_misplaced: 1,
        created_by_id: 5,
      }
      vi.mocked(apiClient.fetchApi).mockResolvedValue(mockCompleted)

      const result = await completeInventoryAudit(1)

      expect(result.completed_at).not.toBeNull()
      expect(result.items_missing).toBe(3)
      expect(apiClient.fetchApi).toHaveBeenCalledWith('/inventory/audits/1/complete', {
        method: 'POST',
        token: 'test-staff-token',
      })
    })

    it('should reject completing an already-completed audit', async () => {
      vi.mocked(apiClient.isApiError).mockReturnValue(true)
      vi.mocked(apiClient.fetchApi).mockRejectedValue({
        detail: 'Audit already completed',
      })

      await expect(completeInventoryAudit(1)).rejects.toThrow('Audit already completed')
    })
  })

  // ==================== Inventory History / List Audits ====================

  describe('getInventoryAudits', () => {
    it('should list audits with pagination', async () => {
      const mockList = {
        items: [
          { id: 3, name: 'March Scan', started_at: '2026-03-01T00:00:00Z', completed_at: '2026-03-01T06:00:00Z' },
          { id: 2, name: 'Feb Scan', started_at: '2026-02-01T00:00:00Z', completed_at: '2026-02-01T05:00:00Z' },
        ],
        total: 2,
      }
      vi.mocked(apiClient.fetchApi).mockResolvedValue(mockList)

      const result = await getInventoryAudits({ page: 1, per_page: 20 })

      expect(result.items).toHaveLength(2)
      expect(result.total).toBe(2)
    })
  })

  describe('getInventoryAudit', () => {
    it('should return audit details with scanned and missing items', async () => {
      const mockDetail = {
        id: 1,
        name: 'Q1 Audit',
        items_expected: 10,
        items_found: 8,
        items_missing: 2,
        scanned_items: [
          { id: 1, barcode: 'LSC-001' },
          { id: 2, barcode: 'LSC-002' },
        ],
        missing_items: [
          { id: 3, barcode: 'LSC-003' },
        ],
      }
      vi.mocked(apiClient.fetchApi).mockResolvedValue(mockDetail)

      const result = await getInventoryAudit(1)

      expect(result.scanned_items).toBeDefined()
      expect(result.missing_items).toBeDefined()
    })
  })

  // ==================== Copies CRUD ====================

  describe('getInventoryCopies', () => {
    it('should list copies with filters', async () => {
      const mockResponse = {
        items: [{ id: 1, barcode: 'LSC-001', condition: 'good', location: 'Adult Fiction A-1' }],
        total: 1,
        page: 1,
        per_page: 20,
      }
      vi.mocked(apiClient.fetchApi).mockResolvedValue(mockResponse)

      const result = await getInventoryCopies({ location: 'Adult Fiction', condition: 'good' })

      expect(result.items).toHaveLength(1)
      expect(result.total).toBe(1)
    })
  })

  describe('getInventoryCopy', () => {
    it('should return single copy details', async () => {
      const mockCopy = { id: 5, barcode: 'LSC-005', condition: 'fair', location: 'Ref Desk' }
      vi.mocked(apiClient.fetchApi).mockResolvedValue(mockCopy)

      const result = await getInventoryCopy(5)

      expect(result.id).toBe(5)
      expect(result.barcode).toBe('LSC-005')
    })
  })

// ==================== Batch Update / Withdraw ====================

  describe('withdrawCopy', () => {
    it('should withdraw a copy from circulation', async () => {
      const mockWithdrawn = {
        id: 5,
        barcode: 'LSC-005',
        condition: 'withdrawn',
        status: 'withdrawn',
      }
      vi.mocked(apiClient.fetchApi).mockResolvedValue(mockWithdrawn)

      const result = await withdrawCopy(5, 'Missing after Q1 inventory')

      expect(result.condition).toBe('withdrawn')
      expect(apiClient.fetchApi).toHaveBeenCalledWith('/inventory/copies/5/withdraw', {
        method: 'POST',
        token: 'test-staff-token',
        body: { reason: 'Missing after Q1 inventory' },
      })
    })
  })

  // ==================== Condition History ====================

  describe('getCopyConditionHistory', () => {
    it('should return condition change history', async () => {
      const mockHistory = [
        { id: 1, copy_id: 5, old_condition: 'good', new_condition: 'fair', changed_at: '2026-01-15T00:00:00Z' },
        { id: 2, copy_id: 5, old_condition: 'fair', new_condition: 'poor', changed_at: '2026-02-01T00:00:00Z' },
      ]
      vi.mocked(apiClient.fetchApi).mockResolvedValue(mockHistory)

      const result = await getCopyConditionHistory(5)

      expect(result).toHaveLength(2)
      expect(result[0]!.old_condition).toBe('good')
    })
  })

  describe('logConditionChange', () => {
    it('should log a condition change', async () => {
      const mockChange = {
        id: 3,
        copy_id: 5,
        old_condition: 'poor',
        new_condition: 'damaged',
        changed_at: '2026-02-25T12:00:00Z',
      }
      vi.mocked(apiClient.fetchApi).mockResolvedValue(mockChange)

      const result = await logConditionChange(5, { new_condition: 'damaged', repair_notes: 'Water damage found' })

      expect(result.new_condition).toBe('damaged')
    })
  })

  // ==================== Repair ====================

  describe('repairCopy', () => {
    it('should repair a damaged item', async () => {
      const mockRepaired = {
        id: 5,
        barcode: 'LSC-005',
        condition: 'good',
        status: 'available',
      }
      vi.mocked(apiClient.fetchApi).mockResolvedValue(mockRepaired)

      const result = await repairCopy(5, {
        new_condition: 'good',
        repair_notes: 'Spine re-glued and pages pressed',
        repair_cost: 15.0,
      })

      expect(result.condition).toBe('good')
      expect(apiClient.fetchApi).toHaveBeenCalledWith('/inventory/copies/5/repair', {
        method: 'POST',
        token: 'test-staff-token',
        body: {
          new_condition: 'good',
          repair_notes: 'Spine re-glued and pages pressed',
          repair_cost: 15.0,
        },
      })
    })
  })

  // ==================== Completion Percentage ====================

  describe('completion percentage calculation', () => {
    it('should compute correct percentage from audit data', async () => {
      const mockAudit = {
        id: 1,
        items_expected: 50,
        items_found: 35,
        items_missing: 15,
      }
      vi.mocked(apiClient.fetchApi).mockResolvedValue(mockAudit)

      const result = await getInventoryAudit(1)
      const pct = result.items_expected > 0
        ? Math.round((result.items_found / result.items_expected) * 100)
        : 0

      expect(pct).toBe(70)
    })

    it('should handle zero expected gracefully', async () => {
      const mockAudit = {
        id: 2,
        items_expected: 0,
        items_found: 0,
        items_missing: 0,
      }
      vi.mocked(apiClient.fetchApi).mockResolvedValue(mockAudit)

      const result = await getInventoryAudit(2)
      const pct = result.items_expected > 0
        ? Math.round((result.items_found / result.items_expected) * 100)
        : 0

      expect(pct).toBe(0)
    })
  })

  // ==================== Authentication Required ====================

  describe('authentication', () => {
    it('should include token in all requests when available', async () => {
      vi.mocked(apiClient.fetchApi).mockResolvedValue({ items: [], total: 0, page: 1, per_page: 20 })

      await getInventoryCopies()

      expect(apiClient.fetchApi).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({ token: 'test-staff-token' })
      )
    })

    it('should handle unauthenticated requests gracefully', async () => {
      vi.mocked(tokenStore.getAccessToken).mockReturnValue(null)
      vi.mocked(apiClient.fetchApi).mockResolvedValue({ items: [], total: 0, page: 1, per_page: 20 })

      await getInventoryCopies()

      // Without a token, the call should still be made (server will reject)
      expect(apiClient.fetchApi).toHaveBeenCalled()
    })
  })
})
