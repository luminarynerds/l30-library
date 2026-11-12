/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
// ==================== Board Member Types ====================

export interface BoardMember {
  id: number
  user_id: number | null
  full_name: string
  email: string | null
  phone: string | null
  position: string
  term_start_date: string
  term_end_date: string | null
  is_current: boolean
  bio: string | null
  photo_url: string | null
  public_email: string | null
  office_hours: string | null
  created_at: string
  updated_at: string | null
}

export interface BoardMemberCreate {
  full_name: string
  email?: string | null
  phone?: string | null
  position?: string
  term_start_date: string
  term_end_date?: string | null
  is_current?: boolean
  bio?: string | null
  photo_url?: string | null
  public_email?: string | null
  office_hours?: string | null
}

export interface BoardMemberUpdate {
  full_name?: string
  email?: string | null
  phone?: string | null
  position?: string
  term_start_date?: string
  term_end_date?: string | null
  is_current?: boolean
  bio?: string | null
  photo_url?: string | null
  public_email?: string | null
  office_hours?: string | null
}

// ==================== Board Meeting Types ====================

export interface BoardMeeting {
  id: number
  meeting_type: string
  title: string
  description: string | null
  scheduled_date: string
  start_time: string | null
  end_time: string | null
  location: string | null
  is_virtual: boolean
  virtual_meeting_url: string | null
  is_cancelled: boolean
  cancellation_reason: string | null
  quorum_met: boolean | null
  minutes_approved: boolean
  public_comment_enabled: boolean
  public_comment_instructions: string | null
  accessibility_info: string | null
  has_executive_session: boolean
  executive_session_reason: string | null
  notice_lead_days_required: number
  notice_status: string
  notice_posted_at: string | null
  notice_posted_by_id: number | null
  notice_posting_locations: NoticePostingLocation[]
  notice_document_id: number | null
  agenda_published_at: string | null
  agenda_published_by_id: number | null
  created_at: string
  created_by_id: number
  updated_at: string | null
}

export interface BoardMeetingCreate {
  meeting_type?: string
  title: string
  description?: string | null
  scheduled_date: string
  start_time?: string | null
  end_time?: string | null
  location?: string | null
  is_virtual?: boolean
  virtual_meeting_url?: string | null
  public_comment_enabled?: boolean
  public_comment_instructions?: string | null
  accessibility_info?: string | null
  has_executive_session?: boolean
  executive_session_reason?: string | null
  notice_lead_days_required?: number
}

export interface BoardMeetingUpdate {
  meeting_type?: string
  title?: string
  description?: string | null
  scheduled_date?: string
  start_time?: string | null
  end_time?: string | null
  location?: string | null
  is_virtual?: boolean
  virtual_meeting_url?: string | null
  public_comment_enabled?: boolean
  public_comment_instructions?: string | null
  accessibility_info?: string | null
  has_executive_session?: boolean
  executive_session_reason?: string | null
  notice_lead_days_required?: number
}

// ==================== Agenda Item Types ====================

export interface AgendaItem {
  id: number
  meeting_id: number
  item_number: string
  title: string
  description: string | null
  presenter: string | null
  estimated_duration_minutes: number | null
  sort_order: number
  requires_action: boolean
  action_type: string | null
  action_taken: string | null
  vote_result: string | null
  created_at: string
  updated_at: string | null
}

export interface AgendaItemCreate {
  item_number: string
  title: string
  description?: string | null
  presenter?: string | null
  estimated_duration_minutes?: number | null
  sort_order?: number
  requires_action?: boolean
  action_type?: string | null
}

// ==================== Board Minutes Types ====================

export interface BoardMinutes {
  id: number
  meeting_id: number
  status: string
  sections: unknown[]
  meeting_called_to_order_at: string | null
  meeting_adjourned_at: string | null
  members_present: unknown[]
  members_absent: unknown[]
  members_excused: unknown[]
  guests_present: unknown[]
  quorum_met: boolean | null
  quorum_count: string | null
  recording_url: string | null
  notes: string | null
  public_notes: string | null
  approved: boolean
  approved_at: string | null
  approved_by_id: number | null
  approval_vote_result: string | null
  published_at: string | null
  published_by_id: number | null
  created_at: string
  updated_at: string | null
}

export interface BoardMinutesCreate {
  status?: string
  sections?: unknown[]
  meeting_called_to_order_at?: string | null
  meeting_adjourned_at?: string | null
  members_present?: unknown[]
  members_absent?: unknown[]
  members_excused?: unknown[]
  guests_present?: unknown[]
  quorum_met?: boolean | null
  quorum_count?: string | null
  recording_url?: string | null
  notes?: string | null
  public_notes?: string | null
}

// ==================== Board Vote Types ====================

export interface BoardVote {
  id: number
  meeting_id: number | null
  title: string
  description: string
  vote_type: string
  opens_at: string
  closes_at: string
  quorum_required: number
  status: string
  passed: boolean | null
  final_tally_yes: number
  final_tally_no: number
  final_tally_abstain: number
  closed_at_actual: string | null
  closed_by_id: number | null
  created_at: string
  created_by_id: number
  updated_at: string | null
}

export interface BoardVoteCreate {
  title: string
  description: string
  vote_type?: string
  opens_at: string
  closes_at: string
  quorum_required?: number
  meeting_id?: number | null
}

export type VoteChoice = 'yes' | 'no' | 'abstain'

export interface VoteCastCreate {
  choice: VoteChoice
  comment?: string | null
}

export interface VoteCastResponse {
  id: number
  vote_id: number
  board_member_id: number
  choice: string
  comment: string | null
  cast_at: string
}

export interface VoteCloseResult {
  message: string
  passed: boolean
  quorum_met: boolean
  members_participating: number
  yes: number
  no: number
  abstain: number
}

// ==================== Board Document Types ====================

export interface BoardDocument {
  id: number
  meeting_id: number | null
  document_type: string
  title: string
  description: string | null
  filename: string
  file_path: string
  file_size_bytes: number | null
  mime_type: string | null
  is_public: boolean
  status: string
  published_date: string | null
  published_by_id: number | null
  view_count: number
  download_count: number
  created_at: string
  updated_at: string | null
}

export interface BoardDocumentCreate {
  document_type: string
  title: string
  description?: string | null
  filename: string
  file_path: string
  file_size_bytes?: number | null
  mime_type?: string | null
  is_public?: boolean
  meeting_id?: number | null
}

// ==================== Document Version Types ====================

export interface DocumentVersion {
  id: number
  document_id: number
  version_number: number
  file_url: string
  file_size: number | null
  file_type: string | null
  change_notes: string | null
  created_by_id: number | null
  created_at: string
}

export interface DocumentVersionCreate {
  file_url: string
  file_size?: number | null
  file_type?: string | null
  change_notes?: string | null
}

// ==================== Meeting Brief Types ====================

export interface MeetingBrief {
  id: number
  meeting_id: number
  status: string
  brief_content: string | null
  key_discussion_points: unknown[] | null
  recommended_questions: unknown[] | null
  background_context: string | null
  model_used: string | null
  generation_time_ms: number | null
  error_message: string | null
  created_at: string
}

// ==================== Attendance Types ====================

export type AttendanceStatus = 'present' | 'tardy' | 'left_early' | 'absent' | 'excused'
export type RsvpStatus = 'no_response' | 'attending' | 'not_attending' | 'tentative'

export interface Attendance {
  id: number
  meeting_id: number
  user_id: number
  rsvp_status: RsvpStatus
  rsvp_notes: string | null
  is_voting_member: boolean
  is_guest: boolean
  guest_affiliation: string | null
  attendance_status: AttendanceStatus | null
  checked_in_at: string | null
  checked_out_at: string | null
  attended_remotely: boolean
  remote_connection_method: string | null
  absence_reason: string | null
  rsvp_at: string | null
  created_at: string
  updated_at: string | null
}

export interface AttendanceCreate {
  user_id: number
  rsvp_status?: RsvpStatus
  rsvp_notes?: string | null
  is_voting_member?: boolean
  is_guest?: boolean
  guest_affiliation?: string | null
}

export interface AttendanceCheckIn {
  attendance_status?: 'present' | 'tardy' | 'left_early'
  attended_remotely?: boolean
  remote_connection_method?: string | null
}

// ==================== Action Item Types ====================

export type ActionItemStatus = 'not_started' | 'in_progress' | 'completed' | 'cancelled' | 'on_hold'
export type ActionItemPriority = 'low' | 'medium' | 'high' | 'critical'

export interface ActionItem {
  id: number
  meeting_id: number
  agenda_item_id: number | null
  title: string
  description: string | null
  assigned_to_id: number | null
  assigned_to_name: string | null
  assigned_by_id: number | null
  priority: ActionItemPriority
  due_date: string | null
  status: ActionItemStatus
  progress_percentage: number
  notes: string | null
  requires_board_update: boolean
  board_update_provided: boolean
  board_update_meeting_id: number | null
  completed_at: string | null
  created_at: string
  updated_at: string | null
}

export interface ActionItemCreate {
  title: string
  description?: string | null
  assigned_to_name?: string | null
  priority?: ActionItemPriority
  due_date?: string | null
  requires_board_update?: boolean
  agenda_item_id?: number | null
  assigned_to_id?: number | null
}

export interface ActionItemUpdate {
  title?: string
  description?: string | null
  assigned_to_id?: number | null
  assigned_to_name?: string | null
  priority?: ActionItemPriority
  due_date?: string | null
  progress_percentage?: number
  notes?: string | null
  requires_board_update?: boolean
}

export interface ActionItemStatusUpdate {
  status: ActionItemStatus
  notes?: string | null
}

// ==================== Notice Types ====================

export interface NoticePostingLocation {
  location: string
  url?: string | null
  posted_at?: string | null
  notes?: string | null
}

export interface NoticeGenerateRequest {
  include_agenda?: boolean
  include_accessibility_info?: boolean
  custom_header?: string | null
  custom_footer?: string | null
}

export interface NoticeResponse {
  meeting_id: number
  notice_content: string
  generated_at: string
  includes_agenda: boolean
  includes_accessibility_info: boolean
}

export interface NoticePostRequest {
  location: string
  url?: string | null
  notes?: string | null
}

export interface NoticePostResult {
  message: string
  notice_status: string
  posting_locations: NoticePostingLocation[]
}

export interface NoticePublishResult {
  message: string
  notice_status: string
  notice_posted_at: string
}

// ==================== Meeting Search Types ====================

export interface MeetingSearchParams {
  q?: string
  meeting_type?: string
  status?: string
  date_from?: string
  date_to?: string
  has_recording?: boolean
  committee_id?: number
  skip?: number
  limit?: number
}

export interface MeetingSearchResponse {
  results: BoardMeeting[]
  total: number
  skip: number
  limit: number
}
