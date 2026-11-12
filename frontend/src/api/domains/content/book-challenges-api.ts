/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { fetchApi, isApiError } from '@/lib/api-client'
import type { AcquisitionRationale } from '@/types/acquisitionRationale'

// ==================== Book Challenges Types ====================

export interface BookChallenge {
  id: number
  title: string
  author: string | null
  isbn: string | null
  catalog_item_id: number | null
  status: ChallengeStatus
  primary_reason: ChallengeReason
  additional_reasons: string | null
  challenger_complaint: string | null
  outcome: ChallengeOutcome
  date_received: string
  date_resolved: string | null
  resolution_summary: string | null
  assigned_staff_id: number | null
  resolved_by_id: number | null
  is_public: boolean
  created_at: string
  updated_at: string | null
}

export interface BookChallengeDetail extends BookChallenge {
  challenger_name: string | null
  challenger_is_patron: boolean | null
  challenger_contact: string | null
  committee_notes: string | null
  public_title: string | null
  public_summary: string | null
  lessons_learned: string | null
  notes: BookChallengeNote[]
  // M3: auto-loaded by the backend GET handler. Null when the challenge
  // has no catalog_item_id link or no rationale exists for the item.
  acquisition_rationale: AcquisitionRationale | null
}

export interface BookChallengePublic {
  id: number
  catalog_item_id: number | null
  public_title: string | null
  title: string
  author: string | null
  primary_reason: ChallengeReason
  outcome: ChallengeOutcome
  public_summary: string | null
  lessons_learned: string | null
  date_received: string
  date_resolved: string | null
}

export interface BookChallengeNote {
  id: number
  challenge_id: number
  note: string
  is_internal: boolean
  created_by_id: number | null
  created_at: string
}

export interface BookChallengeCreate {
  title: string
  author?: string | null
  isbn?: string | null
  catalog_item_id?: number | null
  primary_reason: ChallengeReason
  additional_reasons?: string | null
  challenger_complaint?: string | null
  challenger_name?: string | null
  challenger_is_patron?: boolean
  challenger_contact?: string | null
}

export interface BookChallengeUpdate {
  status?: ChallengeStatus
  outcome?: ChallengeOutcome
  resolution_summary?: string | null
  committee_notes?: string | null
  assigned_staff_id?: number | null
  date_resolved?: string | null
  is_public?: boolean
  public_title?: string | null
  public_summary?: string | null
  lessons_learned?: string | null
}

export interface BookChallengeStats {
  total_challenges: number
  pending_challenges: number
  resolved_this_year: number
  outcomes: Record<string, number>
  reasons: Record<string, number>
  /** Years that have at least one is_public challenge (drives the Transparency Log Year dropdown). */
  available_years: number[]
}

export interface PaginatedBookChallenges {
  items: BookChallenge[]
  total: number
  page: number
  per_page: number
  pages: number
}

export interface BookChallengePublicListResponse {
  items: BookChallengePublic[]
  total: number
  page: number
  per_page: number
  pages: number
}

export interface PublicChallengesQuery {
  year?: number
  outcome?: ChallengeOutcome
  reason?: ChallengeReason
  page?: number
  per_page?: number
}

// Intellectual Freedom Resources
export interface IntellectualFreedomResource {
  id: number
  title: string
  description: string | null
  content: string | null
  url: string | null
  resource_type: 'article' | 'video' | 'external_link' | 'policy'
  display_order: number
  is_active: boolean
  created_at: string
  updated_at: string | null
}

export interface IntellectualFreedomResourceCreate {
  title: string
  description?: string | null
  content?: string | null
  url?: string | null
  resource_type: 'article' | 'video' | 'external_link' | 'policy'
  display_order?: number
  is_active?: boolean
}

// Enums
export type ChallengeStatus =
  | 'received'
  | 'under_review'
  | 'committee_review'
  | 'board_review'
  | 'resolved_retained'
  | 'resolved_restricted'
  | 'resolved_removed'
  | 'withdrawn'

export type ChallengeOutcome =
  | 'retained'
  | 'retained_with_changes'
  | 'restricted'
  | 'removed'
  | 'withdrawn'
  | 'pending'

export type ChallengeReason =
  | 'sexual_content'
  | 'lgbtq_content'
  | 'violence'
  | 'language'
  | 'religious_viewpoint'
  | 'political_viewpoint'
  | 'age_inappropriate'
  | 'racism'
  | 'drugs_alcohol'
  | 'anti_family'
  | 'occult_supernatural'
  | 'other'

// Human-readable labels
export const CHALLENGE_STATUS_LABELS: Record<ChallengeStatus, string> = {
  received: 'Received',
  under_review: 'Under Review',
  committee_review: 'Committee Review',
  board_review: 'Board Review',
  resolved_retained: 'Resolved - Retained',
  resolved_restricted: 'Resolved - Restricted',
  resolved_removed: 'Resolved - Removed',
  withdrawn: 'Withdrawn',
}

export const CHALLENGE_OUTCOME_LABELS: Record<ChallengeOutcome, string> = {
  retained: 'Retained',
  retained_with_changes: 'Retained with Changes',
  restricted: 'Restricted',
  removed: 'Removed',
  withdrawn: 'Withdrawn',
  pending: 'Pending',
}

export const CHALLENGE_REASON_LABELS: Record<ChallengeReason, string> = {
  sexual_content: 'Sexual Content',
  lgbtq_content: 'LGBTQ+ Content',
  violence: 'Violence',
  language: 'Language',
  religious_viewpoint: 'Religious Viewpoint',
  political_viewpoint: 'Political Viewpoint',
  age_inappropriate: 'Age Inappropriate',
  racism: 'Racism',
  drugs_alcohol: 'Drugs/Alcohol',
  anti_family: 'Anti-Family',
  occult_supernatural: 'Occult/Supernatural',
  other: 'Other',
}

// ==================== Public Reconsideration Request ====================

export interface ReconsiderationRequest {
  title: string
  author?: string | null
  isbn?: string | null
  primary_reason: ChallengeReason | ''
  challenger_complaint: string
  challenger_name: string
  challenger_contact?: string | null
  has_read_material: boolean
  turnstile_token?: string | null
}

export interface ReconsiderationResponse {
  message: string
  reference_id: number
  expected_response_days: number
}

// ==================== Public API Functions ====================

export function getPublicChallenges(): Promise<BookChallengePublic[]>
export function getPublicChallenges(limit: number): Promise<BookChallengePublic[]>
export function getPublicChallenges(query: PublicChallengesQuery): Promise<BookChallengePublicListResponse>
export async function getPublicChallenges(
  arg?: number | PublicChallengesQuery,
): Promise<BookChallengePublic[] | BookChallengePublicListResponse> {
  // Build the querystring + decide the return shape.
  const params = new URLSearchParams()
  let wantsEnvelope = false

  if (arg === undefined) {
    // No-args legacy: ask for a large page so the catalog hooks see at
    // least as many rows as before the pagination change.
    params.set('per_page', '100')
  } else if (typeof arg === 'number') {
    // Legacy ``limit`` shim -- map to per_page on the new endpoint.
    params.set('per_page', String(Math.max(1, Math.min(arg, 100))))
  } else {
    wantsEnvelope = true
    if (arg.year !== undefined) params.set('year', String(arg.year))
    if (arg.outcome) params.set('outcome', arg.outcome)
    if (arg.reason) params.set('reason', arg.reason)
    if (arg.page !== undefined) params.set('page', String(arg.page))
    if (arg.per_page !== undefined) params.set('per_page', String(arg.per_page))
  }

  try {
    const url = `/book-challenges/public${params.toString() ? `?${params.toString()}` : ''}`
    const data = await fetchApi<BookChallengePublicListResponse>(url)
    return wantsEnvelope ? data : data.items
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch public challenges')
    }
    throw error
  }
}

export async function getPublicStats(): Promise<BookChallengeStats> {
  try {
    return await fetchApi<BookChallengeStats>('/book-challenges/public/stats')
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch challenge statistics')
    }
    throw error
  }
}

export async function submitReconsiderationRequest(
  data: ReconsiderationRequest
): Promise<ReconsiderationResponse> {
  try {
    return await fetchApi<ReconsiderationResponse>('/book-challenges/public/request', {
      method: 'POST',
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to submit reconsideration request')
    }
    throw error
  }
}

export async function getIntellectualFreedomResources(
  resourceType?: string
): Promise<IntellectualFreedomResource[]> {
  try {
    const url = resourceType
      ? `/intellectual-freedom-resources?resource_type=${resourceType}`
      : '/intellectual-freedom-resources'
    return await fetchApi<IntellectualFreedomResource[]>(url)
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch resources')
    }
    throw error
  }
}

// ==================== Staff API Functions ====================

export interface ChallengeListParams {
  page?: number
  perPage?: number
  status?: ChallengeStatus
  outcome?: ChallengeOutcome
  reason?: ChallengeReason
  search?: string
}

export async function getChallenges(
  token: string,
  params: ChallengeListParams = {}
): Promise<PaginatedBookChallenges> {
  try {
    const { page = 1, perPage = 20, status, outcome, reason, search } = params
    let url = `/book-challenges?page=${page}&per_page=${perPage}`
    if (status) url += `&status=${status}`
    if (outcome) url += `&outcome=${outcome}`
    if (reason) url += `&reason=${reason}`
    if (search) url += `&search=${encodeURIComponent(search)}`
    return await fetchApi<PaginatedBookChallenges>(url, { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch challenges')
    }
    throw error
  }
}

export async function getChallenge(token: string, challengeId: number): Promise<BookChallengeDetail> {
  try {
    return await fetchApi<BookChallengeDetail>(`/book-challenges/${challengeId}`, { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch challenge')
    }
    throw error
  }
}

export async function createChallenge(
  token: string,
  data: BookChallengeCreate
): Promise<BookChallenge> {
  try {
    return await fetchApi<BookChallenge>('/book-challenges', {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to create challenge')
    }
    throw error
  }
}

export async function updateChallenge(
  token: string,
  challengeId: number,
  data: BookChallengeUpdate
): Promise<BookChallenge> {
  try {
    return await fetchApi<BookChallenge>(`/book-challenges/${challengeId}`, {
      method: 'PUT',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to update challenge')
    }
    throw error
  }
}

export async function addChallengeNote(
  token: string,
  challengeId: number,
  note: string,
  isInternal = true
): Promise<BookChallengeNote> {
  try {
    return await fetchApi<BookChallengeNote>(`/book-challenges/${challengeId}/notes`, {
      method: 'POST',
      token,
      body: { note, is_internal: isInternal },
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to add note')
    }
    throw error
  }
}

export async function getChallengeStats(token: string): Promise<BookChallengeStats> {
  try {
    return await fetchApi<BookChallengeStats>('/book-challenges/stats', { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch statistics')
    }
    throw error
  }
}

// ==================== Resource Management (Staff) ====================

export async function createResource(
  token: string,
  data: IntellectualFreedomResourceCreate
): Promise<IntellectualFreedomResource> {
  try {
    return await fetchApi<IntellectualFreedomResource>('/intellectual-freedom-resources', {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to create resource')
    }
    throw error
  }
}

export async function updateResource(
  token: string,
  resourceId: number,
  data: Partial<IntellectualFreedomResourceCreate>
): Promise<IntellectualFreedomResource> {
  try {
    return await fetchApi<IntellectualFreedomResource>(`/intellectual-freedom-resources/${resourceId}`, {
      method: 'PUT',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to update resource')
    }
    throw error
  }
}

export async function deleteResource(token: string, resourceId: number): Promise<void> {
  try {
    await fetchApi<void>(`/intellectual-freedom-resources/${resourceId}`, {
      method: 'DELETE',
      token,
      skipJsonParse: true,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to delete resource')
    }
    throw error
  }
}

// ==================== Challenge Management (Staff) ====================

export async function deleteChallenge(token: string, challengeId: number): Promise<void> {
  try {
    await fetchApi<void>(`/book-challenges/${challengeId}`, {
      method: 'DELETE',
      token,
      skipJsonParse: true,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to delete challenge')
    }
    throw error
  }
}

export function getExportChallengesUrl(
  params: { status?: ChallengeStatus; outcome?: ChallengeOutcome } = {}
): string {
  let url = '/book-challenges/export?'
  if (params.status) url += `status=${params.status}&`
  if (params.outcome) url += `outcome=${params.outcome}&`
  return url.replace(/[&?]$/, '')
}
