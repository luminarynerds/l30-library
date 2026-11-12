/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Privacy API Service
 *
 * Handles GDPR-compliant data export and account deletion operations.
 */

import { fetchApi } from '@/lib/api-client'
import { getAccessToken } from '@/utils/tokenStore'
import { API_BASE as API_ROOT } from '@/api/types'

const API_BASE = `${API_ROOT}`

interface ApiError {
  status: number
  message: string
}

// Types
export interface DeletionBlocker {
  type: string
  description: string
  count?: number
  total_amount?: number
}

export interface DeletionEligibility {
  eligible: boolean
  blockers: DeletionBlocker[]
  has_pending_deletion: boolean
  deletion_scheduled_for?: string
  can_cancel_deletion: boolean
}

export interface DataExport {
  user: {
    id: number
    email: string
    first_name: string
    last_name: string
    created_at: string
    updated_at?: string
  }
  checkouts: Array<{
    id: number
    item_title: string
    item_author?: string
    checked_out_at: string
    due_date: string
    returned_at?: string
    status: string
  }>
  holds: Array<{
    id: number
    item_title: string
    item_author?: string
    status: string
    position?: number
    created_at: string
  }>
  fines: Array<{
    id: number
    amount: number
    amount_paid: number
    reason: string
    created_at: string
    status: string
  }>
  favorites: Array<{
    id: number
    catalog_item_id: number
    title: string
    created_at: string
  }>
  reading_lists: Array<{
    id: number
    name: string
    description?: string
    item_count: number
    created_at: string
  }>
  reading_history: Array<{
    id: number
    title: string
    author?: string
    logged_at: string
    rating?: number
    notes?: string
  }>
  event_registrations: Array<{
    id: number
    event_title: string
    event_date: string
    registered_at: string
    status: string
  }>
  exported_at: string
}

export interface DeletionRequestResponse {
  message: string
  deletion_scheduled_for: string
  grace_period_days: number
}

export interface DeletionCancelResponse {
  message: string
}

export interface ImmediateDeletionResponse {
  message: string
  email_blocked_until: string
}

// Helper function to handle API responses
async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Request failed' }))
    throw { status: res.status, message: err.detail || 'Request failed' } as ApiError
  }
  return res.json()
}

export async function checkDeletionEligibility(): Promise<DeletionEligibility> {
  const token = getAccessToken()
  const res = await fetch(`${API_BASE}/privacy/account/deletion-eligibility`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  return handleResponse<DeletionEligibility>(res)
}

export async function exportUserData(): Promise<DataExport> {
  const token = getAccessToken()
  const res = await fetch(`${API_BASE}/privacy/account/export`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  return handleResponse<DataExport>(res)
}

export async function requestDeletion(password: string): Promise<DeletionRequestResponse> {
  const token = getAccessToken()
  const res = await fetch(`${API_BASE}/privacy/account/request-deletion`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ password }),
  })
  return handleResponse<DeletionRequestResponse>(res)
}

export async function cancelDeletionRequest(): Promise<DeletionCancelResponse> {
  const token = getAccessToken()
  const res = await fetch(`${API_BASE}/privacy/account/cancel-deletion`, {
    method: 'POST',
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  return handleResponse<DeletionCancelResponse>(res)
}

export async function deleteAccountImmediately(password: string): Promise<ImmediateDeletionResponse> {
  const token = getAccessToken()
  const res = await fetch(`${API_BASE}/privacy/account`, {
    method: 'DELETE',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ password }),
  })
  return handleResponse<ImmediateDeletionResponse>(res)
}

// Staff endpoints for patron deletion

export interface StaffDeletionEligibility extends DeletionEligibility {
  patron_id: number
  patron_email: string
  patron_name: string
}

export async function checkPatronDeletionEligibility(patronId: number): Promise<StaffDeletionEligibility> {
  const token = getAccessToken()
  const res = await fetch(`${API_BASE}/privacy/staff/patron/${patronId}/deletion-eligibility`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  return handleResponse<StaffDeletionEligibility>(res)
}

export async function initiatePatronDeletion(
  patronId: number,
  identityVerified: boolean,
  notes?: string
): Promise<DeletionRequestResponse> {
  const token = getAccessToken()
  const res = await fetch(`${API_BASE}/privacy/staff/initiate-deletion`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({
      patron_id: patronId,
      identity_verified: identityVerified,
      notes,
    }),
  })
  return handleResponse<DeletionRequestResponse>(res)
}

export async function cancelPatronDeletion(patronId: number, reason?: string): Promise<DeletionCancelResponse> {
  const token = getAccessToken()
  const res = await fetch(`${API_BASE}/privacy/staff/patron/${patronId}/cancel-deletion`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ reason }),
  })
  return handleResponse<DeletionCancelResponse>(res)
}

// Child account endpoints (COPPA compliance)

export interface ChildRegistrationRequest {
  child_first_name: string
  child_last_name: string
  child_birth_date: string
  parent_email: string
}

export interface ChildRegistrationResponse {
  message: string
  child_id: number
  consent_request_sent: boolean
}

export interface ChildConsentRequest {
  consent_token: string
  parent_signature: string
}

export interface ChildConsentResponse {
  message: string
  child_id: number
  account_activated: boolean
}

export interface ResendConsentRequest {
  child_id: number
  parent_email?: string
}

export interface ResendConsentResponse {
  message: string
  consent_request_sent: boolean
}

export async function registerChild(data: ChildRegistrationRequest): Promise<ChildRegistrationResponse> {
  const token = getAccessToken()
  return fetchApi<ChildRegistrationResponse>('/privacy/child/register', {
    method: 'POST',
    body: data,
    ...(token ? { token } : {}),
  })
}

export async function giveChildConsent(data: ChildConsentRequest): Promise<ChildConsentResponse> {
  const token = getAccessToken()
  return fetchApi<ChildConsentResponse>('/privacy/child/consent', {
    method: 'POST',
    body: data,
    ...(token ? { token } : {}),
  })
}

export async function resendChildConsent(data: ResendConsentRequest): Promise<ResendConsentResponse> {
  const token = getAccessToken()
  return fetchApi<ResendConsentResponse>('/privacy/child/resend-consent', {
    method: 'POST',
    body: data,
    ...(token ? { token } : {}),
  })
}

// Parental consent verification (called from the public /consent page)

export interface ConsentTokenInfo {
  child_first_name: string
  child_last_initial: string
  parent_email: string
  expires_at: string
  already_decided: boolean
}

export interface ParentalConsentDecision {
  message: string
  consent_given: boolean
}

export async function getParentalConsentInfo(consentToken: string): Promise<ConsentTokenInfo> {
  return fetchApi<ConsentTokenInfo>(
    `/privacy/child/consent?token=${encodeURIComponent(consentToken)}`,
    { method: 'GET' },
  )
}

export async function submitParentalConsent(
  consentToken: string,
  consentGiven: boolean,
): Promise<ParentalConsentDecision> {
  return fetchApi<ParentalConsentDecision>('/privacy/child/consent', {
    method: 'POST',
    body: { token: consentToken, consent_given: consentGiven },
  })
}