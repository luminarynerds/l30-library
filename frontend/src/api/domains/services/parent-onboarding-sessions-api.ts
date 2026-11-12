/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Sessions and Care Assignments API client for the parent-onboarding subdomain.
 *
 * Extracted from parent-onboarding-api.ts (pure move, no logic changes).
 * Re-exported from parent-onboarding-api.ts barrel.
 */
import api from '@/lib/api-client';
import { API_BASE } from '@/api/types'

// ============================================================================
// Helper Functions
// ============================================================================

function buildQueryString(params?: Record<string, unknown>): string {
  if (!params) return '';
  const searchParams = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null) {
      searchParams.append(key, String(value));
    }
  });
  const queryString = searchParams.toString();
  return queryString ? `?${queryString}` : '';
}

// ============================================================================
// Types
// ============================================================================

export type ParentOnboardingStatus =
  | 'scheduled'
  | 'in_progress'
  | 'completed'
  | 'cancelled'
  | 'no_show';

export type CareAssignmentStatus =
  | 'active'
  | 'paused'
  | 'completed'
  | 'transferred';

export type CheckInFrequency =
  | 'weekly'
  | 'biweekly'
  | 'monthly';

export type RiskLevel =
  | 'low'
  | 'medium'
  | 'high';

export interface ParentOnboardingSession {
  id: number;
  patron_id: number;
  patron_name?: string;
  coordinator_id?: number;
  coordinator_name?: string;
  status: ParentOnboardingStatus;
  session_type: string;
  scheduled_date: string;
  scheduled_time?: string;
  duration_minutes?: number;
  location?: string;
  notes?: string;
  outcomes?: string;
  resources_provided?: string[];
  referrals_made?: string[];
  follow_up_date?: string;
  created_at: string;
  updated_at?: string;
}

// ============================================================================
// Session detail (matches ParentOnboardingSessionResponse in
// backend/app/schemas/parent_onboarding.py -- the actual columns on
// parent_onboarding_sessions). Used by the session detail page's
// get/update/complete calls. Deliberately NOT the same shape as
// `ParentOnboardingSession` above, which reflects the dashboard's
// recent_sessions summary and predates this reconciliation.
// ============================================================================

export interface ParentOnboardingSessionDetail {
  id: number;
  patron_id: number;
  staff_id?: number | null;
  branch_id: number;
  status: ParentOnboardingStatus;
  scheduled_at: string;
  completed_at?: string | null;
  baby_age_months?: number | null;
  languages_spoken: string[];
  family_situation_notes?: string | null;
  needs_identified: Record<string, unknown>[];
  services_referred: Record<string, unknown>[];
  welcome_packet_id?: number | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface CareCoordinatorAssignment {
  id: number;
  patron_id: number;
  patron_name?: string;
  coordinator_id: number;
  coordinator_name?: string;
  status: CareAssignmentStatus;
  risk_level: RiskLevel;
  check_in_frequency: CheckInFrequency;
  assigned_at: string;
  last_check_in?: string;
  next_check_in_due?: string;
  total_check_ins: number;
  notes?: string;
  goals?: string[];
  transferred_from_id?: number;
  transferred_reason?: string;
}

export interface CareCheckIn {
  id: number;
  assignment_id: number;
  coordinator_id: number;
  coordinator_name?: string;
  check_in_date: string;
  method: string;
  risk_level: RiskLevel;
  mood_assessment?: string;
  needs_identified?: string[];
  actions_taken?: string[];
  referrals_made?: string[];
  follow_up_needed: boolean;
  follow_up_notes?: string;
  notes?: string;
  created_at: string;
}

// ============================================================================
// Sessions API
// ============================================================================

export async function createSession(data: {
  patron_id: number;
  session_type: string;
  scheduled_date: string;
  scheduled_time?: string;
  duration_minutes?: number;
  location?: string;
  notes?: string;
}): Promise<ParentOnboardingSession> {
  return api.post<ParentOnboardingSession>(`${API_BASE}/parent-onboarding/sessions`, data);
}

export async function listSessions(params?: {
  status?: ParentOnboardingStatus;
  patron_id?: number;
  coordinator_id?: number;
  date_from?: string;
  date_to?: string;
  search?: string;
  limit?: number;
  offset?: number;
}): Promise<{ sessions: ParentOnboardingSession[]; total: number }> {
  return api.get(`${API_BASE}/parent-onboarding/sessions${buildQueryString(params)}`);
}

export async function getSession(id: number): Promise<ParentOnboardingSessionDetail> {
  return api.get(`${API_BASE}/parent-onboarding/sessions/${id}`);
}

export async function updateSession(id: number, data: {
  staff_id?: number | null;
  scheduled_at?: string;
  status?: ParentOnboardingStatus;
  baby_age_months?: number | null;
  languages_spoken?: string[];
  family_situation_notes?: string | null;
  needs_identified?: Record<string, unknown>[];
  services_referred?: Record<string, unknown>[];
  welcome_packet_id?: number | null;
}): Promise<ParentOnboardingSessionDetail> {
  return api.patch<ParentOnboardingSessionDetail>(`${API_BASE}/parent-onboarding/sessions/${id}`, data);
}

export async function completeSession(id: number, data: {
  family_situation_notes?: string | null;
  needs_identified?: Record<string, unknown>[];
  services_referred?: Record<string, unknown>[];
  welcome_packet_id?: number | null;
}): Promise<ParentOnboardingSessionDetail> {
  return api.post<ParentOnboardingSessionDetail>(`${API_BASE}/parent-onboarding/sessions/${id}/complete`, data);
}

// ============================================================================
// Care Assignments API
// ============================================================================

export async function createCareAssignment(data: {
  patron_id: number;
  coordinator_id: number;
  risk_level?: RiskLevel;
  check_in_frequency?: CheckInFrequency;
  notes?: string;
  goals?: string[];
}): Promise<CareCoordinatorAssignment> {
  return api.post<CareCoordinatorAssignment>(`${API_BASE}/parent-onboarding/care-assignments`, data);
}

export async function listCareAssignments(params?: {
  status?: CareAssignmentStatus;
  coordinator_id?: number;
  risk_level?: RiskLevel;
  overdue_check_in?: boolean;
  search?: string;
  limit?: number;
  offset?: number;
}): Promise<{ assignments: CareCoordinatorAssignment[]; total: number }> {
  return api.get(`${API_BASE}/parent-onboarding/care-assignments${buildQueryString(params)}`);
}

export async function getCareAssignment(id: number): Promise<CareCoordinatorAssignment> {
  return api.get(`${API_BASE}/parent-onboarding/care-assignments/${id}`);
}

export async function updateCareAssignment(id: number, data: Partial<CareCoordinatorAssignment>): Promise<CareCoordinatorAssignment> {
  return api.patch<CareCoordinatorAssignment>(`${API_BASE}/parent-onboarding/care-assignments/${id}`, data);
}

export async function createCheckIn(assignmentId: number, data: {
  method: string;
  risk_level?: RiskLevel;
  mood_assessment?: string;
  needs_identified?: string[];
  actions_taken?: string[];
  referrals_made?: string[];
  follow_up_needed?: boolean;
  follow_up_notes?: string;
  notes?: string;
}): Promise<CareCheckIn> {
  return api.post<CareCheckIn>(`${API_BASE}/parent-onboarding/care-assignments/${assignmentId}/check-ins`, data);
}

export async function listCheckIns(assignmentId: number, params?: {
  limit?: number;
  offset?: number;
}): Promise<{ check_ins: CareCheckIn[]; total: number }> {
  return api.get(`${API_BASE}/parent-onboarding/care-assignments/${assignmentId}/check-ins${buildQueryString(params)}`);
}
