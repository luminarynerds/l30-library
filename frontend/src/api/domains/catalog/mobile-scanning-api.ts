/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { fetchApi, isApiError } from '@/lib/api-client'
import { getAccessToken } from '@/utils/tokenStore'

// Types
export interface InventorySection {
  location: string
  item_count: number
}

export interface SectionItem {
  id: number
  barcode: string
  copy_number: number
  location: string
  condition: string
  catalog_title: string | null
  catalog_author: string | null
  call_number: string | null
}

export interface BatchScanInput {
  barcode: string
  found_at_location: string | null
}

export interface BatchScanResult {
  barcode: string
  status: 'found' | 'not_found' | 'already_scanned'
  title?: string | null
  is_misplaced?: boolean
  expected_location?: string | null
  message: string
}

export interface AuditProgress {
  items_expected: number
  items_found: number
  items_missing: number
  items_misplaced: number
  completion_pct: number
}

export interface BatchScanResponse {
  audit_id: number
  results: BatchScanResult[]
  total_processed: number
  total_found: number
  total_errors: number
  total_duplicates: number
  audit_progress: AuditProgress
}

// API Functions
export async function getInventorySections(): Promise<{ sections: InventorySection[]; total_sections: number }> {
  const token = getAccessToken()
  try {
    return await fetchApi<{ sections: InventorySection[]; total_sections: number }>('/inventory/sections', {
      ...(token ? { token } : {}),
    })
  } catch (error: unknown) {
    if (isApiError(error)) throw new Error(error.detail || 'Failed to fetch sections')
    throw error
  }
}

export async function getSectionItems(location: string): Promise<{ items: SectionItem[]; total: number; location: string }> {
  const token = getAccessToken()
  try {
    return await fetchApi<{ items: SectionItem[]; total: number; location: string }>(
      `/inventory/sections/${encodeURIComponent(location)}/items`,
      { ...(token ? { token } : {}) },
    )
  } catch (error: unknown) {
    if (isApiError(error)) throw new Error(error.detail || 'Failed to fetch section items')
    throw error
  }
}

export async function batchScanItems(auditId: number, scans: BatchScanInput[]): Promise<BatchScanResponse> {
  const token = getAccessToken()
  try {
    return await fetchApi<BatchScanResponse>(`/inventory/audits/${auditId}/scan/batch`, {
      method: 'POST',
      ...(token ? { token } : {}),
      body: scans,
    })
  } catch (error: unknown) {
    if (isApiError(error)) throw new Error(error.detail || 'Batch scan failed')
    throw error
  }
}
