/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { fetchApi, isApiError } from '@/lib/api-client'
import { getAccessToken } from '@/utils/tokenStore'

// Types
export interface ItemCopy {
  id: number
  catalog_item_id: number
  barcode: string
  call_number: string
  location: string
  condition: 'new' | 'good' | 'fair' | 'poor' | 'damaged' | 'withdrawn'
  status: 'available' | 'checked_out' | 'on_hold' | 'in_transit' | 'in_repair' | 'lost' | 'withdrawn'
  acquisition_date: string | null
  acquisition_price: number | null
  replacement_cost: number | null
  notes: string | null
  created_at: string
  updated_at: string
  catalog_title?: string | null
  catalog_author?: string | null
  catalog_item?: {
    id: number
    title: string
    author: string | null
    item_type: string
  }
}

export interface ConditionHistory {
  id: number
  copy_id: number
  old_condition: string
  new_condition: string
  changed_by: number
  changed_at: string
  notes: string | null
  changed_by_name?: string
}

export interface InventoryAudit {
  id: number
  name: string
  description: string | null
  location_filter: string | null
  started_at: string
  completed_at: string | null
  items_expected: number
  items_found: number
  items_missing: number
  items_misplaced: number
  created_by_id: number
  created_by_name?: string
}

export interface AuditScanResult {
  copy_id: number
  barcode: string
  title: string
  status: 'found' | 'unexpected' | 'already_scanned'
  message: string
}


// Inventory Copies API
export async function getInventoryCopies(params?: {
  catalog_item_id?: number
  location?: string
  condition?: string
  status?: string
  page?: number
  per_page?: number
}): Promise<{ items: ItemCopy[]; total: number; page: number; per_page: number }> {
  const token = getAccessToken()
  const searchParams = new URLSearchParams()
  if (params?.catalog_item_id) searchParams.set('catalog_item_id', params.catalog_item_id.toString())
  if (params?.location) searchParams.set('location', params.location)
  if (params?.condition) searchParams.set('condition', params.condition)
  if (params?.status) searchParams.set('status', params.status)
  if (params?.page) searchParams.set('page', params.page.toString())
  if (params?.per_page) searchParams.set('per_page', params.per_page.toString())
  const query = searchParams.toString() ? `?${searchParams}` : ''
  try {
    return await fetchApi<{ items: ItemCopy[]; total: number; page: number; per_page: number }>(`/inventory/copies${query}`, { ...(token ? { token } : {}) })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Request failed')
    }
    throw error
  }
}

export async function getInventoryCopy(copyId: number): Promise<ItemCopy> {
  const token = getAccessToken()
  try {
    return await fetchApi<ItemCopy>(`/inventory/copies/${copyId}`, { ...(token ? { token } : {}) })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Request failed')
    }
    throw error
  }
}


export async function withdrawCopy(copyId: number, reason?: string): Promise<ItemCopy> {
  const token = getAccessToken()
  try {
    return await fetchApi<ItemCopy>(`/inventory/copies/${copyId}/withdraw`, {
      method: 'POST',
      ...(token ? { token } : {}),
      body: { reason },
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Request failed')
    }
    throw error
  }
}

export async function getCopyConditionHistory(copyId: number): Promise<ConditionHistory[]> {
  const token = getAccessToken()
  try {
    return await fetchApi<ConditionHistory[]>(`/inventory/copies/${copyId}/condition-history`, { ...(token ? { token } : {}) })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Request failed')
    }
    throw error
  }
}

export async function logConditionChange(copyId: number, data: { new_condition: string; repair_notes?: string }): Promise<ConditionHistory> {
  const token = getAccessToken()
  try {
    return await fetchApi<ConditionHistory>(`/inventory/copies/${copyId}/condition`, {
      method: 'POST',
      ...(token ? { token } : {}),
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Request failed')
    }
    throw error
  }
}

export async function lookupByBarcode(barcode: string): Promise<ItemCopy> {
  const token = getAccessToken()
  try {
    return await fetchApi<ItemCopy>(`/inventory/lookup/${encodeURIComponent(barcode)}`, { ...(token ? { token } : {}) })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Request failed')
    }
    throw error
  }
}

// Inventory Audits API
export async function getInventoryAudits(params?: {
  status?: string
  page?: number
  per_page?: number
}): Promise<{ items: InventoryAudit[]; total: number }> {
  const token = getAccessToken()
  const searchParams = new URLSearchParams()
  if (params?.status) searchParams.set('status', params.status)
  if (params?.page) searchParams.set('page', params.page.toString())
  if (params?.per_page) searchParams.set('per_page', params.per_page.toString())
  const query = searchParams.toString() ? `?${searchParams}` : ''
  try {
    return await fetchApi<{ items: InventoryAudit[]; total: number }>(`/inventory/audits${query}`, { ...(token ? { token } : {}) })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Request failed')
    }
    throw error
  }
}

export async function getInventoryAudit(auditId: number): Promise<InventoryAudit & { scanned_items: ItemCopy[]; missing_items: ItemCopy[] }> {
  const token = getAccessToken()
  try {
    return await fetchApi<InventoryAudit & { scanned_items: ItemCopy[]; missing_items: ItemCopy[] }>(`/inventory/audits/${auditId}`, { ...(token ? { token } : {}) })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Request failed')
    }
    throw error
  }
}

export async function startInventoryAudit(data: { name: string; description?: string; location_filter?: string }): Promise<InventoryAudit> {
  const token = getAccessToken()
  try {
    return await fetchApi<InventoryAudit>('/inventory/audits', {
      method: 'POST',
      ...(token ? { token } : {}),
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Request failed')
    }
    throw error
  }
}

export async function scanAuditItem(auditId: number, barcode: string): Promise<AuditScanResult> {
  const token = getAccessToken()
  try {
    return await fetchApi<AuditScanResult>(`/inventory/audits/${auditId}/scan`, {
      method: 'POST',
      ...(token ? { token } : {}),
      body: { barcode },
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Request failed')
    }
    throw error
  }
}

export async function completeInventoryAudit(auditId: number): Promise<InventoryAudit> {
  const token = getAccessToken()
  try {
    return await fetchApi<InventoryAudit>(`/inventory/audits/${auditId}/complete`, {
      method: 'POST',
      ...(token ? { token } : {}),
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Request failed')
    }
    throw error
  }
}

// Repair API
export interface RepairRequest {
  new_condition: 'good' | 'fair' | 'poor'
  repair_notes?: string
  repair_cost?: number
}

export async function repairCopy(copyId: number, data: RepairRequest): Promise<ItemCopy> {
  const token = getAccessToken()
  try {
    return await fetchApi<ItemCopy>(`/inventory/copies/${copyId}/repair`, {
      method: 'POST',
      ...(token ? { token } : {}),
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Request failed')
    }
    throw error
  }
}
