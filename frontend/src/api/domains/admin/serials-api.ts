/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { fetchApi, isApiError } from '@/lib/api-client'
import { getAccessToken } from '../../../utils/tokenStore'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface SerialTitle {
  id: number
  title: string
  catalog_item_id: number | null
  issn_print: string | null
  issn_electronic: string | null
  publisher: string | null
  country_of_publication: string | null
  language: string | null
  frequency: string
  is_active: boolean
  ceased_date: string | null
  preceding_title_id: number | null
  succeeding_title_id: number | null
  notes: string | null
  created_at: string | null
  updated_at: string | null
  active_subscription_count: number | null
}

export interface SerialTitleCreateData {
  title: string
  catalog_item_id?: number | null
  issn_print?: string | null
  issn_electronic?: string | null
  publisher?: string | null
  country_of_publication?: string | null
  language?: string | null
  frequency?: string
  notes?: string | null
}

export interface SerialTitleUpdateData {
  title?: string
  issn_print?: string | null
  issn_electronic?: string | null
  publisher?: string | null
  country_of_publication?: string | null
  language?: string | null
  frequency?: string
  is_active?: boolean
  ceased_date?: string | null
  preceding_title_id?: number | null
  succeeding_title_id?: number | null
  notes?: string | null
}

export interface PredictionPattern {
  id: number
  serial_title_id: number
  frequency: string
  pattern_details: Record<string, unknown>
  volume_scheme: string
  starting_volume: number | null
  starting_number: number | null
  numbers_per_volume: number | null
  designation_template: string | null
  effective_from: string
  effective_to: string | null
  is_active: boolean
  created_at: string | null
}

export interface PredictionPatternCreateData {
  frequency: string
  pattern_details?: Record<string, unknown>
  volume_scheme?: string
  starting_volume?: number | null
  starting_number?: number | null
  numbers_per_volume?: number | null
  designation_template?: string | null
  effective_from: string
  effective_to?: string | null
}

export interface SerialSubscription {
  id: number
  serial_title_id: number
  serial_title_name: string | null
  vendor_id: number | null
  vendor_name: string | null
  fund_id: number | null
  branch_id: number | null
  branch_name: string | null
  subscription_number: string | null
  copies_ordered: number
  start_date: string
  end_date: string
  cost: number | null
  renewal_status: string
  cancelled_date: string | null
  cancellation_reason: string | null
  notes: string | null
  created_at: string | null
}

export interface SerialSubscriptionCreateData {
  serial_title_id: number
  vendor_id?: number | null
  fund_id?: number | null
  branch_id?: number | null
  subscription_number?: string | null
  copies_ordered?: number
  start_date: string
  end_date: string
  cost?: number | null
  notes?: string | null
}

export interface SerialSubscriptionUpdateData {
  vendor_id?: number | null
  fund_id?: number | null
  branch_id?: number | null
  subscription_number?: string | null
  copies_ordered?: number
  end_date?: string
  cost?: number | null
  renewal_status?: string
  cancelled_date?: string | null
  cancellation_reason?: string | null
  notes?: string | null
}

export type SerialIssueStatus = 'expected' | 'received' | 'late' | 'claimed' | 'missing' | 'not_published'

export interface SerialIssue {
  id: number
  serial_title_id: number
  serial_title_name: string | null
  serial_subscription_id: number
  volume: string | null
  number: string | null
  designation: string | null
  designation_override: string | null
  expected_date: string
  received_date: string | null
  received_by_name: string | null
  status: SerialIssueStatus
  is_combined: boolean
  combined_designation: string | null
  is_supplement: boolean
  supplement_title: string | null
  barcode: string | null
  branch_name: string | null
  notes: string | null
  created_at: string | null
}

export interface SerialIssueCheckinRequest {
  issue_ids: number[]
  received_date?: string | null
  notes?: string | null
}

export interface SerialClaim {
  id: number
  serial_issue_id: number
  claim_date: string
  claim_type: string
  claim_number: string | null
  claimed_by_name: string | null
  response: string | null
  vendor_response_date: string | null
  replacement_expected_date: string | null
  resolution: string | null
  resolved_date: string | null
  created_at: string | null
}

export interface SerialClaimCreateData {
  claim_type?: string
  claim_number?: string | null
  notes?: string | null
}

export interface SerialsDashboard {
  expected_today: number
  overdue_count: number
  claimed_count: number
  received_this_week: number
  expiring_subscriptions: number
  total_active_titles: number
  total_active_subscriptions: number
}

interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  per_page: number
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function buildQuery(params: Record<string, string | number | boolean | null | undefined>): string {
  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value === null || value === undefined || value === '') continue
    search.set(key, String(value))
  }
  const qs = search.toString()
  return qs ? `?${qs}` : ''
}

async function call<T>(path: string, init?: Parameters<typeof fetchApi>[1]): Promise<T> {
  const token = getAccessToken()
  try {
    return await fetchApi<T>(path, { ...(token ? { token } : {}), ...(init ?? {}) })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Serials request failed')
    }
    throw error
  }
}

// ---------------------------------------------------------------------------
// Dashboard
// ---------------------------------------------------------------------------

export async function getSerialsDashboard(): Promise<SerialsDashboard> {
  return call<SerialsDashboard>('/serials/dashboard')
}

// ---------------------------------------------------------------------------
// Titles
// ---------------------------------------------------------------------------

export async function listSerialTitles(params?: {
  page?: number
  per_page?: number
  search?: string
  is_active?: boolean
  frequency?: string
}): Promise<PaginatedResponse<SerialTitle>> {
  return call<PaginatedResponse<SerialTitle>>(`/serials/titles${buildQuery({ ...params })}`)
}

export async function getSerialTitle(id: number): Promise<SerialTitle> {
  return call<SerialTitle>(`/serials/titles/${id}`)
}

export async function createSerialTitle(data: SerialTitleCreateData): Promise<SerialTitle> {
  return call<SerialTitle>('/serials/titles', { method: 'POST', body: data })
}

export async function updateSerialTitle(id: number, data: SerialTitleUpdateData): Promise<SerialTitle> {
  return call<SerialTitle>(`/serials/titles/${id}`, { method: 'PATCH', body: data })
}

// ---------------------------------------------------------------------------
// Prediction
// ---------------------------------------------------------------------------

export async function predictIssues(
  titleId: number,
  subscriptionId: number,
  monthsAhead = 12,
): Promise<SerialIssue[]> {
  return call<SerialIssue[]>(
    `/serials/titles/${titleId}/predict${buildQuery({ subscription_id: subscriptionId, months_ahead: monthsAhead })}`,
    { method: 'POST' },
  )
}

export async function createPredictionPattern(
  titleId: number,
  data: PredictionPatternCreateData,
): Promise<PredictionPattern> {
  return call<PredictionPattern>(`/serials/titles/${titleId}/patterns`, {
    method: 'POST',
    body: data,
  })
}

// ---------------------------------------------------------------------------
// Subscriptions
// ---------------------------------------------------------------------------

export async function listSerialSubscriptions(params?: {
  page?: number
  per_page?: number
  title_id?: number
  renewal_status?: string
}): Promise<PaginatedResponse<SerialSubscription>> {
  return call<PaginatedResponse<SerialSubscription>>(`/serials/subscriptions${buildQuery({ ...params })}`)
}

export async function createSerialSubscription(data: SerialSubscriptionCreateData): Promise<SerialSubscription> {
  return call<SerialSubscription>('/serials/subscriptions', { method: 'POST', body: data })
}

export async function updateSerialSubscription(
  id: number,
  data: SerialSubscriptionUpdateData,
): Promise<SerialSubscription> {
  return call<SerialSubscription>(`/serials/subscriptions/${id}`, { method: 'PATCH', body: data })
}

// ---------------------------------------------------------------------------
// Issues
// ---------------------------------------------------------------------------

export async function listSerialIssues(params?: {
  page?: number
  per_page?: number
  title_id?: number
  subscription_id?: number
  status?: SerialIssueStatus
  expected_from?: string
  expected_to?: string
}): Promise<PaginatedResponse<SerialIssue>> {
  return call<PaginatedResponse<SerialIssue>>(`/serials/issues${buildQuery({ ...params })}`)
}

export async function checkinSerialIssues(data: SerialIssueCheckinRequest): Promise<{
  checked_in: number
  issue_ids: number[]
}> {
  return call<{ checked_in: number; issue_ids: number[] }>('/serials/issues/checkin', {
    method: 'POST',
    body: data,
  })
}

// ---------------------------------------------------------------------------
// Claims
// ---------------------------------------------------------------------------

export async function createSerialClaim(
  issueId: number,
  data: SerialClaimCreateData,
): Promise<SerialClaim> {
  return call<SerialClaim>(`/serials/issues/${issueId}/claim`, {
    method: 'POST',
    body: data,
  })
}
