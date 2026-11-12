/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Parent Onboarding Reports API Client
 *
 * Routes: GET /dashboard, GET /reports/weekly-summary,
 * GET+POST /sessions/{id}/family-snapshot[/reveal],
 * GET+POST /patrons/{id}/consent/family-snapshot
 */
import api from '@/lib/api-client'
import { API_BASE } from '@/api/types'
import { triggerBlobDownload } from './parent-onboarding-download'

// ============================================================================
// Types (reports-only)
// ============================================================================

import type { ParentOnboardingStatus, RiskLevel } from './parent-onboarding-sessions-api'
import type { HomeVisitPurpose, HomeVisitStatus } from './parent-onboarding-home-visits-api'

// Dashboard list items are SUMMARY shapes (ParentOnboardingSessionSummary /
// CareAssignmentSummary / ParentHomeVisitSummary in
// backend/app/schemas/parent_onboarding.py), NOT the full entity responses.
// The rail previously typed these as the full shapes and filtered on fields
// the payload never carried, which silently emptied the Up Next rail.

export interface ParentOnboardingSessionSummary {
  id: number
  patron_id: number
  patron_name?: string | null
  /** Owning staff member; the Up Next rail scopes by this. */
  staff_id?: number | null
  /** Full ISO datetime (serialized from the model's scheduled_at). */
  scheduled_date: string
  status: ParentOnboardingStatus
}

export interface CareAssignmentSummary {
  id: number
  patron_id: number
  patron_name?: string | null
  /** Owning coordinator; the Up Next rail scopes by this. */
  coordinator_id?: number | null
  next_check_in_due?: string | null
  risk_level: RiskLevel
}

export interface ParentHomeVisitSummary {
  id: number
  patron_id: number
  patron_name?: string | null
  /** Visiting staff member; the Up Next rail scopes by this. */
  visitor_id?: number | null
  visitor_name?: string | null
  scheduled_date: string
  scheduled_time?: string | null
  purpose: HomeVisitPurpose
  status: HomeVisitStatus
}

export interface ParentOnboardingDashboard {
  active_families: number
  upcoming_sessions: number
  overdue_check_ins: number
  active_childcare_sessions: number
  active_connection_groups: number
  pending_enrollments: number
  upcoming_home_visits: number
  recent_sessions: ParentOnboardingSessionSummary[]
  overdue_assignments: CareAssignmentSummary[]
  upcoming_visits: ParentHomeVisitSummary[]
}

export type WeeklySummaryExportFormat = 'csv' | 'pdf'

export interface WeeklySummaryExportOptions {
  /** 'csv' is supported today; 'pdf' returns 422 from the backend (deferred). */
  format: WeeklySummaryExportFormat
  /** Optional ISO YYYY-MM-DD; defaults to today (library timezone, server-resolved). */
  endDate?: string
  /** Pass `"me"` to scope to the requester, an integer id for a specific coordinator, or undefined for whole team. */
  coordinatorId?: number | 'me'
}

export interface WeeklySummaryDownload {
  blob: Blob
  filename: string
}

export type FamilySnapshotConsentStatus = 'granted' | 'revoked' | 'not_requested'

export interface FamilySnapshotMember {
  first_name_revealed: string
  age_range: string
  is_parent: boolean
}

export interface FamilySnapshot {
  patron_id: number
  consent_status: FamilySnapshotConsentStatus
  consent_recorded_at?: string | null
  language_preference?: string | null
  language_preference_label?: string | null
  household_size?: number | null
  household_members: FamilySnapshotMember[]
  household_notes_summary?: string | null
  baby_age_months?: number | null
  sensitive_fields_hidden: boolean
}

export interface PatronFamilySnapshotConsentStatus {
  patron_id: number
  consent_status: FamilySnapshotConsentStatus
  consent_recorded_at?: string | null
  recorded_by_staff_id?: number | null
}

export interface PatronConsentDecision {
  granted: boolean
  notes?: string | null
}

export interface PatronConsentRecord {
  id: number
  patron_id: number
  consent_type: string
  granted: boolean
  recorded_by_staff_id: number | null
  recorded_at: string
  revoked_at: string | null
  notes: string | null
}

// ============================================================================
// Dashboard API
// ============================================================================

export async function getDashboard(): Promise<ParentOnboardingDashboard> {
  return api.get(`${API_BASE}/parent-onboarding/dashboard`)
}

// ============================================================================
// Weekly Summary Export
// ============================================================================

export async function downloadWeeklySummary(
  options: WeeklySummaryExportOptions,
): Promise<WeeklySummaryDownload> {
  const params = new URLSearchParams()
  params.set('format', options.format)
  if (options.endDate) params.set('end_date', options.endDate)
  if (options.coordinatorId !== undefined && options.coordinatorId !== null) {
    params.set('coordinator_id', String(options.coordinatorId))
  }

  const { getAccessToken } = await import('@/utils/tokenStore')
  const token = getAccessToken()
  const response = await fetch(
    `${API_BASE}/parent-onboarding/reports/weekly-summary?${params.toString()}`,
    {
      method: 'GET',
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    },
  )
  if (!response.ok) {
    let detail = `Report download failed (${response.status})`
    try {
      const body = await response.json()
      if (body?.detail && typeof body.detail === 'string') detail = body.detail
    } catch {
      // Body wasn't JSON; keep the default detail.
    }
    throw new Error(detail)
  }

  const blob = await response.blob()
  const dispo = response.headers.get('Content-Disposition') || ''
  const match = dispo.match(/filename="?([^";]+)"?/i)
  const filename = (match?.[1] || `parent-onboarding-weekly.${options.format}`).trim()

  return { blob, filename }
}

export async function triggerWeeklySummaryDownload(
  options: WeeklySummaryExportOptions,
): Promise<{ filename: string }> {
  const { blob, filename } = await downloadWeeklySummary(options)
  triggerBlobDownload(blob, filename)
  return { filename }
}

// ============================================================================
// Family Snapshot API
// ============================================================================

export async function getSessionFamilySnapshot(
  sessionId: number,
): Promise<FamilySnapshot> {
  return api.get(
    `${API_BASE}/parent-onboarding/sessions/${sessionId}/family-snapshot`,
  )
}

export async function revealSessionFamilySnapshot(
  sessionId: number,
): Promise<FamilySnapshot> {
  return api.post(
    `${API_BASE}/parent-onboarding/sessions/${sessionId}/family-snapshot/reveal`,
    null,
  )
}

export async function getPatronFamilySnapshotConsent(
  patronId: number,
): Promise<PatronFamilySnapshotConsentStatus> {
  return api.get(
    `${API_BASE}/parent-onboarding/patrons/${patronId}/consent/family-snapshot`,
  )
}

export async function recordPatronFamilySnapshotConsent(
  patronId: number,
  decision: PatronConsentDecision,
): Promise<PatronConsentRecord> {
  return api.post(
    `${API_BASE}/parent-onboarding/patrons/${patronId}/consent/family-snapshot`,
    decision,
  )
}
