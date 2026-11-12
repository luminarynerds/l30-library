/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Parent Onboarding — Connection Groups API client.
 *
 * Pure move from parent-onboarding-api.ts.  Re-exported from the barrel so
 * existing component imports keep working unchanged.
 */
import api from '@/lib/api-client';
import { API_BASE } from '@/api/types'

// ============================================================================
// Helper Functions (local copy — identical to parent-onboarding-api.ts)
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

export type ConnectionGroupType =
  | 'first_time_parents'
  | 'teen_parents'
  | 'single_parents'
  | 'postpartum_support'
  | 'general';

export type MeetingFrequency = 'weekly' | 'biweekly' | 'monthly';

export interface ParentConnectionGroup {
  id: number;
  name: string;
  description?: string;
  group_type: ConnectionGroupType;
  // Confidentiality-stripped: facilitator + member-count keys MAY be absent
  // on confidential groups when caller is non-staff. Treat undefined as
  // "do not render" rather than 0/null.
  facilitator_id?: number;
  facilitator_name?: string;
  branch_id?: number;
  meeting_schedule?: string;
  meeting_location?: string;
  meeting_frequency?: MeetingFrequency;
  meeting_day_of_week?: string | null;
  meeting_time?: string | null;
  location?: string | null;
  languages?: string[];
  max_members: number;
  current_members?: number;
  member_count?: number;
  is_active: boolean;
  next_meeting_date?: string;
  topics?: string[];
  created_at: string;
  // Confidentiality config (always present; may be false).
  confidential?: boolean;
  confidential_card_description?: string | null;
  confidential_approval_message?: string | null;
  estimated_response_window_hours?: number;
  // Lifecycle (cg_lifecycle_001).
  cohort_start_date?: string | null;
  cohort_end_date?: string | null;
  archived_at?: string | null;
  archived_by_id?: number | null;
  archive_reason?: string | null;
  archive_notes?: string | null;
}

export interface ConfidentialJoinRequestResult {
  id: number;
  group_id: number;
  patron_id: number;
  status: 'pending_approval' | 'active' | 'waitlisted' | 'denied';
  requested_at: string;
  requested_by_id: number;
  estimated_response_window_hours: number;
  email_partial?: boolean;
}

export interface ApprovalQueueEntry {
  id: number;
  group_id: number;
  group_name: string;
  patron_id: number;
  patron_name?: string | null;
  patron_contact_visible: boolean;
  patron_email?: string | null;
  patron_phone?: string | null;
  request_message?: string | null;
  requested_at: string;
  days_pending: number;
}

export interface ApprovalDecisionLogEntry {
  id: number;
  patron_name?: string | null;
  decision: 'active' | 'waitlisted' | 'denied';
  decided_at: string;
  decided_by_id?: number | null;
  decided_by_name?: string | null;
}

export interface ApprovalQueueResult {
  pending: ApprovalQueueEntry[];
  approval_decision_log: ApprovalDecisionLogEntry[];
}

export interface DecideRequestResult {
  id: number;
  group_id: number;
  patron_id: number;
  status: 'active' | 'waitlisted' | 'denied' | 'pending_approval';
  decided_at: string;
  decided_by_id: number;
  email_partial?: boolean;
}

export interface GroupMemberDetail {
  id: number;
  group_id: number;
  patron_id: number;
  patron_name?: string | null;
  status: 'active' | 'waitlisted' | 'inactive';
  joined_date: string;
  left_date?: string | null;
  attendance_count: number;
  enrolled_by_id?: number | null;
  enrolled_by_name?: string | null;
  capacity_override?: boolean;
}

export interface EnrollMemberResponse {
  id: number;
  group_id: number;
  patron_id: number;
  patron_name?: string | null;
  status: 'active' | 'waitlisted' | 'inactive';
  joined_date: string;
  enrolled_by_id?: number | null;
  enrolled_by_name?: string | null;
  consent_note_recorded: boolean;
  capacity_overridden: boolean;
}

export type RemovalReason =
  | 'patron_request'
  | 'attendance_lapse'
  | 'safety'
  | 'program_ended'
  | 'other';

export interface ConnectionGroupCreatePayload {
  name: string;
  description?: string;
  group_type: ConnectionGroupType;
  facilitator_id?: number;
  branch_id: number;
  meeting_frequency?: MeetingFrequency;
  meeting_day_of_week?: string | null;
  meeting_time?: string | null;
  location?: string | null;
  languages?: string[];
  max_members?: number;
  confidential?: boolean;
  confidential_card_description?: string | null;
  confidential_approval_message?: string | null;
  estimated_response_window_hours?: number;
  cohort_start_date?: string | null;
  cohort_end_date?: string | null;
}

export interface ConnectionGroupUpdatePayload extends Partial<Omit<ConnectionGroupCreatePayload, 'branch_id'>> {
  is_active?: boolean;
}

export interface GroupMeeting {
  id: number;
  group_id: number;
  meeting_date: string;
  scheduled_time?: string | null;
  location?: string | null;
  status: MeetingStatus;
  cancelled_reason?: string | null;
  cancelled_at?: string | null;
  cancelled_by_id?: number | null;
  rescheduled_to_meeting_id?: number | null;
  staff_notes?: string | null;
  patron_message?: string | null;
  email_dispatched_at?: string | null;
  email_dispatched_count?: number;
}

export interface GroupMeetingsListResponse {
  meetings: GroupMeeting[];
  total: number;
}

export type CancelMeetingReason =
  | 'facilitator_sick'
  | 'venue_unavailable'
  | 'weather'
  | 'low_rsvp'
  | 'other';

export type MeetingStatus = 'scheduled' | 'cancelled' | 'rescheduled' | 'completed';

export interface CancelMeetingRequest {
  reason: CancelMeetingReason;
  notes?: string;
  patron_message?: string;
}

export interface RescheduleMeetingRequest {
  new_date: string;
  new_time?: string | null;
  new_location?: string | null;
  notes?: string;
  patron_message?: string;
}

export interface MeetingDispatchResponse {
  meeting: GroupMeeting;
  new_meeting?: GroupMeeting | null;
  notified_member_count: number;
  email_dispatched: boolean;
  email_partial: boolean;
}

export type ArchiveReason =
  | 'cohort_complete'
  | 'low_attendance'
  | 'facilitator_departed'
  | 'other';

export interface ArchiveGroupRequest {
  archive_reason: ArchiveReason;
  archive_notes?: string;
  notify_members?: boolean;
  patron_message?: string;
}

export interface ArchiveGroupResponse {
  id: number;
  is_active: boolean;
  archived_at?: string | null;
  archived_by_id?: number | null;
  archive_reason?: string | null;
  archive_notes?: string | null;
  notified_member_count?: number;
  email_dispatched?: boolean;
  email_partial?: boolean;
}


// ============================================================================
// Connection Groups API
// ============================================================================





export async function createConnectionGroup(
  data: ConnectionGroupCreatePayload,
): Promise<ParentConnectionGroup> {
  return api.post<ParentConnectionGroup>(`${API_BASE}/parent-onboarding/connection-groups`, data);
}

export async function updateConnectionGroup(
  groupId: number,
  data: ConnectionGroupUpdatePayload,
): Promise<ParentConnectionGroup> {
  return api.patch<ParentConnectionGroup>(
    `${API_BASE}/parent-onboarding/connection-groups/${groupId}`,
    data,
  );
}





export async function archiveConnectionGroup(
  groupId: number,
  payload: ArchiveGroupRequest,
): Promise<ArchiveGroupResponse> {
  return api.post<ArchiveGroupResponse>(
    `${API_BASE}/parent-onboarding/connection-groups/${groupId}/archive`,
    payload,
  );
}

export async function unarchiveConnectionGroup(
  groupId: number,
): Promise<ArchiveGroupResponse> {
  return api.post<ArchiveGroupResponse>(
    `${API_BASE}/parent-onboarding/connection-groups/${groupId}/unarchive`,
    {},
  );
}











export async function listConnectionGroupMeetings(
  groupId: number,
): Promise<GroupMeetingsListResponse> {
  return api.get<GroupMeetingsListResponse>(
    `${API_BASE}/parent-onboarding/connection-groups/${groupId}/meetings`,
  );
}

export async function cancelConnectionGroupMeeting(
  groupId: number,
  meetingId: number,
  payload: CancelMeetingRequest,
): Promise<MeetingDispatchResponse> {
  return api.post<MeetingDispatchResponse>(
    `${API_BASE}/parent-onboarding/connection-groups/${groupId}/meetings/${meetingId}/cancel`,
    payload,
  );
}

export async function rescheduleConnectionGroupMeeting(
  groupId: number,
  meetingId: number,
  payload: RescheduleMeetingRequest,
): Promise<MeetingDispatchResponse> {
  return api.post<MeetingDispatchResponse>(
    `${API_BASE}/parent-onboarding/connection-groups/${groupId}/meetings/${meetingId}/reschedule`,
    payload,
  );
}

export async function listConnectionGroups(params?: {
  group_type?: ConnectionGroupType;
  is_active?: boolean;
  has_availability?: boolean;
  search?: string;
  limit?: number;
  offset?: number;
}): Promise<{ groups: ParentConnectionGroup[]; total: number }> {
  return api.get(`${API_BASE}/parent-onboarding/connection-groups${buildQueryString(params)}`);
}

export async function getConnectionGroup(id: number): Promise<ParentConnectionGroup> {
  return api.get(`${API_BASE}/parent-onboarding/connection-groups/${id}`);
}





export async function enrollPatronInGroup(
  groupId: number,
  payload: {
    patron_id: number;
    consent_note?: string;
    override_capacity?: boolean;
    override_justification?: string;
  },
): Promise<EnrollMemberResponse> {
  return api.post<EnrollMemberResponse>(
    `${API_BASE}/parent-onboarding/connection-groups/${groupId}/enroll`,
    payload,
  );
}

export async function listConnectionGroupMembers(
  groupId: number,
): Promise<{ members: GroupMemberDetail[]; active_count: number; waitlisted_count: number }> {
  return api.get(`${API_BASE}/parent-onboarding/connection-groups/${groupId}/members`);
}

export async function removeConnectionGroupMember(
  groupId: number,
  patronId: number,
  reason: RemovalReason,
): Promise<void> {
  // DELETE with reason= query param. The wrapper api client doesn'''t expose
  // delete-with-querystring sugar; build the URL inline.
  await api.delete(
    `${API_BASE}/parent-onboarding/connection-groups/${groupId}/members/${patronId}?reason=${encodeURIComponent(reason)}`,
  );
}

// ---------------------------------------------------------------------------
// Confidentiality + approval-gated waitlist
// ---------------------------------------------------------------------------

export async function requestToJoinConfidentialGroup(
  groupId: number,
  payload: {
    patron_id: number;
    request_message?: string;
    consent_to_share_contact?: boolean;
  },
): Promise<ConfidentialJoinRequestResult> {
  return api.post<ConfidentialJoinRequestResult>(
    `${API_BASE}/parent-onboarding/connection-groups/${groupId}/request`,
    payload,
  );
}

export async function getApprovalQueue(
  groupId: number,
): Promise<ApprovalQueueResult> {
  return api.get(
    `${API_BASE}/parent-onboarding/connection-groups/${groupId}/approval-queue`,
  );
}

export async function decideApprovalRequest(
  groupId: number,
  memberId: number,
  payload: {
    decision: 'approve' | 'deny';
    decision_note?: string;
    patron_message?: string;
  },
): Promise<DecideRequestResult> {
  return api.post<DecideRequestResult>(
    `${API_BASE}/parent-onboarding/connection-groups/${groupId}/approval-queue/${memberId}/decide`,
    payload,
  );
}

// Issues DELETE /api/v1/parent-onboarding/connection-groups/{group_id}/members/{user_id} —
// the only self-leave route the backend exposes (see PR #825). The 2-arg shape
// the vitest already asserts was dropped from #825's squash-merge; this restores it.
export async function leaveConnectionGroup(groupId: number, userId: number): Promise<void> {
  return api.delete<void>(`${API_BASE}/parent-onboarding/connection-groups/${groupId}/members/${userId}`);
}
