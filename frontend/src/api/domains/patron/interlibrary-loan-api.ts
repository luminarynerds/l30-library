/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { fetchApi, isApiError } from '@/lib/api-client'

// ==================== Types ====================

export type ILLRequestStatus =
  | 'pending' | 'searching' | 'located' | 'not_found'
  | 'submitted' | 'approved' | 'denied'
  | 'in_transit' | 'received' | 'checked_out'
  | 'returned' | 'return_in_transit' | 'completed'
  | 'cancelled' | 'lost'

export type ILLRequestType = 'borrow' | 'lend'

export type ShippingMethod = 'usps' | 'ups' | 'fedex' | 'courier' | 'digital'

export type ILLCostCategory =
  | 'shipping' | 'lending_fee' | 'photocopy'
  | 'processing' | 'lost_item' | 'damage' | 'other'

export interface ILLTrackingUpdate {
  id: number
  ill_request_id: number
  status: ILLRequestStatus
  message: string
  is_patron_visible: boolean
  created_at: string
  created_by_id: number | null
}

export interface ILLRequest {
  id: number
  patron_id: number | null
  staff_id: number | null
  request_type: ILLRequestType
  partner_library_id: number | null
  partner_library_name: string | null
  catalog_item_id: number | null
  title: string
  author: string | null
  isbn: string | null
  issn: string | null
  publication_year: string | null
  edition: string | null
  volume: string | null
  material_type: string | null
  notes: string | null
  patron_notes: string | null
  status: ILLRequestStatus
  pickup_branch_id: number | null
  needed_by: string | null
  due_date: string | null
  shipped_at: string | null
  received_at: string | null
  checked_out_at: string | null
  returned_at: string | null
  completed_at: string | null
  shipping_method: ShippingMethod | null
  outbound_tracking: string | null
  return_tracking: string | null
  estimated_cost: string
  actual_cost: string
  renewal_count: number
  max_renewals: number
  created_at: string
  updated_at: string
}

export interface ILLPatronView {
  id: number
  title: string
  author: string | null
  status: ILLRequestStatus
  status_label: string
  due_date: string | null
  needed_by: string | null
  pickup_branch_id: number | null
  renewal_count: number
  max_renewals: number
  tracking_updates: ILLTrackingUpdate[]
  created_at: string
}

export interface PartnerSearchResult {
  partner_library_id: number
  partner_library_name: string
  partner_library_code: string
  available: boolean
  call_number: string | null
  estimated_delivery_days: number | null
  lending_fee: number
}

export interface PartnerLibrary {
  id: number
  name: string
  code: string
  address: string | null
  city: string | null
  state: string | null
  zip_code: string | null
  country: string | null
  contact_name: string | null
  contact_email: string | null
  status: string
  lending_fee: string
  borrowing_fee: string
  max_loan_days: number
  max_renewals: number
  reciprocal_agreement: boolean
  agreement_expires_at: string | null
  created_at: string
}

export interface ILLCostRecord {
  id: number
  ill_request_id: number
  category: ILLCostCategory
  description: string | null
  amount: string
  is_invoiced: boolean
  invoiced_at: string | null
  created_at: string
}

export interface ILLFillRateReport {
  total_requests: number
  filled_requests: number
  unfilled_requests: number
  cancelled_requests: number
  fill_rate_percent: number
  average_turnaround_days: number | null
  period_start: string
  period_end: string
}

export interface ILLCostSummary {
  total_borrowing_costs: string
  total_lending_revenue: string
  net_cost: string
  average_cost_per_request: string
  cost_by_category: Record<string, string>
  period_start: string
  period_end: string
}

export interface ReciprocallLendingStats {
  partner_library_id: number
  partner_library_name: string
  partner_library_code: string
  items_borrowed: number
  items_lent: number
  balance: number
  total_borrowing_cost: string
  total_lending_revenue: string
  active_borrows: number
  active_lends: number
  fill_rate_percent: number
}

export interface ReciprocallLendingDashboard {
  total_partners: number
  active_partners: number
  total_items_borrowed: number
  total_items_lent: number
  overall_balance: number
  net_cost: string
  partner_stats: ReciprocallLendingStats[]
  period_start: string
  period_end: string
}

export interface DueRemindersResponse {
  upcoming: ILLRequest[]
  overdue: ILLRequest[]
  upcoming_count: number
  overdue_count: number
}

// ==================== Patron Functions ====================

export async function createILLRequest(
  token: string,
  data: {
    title: string
    author?: string
    isbn?: string
    issn?: string
    publication_year?: string
    edition?: string
    volume?: string
    material_type?: string
    patron_notes?: string
    needed_by?: string
    pickup_branch_id?: number
  }
): Promise<ILLRequest> {
  try {
    return await fetchApi<ILLRequest>('/ill/requests', {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to submit interlibrary loan request')
    }
    throw error
  }
}

export async function getMyILLRequests(
  token: string,
  activeOnly = false
): Promise<ILLPatronView[]> {
  try {
    const params = activeOnly ? '?active_only=true' : ''
    return await fetchApi<ILLPatronView[]>(`/ill/requests/my${params}`, { token })
  } catch {
    throw new Error('Failed to fetch interlibrary loan requests')
  }
}

export async function getILLRequestTracking(
  token: string,
  requestId: number
): Promise<ILLTrackingUpdate[]> {
  try {
    return await fetchApi<ILLTrackingUpdate[]>(`/ill/requests/${requestId}/tracking`, { token })
  } catch {
    throw new Error('Failed to fetch tracking updates')
  }
}

export async function cancelILLRequest(
  token: string,
  requestId: number
): Promise<ILLRequest> {
  try {
    return await fetchApi<ILLRequest>(`/ill/requests/${requestId}/cancel`, {
      method: 'POST',
      token,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      if (error.status === 400) {
        throw new Error('This request cannot be cancelled in its current state.')
      }
      throw new Error(error.detail || 'Failed to cancel request')
    }
    throw error
  }
}

export async function searchPartnerCatalogs(
  token: string,
  title: string,
  author?: string,
  isbn?: string
): Promise<PartnerSearchResult[]> {
  try {
    const params = new URLSearchParams({ title })
    if (author) params.set('author', author)
    if (isbn) params.set('isbn', isbn)
    return await fetchApi<PartnerSearchResult[]>(`/ill/search-partners?${params}`, { token })
  } catch {
    throw new Error('Failed to search partner library catalogs')
  }
}

// ==================== Staff Functions ====================

export async function staffListILLRequests(
  token: string,
  filters?: {
    patron_id?: number
    partner_library_id?: number
    request_type?: ILLRequestType
    status?: ILLRequestStatus
    active_only?: boolean
    skip?: number
    limit?: number
  }
): Promise<ILLRequest[]> {
  try {
    const params = new URLSearchParams()
    if (filters?.patron_id) params.set('patron_id', String(filters.patron_id))
    if (filters?.partner_library_id) params.set('partner_library_id', String(filters.partner_library_id))
    if (filters?.request_type) params.set('request_type', filters.request_type)
    if (filters?.status) params.set('status', filters.status)
    if (filters?.active_only) params.set('active_only', 'true')
    if (filters?.skip) params.set('skip', String(filters.skip))
    if (filters?.limit) params.set('limit', String(filters.limit))
    const qs = params.toString() ? `?${params}` : ''
    return await fetchApi<ILLRequest[]>(`/ill/staff/requests${qs}`, { token })
  } catch {
    throw new Error('Failed to fetch ILL requests')
  }
}

export async function staffGetILLRequest(
  token: string,
  requestId: number
): Promise<ILLRequest> {
  try {
    return await fetchApi<ILLRequest>(`/ill/staff/requests/${requestId}`, { token })
  } catch (error: unknown) {
    if (isApiError(error) && error.status === 404) {
      throw new Error('ILL request not found')
    }
    throw new Error('Failed to fetch ILL request')
  }
}

export async function staffUpdateILLRequest(
  token: string,
  requestId: number,
  data: {
    status?: ILLRequestStatus
    partner_library_id?: number
    shipping_method?: ShippingMethod
    outbound_tracking?: string
    return_tracking?: string
    due_date?: string
    estimated_cost?: string
    actual_cost?: string
    notes?: string
  }
): Promise<ILLRequest> {
  try {
    return await fetchApi<ILLRequest>(`/ill/staff/requests/${requestId}`, {
      method: 'PATCH',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to update ILL request')
    }
    throw error
  }
}

export async function staffAutoSearchAndSubmit(
  token: string,
  requestId: number
): Promise<ILLRequest> {
  try {
    return await fetchApi<ILLRequest>(`/ill/staff/requests/${requestId}/auto-search`, {
      method: 'POST',
      token,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Auto-search failed')
    }
    throw error
  }
}

export async function staffRenewILLRequest(
  token: string,
  requestId: number
): Promise<ILLRequest> {
  try {
    return await fetchApi<ILLRequest>(`/ill/staff/requests/${requestId}/renew`, {
      method: 'POST',
      token,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      if (error.status === 400) {
        throw new Error('Cannot renew: not checked out or max renewals reached')
      }
      throw new Error(error.detail || 'Renewal failed')
    }
    throw error
  }
}

export async function staffAddTrackingUpdate(
  token: string,
  requestId: number,
  data: { message: string; is_patron_visible?: boolean }
): Promise<ILLTrackingUpdate> {
  try {
    return await fetchApi<ILLTrackingUpdate>(`/ill/staff/requests/${requestId}/tracking`, {
      method: 'POST',
      token,
      body: data,
    })
  } catch {
    throw new Error('Failed to add tracking update')
  }
}

export async function getReturnShippingLabel(
  token: string,
  requestId: number
): Promise<Record<string, unknown>> {
  try {
    return await fetchApi<Record<string, unknown>>(`/ill/staff/requests/${requestId}/shipping-label`, { token })
  } catch (error: unknown) {
    if (isApiError(error) && error.status === 404) {
      throw new Error('Request or partner library not found')
    }
    throw new Error('Failed to generate shipping label')
  }
}

export async function staffAddCostRecord(
  token: string,
  requestId: number,
  data: { category: ILLCostCategory; amount: string; description?: string }
): Promise<ILLCostRecord> {
  try {
    return await fetchApi<ILLCostRecord>(`/ill/staff/requests/${requestId}/costs`, {
      method: 'POST',
      token,
      body: data,
    })
  } catch {
    throw new Error('Failed to add cost record')
  }
}

export async function staffGetCostRecords(
  token: string,
  requestId: number
): Promise<ILLCostRecord[]> {
  try {
    return await fetchApi<ILLCostRecord[]>(`/ill/staff/requests/${requestId}/costs`, { token })
  } catch {
    throw new Error('Failed to fetch cost records')
  }
}

export async function getDueReminders(
  token: string,
  daysAhead = 7
): Promise<DueRemindersResponse> {
  try {
    return await fetchApi<DueRemindersResponse>(`/ill/staff/due-reminders?days_ahead=${daysAhead}`, { token })
  } catch {
    throw new Error('Failed to fetch due date reminders')
  }
}

export async function getFillRateReport(
  token: string,
  periodStart?: string,
  periodEnd?: string
): Promise<ILLFillRateReport> {
  try {
    const params = new URLSearchParams()
    if (periodStart) params.set('period_start', periodStart)
    if (periodEnd) params.set('period_end', periodEnd)
    const qs = params.toString() ? `?${params}` : ''
    return await fetchApi<ILLFillRateReport>(`/ill/staff/reports/fill-rate${qs}`, { token })
  } catch {
    throw new Error('Failed to fetch fill rate report')
  }
}

export async function getCostSummaryReport(
  token: string,
  periodStart?: string,
  periodEnd?: string
): Promise<ILLCostSummary> {
  try {
    const params = new URLSearchParams()
    if (periodStart) params.set('period_start', periodStart)
    if (periodEnd) params.set('period_end', periodEnd)
    const qs = params.toString() ? `?${params}` : ''
    return await fetchApi<ILLCostSummary>(`/ill/staff/reports/costs${qs}`, { token })
  } catch {
    throw new Error('Failed to fetch cost summary')
  }
}

export async function getReciprocalLendingDashboard(
  token: string,
  periodStart?: string,
  periodEnd?: string
): Promise<ReciprocallLendingDashboard> {
  try {
    const params = new URLSearchParams()
    if (periodStart) params.set('period_start', periodStart)
    if (periodEnd) params.set('period_end', periodEnd)
    const qs = params.toString() ? `?${params}` : ''
    return await fetchApi<ReciprocallLendingDashboard>(`/ill/staff/reports/reciprocal-dashboard${qs}`, { token })
  } catch {
    throw new Error('Failed to fetch reciprocal lending dashboard')
  }
}

// ==================== Partner Library Management ====================

export async function staffListPartnerLibraries(
  token: string,
  filters?: { status?: string; search?: string }
): Promise<PartnerLibrary[]> {
  try {
    const params = new URLSearchParams()
    if (filters?.status) params.set('status', filters.status)
    if (filters?.search) params.set('search', filters.search)
    const qs = params.toString() ? `?${params}` : ''
    return await fetchApi<PartnerLibrary[]>(`/ill/staff/partners${qs}`, { token })
  } catch {
    throw new Error('Failed to fetch partner libraries')
  }
}

export async function staffCreatePartnerLibrary(
  token: string,
  data: {
    name: string
    code: string
    address?: string
    city?: string
    state?: string
    zip_code?: string
    contact_name?: string
    contact_email?: string
    lending_fee?: string
    borrowing_fee?: string
    max_loan_days?: number
    reciprocal_agreement?: boolean
  }
): Promise<PartnerLibrary> {
  try {
    return await fetchApi<PartnerLibrary>('/ill/staff/partners', {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to create partner library')
    }
    throw error
  }
}

export async function staffUpdatePartnerLibrary(
  token: string,
  partnerId: number,
  data: Record<string, unknown>
): Promise<PartnerLibrary> {
  try {
    return await fetchApi<PartnerLibrary>(`/ill/staff/partners/${partnerId}`, {
      method: 'PATCH',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to update partner library')
    }
    throw error
  }
}
