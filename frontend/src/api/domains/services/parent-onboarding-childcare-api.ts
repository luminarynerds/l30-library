/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Parent Onboarding — Emergency Childcare API client (Component 4).
 *
 * Extracted from parent-onboarding-api.ts. Zero behaviour change — pure file move.
 */
import api from '@/lib/api-client';
import { API_BASE } from '@/api/types'

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

export type ChildcareSessionStatus =
  | 'available'
  | 'full'
  | 'in_progress'
  | 'completed'
  | 'cancelled';

export type ChildcareRegistrationStatus =
  | 'registered'
  | 'checked_in'
  | 'checked_out'
  | 'no_show'
  | 'cancelled';

// Matches backend `ChildcareSessionResponse` in
// app/schemas/parent_onboarding.py. The PREVIOUS shape of this interface
// (name / location / capacity / description / age_range_min / age_range_max
// / staff_assigned / notes) did not match the backend response and would
// render `undefined` on every card -- the prod page worked only because
// the childcare_sessions table was empty. Field names + units MUST stay
// aligned with `ChildcareSessionResponse` since the backend uses
// `extra="forbid"` on input schemas (memory:
// `feedback_l30_openapi_handwritten_drift`).
export interface ChildcareSession {
  id: number;
  branch_id: number;
  room_id?: number | null;
  staff_id?: number | null;
  date: string;
  start_time: string;
  end_time: string;
  max_children: number;
  age_range_min_months: number;
  age_range_max_months: number;
  status: ChildcareSessionStatus;
  registered_count: number;
  created_at?: string | null;
}

export interface AuthorizedPickupEntry {
  name: string;
  phone: string;
  relationship: string;
  id_required: boolean;
}

// Matches backend `ChildcareRegistrationResponse` in
// app/schemas/parent_onboarding.py. Field names + units must stay in sync
// with the server contract; the backend uses `extra="forbid"` on input
// schemas so any drift on the create path is a 422, not a silent drop.
export interface ChildcareRegistration {
  id: number;
  session_id: number;
  patron_id: number;
  patron_name?: string;
  child_name: string;
  // Age in MONTHS, 0-60 (capped at 5 years to match the session age band).
  child_age_months: number;
  status: ChildcareRegistrationStatus;
  special_needs_notes?: string | null;
  emergency_contact_name: string;
  emergency_contact_phone: string;
  checked_in_at?: string | null;
  checked_out_at?: string | null;
  created_at?: string | null;
  authorized_pickup?: AuthorizedPickupEntry[];
  checked_out_by_name?: string | null;
  checked_out_by_phone?: string | null;
  pickup_override_reason?: string | null;
  // Staff-side audit fields populated by the roster check-in flow.
  // Distinct from checked_out_by_name (the *adult* picking up).
  checked_in_by_staff_id?: number | null;
  checked_out_by_staff_id?: number | null;
  no_show_flagged_by_staff_id?: number | null;
  no_show_flagged_at?: string | null;
  no_show_reason?: string | null;
}

export interface ChildcareRosterEntry {
  registration: ChildcareRegistration;
  parent_name: string;
  parent_email?: string | null;
  // Pre-resolved staff display names; null when the FK is NULL or the
  // staff account was deleted (FK is ON DELETE SET NULL).
  checked_in_by_name?: string | null;
  checked_out_by_staff_name?: string | null;
  no_show_flagged_by_name?: string | null;
}

export interface ChildcareRosterCounts {
  registered: number;
  checked_in: number;
  checked_out: number;
  no_show: number;
  cancelled: number;
}

export interface ChildcareRosterResponse {
  session_id: number;
  entries: ChildcareRosterEntry[];
  // Optional only for backward-compat with the original #1037 shape; the
  // server now always populates it.
  counts?: ChildcareRosterCounts;
}

// ============================================================================
// Childcare API
// ============================================================================

// Request payload mirrors backend `ChildcareSessionCreate`
// (StrictInputSchema, extra="forbid"). DO NOT add fields here that the
// backend schema does not accept -- doing so will 422 every submission
// (memory: `feedback_l30_openapi_handwritten_drift`).
//
// Time fields are HH:MM strings (regex-validated server-side). Age fields
// are MONTHS (0-60 is the practical band). `max_children` is bounded
// 1..20 by the backend; surface inline validation rather than relying on
// the 422 to bubble up.
export async function createChildcareSession(data: {
  branch_id: number;
  room_id?: number | null;
  staff_id?: number | null;
  date: string;
  start_time: string;
  end_time: string;
  max_children?: number;
  age_range_min_months?: number;
  age_range_max_months?: number;
}): Promise<ChildcareSession> {
  return api.post<ChildcareSession>(`${API_BASE}/parent-onboarding/childcare/sessions`, data);
}

export async function listChildcareSessions(params?: {
  status?: ChildcareSessionStatus;
  branch_id?: number;
  from_date?: string;
  to_date?: string;
  limit?: number;
  offset?: number;
}): Promise<{ sessions: ChildcareSession[]; total: number }> {
  return api.get(`${API_BASE}/parent-onboarding/childcare/sessions${buildQueryString(params)}`);
}

// PATCH on the session itself. Backend wires this to the previously
// orphaned `ChildcareSessionUpdate` schema and gates on `require_library_admin`
// (STRICT -- only LIBRARY_ADMIN passes; ADMIN / SUPER_ADMIN / DIRECTOR do
// NOT, by design; see app/api/v1/dependencies.py). `branch_id` and `date`
// are immutable post-create and the schema doesn't expose them.
export async function updateChildcareSession(sessionId: number, data: {
  room_id?: number | null;
  staff_id?: number | null;
  start_time?: string;
  end_time?: string;
  max_children?: number;
  status?: ChildcareSessionStatus;
}): Promise<ChildcareSession> {
  return api.patch<ChildcareSession>(
    `${API_BASE}/parent-onboarding/childcare/sessions/${sessionId}`,
    data,
  );
}

// Request payload mirrors backend `ChildcareRegistrationCreate`
// (StrictInputSchema, extra="forbid"). DO NOT add fields here that the
// backend schema does not accept -- doing so will 422 every submission.
// Age is MONTHS (0-60); callers should convert from a years-facing input.
export async function registerForChildcare(sessionId: number, data: {
  child_name: string;
  child_age_months: number;
  special_needs_notes?: string;
  emergency_contact_name: string;
  emergency_contact_phone: string;
  authorized_pickup?: AuthorizedPickupEntry[];
}): Promise<ChildcareRegistration> {
  return api.post<ChildcareRegistration>(`${API_BASE}/parent-onboarding/childcare/sessions/${sessionId}/register`, data);
}

export async function updateChildcareRegistration(registrationId: number, data: {
  status?: ChildcareRegistrationStatus;
  special_needs_notes?: string;
  authorized_pickup?: AuthorizedPickupEntry[];
  // no_show_reason is only meaningful when status === "no_show"; the
  // backend silently drops it for any other transition.
  no_show_reason?: string;
}): Promise<ChildcareRegistration> {
  return api.patch<ChildcareRegistration>(`${API_BASE}/parent-onboarding/childcare/registrations/${registrationId}`, data);
}

export async function getChildcareRoster(sessionId: number): Promise<ChildcareRosterResponse> {
  return api.get<ChildcareRosterResponse>(`${API_BASE}/parent-onboarding/childcare/sessions/${sessionId}/roster`);
}

export async function checkoutChildcareRegistration(
  registrationId: number,
  data: {
    picked_up_by_name: string;
    picked_up_by_phone: string;
    staff_override_reason?: string;
  },
): Promise<ChildcareRegistration> {
  return api.post<ChildcareRegistration>(
    `${API_BASE}/parent-onboarding/childcare/registrations/${registrationId}/checkout`,
    data,
  );
}
