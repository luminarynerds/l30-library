/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Staff Picks API Service
 * Handles API calls for staff picks management
 */
import { fetchApi, isApiError } from '@/lib/api-client'

// ==================== Types ====================

export interface CatalogItemSummary {
  id: number
  title: string
  author: string | null
  cover_url: string | null
  item_type: string | null
  /** ItemStatus value (e.g. 'available', 'checked_out'); null on legacy rows. */
  status?: string | null
}

export interface StaffPicksItem {
  id: number
  catalog_item_id: number
  catalog_item: CatalogItemSummary
  staff_notes: string | null
  display_order: number
  added_at: string
  added_by_name: string | null
}

export interface StaffPicksList {
  id: number
  title: string
  description: string | null
  is_active: boolean
  display_order: number
  item_count: number
  created_at: string
  updated_at: string
  created_by_name: string | null
}

export interface StaffPicksListWithItems extends StaffPicksList {
  items: StaffPicksItem[]
}

// ==================== Staff Endpoints ====================

export async function getStaffPicksLists(
  token: string,
  includeInactive: boolean = false
): Promise<StaffPicksList[]> {
  try {
    const params = includeInactive ? '?active_only=false' : ''
    return await fetchApi<StaffPicksList[]>(`/staff/picks${params}`, { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to load staff picks lists')
    }
    throw error
  }
}

export async function createStaffPicksList(
  token: string,
  title: string,
  description?: string
): Promise<StaffPicksList> {
  try {
    return await fetchApi<StaffPicksList>('/staff/picks', {
      method: 'POST',
      token,
      body: { title, description: description || null, is_active: true, display_order: 0 },
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to create list')
    }
    throw error
  }
}

export async function getStaffPicksListWithItems(
  token: string,
  listId: number
): Promise<StaffPicksListWithItems> {
  try {
    return await fetchApi<StaffPicksListWithItems>(`/staff/picks/${listId}`, { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to load list')
    }
    throw error
  }
}

export async function updateStaffPicksList(
  token: string,
  listId: number,
  updates: { title?: string; description?: string; is_active?: boolean; display_order?: number }
): Promise<StaffPicksList> {
  try {
    return await fetchApi<StaffPicksList>(`/staff/picks/${listId}`, {
      method: 'PUT',
      token,
      body: updates,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to update list')
    }
    throw error
  }
}

export async function deleteStaffPicksList(token: string, listId: number): Promise<void> {
  try {
    await fetchApi<void>(`/staff/picks/${listId}`, {
      method: 'DELETE',
      token,
      skipJsonParse: true,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to delete list')
    }
    throw error
  }
}

export async function addItemToStaffPicksList(
  token: string,
  listId: number,
  catalogItemId: number,
  staffNotes?: string
): Promise<StaffPicksItem> {
  try {
    return await fetchApi<StaffPicksItem>(`/staff/picks/${listId}/items`, {
      method: 'POST',
      token,
      body: { catalog_item_id: catalogItemId, staff_notes: staffNotes || null, display_order: 0 },
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to add item')
    }
    throw error
  }
}

export async function removeItemFromStaffPicksList(
  token: string,
  listId: number,
  itemId: number
): Promise<void> {
  try {
    await fetchApi<void>(`/staff/picks/${listId}/items/${itemId}`, {
      method: 'DELETE',
      token,
      skipJsonParse: true,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to remove item')
    }
    throw error
  }
}

// ==================== Public Endpoints ====================

export async function getPublicStaffPicksLists(limit: number = 10): Promise<StaffPicksList[]> {
  try {
    return await fetchApi<StaffPicksList[]>(`/staff/picks/public/lists?limit=${limit}`)
  } catch {
    return []
  }
}

export async function getPublicStaffPicksList(listId: number): Promise<StaffPicksListWithItems | null> {
  try {
    return await fetchApi<StaffPicksListWithItems>(`/staff/picks/public/${listId}`)
  } catch {
    return null
  }
}

// ==================== Additional Staff Endpoints ====================

export async function updateStaffPicksItem(
  token: string,
  listId: number,
  itemId: number,
  updates: { staff_notes?: string; display_order?: number }
): Promise<StaffPicksItem> {
  try {
    return await fetchApi<StaffPicksItem>(`/staff/picks/${listId}/items/${itemId}`, {
      method: 'PATCH',
      token,
      body: updates,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to update item')
    }
    throw error
  }
}

export async function reorderStaffPicksItems(
  token: string,
  listId: number,
  itemIds: number[]
): Promise<StaffPicksItem[]> {
  try {
    return await fetchApi<StaffPicksItem[]>(`/staff/picks/${listId}/reorder`, {
      method: 'POST',
      token,
      body: { item_ids: itemIds },
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to reorder items')
    }
    throw error
  }
}
