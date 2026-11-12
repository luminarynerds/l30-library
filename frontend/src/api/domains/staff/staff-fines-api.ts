/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Staff Fines Management API
 * Handles fine creation, payments, waiving, and payment plan management
 */

import { fetchApi, isApiError } from '@/lib/api-client'
import { getAccessToken } from '../../../utils/tokenStore'
import type { components } from '@/api/generated/schema';

// ==================== Types ====================

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

export interface FineCreateRequest {
  user_id: number
  checkout_id?: number | null
  fine_type: FineType
  amount: number
  description?: string | null
  notes?: string | null
}

export interface FineWaiveRequest {
  reason: string
}

export interface FinePaymentRequest {
  amount: number
  notes?: string | null
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

export interface PartialPaymentRequest {
  amount: number
  payment_method: PaymentMethod
  notes?: string | null
}

export interface PartialPaymentResponse {
  fine: Fine
  payment: PaymentHistory
  receipt_number: string
}

export interface PaymentPlanCreateRequest {
  total_amount: number
  installment_amount: number
  frequency: PaymentPlanFrequency
  reminder_enabled?: boolean
  notes?: string | null
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

// ==================== Fine Management Functions ====================

export async function createFine(data: FineCreateRequest): Promise<Fine> {
  const token = getAccessToken()
  try {
    return await fetchApi<Fine>('/staff/fines', {
      method: 'POST',
      ...(token ? { token } : {}),
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

export async function waiveFine(fineId: number, data: FineWaiveRequest): Promise<Fine> {
  const token = getAccessToken()
  try {
    return await fetchApi<Fine>(`/staff/fines/${fineId}/waive`, {
      method: 'POST',
      ...(token ? { token } : {}),
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      if (error.status === 404) {
        throw new Error('Fine not found')
      }
      if (error.status === 400) {
        throw new Error(error.detail || 'Fine cannot be waived')
      }
      throw new Error(error.detail || 'Failed to waive fine')
    }
    throw error
  }
}

export async function payFine(fineId: number, data: FinePaymentRequest): Promise<Fine> {
  const token = getAccessToken()
  try {
    return await fetchApi<Fine>(`/staff/fines/${fineId}/pay`, {
      method: 'POST',
      ...(token ? { token } : {}),
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

export async function makePartialPayment(
  fineId: number,
  data: PartialPaymentRequest
): Promise<PartialPaymentResponse> {
  const token = getAccessToken()
  try {
    return await fetchApi<PartialPaymentResponse>(`/staff/fines/${fineId}/partial-payment`, {
      method: 'POST',
      ...(token ? { token } : {}),
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
      throw new Error(error.detail || 'Failed to process partial payment')
    }
    throw error
  }
}

export async function createPaymentPlan(
  patronId: number,
  data: PaymentPlanCreateRequest
): Promise<PaymentPlan> {
  const token = getAccessToken()
  try {
    return await fetchApi<PaymentPlan>(`/staff/patrons/${patronId}/payment-plan`, {
      method: 'POST',
      ...(token ? { token } : {}),
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      if (error.status === 404) {
        throw new Error('Patron not found')
      }
      if (error.status === 400) {
        throw new Error(error.detail || 'Failed to create payment plan')
      }
      throw new Error(error.detail || 'Failed to create payment plan')
    }
    throw error
  }
}

export async function makePaymentPlanPayment(
  patronId: number,
  data: PartialPaymentRequest
): Promise<PaymentPlan> {
  const token = getAccessToken()
  try {
    return await fetchApi<PaymentPlan>(`/staff/patrons/${patronId}/payment-plan/payment`, {
      method: 'POST',
      ...(token ? { token } : {}),
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      if (error.status === 404) {
        throw new Error('No active payment plan found')
      }
      if (error.status === 400) {
        throw new Error(error.detail || 'Invalid payment amount')
      }
      throw new Error(error.detail || 'Failed to record payment')
    }
    throw error
  }
}
