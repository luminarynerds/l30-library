/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Patron Claims Returned API Service
 *
 * Allows patrons to:
 * - File claims returned disputes for items they believe they've returned
 * - View their dispute history and status
 * - View claims returned policies
 */

import { fetchApi, isApiError } from '@/lib/api-client'

// ==================== Types ====================

export type ClaimDisputeStatus =
  | 'pending'
  | 'under_review'
  | 'search_in_progress'
  | 'approved'
  | 'denied'
  | 'item_found'

export interface PatronFileClaimRequest {
  checkout_id: number
  statement: string
  return_date?: string | null
  return_location?: string | null
}

export interface PatronClaimResponse {
  id: number
  checkout_id: number
  item_title: string
  item_author: string | null
  status: ClaimDisputeStatus
  status_display: string
  patron_statement: string
  claimed_return_date: string | null
  claimed_return_location: string | null
  filed_at: string
  resolution: string | null
  resolution_reason: string | null
  credit_amount: string | null
}

export interface PatronClaimsListResponse {
  claims: PatronClaimResponse[]
  total: number
}

export interface ClaimsReturnedPolicyResponse {
  max_claims_per_year: number
  review_period_days: number
  claims_this_year: number
  claims_remaining: number
  is_eligible_to_file: boolean
  message: string
}

export interface EligibleCheckout {
  checkout_id: number
  item_title: string
  item_author: string | null
  due_date: string
  status: string
  has_active_dispute: boolean
}

// ==================== API Functions ====================

export async function getClaimsReturnedPolicy(
  token: string
): Promise<ClaimsReturnedPolicyResponse> {
  try {
    return await fetchApi<ClaimsReturnedPolicyResponse>(
      '/patron/claims-returned/policy',
      { token }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      if (error.status === 401) {
        throw new Error('Please sign in to view claims policy.')
      }
      throw new Error(error.detail || 'Failed to fetch claims returned policy')
    }
    throw new Error('Failed to fetch claims returned policy')
  }
}

export async function fileClaim(
  token: string,
  request: PatronFileClaimRequest
): Promise<PatronClaimResponse> {
  try {
    return await fetchApi<PatronClaimResponse>(
      '/patron/claims-returned/file',
      {
        method: 'POST',
        token,
        body: request,
      }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      if (error.status === 401) {
        throw new Error('Please sign in to file a claim.')
      }
      if (error.status === 403) {
        throw new Error('You can only file claims for your own checkouts.')
      }
      if (error.status === 404) {
        throw new Error('Checkout not found.')
      }
      if (error.status === 400) {
        throw new Error(error.detail || 'Unable to file claim for this checkout.')
      }
      throw new Error(error.detail || 'Failed to file claims returned dispute')
    }
    throw new Error('Failed to file claims returned dispute')
  }
}

export async function listMyClaims(
  token: string,
  params?: {
    include_resolved?: boolean
    limit?: number
    offset?: number
  }
): Promise<PatronClaimsListResponse> {
  const searchParams = new URLSearchParams()
  if (params?.include_resolved) {
    searchParams.set('include_resolved', 'true')
  }
  if (params?.limit !== undefined) {
    searchParams.set('limit', String(params.limit))
  }
  if (params?.offset !== undefined) {
    searchParams.set('offset', String(params.offset))
  }

  const queryString = searchParams.toString()
  try {
    return await fetchApi<PatronClaimsListResponse>(
      `/patron/claims-returned${queryString ? '?' + queryString : ''}`,
      { token }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      if (error.status === 401) {
        throw new Error('Please sign in to view your claims.')
      }
      throw new Error(error.detail || 'Failed to fetch your claims')
    }
    throw new Error('Failed to fetch your claims')
  }
}

export async function getClaimDetails(
  token: string,
  claimId: number
): Promise<PatronClaimResponse> {
  try {
    return await fetchApi<PatronClaimResponse>(
      `/patron/claims-returned/${claimId}`,
      { token }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      if (error.status === 401) {
        throw new Error('Please sign in to view claim details.')
      }
      if (error.status === 403) {
        throw new Error('You can only view your own claims.')
      }
      if (error.status === 404) {
        throw new Error('Claim not found.')
      }
      throw new Error(error.detail || 'Failed to fetch claim details')
    }
    throw new Error('Failed to fetch claim details')
  }
}

export async function getEligibleCheckouts(
  token: string
): Promise<EligibleCheckout[]> {
  try {
    return await fetchApi<EligibleCheckout[]>(
      '/patron/claims-returned/eligible-checkouts',
      { token }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      if (error.status === 401) {
        throw new Error('Please sign in to view eligible checkouts.')
      }
      throw new Error(error.detail || 'Failed to fetch eligible checkouts')
    }
    throw new Error('Failed to fetch eligible checkouts')
  }
}

// ==================== Helper Functions ====================

export function formatClaimStatus(status: ClaimDisputeStatus): string {
  const statusLabels: Record<ClaimDisputeStatus, string> = {
    pending: 'Pending Review',
    under_review: 'Under Review',
    search_in_progress: 'Search in Progress',
    approved: 'Approved',
    denied: 'Denied',
    item_found: 'Item Found',
  }
  return statusLabels[status] || status
}

export function getClaimStatusColor(status: ClaimDisputeStatus): string {
  const colors: Record<ClaimDisputeStatus, string> = {
    pending: 'bg-status-warning-100 text-status-warning-700',
    under_review: 'bg-earth-100 text-lsc-rose',
    search_in_progress: 'bg-category-100 text-category-700',
    approved: 'bg-status-success-100 text-status-success-700',
    denied: 'bg-status-danger-100 text-status-danger-700',
    item_found: 'bg-status-success-100 text-status-success-700',
  }
  return colors[status] || 'bg-earth-100 text-earth-700 dark:text-earth-200'
}

export function isClaimResolved(status: ClaimDisputeStatus): boolean {
  return ['approved', 'denied', 'item_found'].includes(status)
}

export function isClaimPending(status: ClaimDisputeStatus): boolean {
  return ['pending', 'under_review', 'search_in_progress'].includes(status)
}

export { isApiError }
