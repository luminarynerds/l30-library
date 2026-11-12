/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { fetchApi, isApiError } from '@/lib/api-client'
import type { components } from '@/api/generated/schema';

// ==================== Fine Management Types ====================

export type FineType = components['schemas']['FineType'];
export type FineStatus = components['schemas']['FineStatus'];
export type PaymentMethod = components['schemas']['PaymentMethod'];
export type PaymentPlanFrequency = components['schemas']['PaymentPlanFrequency'];
export type PaymentPlanStatus = components['schemas']['PaymentPlanStatus'];
export interface Fine {
  id: number
  user_id: number
  checkout_id: number | null
  fine_type: FineType
  status: FineStatus
  amount: number
  amount_paid: number
  balance: number
  description: string | null
  notes: string | null
  created_at: string
  paid_at: string | null
  waived_at: string | null
  waived_by_id: number | null
  patron_name: string | null
  patron_email: string | null
  patron_library_card: string | null
}

export interface PaymentHistory {
  id: number
  fine_id: number
  user_id: number | null
  amount: number
  payment_method: PaymentMethod
  notes: string | null
  receipt_number: string | null
  processed_by_id: number | null
  processed_by_name: string | null
  created_at: string
}

export interface PaymentPlan {
  id: number
  user_id: number
  total_amount: number
  installment_amount: number
  frequency: PaymentPlanFrequency
  status: PaymentPlanStatus
  amount_paid: number
  remaining_balance: number
  payments_made: number
  total_payments_expected: number
  progress_percentage: number
  start_date: string
  next_payment_date: string | null
  completed_at: string | null
  reminder_enabled: boolean
  last_reminder_sent: string | null
  notes: string | null
  created_by_id: number | null
  created_by_name: string | null
  created_at: string
  updated_at: string | null
}

export interface FineHistoryResponse {
  patron_id: number
  patron_name: string
  fines: Fine[]
  outstanding_fines?: Fine[]
  payments: PaymentHistory[]
  total_count: number
  total_fines_amount: number
  total_paid_amount: number
  current_balance: number
}

export interface PartialPaymentRequest {
  amount: number
  payment_method: PaymentMethod
  notes?: string
}

export interface PartialPaymentResponse {
  fine: Fine
  payment: PaymentHistory
  receipt_number: string
}

export interface PaymentPlanCreate {
  total_amount: number
  installment_amount: number
  frequency: PaymentPlanFrequency
  reminder_enabled?: boolean
  notes?: string
}

export interface PaymentPlanUpdate {
  installment_amount?: number
  frequency?: PaymentPlanFrequency
  reminder_enabled?: boolean
  status?: PaymentPlanStatus
  notes?: string
}

export interface ReceiptData {
  receipt_number: string
  payment_date: string
  payment_amount: number
  payment_method: PaymentMethod
  patron_id: number
  patron_name: string
  patron_email: string | null
  patron_library_card: string | null
  fine_id: number
  fine_type: FineType
  fine_description: string | null
  original_fine_amount: number
  amount_paid_before: number
  amount_paid_now: number
  remaining_balance: number
  staff_id: number
  staff_name: string
  library_name: string
  library_address: string | null
  library_phone: string | null
}

export interface FineAnalyticsByType {
  fine_type: FineType
  count: number
  total_amount: number
  percentage: number
}

export interface FineAccumulationPoint {
  date: string
  amount: number
  count: number
}

export interface PatronFinePatterns {
  frequent_late_returns: boolean
  average_days_overdue: number | null
  most_common_fine_type: FineType | null
  total_lifetime_fines: number
  total_lifetime_paid: number
  average_fine_amount: number | null
}

export interface FineAnalyticsResponse {
  patron_id: number
  patron_name: string
  current_balance: number
  total_fines_count: number
  unpaid_fines_count: number
  breakdown_by_type: FineAnalyticsByType[]
  accumulation_history: FineAccumulationPoint[]
  patterns: PatronFinePatterns
  average_patron_balance: number
  comparison_to_average: 'above' | 'below' | 'average'
}

export interface PaymentHistoryListResponse {
  payments: PaymentHistory[]
  total_count: number
  total_amount: number
}

export interface FineListResponse {
  fines: Fine[]
  total_count: number
  total_unpaid: number
}

export interface FineCreateRequest {
  user_id: number
  checkout_id?: number | null
  fine_type: FineType
  amount: number
  description?: string | null
  notes?: string | null
}

export interface FinePaymentRequest {
  amount: number
  notes?: string | null
}

// ==================== Fine Management Functions ====================

export async function listFines(
  token: string,
  filters: {
    patron_id?: number
    status?: FineStatus
    unpaid_only?: boolean
    limit?: number
    offset?: number
  } = {}
): Promise<FineListResponse> {
  try {
    const params = new URLSearchParams()
    if (filters.patron_id) params.set('patron_id', String(filters.patron_id))
    if (filters.status) params.set('status', filters.status)
    if (filters.unpaid_only) params.set('unpaid_only', 'true')
    if (filters.limit !== undefined) params.set('limit', String(filters.limit))
    if (filters.offset !== undefined) params.set('offset', String(filters.offset))

    const query = params.toString()
    const endpoint = query ? `/staff/fines?${query}` : '/staff/fines'
    return await fetchApi<FineListResponse>(endpoint, { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch fines')
    }
    throw error
  }
}

export async function createFine(token: string, data: FineCreateRequest): Promise<Fine> {
  try {
    return await fetchApi<Fine>('/staff/fines', {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      if (error.status === 404) {
        throw new Error('Patron or checkout not found')
      }
      throw new Error(error.detail || 'Failed to create fine')
    }
    throw error
  }
}

export async function getPatronFineHistory(token: string, patronId: number): Promise<FineHistoryResponse> {
  try {
    return await fetchApi<FineHistoryResponse>(`/staff/patrons/${patronId}/fines/history`, { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch fine history')
    }
    throw error
  }
}

export async function makePartialPayment(
  token: string,
  fineId: number,
  data: PartialPaymentRequest
): Promise<PartialPaymentResponse> {
  try {
    return await fetchApi<PartialPaymentResponse>(`/staff/fines/${fineId}/partial-payment`, {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to process payment')
    }
    throw error
  }
}

export async function payFine(token: string, fineId: number, data: FinePaymentRequest): Promise<Fine> {
  try {
    return await fetchApi<Fine>(`/staff/fines/${fineId}/pay`, {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      if (error.status === 404) {
        throw new Error('Fine not found')
      }
      if (error.status === 400) {
        throw new Error(error.detail || 'Invalid payment amount')
      }
      throw new Error(error.detail || 'Failed to process payment')
    }
    throw error
  }
}

export async function createPaymentPlan(
  token: string,
  patronId: number,
  data: PaymentPlanCreate
): Promise<PaymentPlan> {
  try {
    return await fetchApi<PaymentPlan>(`/staff/patrons/${patronId}/payment-plan`, {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to create payment plan')
    }
    throw error
  }
}

export async function getPaymentPlan(token: string, patronId: number): Promise<PaymentPlan | null> {
  try {
    return await fetchApi<PaymentPlan | null>(`/staff/patrons/${patronId}/payment-plan`, { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      // 404 means no active plan, return null
      if (error.status === 404) return null
      throw new Error(error.detail || 'Failed to fetch payment plan')
    }
    throw error
  }
}

export async function updatePaymentPlan(
  token: string,
  patronId: number,
  data: PaymentPlanUpdate
): Promise<PaymentPlan> {
  try {
    return await fetchApi<PaymentPlan>(`/staff/patrons/${patronId}/payment-plan`, {
      method: 'PUT',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to update payment plan')
    }
    throw error
  }
}

export async function recordPaymentPlanPayment(
  token: string,
  patronId: number,
  data: PartialPaymentRequest
): Promise<PaymentPlan> {
  try {
    return await fetchApi<PaymentPlan>(`/staff/patrons/${patronId}/payment-plan/payment`, {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to record payment')
    }
    throw error
  }
}

export async function getReceipt(token: string, fineId: number, paymentId?: number): Promise<ReceiptData> {
  try {
    const params = paymentId ? `?payment_id=${paymentId}` : ''
    return await fetchApi<ReceiptData>(`/staff/fines/${fineId}/receipt${params}`, { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to generate receipt')
    }
    throw error
  }
}

export async function getPatronFineAnalytics(token: string, patronId: number): Promise<FineAnalyticsResponse> {
  try {
    return await fetchApi<FineAnalyticsResponse>(`/staff/patrons/${patronId}/fines/analytics`, { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch fine analytics')
    }
    throw error
  }
}

export async function getPatronPayments(
  token: string,
  patronId: number,
  limit = 50,
  offset = 0
): Promise<PaymentHistoryListResponse> {
  try {
    return await fetchApi<PaymentHistoryListResponse>(
      `/staff/patrons/${patronId}/payments?limit=${limit}&offset=${offset}`,
      { token }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch payment history')
    }
    throw error
  }
}

// ==================== Fine Waiver Types ====================

export type FineWaiverStatus = 'waived' | 'pending_approval' | 'rejected'

export interface FineWaiveRequest {
  reason: string
  /** Defaults to the fine's full outstanding balance on the server. */
  amount?: string | number
  /** Force the waiver into pending_approval regardless of amount. */
  requires_approval?: boolean
}

export interface FineWaiverResponse {
  waiver_id: number
  fine_id: number
  amount_waived: string
  remaining_balance: string
  status: FineWaiverStatus
  waived_by: number | null
  waived_at: string | null
  approved_by: number | null
  approved_at: string | null
  reason: string
}

export interface PendingWaiverListItem {
  waiver_id: number
  fine_id: number
  patron_id: number | null
  patron_name: string | null
  fine_amount: string
  amount_waived: string
  reason: string
  status: FineWaiverStatus
  waived_by_user_id: number | null
  waived_by_name: string | null
  waived_at: string | null
  requested_at: string
}

export interface PendingWaiverListResponse {
  waivers: PendingWaiverListItem[]
  total_count: number
}

export async function waiveFine(
  token: string,
  fineId: number,
  data: FineWaiveRequest
): Promise<FineWaiverResponse> {
  try {
    return await fetchApi<FineWaiverResponse>(`/staff/fines/${fineId}/waive`, {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      if (error.status === 404) {
        throw new Error('Fine not found')
      }
      if (error.status === 409) {
        throw new Error(error.detail || 'Fine is already paid or fully waived')
      }
      if (error.status === 400) {
        throw new Error(error.detail || 'Invalid waive request')
      }
      throw new Error(error.detail || 'Failed to waive fine')
    }
    throw error
  }
}

export async function listPendingWaivers(
  token: string,
  opts: { limit?: number; offset?: number } = {}
): Promise<PendingWaiverListResponse> {
  const params = new URLSearchParams()
  if (opts.limit != null) params.set('limit', String(opts.limit))
  if (opts.offset != null) params.set('offset', String(opts.offset))
  const qs = params.toString()
  const path = `/staff/fine-waivers/pending${qs ? `?${qs}` : ''}`
  return fetchApi<PendingWaiverListResponse>(path, { method: 'GET', token })
}

export async function approveFineWaiver(
  token: string,
  waiverId: number,
  notes?: string
): Promise<FineWaiverResponse> {
  return fetchApi<FineWaiverResponse>(
    `/staff/fine-waivers/${waiverId}/approve`,
    {
      method: 'POST',
      token,
      body: notes ? { notes } : {},
    }
  )
}

export async function rejectFineWaiver(
  token: string,
  waiverId: number,
  notes?: string
): Promise<FineWaiverResponse> {
  return fetchApi<FineWaiverResponse>(
    `/staff/fine-waivers/${waiverId}/reject`,
    {
      method: 'POST',
      token,
      body: notes ? { notes } : {},
    }
  )
}

// ==================== Fine Detail Types ====================

export interface FinePaymentDetail {
  id: number
  amount: number
  payment_method: string
  notes: string | null
  receipt_number: string | null
  processed_by_name: string | null
  created_at: string
}

export interface FineDetailItem {
  id: number
  fine_type: string
  status: string
  amount: number
  amount_paid: number
  balance: number
  description: string | null
  notes: string | null
  created_at: string
  paid_at: string | null
  waived_at: string | null
  waived_by_name: string | null
  item_title: string | null
  item_author: string | null
  item_type: string | null
  item_barcode: string | null
  checked_out_at: string | null
  due_date: string | null
  returned_at: string | null
  explanation: string
  payments: FinePaymentDetail[]
}

export interface FineDetailResponse {
  patron_id: number
  patron_name: string
  patron_email: string | null
  total_fines: number
  total_outstanding: number
  fines: FineDetailItem[]
}

export async function getPatronFinesDetail(patronId: number): Promise<FineDetailResponse> {
  return fetchApi<FineDetailResponse>(`/staff/fines/patron/${patronId}/detail`)
}
