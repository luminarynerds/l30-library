/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Home Visits API client for the parent-onboarding subdomain.
 *
 * Extracted from parent-onboarding-api.ts (pure move, no logic changes).
 * Re-exported from parent-onboarding-api.ts barrel.
 */
import api from '@/lib/api-client';
import { API_BASE } from '@/api/types'
// ============================================================================
// Home Visit core types
// (moved here from parent-onboarding-api.ts; re-exported via the barrel)
// ============================================================================

export type HomeVisitPurpose =
  | 'intake'
  | 'resource_delivery'
  | 'check_in'
  | 'service_enrollment'
  | 'follow_up';

export type HomeVisitStatus =
  | 'scheduled'
  | 'confirmed'
  | 'completed'
  | 'cancelled'
  | 'rescheduled';

export interface ParentHomeVisit {
  id: number;
  patron_id: number;
  patron_name?: string;
  visitor_id: number;
  visitor_name?: string;
  purpose: HomeVisitPurpose;
  status: HomeVisitStatus;
  scheduled_date: string;
  scheduled_time?: string;
  address?: string;
  duration_minutes?: number;
  notes?: string;
  outcomes?: string;
  resources_delivered?: string[];
  follow_up_needed: boolean;
  follow_up_date?: string;
  completed_at?: string;
  cancelled_reason?: string;
  // Reschedule back-link id added by home_visit_mutations_001. The
  // older `rescheduled_to` string field is kept for back-compat (it was
  // a date) but new code should reach for `rescheduled_to_id` and look
  // up the replacement visit in the list.
  rescheduled_to?: string;
  rescheduled_to_id?: number | null;
  created_at: string;
  // Lone-worker safety check-in fields (feature flag: home_visit_safety_enabled).
  // All five are optional/nullable so old visits load without changes.
  safety_checkin_at?: string | null;
  safety_checkout_at?: string | null;
  safety_checkout_due_at?: string | null;
  safety_buddy_user_id?: number | null;
  safety_overdue_flagged_at?: string | null;
}

// ---- Status-mutation request/response types (home_visit_mutations_001) ----

export interface HomeVisitConfirmRequest {
  reason?: string;
}

export interface HomeVisitCompleteRequest {
  outcomes: string;
  resources_delivered: string[];
  follow_up_needed?: boolean;
  follow_up_date?: string;
  follow_up_notes?: string;
  referrals?: string[];
}

export interface HomeVisitCancelRequest {
  cancelled_reason: string;
  notify_acknowledged?: boolean;
}

export interface HomeVisitRescheduleRequest {
  new_scheduled_date: string;
  new_scheduled_time?: string;
  duration_minutes?: number;
  reason: string;
}

export interface HomeVisitRescheduleResult {
  visit: ParentHomeVisit;
  replacement_visit: ParentHomeVisit;
}

export interface HomeVisitConflictItem {
  id: number;
  scheduled_date: string;
  scheduled_time?: string;
  patron_id: number;
  patron_name?: string;
  status: HomeVisitStatus;
}

export interface HomeVisitConflictCheck {
  has_conflict: boolean;
  conflicting_visits: HomeVisitConflictItem[];
}

export interface HomeVisitStatusHistoryItem {
  id: number;
  visit_id: number;
  from_status?: HomeVisitStatus;
  to_status: HomeVisitStatus;
  changed_by_id?: number;
  changed_by_name?: string;
  changed_at: string;
  reason?: string;
  metadata_json?: Record<string, unknown> | null;
}

export interface HomeVisitStatusHistoryResult {
  history: HomeVisitStatusHistoryItem[];
  total: number;
}

export interface HomeVisitSafetyResponse {
  visit_id: number;
  safety_checkin_at?: string | null;
  safety_checkout_at?: string | null;
  safety_checkout_due_at?: string | null;
  safety_buddy_user_id?: number | null;
  buddy_warning?: string | null;
}

export interface OverdueHomeVisitSummary {
  visit_id: number;
  visitor_id?: number | null;
  visitor_name?: string | null;
  safety_buddy_user_id?: number | null;
  safety_buddy_name?: string | null;
  safety_checkin_at: string;
  safety_checkout_due_at: string;
  safety_overdue_flagged_at?: string | null;
  address?: string | null;
  scheduled_date: string;
  minutes_overdue: number;
}

// ============================================================================
// Home Visit Access Notes types
// (originally in parent-onboarding-api.ts Day Plan section; defined here so
//  consumers can import from either the barrel or this module)
// ============================================================================

export interface HomeVisitAccessNotes {
  has_steps: boolean;
  has_elevator: boolean;
  multi_floor: boolean;
  dog_on_premises: boolean;
  dog_safety_note?: string | null;
  primary_language?: string | null;
  needs_interpreter: boolean;
  buzzer_or_intercom?: string | null;
  parking_notes?: string | null;
  other_notes?: string | null;
  updated_at?: string | null;
  updated_by_id?: number | null;
}

export type HomeVisitAccessNotesUpsert = Partial<
  Omit<HomeVisitAccessNotes, 'updated_at' | 'updated_by_id'>
>;

export interface DayPlanLeg {
  drive_minutes: number;
  walk_minutes: number;
  distance_km: number;
  // 'osrm' = real routing; 'haversine' = great-circle fallback when OSRM
  // is unreachable. The UI surfaces this so staff know whether the ETA
  // is from a router or a guess.
  provider: 'osrm' | 'haversine';
}

export interface DayPlanStop {
  visit_id: number;
  sort_index: number;
  scheduled_time?: string | null;
  patron_id: number;
  patron_name?: string | null;
  address?: string | null;
  lat?: number | null;
  lng?: number | null;
  purpose: HomeVisitPurpose;
  status: HomeVisitStatus;
  access_notes?: HomeVisitAccessNotes | null;
  leg_from_previous?: DayPlanLeg | null;
  manual_order: boolean;
}

export interface DayPlanResponse {
  date: string; // YYYY-MM-DD
  visitor_id: number;
  stops: DayPlanStop[];
  total_drive_minutes: number;
  total_distance_km: number;
  // e.g. ['no_geocode_for_visit_42'] -- UI maps these to per-stop badges.
  warnings: string[];
}

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
// Home Visits API
// ============================================================================

export async function createHomeVisit(data: {
  patron_id: number;
  visitor_id: number;
  purpose: HomeVisitPurpose;
  scheduled_date: string;
  scheduled_time?: string;
  address?: string;
  duration_minutes?: number;
  notes?: string;
}): Promise<ParentHomeVisit> {
  return api.post<ParentHomeVisit>(`${API_BASE}/parent-onboarding/home-visits`, data);
}

export async function listHomeVisits(params?: {
  status?: HomeVisitStatus;
  patron_id?: number;
  visitor_id?: number;
  purpose?: HomeVisitPurpose;
  date_from?: string;
  date_to?: string;
  search?: string;
  limit?: number;
  offset?: number;
}): Promise<{ visits: ParentHomeVisit[]; total: number }> {
  return api.get(`${API_BASE}/parent-onboarding/home-visits${buildQueryString(params)}`);
}

export async function getHomeVisit(id: number): Promise<ParentHomeVisit> {
  return api.get(`${API_BASE}/parent-onboarding/home-visits/${id}`);
}

export async function updateHomeVisit(id: number, data: Partial<ParentHomeVisit>): Promise<ParentHomeVisit> {
  return api.patch<ParentHomeVisit>(`${API_BASE}/parent-onboarding/home-visits/${id}`, data);
}

// ----------------------------------------------------------------------------
// Status-mutation client functions (home_visit_mutations_001).
//
// These replace the dead `updateHomeVisitStatus` (POST .../status, which the
// backend never had a route for -- every call would 404). Each function maps
// 1:1 to a backend route that validates the transition, writes a history row,
// and emits a pii_access_log entry.
// ----------------------------------------------------------------------------

export async function confirmHomeVisit(
  visitId: number,
  data: HomeVisitConfirmRequest = {},
): Promise<ParentHomeVisit> {
  return api.post<ParentHomeVisit>(
    `${API_BASE}/parent-onboarding/home-visits/${visitId}/confirm`,
    data,
  );
}

export async function completeHomeVisitWithOutcomes(
  visitId: number,
  data: HomeVisitCompleteRequest,
): Promise<ParentHomeVisit> {
  return api.post<ParentHomeVisit>(
    `${API_BASE}/parent-onboarding/home-visits/${visitId}/complete-with-outcomes`,
    data,
  );
}

export async function cancelHomeVisit(
  visitId: number,
  data: HomeVisitCancelRequest,
): Promise<ParentHomeVisit> {
  return api.post<ParentHomeVisit>(
    `${API_BASE}/parent-onboarding/home-visits/${visitId}/cancel`,
    data,
  );
}

export async function rescheduleHomeVisit(
  visitId: number,
  data: HomeVisitRescheduleRequest,
): Promise<HomeVisitRescheduleResult> {
  return api.post<HomeVisitRescheduleResult>(
    `${API_BASE}/parent-onboarding/home-visits/${visitId}/reschedule`,
    data,
  );
}

export async function checkHomeVisitConflicts(params: {
  visitor_id: number;
  date: string;
  exclude_visit_id?: number;
}): Promise<HomeVisitConflictCheck> {
  return api.get<HomeVisitConflictCheck>(
    `${API_BASE}/parent-onboarding/home-visits/conflicts${buildQueryString(params)}`,
  );
}

export async function getHomeVisitStatusHistory(
  visitId: number,
  limit = 50,
): Promise<HomeVisitStatusHistoryResult> {
  return api.get<HomeVisitStatusHistoryResult>(
    `${API_BASE}/parent-onboarding/home-visits/${visitId}/history?limit=${limit}`,
  );
}

export async function getMyHomeVisits(params?: {
  status?: HomeVisitStatus;
  limit?: number;
  offset?: number;
}): Promise<{ visits: ParentHomeVisit[]; total: number }> {
  return api.get(`${API_BASE}/parent-onboarding/home-visits/my${buildQueryString(params)}`);
}

// ============================================================================
// Lone-worker safety check-in (feature flag: home_visit_safety_enabled)
// ============================================================================

export async function homeVisitSafetyCheckin(
  visitId: number,
  visitDurationMinutes: number,
): Promise<HomeVisitSafetyResponse> {
  return api.post<HomeVisitSafetyResponse>(
    `${API_BASE}/parent-onboarding/home-visits/${visitId}/safety-checkin`,
    { visit_duration_minutes: visitDurationMinutes },
  );
}

export async function homeVisitSafetyCheckout(
  visitId: number,
): Promise<HomeVisitSafetyResponse> {
  return api.post<HomeVisitSafetyResponse>(
    `${API_BASE}/parent-onboarding/home-visits/${visitId}/safety-checkout`,
    {},
  );
}

export async function listOverdueHomeVisits(): Promise<{
  visits: OverdueHomeVisitSummary[];
  total: number;
}> {
  return api.get(`${API_BASE}/parent-onboarding/home-visits/overdue`);
}

export interface EligibleSafetyBuddy {
  id: number;
  full_name: string;
}

export async function listEligibleSafetyBuddies(): Promise<EligibleSafetyBuddy[]> {
  return api.get(`${API_BASE}/parent-onboarding/home-visits/eligible-buddies`);
}

// ============================================================================
// Home Visit Day Plan (feature flag: home_visit_day_plan_enabled)
// ============================================================================

export async function getHomeVisitDayPlan(date: string): Promise<DayPlanResponse> {
  return api.get(
    `${API_BASE}/parent-onboarding/home-visits/day-plan${buildQueryString({ date })}`,
  );
}

export async function setHomeVisitDayPlanSort(
  visitId: number,
  sortIndex: number | null,
): Promise<DayPlanResponse> {
  return api.patch<DayPlanResponse>(
    `${API_BASE}/parent-onboarding/home-visits/${visitId}/day-plan-sort`,
    { sort_index: sortIndex },
  );
}

export async function geocodeHomeVisit(
  visitId: number,
  manual?: { lat: number; lng: number },
): Promise<ParentHomeVisit> {
  return api.post<ParentHomeVisit>(
    `${API_BASE}/parent-onboarding/home-visits/${visitId}/geocode`,
    manual ?? null,
  );
}

export async function getHomeVisitAccessNotes(
  patronId: number,
): Promise<HomeVisitAccessNotes> {
  return api.get(`${API_BASE}/parent-onboarding/home-visit-access-notes/${patronId}`);
}

export async function setHomeVisitAccessNotes(
  patronId: number,
  notes: HomeVisitAccessNotesUpsert,
): Promise<HomeVisitAccessNotes> {
  return api.put<HomeVisitAccessNotes>(
    `${API_BASE}/parent-onboarding/home-visit-access-notes/${patronId}`,
    notes,
  );
}
