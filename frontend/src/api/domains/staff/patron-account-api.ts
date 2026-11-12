/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Patron Account & Print Credits API
 *
 * API functions for managing patron prepaid accounts used for printing and other services.
 * Corresponds to backend endpoints in /patron/account/* and /staff/patron/*
 */

import { fetchApi, isApiError } from '@/lib/api-client'

// ==================== Types ====================

export interface PatronAccountBalance {
  id: number
  patron_id: number
  balance: number
  total_deposited: number
  total_spent: number
  is_active: boolean
  low_balance_threshold: number
  auto_reload_enabled: boolean
  last_deposit_at: string | null
  last_charge_at: string | null
  created_at: string
}

export type TransactionType = 'deposit' | 'charge' | 'refund' | 'adjustment'
export type TransactionStatus = 'pending' | 'completed' | 'failed' | 'reversed'
export type AccountPaymentMethod = 'cash' | 'credit_card' | 'debit_card' | 'online' | 'system'

export interface PatronTransaction {
  id: number
  account_id: number
  transaction_type: TransactionType
  status: TransactionStatus
  amount: number
  balance_before: number
  balance_after: number
  payment_method: AccountPaymentMethod | null
  description: string
  reference_type: string | null
  reference_id: number | null
  receipt_number: string | null
  notes: string | null
  created_at: string
}

export interface TransactionListResponse {
  items: PatronTransaction[]
  total: number
  page: number
  per_page: number
}

export interface StaffDepositRequest {
  amount: number
  payment_method: AccountPaymentMethod
  notes?: string
}

export interface RefundRequest {
  amount: number
  reason: string
  notes?: string
}

// ==================== Staff Endpoints ====================

export async function getPatronAccountBalance(
  token: string,
  patronId: number,
): Promise<PatronAccountBalance> {
  try {
    return await fetchApi<PatronAccountBalance>(`/staff/patron/${patronId}/account`, { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch patron account balance')
    }
    throw error
  }
}

export async function getPatronTransactions(
  token: string,
  patronId: number,
  options?: {
    page?: number
    per_page?: number
    transaction_type?: TransactionType
  },
): Promise<TransactionListResponse> {
  try {
    const params = new URLSearchParams()
    if (options?.page) params.set('page', options.page.toString())
    if (options?.per_page) params.set('per_page', options.per_page.toString())
    if (options?.transaction_type) params.set('transaction_type', options.transaction_type)

    const queryString = params.toString()
    const url = `/staff/patron/${patronId}/transactions${queryString ? `?${queryString}` : ''}`

    return await fetchApi<TransactionListResponse>(url, { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch transactions')
    }
    throw error
  }
}

export async function staffDeposit(
  token: string,
  patronId: number,
  data: StaffDepositRequest,
): Promise<PatronTransaction> {
  try {
    return await fetchApi<PatronTransaction>(`/staff/patron/${patronId}/deposit`, {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to process deposit')
    }
    throw error
  }
}

export async function staffRefund(
  token: string,
  patronId: number,
  data: RefundRequest,
): Promise<PatronTransaction> {
  try {
    return await fetchApi<PatronTransaction>(`/staff/patron/${patronId}/refund`, {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to process refund')
    }
    throw error
  }
}
