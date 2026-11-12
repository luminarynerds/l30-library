/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { fetchApi, isApiError } from '@/lib/api-client'

// ==================== Pagination Types ====================

export interface PaginationInfo {
  page: number
  per_page: number
  total: number
  total_pages: number
  has_next: boolean
  has_previous: boolean
}

export interface PaginatedResponse<T> {
  data: T[]
  pagination: PaginationInfo
}

// ==================== Circulation Types ====================

export interface Checkout {
  id: number
  user_id: number
  item_id: number
  status: 'active' | 'returned' | 'overdue' | 'lost'
  checked_out_at: string
  due_date: string
  returned_at: string | null
  renewal_count?: number
  renewals_remaining?: number
  item_title: string | null
  item_author: string | null
}

export interface Hold {
  id: number
  user_id: number
  item_id: number
  status: 'pending' | 'ready' | 'fulfilled' | 'cancelled' | 'expired'
  position: number
  created_at: string
  notified_at: string | null
  expires_at: string | null
  cancelled_at: string | null
  cancellation_reason: string | null
  cancelled_by: string | null
  item_title: string | null
  item_author: string | null
  pickup_location_id?: number | null
  pickup_branch_name?: string | null
  is_ready?: boolean
  queue_position?: number
  placed_at?: string
  estimated_wait_days?: number | null
  estimated_wait_weeks?: number | null
}

export interface Fine {
  id: number
  amount: string
  reason: string
  description?: string
  created_at: string
  paid_at?: string
  waived_at?: string
  item_title?: string
}

export interface FinesSummary {
  total_outstanding: number
  total_paid: number
  outstanding_count: number
  paid_count: number
}

export interface HoldResponse {
  message: string
  item_id: number
}

// ==================== Circulation Functions ====================

export async function getMyCheckouts(token: string): Promise<Checkout[]> {
  try {
    const response = await fetchApi<PaginatedResponse<Checkout>>('/circulation/checkouts', { token })
    return response.data
  } catch {
    throw new Error('Failed to fetch checkouts')
  }
}

export async function getMyHolds(token: string): Promise<Hold[]> {
  try {
    const response = await fetchApi<PaginatedResponse<Hold>>('/circulation/holds', { token })
    return response.data
  } catch (error: unknown) {
    if (isApiError(error)) {
      if (error.status === 401) {
        throw new Error('Please sign in to view your holds.')
      }
      throw new Error(error.detail || 'Failed to fetch your holds')
    }
    throw new Error('Failed to fetch holds')
  }
}

export async function renewCheckout(token: string, checkoutId: number): Promise<Checkout> {
  try {
    return await fetchApi<Checkout>(`/circulation/renew/${checkoutId}`, {
      method: 'POST',
      token,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Renewal failed')
    }
    throw error
  }
}

export async function cancelHold(token: string, holdId: number, reason?: string): Promise<void> {
  try {
    await fetchApi(`/circulation/holds/${holdId}`, {
      method: 'DELETE',
      token,
      body: reason ? { reason } : undefined,
      skipJsonParse: true,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      if (error.status === 401) {
        throw new Error('Please sign in to cancel holds.')
      }
      if (error.status === 404) {
        throw new Error('This hold was not found. It may have already been cancelled.')
      }
      throw new Error(error.detail || 'Failed to cancel hold. Please try again.')
    }
    throw error
  }
}

export async function getMyHistory(token: string): Promise<Checkout[]> {
  try {
    const response = await fetchApi<PaginatedResponse<Checkout>>('/circulation/history', { token })
    return response.data
  } catch {
    throw new Error('Failed to fetch history')
  }
}

export async function getMyFines(token: string): Promise<Fine[]> {
  try {
    const response = await fetchApi<PaginatedResponse<Fine>>('/circulation/fines', { token })
    return response.data
  } catch {
    throw new Error('Failed to fetch fines')
  }
}

export async function getMyFinesSummary(token: string): Promise<FinesSummary> {
  try {
    return await fetchApi<FinesSummary>('/circulation/fines/summary', { token })
  } catch {
    throw new Error('Failed to fetch fines summary')
  }
}

// placeHold moved from catalog-api (uses /circulation/holds endpoint)
export async function placeHold(token: string, itemId: number, pickupLocationId?: number): Promise<HoldResponse> {
  try {
    return await fetchApi<HoldResponse>('/circulation/holds', {
      method: 'POST',
      token,
      body: { item_id: itemId, pickup_location_id: pickupLocationId ?? null },
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      // Provide specific error messages based on status code
      if (error.status === 401) {
        throw new Error('Please sign in to place a hold. Please log in and try again.')
      }
      if (error.status === 403) {
        // Eligibility checks (expired card, account restriction, or fine block)
        // supply a patron-safe explanation. Preserve it so the hold dialog can
        // explain the next step instead of presenting a misleading permission error.
        throw new Error(error.detail || 'Your account cannot place holds right now. Please contact the library.')
      }
      if (error.status === 409) {
        throw new Error('You already have a hold on this item.')
      }
      if (error.status === 422) {
        throw new Error(error.detail || 'Invalid request. Please check your input and try again.')
      }
      throw new Error(error.detail || 'Failed to place hold. Please try again.')
    }
    throw error
  }
}

// ==================== Self-Checkout Functions ====================

export interface SelfCheckoutItem {
  id: number
  title: string
  author: string | null
  item_type: string
  status: string
  isbn: string | null
  publisher: string | null
  publication_year: number | null
  description: string | null
  location: string | null
  barcode: string | null
}

export async function lookupItemByBarcode(barcode: string): Promise<SelfCheckoutItem> {
  try {
    return await fetchApi<SelfCheckoutItem>(`/catalog/barcode/${encodeURIComponent(barcode)}`)
  } catch (error: unknown) {
    if (isApiError(error)) {
      if (error.status === 404) {
        throw new Error('Item not found with that barcode')
      }
      throw new Error(error.detail || 'Failed to look up item')
    }
    throw error
  }
}

export async function selfCheckoutItem(token: string, itemId: number): Promise<Checkout> {
  try {
    return await fetchApi<Checkout>('/circulation/checkout', {
      method: 'POST',
      token,
      body: { item_id: itemId },
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Checkout failed')
    }
    throw error
  }
}

// ==================== Checkin/Return Functions ====================

export interface CheckinRequest {
  checkout_id?: number
  barcode?: string
}

export interface CheckinResponse {
  message: string
  checkout: Checkout
}

export async function checkinItem(token: string, request: CheckinRequest): Promise<CheckinResponse> {
  try {
    return await fetchApi<CheckinResponse>('/circulation/checkin', {
      method: 'POST',
      token,
      body: request,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      if (error.status === 401) {
        throw new Error('Please sign in to check in items.')
      }
      if (error.status === 404) {
        throw new Error('Item or checkout not found.')
      }
      if (error.status === 422) {
        throw new Error(error.detail || 'Invalid request. Please provide checkout_id or barcode.')
      }
      throw new Error(error.detail || 'Checkin failed')
    }
    throw error
  }
}

export interface ReturnResponse {
  message: string
  checkout: Checkout
}

export async function returnItem(token: string, checkoutId: number): Promise<ReturnResponse> {
  try {
    return await fetchApi<ReturnResponse>(`/circulation/return/${checkoutId}`, {
      method: 'POST',
      token,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      if (error.status === 401) {
        throw new Error('Please sign in to return items.')
      }
      if (error.status === 404) {
        throw new Error('Checkout not found.')
      }
      throw new Error(error.detail || 'Return failed')
    }
    throw error
  }
}

// ==================== Admin Job Functions ====================

export interface ProcessExpiredHoldsResponse {
  message: string
  expired_count: number
}

export async function processExpiredHolds(token: string): Promise<ProcessExpiredHoldsResponse> {
  try {
    return await fetchApi<ProcessExpiredHoldsResponse>('/circulation/holds/process-expired', {
      method: 'POST',
      token,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      if (error.status === 401) {
        throw new Error('Please sign in to perform this action.')
      }
      if (error.status === 403) {
        throw new Error('You do not have permission to process expired holds.')
      }
      throw new Error(error.detail || 'Failed to process expired holds')
    }
    throw error
  }
}

export interface JobResponse {
  message: string
  processed_count: number
}

export async function jobProcessExpiredHolds(token: string): Promise<JobResponse> {
  try {
    return await fetchApi<JobResponse>('/circulation/jobs/process-expired-holds', {
      method: 'POST',
      token,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      if (error.status === 401) {
        throw new Error('Please sign in to run this job.')
      }
      if (error.status === 403) {
        throw new Error('You do not have admin permission to run this job.')
      }
      throw new Error(error.detail || 'Failed to run expired holds job')
    }
    throw error
  }
}

export async function jobProcessOverdueFines(token: string): Promise<JobResponse> {
  try {
    return await fetchApi<JobResponse>('/circulation/jobs/process-overdue-fines', {
      method: 'POST',
      token,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      if (error.status === 401) {
        throw new Error('Please sign in to run this job.')
      }
      if (error.status === 403) {
        throw new Error('You do not have admin permission to run this job.')
      }
      throw new Error(error.detail || 'Failed to run overdue fines job')
    }
    throw error
  }
}
