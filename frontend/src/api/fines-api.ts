/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { API_BASE as API_ROOT } from '@/api/types'
import type { components } from '@/api/generated/schema';
/**
 * Fine Management API client.
 *
 * Provides access to fine tracking, payments, waivers,
 * payment plans, and check clearance workflows.
 */

const API_BASE = `${API_ROOT}/staff/fines`

// ============ Types ============

export type FineStatus = components['schemas']['FineStatus'];
export type FineType = components['schemas']['FineType'];
export type PaymentMethod = components['schemas']['PaymentMethod'];
export type CheckClearanceStatus = 'pending' | 'cleared' | 'bounced'
export type PaymentPlanStatus = components['schemas']['PaymentPlanStatus'];
export type PaymentPlanFrequency = components['schemas']['PaymentPlanFrequency'];
export interface Fine {
  id: number
  user_id: number
  patron_name?: string
  checkout_id: number | null
  item_title?: string
  fine_type: FineType
  status: FineStatus
  amount: number
  amount_paid: number
  balance: number
  description?: string
  created_at: string
  paid_at: string | null
  waived_at: string | null
  waived_by_name?: string
  waive_reason?: string
}

export interface FineListResponse {
  fines: Fine[]
  total: number
}

export interface Payment {
  id: number
  fine_id: number
  amount: number
  payment_method: PaymentMethod
  receipt_number: string
  check_clearance_status?: CheckClearanceStatus
  created_at: string
  patron_name?: string
}

export interface PendingCheck {
  id: number
  fine_id: number
  patron_name?: string
  item_title?: string
  amount: number
  payment_method: string
  receipt_number: string
  check_clearance_status: CheckClearanceStatus
  created_at: string
}

export interface PaymentPlan {
  id: number
  user_id: number
  patron_name?: string
  total_amount: number
  installment_amount: number
  frequency: PaymentPlanFrequency
  status: PaymentPlanStatus
  amount_paid: number
  payments_made: number
  start_date: string
  next_payment_date: string | null
  remaining_balance: number
  progress_percentage: number
}

export interface FineAnalytics {
  total_outstanding: number
  total_collected: number
  total_waived: number
  collection_rate: number
  fines_by_type: Record<string, number>
  fines_by_status: Record<string, number>
}

export interface Receipt {
  receipt_number: string
  fine_id: number
  patron_name: string
  item_title?: string
  fine_type: FineType
  amount_paid: number
  payment_method: PaymentMethod
  paid_at: string
}

// ============ Helpers ============

async function apiFetch<T>(token: string, endpoint: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(API_BASE + endpoint, {
    ...options,
    headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + token, ...options.headers },
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Request failed' }))
    throw new Error(err.detail || err.error?.message || 'Request failed')
  }
  if (res.status === 204) return undefined as T
  return res.json()
}

// ============ API Functions ============

export function getFines(
  token: string,
  params: { status?: string; fine_type?: string; unpaid_only?: boolean; patron_id?: number } = {}
): Promise<FineListResponse> {
  const sp = new URLSearchParams()
  if (params.status) sp.set('status', params.status)
  if (params.fine_type) sp.set('fine_type', params.fine_type)
  if (params.unpaid_only) sp.set('unpaid_only', 'true')
  if (params.patron_id) sp.set('patron_id', String(params.patron_id))
  const q = sp.toString()
  return apiFetch<FineListResponse>(token, `/fines${q ? `?${q}` : ''}`)
}

export function createFine(
  token: string,
  data: { user_id: number; fine_type: FineType; amount: number; description?: string; checkout_id?: number }
): Promise<Fine> {
  return apiFetch<Fine>(token, '/fines', { method: 'POST', body: JSON.stringify(data) })
}

export function waiveFine(token: string, fineId: number, reason: string): Promise<Fine> {
  return apiFetch<Fine>(token, `/fines/${fineId}/waive`, { method: 'POST', body: JSON.stringify({ reason }) })
}

export function payFine(
  token: string,
  fineId: number,
  data: { amount: number; payment_method: PaymentMethod }
): Promise<{ fine: Fine; receipt_number: string }> {
  return apiFetch(token, `/fines/${fineId}/pay`, { method: 'POST', body: JSON.stringify(data) })
}

export function partialPayment(
  token: string,
  fineId: number,
  data: { amount: number; payment_method: PaymentMethod }
): Promise<{ fine: Fine; receipt_number: string }> {
  return apiFetch(token, `/fines/${fineId}/partial-payment`, { method: 'POST', body: JSON.stringify(data) })
}

export function getReceipt(token: string, fineId: number): Promise<Receipt> {
  return apiFetch<Receipt>(token, `/fines/${fineId}/receipt`)
}

export function getPatronFineHistory(token: string, patronId: number): Promise<{ fines: Fine[] }> {
  return apiFetch(token, `/../patrons/${patronId}/fines/history`)
}

export function getPatronAnalytics(token: string, patronId: number): Promise<FineAnalytics> {
  return apiFetch<FineAnalytics>(token, `/../patrons/${patronId}/fines/analytics`)
}

export function getPatronPayments(token: string, patronId: number): Promise<{ payments: Payment[] }> {
  return apiFetch(token, `/../patrons/${patronId}/payments`)
}

export function createPaymentPlan(
  token: string,
  patronId: number,
  data: { installment_amount: number; frequency: PaymentPlanFrequency }
): Promise<PaymentPlan> {
  return apiFetch<PaymentPlan>(token, `/../patrons/${patronId}/payment-plan`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export function getPaymentPlan(token: string, patronId: number): Promise<PaymentPlan> {
  return apiFetch<PaymentPlan>(token, `/../patrons/${patronId}/payment-plan`)
}

export function getPendingChecks(token: string): Promise<{ checks: PendingCheck[] }> {
  return apiFetch(token, '/payments/pending-checks')
}

export function markCheckCleared(token: string, paymentId: number): Promise<Payment> {
  return apiFetch<Payment>(token, `/payments/${paymentId}/check-cleared`, { method: 'POST', body: '{}' })
}

export function markCheckBounced(token: string, paymentId: number): Promise<Payment> {
  return apiFetch<Payment>(token, `/payments/${paymentId}/check-bounced`, { method: 'POST', body: '{}' })
}