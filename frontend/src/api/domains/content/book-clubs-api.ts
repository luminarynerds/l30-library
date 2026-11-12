/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { fetchApi } from '@/lib/api-client'
import { API_BASE } from '@/api/types'
import { getAccessToken } from '@/utils/tokenStore'

// ==================== Types ====================

export interface BookClubListItem {
  id: number
  name: string
  description: string | null
  genre: string | null
  meeting_frequency: string | null
  member_count: number
  max_members: number | null
  /**
   * Capacity signals (waitlist feature, PR #914). The backend ships
   * both `member_count` and `current_member_count` as mirrors today;
   * new UI converges on `current_member_count`.
   */
  current_member_count: number
  waitlist_count: number
  is_full: boolean
  current_book_title: string | null
  current_book_author: string | null
  is_member: boolean
  next_meeting_date: string | null
}

export interface BookClubDetail extends BookClubListItem {
  created_at: string
  /**
   * null = caller is not on the waitlist (or anonymous); 1-based FIFO
   * position otherwise. Omitted from list items (expensive at scale).
   */
  patron_waitlist_position: number | null
  // null when caller is anonymous; array (possibly empty) when authenticated.
  members: BookClubMemberInfo[] | null
  upcoming_meetings?: BookClubMeetingInfo[]
  meetings?: Array<{
    id: number
    title: string
    meeting_date: string
    location: string | null
    status: string
  }>
  status?: string
  is_public?: boolean
}

export interface BookClubMemberInfo {
  id: number
  user_id: number
  display_name?: string
  joined_at: string
  role: string
  book_club_id?: number
}

export interface BookClubMeetingInfo {
  id: number
  title: string | null
  scheduled_at: string
  location: string | null
  is_virtual: boolean
  discussion_count: number
}

export interface BookClubListResponse {
  clubs: BookClubListItem[]
  total: number
  page: number
  per_page: number
}

export interface DiscussionThread {
  id: number
  meeting_id: number
  user_id: number
  author_name: string
  title: string
  content: string
  created_at: string
  is_pinned: boolean
  reply_count: number
}

export interface DiscussionReply {
  id: number
  discussion_id: number
  user_id: number
  author_name: string
  content: string
  created_at: string
}

// ==================== API Functions ====================

export async function listBookClubs(params?: {
  genre?: string
  search?: string
  page?: number
  per_page?: number
}): Promise<BookClubListResponse> {
  const searchParams = new URLSearchParams()
  if (params?.genre) searchParams.set('genre', params.genre)
  if (params?.search) searchParams.set('search', params.search)
  if (params?.page) searchParams.set('page', String(params.page))
  if (params?.per_page) searchParams.set('per_page', String(params.per_page))
  const qs = searchParams.toString()
  return fetchApi<BookClubListResponse>(`/book-clubs${qs ? `?${qs}` : ''}`)
}

export async function listBookClubGenres(): Promise<string[]> {
  return fetchApi<string[]>('/book-clubs/genres')
}

export async function getBookClub(clubId: number): Promise<BookClubDetail> {
  return fetchApi<BookClubDetail>(`/book-clubs/${clubId}`)
}

export type BookClubJoinStatus =
  | 'joined'
  | 'waitlisted'
  | 'already_member'
  | 'already_waitlisted'
  | 'uncapped'
  | 'not_found'

export interface BookClubJoinResult {
  status: BookClubJoinStatus
  position: number | null
  success: boolean
}

export async function joinBookClub(clubId: number): Promise<BookClubJoinResult> {
  return fetchApi<BookClubJoinResult>(`/book-clubs/${clubId}/join`, { method: 'POST' })
}

export async function leaveBookClub(clubId: number): Promise<{ success: boolean }> {
  return fetchApi<{ success: boolean }>(`/book-clubs/${clubId}/leave`, { method: 'DELETE' })
}

export async function joinBookClubWaitlist(clubId: number): Promise<BookClubJoinResult> {
  return fetchApi<BookClubJoinResult>(`/book-clubs/${clubId}/waitlist`, { method: 'POST' })
}

export async function leaveBookClubWaitlist(clubId: number): Promise<void> {
  await fetchApi<void>(`/book-clubs/${clubId}/waitlist`, { method: 'DELETE' })
}

// ==================== Staff waitlist ====================

export interface BookClubWaitlistEntry {
  id: number
  user_id: number
  position: number
  display_name: string
  email: string | null
  created_at: string | null
  notified_at: string | null
}

export interface BookClubWaitlistListResponse {
  club_id: number
  total: number
  entries: BookClubWaitlistEntry[]
}

export async function getBookClubWaitlist(
  clubId: number,
  token?: string,
): Promise<BookClubWaitlistListResponse> {
  return fetchApi<BookClubWaitlistListResponse>(`/book-clubs/${clubId}/waitlist`, {
    ...(token ? { token } : {}),
  })
}

export async function removeBookClubWaitlistEntry(
  clubId: number,
  patronId: number,
  token?: string,
): Promise<void> {
  await fetchApi<void>(`/book-clubs/${clubId}/waitlist/${patronId}`, {
    method: 'DELETE',
    ...(token ? { token } : {}),
  })
}

export async function listDiscussions(
  clubId: number,
  meetingId: number
): Promise<DiscussionThread[]> {
  return fetchApi<DiscussionThread[]>(`/book-clubs/${clubId}/meetings/${meetingId}/discussions`)
}

export async function createDiscussion(
  clubId: number,
  meetingId: number,
  data: { title: string; content: string }
): Promise<DiscussionThread> {
  return fetchApi<DiscussionThread>(`/book-clubs/${clubId}/meetings/${meetingId}/discussions`, {
    method: 'POST',
    body: data,
  })
}

export async function listReplies(
  clubId: number,
  discussionId: number
): Promise<DiscussionReply[]> {
  return fetchApi<DiscussionReply[]>(`/book-clubs/${clubId}/discussions/${discussionId}/replies`)
}

export async function createReply(
  clubId: number,
  discussionId: number,
  data: { content: string }
): Promise<DiscussionReply> {
  return fetchApi<DiscussionReply>(`/book-clubs/${clubId}/discussions/${discussionId}/replies`, {
    method: 'POST',
    body: data,
  })
}

// ==================== Discussion archive + search ====================

export interface BookClubMeetingRow {
  id: number
  book_club_id: number
  title: string
  description: string | null
  catalog_item_id: number | null
  status: string
  meeting_date: string
  location: string | null
  notes: string | null
  is_archived: boolean
  created_at?: string | null
  updated_at?: string | null
}

export interface DiscussionSearchHit {
  id: number
  meeting_id: number
  meeting_title: string | null
  meeting_scheduled_at: string
  meeting_is_archived: boolean
  snippet: string
  author_display_name: string
  created_at: string
  rank: number
}

export interface DiscussionSearchResponse {
  hits: DiscussionSearchHit[]
  total: number
  q: string
  include_archived: boolean
}

export async function archiveBookClubMeeting(
  clubId: number,
  meetingId: number
): Promise<BookClubMeetingRow> {
  return fetchApi<BookClubMeetingRow>(
    `/book-clubs/${clubId}/meetings/${meetingId}/archive`,
    { method: 'PATCH' },
  )
}

export async function unarchiveBookClubMeeting(
  clubId: number,
  meetingId: number
): Promise<BookClubMeetingRow> {
  return fetchApi<BookClubMeetingRow>(
    `/book-clubs/${clubId}/meetings/${meetingId}/unarchive`,
    { method: 'PATCH' },
  )
}

export async function listClubMeetings(
  clubId: number,
  params?: { archived?: 'false' | 'true' | 'all' }
): Promise<BookClubMeetingRow[]> {
  const sp = new URLSearchParams()
  if (params?.archived) sp.set('archived', params.archived)
  const qs = sp.toString()
  return fetchApi<BookClubMeetingRow[]>(
    `/book-clubs/${clubId}/meetings${qs ? `?${qs}` : ''}`,
  )
}

export async function searchClubDiscussions(
  clubId: number,
  params: {
    q: string
    from?: string
    to?: string
    include_archived?: boolean
  },
): Promise<DiscussionSearchResponse> {
  const sp = new URLSearchParams({ q: params.q })
  if (params.from) sp.set('from', params.from)
  if (params.to) sp.set('to', params.to)
  if (params.include_archived) sp.set('include_archived', 'true')
  return fetchApi<DiscussionSearchResponse>(
    `/book-clubs/${clubId}/discussions/search?${sp.toString()}`,
  )
}

// ==================== Member Bulk Import ====================

export type MemberImportRowStatus =
  | "success"
  | "duplicate"
  | "not_found"
  | "invalid_email"
  | "invalid_role"
  | "deactivated"
  | "parse_error"

export interface MemberImportRowResult {
  row: number
  email: string | null
  patron_id: number | null
  role: string | null
  status: MemberImportRowStatus
  user_id: number | null
  message: string | null
}

export interface MemberImportResponse {
  import_id: string | null
  dry_run: boolean
  total_rows: number
  success_count: number
  skipped_count: number
  error_count: number
  rows: MemberImportRowResult[]
}

export async function importBookClubMembers(
  clubId: number,
  file: File,
  defaultRole: string,
  dryRun: boolean,
): Promise<MemberImportResponse> {
  const token = getAccessToken()
  const formData = new FormData()
  formData.append("file", file)
  formData.append("default_role", defaultRole)
  formData.append("dry_run", String(dryRun))

  const response = await fetch(
    `${API_BASE}/book-clubs/${clubId}/members/import`,
    {
      method: "POST",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: formData,
    },
  )

  if (!response.ok) {
    const err = await response.json().catch(() => ({}))
    // L30 wraps HTTPException as { error: { message } }; fall back to detail.
    const msg =
      err?.error?.message ||
      err?.detail ||
      `Import failed (HTTP ${response.status})`
    throw new Error(msg)
  }

  return response.json()
}
