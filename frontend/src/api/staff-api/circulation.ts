/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { fetchApi, isApiError } from '@/lib/api-client'
import type { Checkout, Hold } from '../circulation-api'
import type { PatronCheckout } from './patrons'

// ==================== Quick Circulation Types ====================

export interface QuickCheckoutRequest {
  barcode: string
}

export interface QuickCheckoutResponse {
  checkout: PatronCheckout
  message: string
}

export interface RenewAllResponse {
  renewed_count: number
  failed_count: number
  renewals: PatronCheckout[]
  failures: Array<{
    item_id: number
    item_title: string
    reason: string
  }>
  message: string
}

export interface ReturnAllResponse {
  returned_count: number
  returns: PatronCheckout[]
  message: string
}

export interface PlaceHoldForPatronRequest {
  item_id: number
}

export interface PlaceHoldForPatronResponse {
  hold: Hold
  message: string
}

// ==================== Circulation Functions ====================

export interface HoldOverrideOptions {
  override_hold: true
  hold_disposition: 'bump_to_front' | 'cancel'
}

export async function staffCheckoutItem(
  token: string,
  patronId: number,
  barcode: string,
  override?: HoldOverrideOptions,
): Promise<Checkout> {
  try {
    const response = await fetchApi<QuickCheckoutResponse>(`/staff/patrons/${patronId}/quick-checkout`, {
      method: 'POST',
      token,
      body: override ? { barcode, ...override } : { barcode },
    })
    return response.checkout as unknown as Checkout
  } catch (error: unknown) {
    if (isApiError(error)) {
      const err = new Error(error.detail || 'Checkout failed') as Error & { response?: unknown }
      err.response = error
      throw err
    }
    throw error
  }
}

interface HoldCheckoutResponse {
  checkout: unknown
  hold_id: number
  message: string
}

export async function staffCheckoutHold(token: string, holdId: number): Promise<Checkout> {
  try {
    const response = await fetchApi<HoldCheckoutResponse>(
      `/circulation/holds/${holdId}/checkout`,
      { method: 'POST', token },
    )
    return response.checkout as unknown as Checkout
  } catch (error: unknown) {
    if (isApiError(error)) {
      const err = new Error(error.detail || 'Hold checkout failed') as Error & { response?: unknown }
      err.response = error
      throw err
    }
    throw error
  }
}
export interface NextHoldInfo {
  hold_id: number
  patron_first_name: string
  patron_last_initial: string
  shelf_slot: string | null
  expires_at: string | null
  item_title: string | null
}

export interface StaffCheckinResponse {
  message: string
  checkout: Checkout
  next_hold: NextHoldInfo | null
}

export async function staffCheckinItem(
  token: string,
  barcode: string,
): Promise<StaffCheckinResponse> {
  try {
    // Backend now returns {message, checkout, next_hold}. Type defensively in
    // case the deploy lags the FE: missing fields fall back to safe defaults.
    const raw = await fetchApi<Partial<StaffCheckinResponse> & { id?: number }>(
      `/staff/checkin-barcode?barcode=${encodeURIComponent(barcode)}`,
      {
        method: 'POST',
        token,
      },
    )
    const checkout = (raw.checkout ?? (raw as unknown as Checkout))
    return {
      message: raw.message ?? 'Item checked in successfully',
      checkout: checkout as Checkout,
      next_hold: raw.next_hold ?? null,
    }
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Check-in failed')
    }
    throw error
  }
}

export async function getOverdueItems(token: string): Promise<PatronCheckout[]> {
  try {
    return await fetchApi<PatronCheckout[]>('/staff/circulation/overdue', { token })
  } catch {
    return []
  }
}

// ==================== Quick Circulation Functions ====================

export async function quickCheckoutForPatron(
  token: string,
  patronId: number,
  barcode: string
): Promise<QuickCheckoutResponse> {
  try {
    return await fetchApi<QuickCheckoutResponse>(`/staff/patrons/${patronId}/quick-checkout`, {
      method: 'POST',
      token,
      body: { barcode },
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Checkout failed')
    }
    throw error
  }
}

export async function renewAllEligible(token: string, patronId: number): Promise<RenewAllResponse> {
  try {
    return await fetchApi<RenewAllResponse>(`/staff/patrons/${patronId}/renew-all`, {
      method: 'POST',
      token,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Renew all failed')
    }
    throw error
  }
}

export async function staffRenewCheckout(
  token: string,
  checkoutId: number,
  override = false,
): Promise<Checkout> {
  try {
    return await fetchApi<Checkout>(
      `/staff/override-renew/${checkoutId}?override=${override}`,
      { method: 'POST', token },
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Renewal failed')
    }
    throw error
  }
}

export async function returnAllItems(token: string, patronId: number): Promise<ReturnAllResponse> {
  try {
    return await fetchApi<ReturnAllResponse>(`/staff/patrons/${patronId}/return-all`, {
      method: 'POST',
      token,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Return all failed')
    }
    throw error
  }
}

export async function placeHoldForPatron(
  token: string,
  patronId: number,
  itemId: number
): Promise<PlaceHoldForPatronResponse> {
  try {
    return await fetchApi<PlaceHoldForPatronResponse>(`/staff/patrons/${patronId}/place-hold`, {
      method: 'POST',
      token,
      body: { item_id: itemId },
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to place hold')
    }
    throw error
  }
}

// ==================== Checkin Condition Report ====================

export async function reportCheckinCondition(
  token: string,
  checkoutId: number,
  conditionType: string,
  notes: string
): Promise<{ success: boolean; message: string; condition_type: string }> {
  try {
    const params = new URLSearchParams({
      checkout_id: checkoutId.toString(),
      condition_type: conditionType,
      notes,
    })
    return await fetchApi<{ success: boolean; message: string; condition_type: string }>(
      `/staff/checkin-condition-report?${params.toString()}`,
      {
        method: "POST",
        token,
      }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || "Failed to submit condition report")
    }
    throw error
  }
}

// ==================== Holds Pull List ====================

// Backend returns PullListResponse with locations grouped by shelf location.
// Frontend flattens to a simple list. See backend: PullListResponse in
// app/schemas/circulation.py and app/api/v1/circulation/hold_shelf.py.

interface BackendPullListItem {
  hold_id: number
  item_id: number
  item_title: string
  item_author: string | null
  call_number: string | null
  shelf_location: string | null
  barcode: string | null
  patron_name: string
  patron_initials: string
  patron_library_card: string | null
  hold_expires_at: string | null
  hold_created_at: string
  days_until_expiry: number | null
  shelf_slot: string | null
  patron_on_way: boolean
  qr_pickup_code: string | null
  no_show_count: number
}

interface BackendLocationGroup {
  location: string
  items: BackendPullListItem[]
  item_count: number
}

interface BackendPullListResponse {
  locations: BackendLocationGroup[]
  total_items: number
  generated_at: string
}

export interface PullListItem {
  id: number
  title: string
  author: string | null
  call_number: string | null
  patron_initials: string
  expires_at: string | null
  pickup_location: string | null
}

export async function getHoldsPullList(token: string): Promise<PullListItem[]> {
  try {
    const response = await fetchApi<BackendPullListResponse>(
      "/circulation/holds/pull-list",
      { token }
    )
    return response.locations.flatMap(group =>
      group.items.map(item => ({
        id: item.hold_id,
        title: item.item_title,
        author: item.item_author,
        call_number: item.call_number,
        patron_initials: item.patron_initials,
        expires_at: item.hold_expires_at,
        pickup_location: group.location || item.shelf_location,
      }))
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || "Failed to fetch holds pull list")
    }
    throw error
  }
}
