/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { API_BASE as API_ROOT } from '@/api/types'
/**
 * Smart Weeding Recommendations API client.
 *
 * Provides access to CREW method-based weeding analysis,
 * candidate management, and collection health analytics.
 */

const API_BASE = `${API_ROOT}/weeding`

// ============ Types ============

export type WeedingStatus = 'candidate' | 'under_review' | 'approved' | 'rejected' | 'disposed'
export type WeedingReason = 'low_circulation' | 'poor_condition' | 'outdated' | 'duplicate' | 'superseded' | 'damaged_beyond_repair' | 'missing_long_term' | 'out_of_scope' | 'never_circulated' | 'space_pressure' | 'other'
export type DisposalMethod = 'discard' | 'donation' | 'sale' | 'recycling' | 'transfer' | 'other'
export type DispositionRecommendation = 'donate_good_condition' | 'recycle_poor_condition' | 'sell_popular_title' | 'transfer_to_branch' | 'discard'
export type CREWCategory = '000' | '100' | '200' | '300' | '400' | '500' | '600' | '700' | '800' | '900' | 'fiction' | 'travel' | 'law' | 'medical' | 'computing'

export interface WeedingCandidate {
  id: number
  item_copy_id: number
  status: WeedingStatus
  reason: WeedingReason
  reason_notes: string | null
  item_title: string | null
  item_author: string | null
  item_barcode: string | null
  item_location: string | null
  item_type: string | null
  item_condition: string | null
  publication_year: number | null
  isbn: string | null
  last_checkout_date: string | null
  total_checkouts: number
  years_since_acquisition: number | null
  condition_score: number | null
  days_since_last_circulation: number | null
  crew_category: CREWCategory | null
  crew_score: number | null
  is_outdated_content: boolean
  outdated_flags: string | null
  is_duplicate: boolean
  duplicate_count: number
  is_superseded: boolean
  never_circulated: boolean
  section_fill_rate: number | null
  disposition_recommendation: DispositionRecommendation | null
  disposition_rationale: string | null
  auto_generated: boolean
  created_at: string
  created_by_id: number
  reviewed_by_id: number | null
  reviewed_at: string | null
  approved_by_id: number | null
  approved_at: string | null
}

export interface WeedingCandidateList {
  items: WeedingCandidate[]
  total: number
  page: number
  per_page: number
}

export interface WeedingSummary {
  total_candidates: number
  by_status: Record<string, number>
  by_reason: Record<string, number>
  sections_over_capacity: number
  total_duplicates_excess: number
  outdated_items: number
  never_circulated_items: number
  avg_crew_score: number | null
}

export interface SectionPressure {
  location: string
  total_items: number
  capacity_estimate: number
  fill_rate: number
  weeding_candidates_count: number
  avg_item_age_years: number
  avg_checkouts: number
  low_circ_items: number
}

export interface DuplicateGroup {
  catalog_item_id: number
  title: string
  author: string | null
  isbn: string | null
  total_copies: number
  recommended_copies: number
  excess_copies: number
  copies: Array<{ id: number; barcode: string; condition: string; location: string | null; acquisition_date: string | null }>
}

export interface SupersededEdition {
  older_item_id: number
  older_title: string
  older_edition: string | null
  older_publication_year: number | null
  newer_item_id: number
  newer_title: string
  newer_edition: string | null
  newer_publication_year: number | null
}

export interface WeedingRule {
  id: number
  name: string
  description: string | null
  is_active: boolean
  crew_category: CREWCategory | null
  max_age_years: number | null
  max_years_no_circulation: number | null
  min_condition_score: number | null
  max_duplicate_copies: number | null
  section_fill_threshold: number | null
  subject_keywords: string | null
  location_filter: string | null
  created_at: string
}

// ============ API Helper ============

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

export function getSummary(token: string): Promise<WeedingSummary> {
  return apiFetch<WeedingSummary>(token, '/summary')
}

export function runAnalysis(
  token: string,
  params: {
    location_filter?: string
    crew_category?: CREWCategory
    min_crew_score?: number
    include_reasons?: WeedingReason[]
    max_results?: number
  } = {}
): Promise<WeedingCandidateList> {
  return apiFetch<WeedingCandidateList>(token, '/analyze', {
    method: 'POST',
    body: JSON.stringify(params),
  })
}

export function listCandidates(
  token: string,
  params: {
    status?: WeedingStatus
    reason?: WeedingReason
    location?: string
    min_score?: number
    page?: number
    per_page?: number
  } = {}
): Promise<WeedingCandidateList> {
  const searchParams = new URLSearchParams()
  if (params.status) searchParams.set('status', params.status)
  if (params.reason) searchParams.set('reason', params.reason)
  if (params.location) searchParams.set('location', params.location)
  if (params.min_score !== undefined) searchParams.set('min_score', String(params.min_score))
  if (params.page) searchParams.set('page', String(params.page))
  if (params.per_page) searchParams.set('per_page', String(params.per_page))
  const qs = searchParams.toString()
  return apiFetch<WeedingCandidateList>(token, '/candidates' + (qs ? '?' + qs : ''))
}

export function getCandidate(token: string, id: number): Promise<WeedingCandidate> {
  return apiFetch<WeedingCandidate>(token, `/candidates/${id}`)
}

export function createCandidate(
  token: string,
  data: { item_copy_id: number; reason: WeedingReason; reason_notes?: string }
): Promise<WeedingCandidate> {
  return apiFetch<WeedingCandidate>(token, '/candidates', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export function reviewCandidate(
  token: string,
  id: number,
  data: { action: 'approve' | 'reject'; review_notes?: string; rejection_reason?: string }
): Promise<WeedingCandidate> {
  return apiFetch<WeedingCandidate>(token, `/candidates/${id}/review`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export function withdrawCandidate(
  token: string,
  id: number,
  data: { disposal_method: DisposalMethod; disposal_notes?: string; disposal_recipient?: string }
): Promise<WeedingCandidate> {
  return apiFetch<WeedingCandidate>(token, `/candidates/${id}/withdraw`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export function batchApprove(token: string, candidateIds: number[]): Promise<{ approved: number; total_requested: number }> {
  return apiFetch(token, '/candidates/batch-approve', {
    method: 'POST',
    body: JSON.stringify(candidateIds),
  })
}

export function batchWithdraw(
  token: string,
  candidateIds: number[],
  disposalMethod: DisposalMethod
): Promise<{ withdrawn: number; total_requested: number }> {
  return apiFetch(token, `/candidates/batch-withdraw?disposal_method=${disposalMethod}`, {
    method: 'POST',
    body: JSON.stringify(candidateIds),
  })
}

export function getSectionPressure(token: string, location?: string): Promise<{ sections: SectionPressure[] }> {
  const qs = location ? '?location=' + encodeURIComponent(location) : ''
  return apiFetch(token, '/section-pressure' + qs)
}

export function getDuplicates(token: string): Promise<{ groups: DuplicateGroup[]; total_excess_copies: number }> {
  return apiFetch(token, '/duplicates')
}

export function getSupersededEditions(token: string): Promise<{ items: SupersededEdition[]; total: number }> {
  return apiFetch(token, '/superseded')
}

export function listRules(token: string): Promise<{ rules: WeedingRule[]; total: number }> {
  return apiFetch(token, '/rules')
}

export function createRule(
  token: string,
  data: {
    name: string
    description?: string
    crew_category?: CREWCategory
    max_age_years?: number
    max_years_no_circulation?: number
    min_condition_score?: number
    max_duplicate_copies?: number
    section_fill_threshold?: number
    subject_keywords?: string
    location_filter?: string
  }
): Promise<WeedingRule> {
  return apiFetch<WeedingRule>(token, '/rules', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export function deleteRule(token: string, id: number): Promise<void> {
  return apiFetch<void>(token, `/rules/${id}`, { method: 'DELETE' })
}