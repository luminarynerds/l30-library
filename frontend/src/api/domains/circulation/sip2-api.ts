/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * SIP2 Terminal Management API Service
 *
 * Provides functions for managing SIP2 self-checkout terminals.
 * All endpoints require STAFF or ADMIN role.
 */

import { fetchApi, isApiError } from '@/lib/api-client'

// ==================== Types ====================

export interface SIP2Terminal {
  id: number
  terminal_id: string
  name: string
  description: string | null
  location: string | null
  institution_id: string | null
  is_active: boolean
  allow_checkout: boolean
  allow_checkin: boolean
  allow_renewal: boolean
  allow_patron_info: boolean
  settings: Record<string, unknown> | null
  last_seen_at: string | null
  last_ip: string | null
  created_at: string | null
  updated_at: string | null
}

export interface TerminalListResponse {
  terminals: SIP2Terminal[]
  total: number
  page: number
  per_page: number
}

export interface TerminalCreate {
  terminal_id: string
  name: string
  description?: string
  location?: string
  institution_id?: string
  password?: string
  is_active?: boolean
  allow_checkout?: boolean
  allow_checkin?: boolean
  allow_renewal?: boolean
  allow_patron_info?: boolean
  settings?: Record<string, unknown>
}

export interface TerminalUpdate {
  name?: string
  description?: string
  location?: string
  institution_id?: string
  password?: string
  is_active?: boolean
  allow_checkout?: boolean
  allow_checkin?: boolean
  allow_renewal?: boolean
  allow_patron_info?: boolean
  settings?: Record<string, unknown>
}

export interface SIP2Transaction {
  id: number
  session_id: string
  terminal_id: string | null
  institution_id: string | null
  request_id: string | null
  command: string
  patron_id: string | null
  item_id: string | null
  success: boolean
  error_message: string | null
  client_ip: string | null
  created_at: string
  response_at: string | null
  processing_time_ms: number | null
}

export interface TransactionListResponse {
  transactions: SIP2Transaction[]
  total: number
  page: number
  per_page: number
}

export interface TerminalStats {
  total_terminals: number
  active_terminals: number
  inactive_terminals: number
  terminals_online_today: number
}

export interface TransactionStats {
  total_transactions: number
  successful_transactions: number
  failed_transactions: number
  checkouts: number
  checkins: number
  renewals: number
  patron_lookups: number
  avg_processing_time_ms: number | null
}

// ==================== Terminal Management Functions ====================

export async function listTerminals(
  token: string,
  options?: {
    page?: number
    limit?: number
    is_active?: boolean
    search?: string
  }
): Promise<TerminalListResponse> {
  try {
    const params = new URLSearchParams()
    if (options?.page) params.set('page', options.page.toString())
    if (options?.limit) params.set('limit', options.limit.toString())
    if (options?.is_active !== undefined) params.set('is_active', options.is_active.toString())
    if (options?.search) params.set('search', options.search)

    const queryString = params.toString() ? `?${params.toString()}` : ''
    return await fetchApi<TerminalListResponse>(`/sip2/terminals${queryString}`, { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch terminals')
    }
    throw error
  }
}

export async function createTerminal(
  token: string,
  data: TerminalCreate
): Promise<SIP2Terminal> {
  try {
    return await fetchApi<SIP2Terminal>('/sip2/terminals', {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to create terminal')
    }
    throw error
  }
}

export async function getTerminal(
  token: string,
  terminalId: string
): Promise<SIP2Terminal> {
  try {
    return await fetchApi<SIP2Terminal>(`/sip2/terminals/${encodeURIComponent(terminalId)}`, {
      token,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch terminal')
    }
    throw error
  }
}

export async function updateTerminal(
  token: string,
  terminalId: string,
  data: TerminalUpdate
): Promise<SIP2Terminal> {
  try {
    return await fetchApi<SIP2Terminal>(`/sip2/terminals/${encodeURIComponent(terminalId)}`, {
      method: 'PATCH',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to update terminal')
    }
    throw error
  }
}

export async function deleteTerminal(
  token: string,
  terminalId: string
): Promise<void> {
  try {
    await fetchApi<void>(`/sip2/terminals/${encodeURIComponent(terminalId)}`, {
      method: 'DELETE',
      token,
      skipJsonParse: true,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to delete terminal')
    }
    throw error
  }
}

// ==================== Transaction Log Functions ====================

export async function listTransactions(
  token: string,
  options?: {
    page?: number
    limit?: number
    terminal_id?: string
    patron_id?: string
    item_id?: string
    command?: string
    success?: boolean
    start_date?: string
    end_date?: string
  }
): Promise<TransactionListResponse> {
  try {
    const params = new URLSearchParams()
    if (options?.page) params.set('page', options.page.toString())
    if (options?.limit) params.set('limit', options.limit.toString())
    if (options?.terminal_id) params.set('terminal_id', options.terminal_id)
    if (options?.patron_id) params.set('patron_id', options.patron_id)
    if (options?.item_id) params.set('item_id', options.item_id)
    if (options?.command) params.set('command', options.command)
    if (options?.success !== undefined) params.set('success', options.success.toString())
    if (options?.start_date) params.set('start_date', options.start_date)
    if (options?.end_date) params.set('end_date', options.end_date)

    const queryString = params.toString() ? `?${params.toString()}` : ''
    return await fetchApi<TransactionListResponse>(`/sip2/transactions${queryString}`, { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch transactions')
    }
    throw error
  }
}

export async function getTransaction(
  token: string,
  transactionId: number
): Promise<SIP2Transaction & {
  user_id: number | null
  catalog_item_id: number | null
  checkout_id: number | null
  request_message: string | null
  response_message: string | null
  transaction_data: Record<string, unknown> | null
  client_port: number | null
}> {
  try {
    return await fetchApi(`/sip2/transactions/${transactionId}`, { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch transaction')
    }
    throw error
  }
}

// ==================== Statistics Functions ====================

export async function getTerminalStats(token: string): Promise<TerminalStats> {
  try {
    return await fetchApi<TerminalStats>('/sip2/stats/terminals', { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch terminal statistics')
    }
    throw error
  }
}

export async function getTransactionStats(
  token: string,
  options?: {
    days?: number
    terminal_id?: string
  }
): Promise<TransactionStats> {
  try {
    const params = new URLSearchParams()
    if (options?.days) params.set('days', options.days.toString())
    if (options?.terminal_id) params.set('terminal_id', options.terminal_id)

    const queryString = params.toString() ? `?${params.toString()}` : ''
    return await fetchApi<TransactionStats>(`/sip2/stats/transactions${queryString}`, { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch transaction statistics')
    }
    throw error
  }
}

// ==================== Utility Functions ====================

export function getCommandLabel(command: string): string {
  const labels: Record<string, string> = {
    CHECKOUT_RESPONSE: 'Checkout',
    CHECKIN_RESPONSE: 'Checkin',
    RENEW_RESPONSE: 'Renewal',
    PATRON_STATUS_RESPONSE: 'Patron Lookup',
    ITEM_STATUS_RESPONSE: 'Item Status',
    FEE_PAID_RESPONSE: 'Fee Payment',
    END_SESSION_RESPONSE: 'Session End',
    PATRON_INFO_RESPONSE: 'Patron Info',
    ITEM_INFO_RESPONSE: 'Item Info',
  }
  return labels[command] || command.replace(/_/g, ' ').toLowerCase()
}

/**
 * Available SIP2 commands for filtering
 */
export const SIP2_COMMANDS = [
  { value: 'CHECKOUT_RESPONSE', label: 'Checkout' },
  { value: 'CHECKIN_RESPONSE', label: 'Checkin' },
  { value: 'RENEW_RESPONSE', label: 'Renewal' },
  { value: 'PATRON_STATUS_RESPONSE', label: 'Patron Lookup' },
  { value: 'PATRON_INFO_RESPONSE', label: 'Patron Info' },
  { value: 'ITEM_INFO_RESPONSE', label: 'Item Info' },
  { value: 'FEE_PAID_RESPONSE', label: 'Fee Payment' },
]

export function getTerminalStatusInfo(terminal: SIP2Terminal): {
  status: 'online' | 'offline' | 'inactive'
  label: string
  color: string
} {
  if (!terminal.is_active) {
    return { status: 'inactive', label: 'Inactive', color: 'gray' }
  }

  if (terminal.last_seen_at) {
    const lastSeen = new Date(terminal.last_seen_at)
    const now = new Date()
    const diffMinutes = (now.getTime() - lastSeen.getTime()) / (1000 * 60)

    if (diffMinutes < 15) {
      return { status: 'online', label: 'Online', color: 'green' }
    }
  }

  return { status: 'offline', label: 'Offline', color: 'red' }
}
