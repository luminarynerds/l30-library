/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Typed client for the session follow-ups + referrals endpoints.
 *
 * Kept separate from `parent-onboarding-api.ts` because the latter ships
 * a hand-written contract that has drifted from the backend (fields like
 * `coordinator_id`, `session_type`, `outcomes` are FE-only fictions).
 * Per memory `feedback_l30_openapi_handwritten_drift`, the long-term fix
 * is openapi-typescript codegen; until that lands, this PR's new surface
 * lives in its own file so any drift here is auditable in isolation.
 *
 * The shapes below mirror the Pydantic response models in
 * `app/schemas/parent_onboarding.py` (FollowupResponse, ReferralResponse,
 * PartnerAgencyResponse) exactly.
 */
import api from '@/lib/api-client'

const BASE = '/api/v1/parent-onboarding'

// ============================================================================
// Types
// ============================================================================

export type FollowupStatus =
  | 'open'
  | 'in_progress'
  | 'completed'
  | 'cancelled'

export type FollowupPriority = 'low' | 'normal' | 'high'

export type ReferralStatus =
  | 'made'
  | 'scheduled'
  | 'completed'
  | 'declined_by_patron'
  | 'declined_by_agency'

export interface SessionFollowup {
  id: number
  session_id: number
  title: string
  description?: string | null
  assignee_id?: number | null
  assignee_name?: string | null
  due_date: string // YYYY-MM-DD
  status: FollowupStatus
  priority: FollowupPriority
  completed_at?: string | null
  completed_by_id?: number | null
  completion_note?: string | null
  created_at?: string | null
  updated_at?: string | null
  created_by_id?: number | null
}

export interface FollowupCreateInput {
  title: string
  description?: string
  assignee_id?: number
  due_date: string
  priority?: FollowupPriority
}

export interface FollowupUpdateInput {
  title?: string
  description?: string
  assignee_id?: number
  due_date?: string
  status?: FollowupStatus
  priority?: FollowupPriority
}

export interface FollowupCompleteInput {
  completion_note?: string
}

export interface SessionReferral {
  id: number
  session_id: number
  partner_agency_id?: number | null
  partner_agency_name?: string | null
  agency_name_freetext?: string | null
  purpose: string
  status: ReferralStatus
  warm_handoff: boolean
  patron_consent_to_share: boolean
  notes?: string | null
  made_at: string
  made_by_id?: number | null
  created_at?: string | null
  updated_at?: string | null
}

export interface ReferralCreateInput {
  partner_agency_id?: number
  agency_name_freetext?: string
  purpose: string
  status?: ReferralStatus
  warm_handoff?: boolean
  patron_consent_to_share?: boolean
  notes?: string
}

export interface ReferralUpdateInput {
  partner_agency_id?: number
  agency_name_freetext?: string
  purpose?: string
  status?: ReferralStatus
  warm_handoff?: boolean
  patron_consent_to_share?: boolean
  notes?: string
}

export interface PartnerAgency {
  id: number
  name: string
  slug: string
  agency_type?: string | null
  contact_phone?: string | null
  contact_email?: string | null
  website_url?: string | null
  service_area?: string | null
  languages_served: string[]
  notes?: string | null
  is_active: boolean
  created_at?: string | null
  updated_at?: string | null
}

// ============================================================================
// Followups
// ============================================================================

export async function listSessionFollowups(
  sessionId: number,
): Promise<{ followups: SessionFollowup[]; total: number }> {
  const { data } = await api.get(`${BASE}/sessions/${sessionId}/followups`)
  return data
}

export async function createSessionFollowup(
  sessionId: number,
  input: FollowupCreateInput,
): Promise<SessionFollowup> {
  const { data } = await api.post(
    `${BASE}/sessions/${sessionId}/followups`,
    input,
  )
  return data
}

export async function updateFollowup(
  followupId: number,
  input: FollowupUpdateInput,
): Promise<SessionFollowup> {
  const { data } = await api.patch(`${BASE}/followups/${followupId}`, input)
  return data
}

export async function completeFollowup(
  followupId: number,
  input: FollowupCompleteInput = {},
): Promise<SessionFollowup> {
  const { data } = await api.post(
    `${BASE}/followups/${followupId}/complete`,
    input,
  )
  return data
}

export async function deleteFollowup(followupId: number): Promise<void> {
  await api.delete(`${BASE}/followups/${followupId}`)
}

// ============================================================================
// Referrals
// ============================================================================

export async function listSessionReferrals(
  sessionId: number,
): Promise<{ referrals: SessionReferral[]; total: number }> {
  const { data } = await api.get(`${BASE}/sessions/${sessionId}/referrals`)
  return data
}

export async function createSessionReferral(
  sessionId: number,
  input: ReferralCreateInput,
): Promise<SessionReferral> {
  const { data } = await api.post(
    `${BASE}/sessions/${sessionId}/referrals`,
    input,
  )
  return data
}

export async function updateReferral(
  referralId: number,
  input: ReferralUpdateInput,
): Promise<SessionReferral> {
  const { data } = await api.patch(`${BASE}/referrals/${referralId}`, input)
  return data
}

export async function deleteReferral(referralId: number): Promise<void> {
  await api.delete(`${BASE}/referrals/${referralId}`)
}

// ============================================================================
// Partner agencies (autocomplete)
// ============================================================================

export async function searchPartnerAgencies(
  q?: string,
  limit = 20,
): Promise<{ agencies: PartnerAgency[]; total: number }> {
  const params = new URLSearchParams()
  if (q) params.append('q', q)
  params.append('limit', String(limit))
  const { data } = await api.get(
    `${BASE}/partner-agencies?${params.toString()}`,
  )
  return data
}
