/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Cash Drawer Management API
 * Handles drawer CRUD, session lifecycle, transactions, and PDF reports
 */

import { fetchApi } from '@/lib/api-client'
import { getAccessToken } from '../../../utils/tokenStore'
import { API_BASE } from '@/api/types'

// ==================== Types ====================

export type DrawerMode = 'shift_based' | 'day_based'
export type SessionStatus = 'open' | 'pending_approval' | 'closed'
export type TransactionDirection = 'inflow' | 'outflow'
export type TransactionCategory =
  | 'fine_payment' | 'print_fee' | 'copy_fee' | 'room_fee'
  | 'card_replacement' | 'makerspace_fee' | 'petty_cash' | 'other'

export interface CashDrawer {
  id: number
  name: string
  default_float: number
  mode: DrawerMode
  discrepancy_threshold: number
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface SessionSummary {
  total_inflows: number
  total_outflows: number
  transaction_count: number
  inflow_by_category: Record<string, number>
  outflow_by_category: Record<string, number>
}

export interface CashDrawerSession {
  id: number
  drawer_id: number
  opened_by: number
  closed_by: number | null
  approved_by: number | null
  status: SessionStatus
  opening_float: number
  expected_total: number | null
  counted_total: number | null
  discrepancy: number | null
  denomination_breakdown: Record<string, number> | null
  notes: string | null
  opened_at: string
  closed_at: string | null
  opener_name: string | null
  closer_name: string | null
  approver_name: string | null
  summary: SessionSummary | null
}

export interface CashTransaction {
  id: number
  session_id: number
  staff_id: number
  direction: TransactionDirection
  category: TransactionCategory
  amount: number
  amount_tendered: number | null
  change_given: number | null
  description: string | null
  reference_type: string | null
  reference_id: number | null
  voided: boolean
  created_at: string
  staff_name: string | null
}

export interface CashDrawerCreateRequest {
  name: string
  default_float?: number
  mode?: DrawerMode
  discrepancy_threshold?: number
}

export interface CashDrawerUpdateRequest {
  name?: string
  default_float?: number
  mode?: DrawerMode
  discrepancy_threshold?: number
  is_active?: boolean
}

export interface OpenSessionRequest {
  opening_float: number
}

export interface CloseSessionRequest {
  counted_total: number
  denomination_breakdown?: Record<string, number>
  notes?: string
}

export interface ApproveSessionRequest {
  notes?: string
}

export interface CreateTransactionRequest {
  direction: TransactionDirection
  category: TransactionCategory
  amount: number
  amount_tendered?: number
  description?: string
  reference_type?: string
  reference_id?: number
}

export interface TransactionListResponse {
  transactions: CashTransaction[]
  total: number
}

export interface SessionHistoryResponse {
  sessions: CashDrawerSession[]
  total: number
  page: number
  per_page: number
}

// ==================== Drawer CRUD ====================

const BASE = '/cash-drawers'

function authHeaders() {
  const token = getAccessToken()
  return token ? { token } : {}
}

export async function listDrawers(activeOnly = true): Promise<CashDrawer[]> {
  return fetchApi<CashDrawer[]>(`${BASE}?active_only=${activeOnly}`, {
    ...authHeaders(),
  })
}

export async function createDrawer(data: CashDrawerCreateRequest): Promise<CashDrawer> {
  return fetchApi<CashDrawer>(BASE, {
    method: 'POST',
    ...authHeaders(),
    body: data,
  })
}

export async function updateDrawer(drawerId: number, data: CashDrawerUpdateRequest): Promise<CashDrawer> {
  return fetchApi<CashDrawer>(`${BASE}/${drawerId}`, {
    method: 'PATCH',
    ...authHeaders(),
    body: data,
  })
}

export async function deleteDrawer(drawerId: number): Promise<void> {
  await fetchApi(`${BASE}/${drawerId}`, {
    method: 'DELETE',
    ...authHeaders(),
  })
}

// ==================== Session Lifecycle ====================

export async function openSession(drawerId: number, data: OpenSessionRequest): Promise<CashDrawerSession> {
  return fetchApi<CashDrawerSession>(`${BASE}/${drawerId}/open`, {
    method: 'POST',
    ...authHeaders(),
    body: data,
  })
}

export async function getCurrentSession(drawerId: number): Promise<CashDrawerSession> {
  return fetchApi<CashDrawerSession>(`${BASE}/${drawerId}/current-session`, {
    ...authHeaders(),
  })
}

export async function closeSession(drawerId: number, data: CloseSessionRequest): Promise<CashDrawerSession> {
  return fetchApi<CashDrawerSession>(`${BASE}/${drawerId}/close`, {
    method: 'POST',
    ...authHeaders(),
    body: data,
  })
}

export async function approveSession(sessionId: number, data: ApproveSessionRequest): Promise<CashDrawerSession> {
  return fetchApi<CashDrawerSession>(`${BASE}/sessions/${sessionId}/approve`, {
    method: 'POST',
    ...authHeaders(),
    body: data,
  })
}

// ==================== Transactions ====================

export async function createTransaction(sessionId: number, data: CreateTransactionRequest): Promise<CashTransaction> {
  return fetchApi<CashTransaction>(`${BASE}/sessions/${sessionId}/transactions`, {
    method: 'POST',
    ...authHeaders(),
    body: data,
  })
}

export async function listTransactions(sessionId: number, includeVoided = false): Promise<TransactionListResponse> {
  return fetchApi<TransactionListResponse>(
    `${BASE}/sessions/${sessionId}/transactions?include_voided=${includeVoided}`,
    { ...authHeaders() },
  )
}

export async function voidTransaction(sessionId: number, txnId: number): Promise<CashTransaction> {
  return fetchApi<CashTransaction>(`${BASE}/sessions/${sessionId}/transactions/${txnId}`, {
    method: 'DELETE',
    ...authHeaders(),
  })
}

// ==================== History ====================

export async function getSessionHistory(
  drawerId: number,
  page = 1,
  perPage = 20,
): Promise<SessionHistoryResponse> {
  return fetchApi<SessionHistoryResponse>(
    `${BASE}/${drawerId}/history?page=${page}&per_page=${perPage}`,
    { ...authHeaders() },
  )
}

// ==================== PDF Reports ====================

export async function getReconciliationReport(sessionId: number): Promise<Blob> {
  const token = getAccessToken()
  const response = await fetch(`${API_BASE}${BASE}/sessions/${sessionId}/reconciliation-report`, {
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  })
  if (!response.ok) throw new Error('Failed to generate reconciliation report')
  return response.blob()
}

export async function getDepositSlip(sessionId: number): Promise<Blob> {
  const token = getAccessToken()
  const response = await fetch(`${API_BASE}${BASE}/sessions/${sessionId}/deposit-slip`, {
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  })
  if (!response.ok) throw new Error('Failed to generate deposit slip')
  return response.blob()
}