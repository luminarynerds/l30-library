/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import api from '@/lib/api-client'
import { API_BASE } from '@/api/types'

// ==================== Public Comment Types ====================

export interface PublicComment {
  id: number
  meeting_id: number
  agenda_item_id?: number
  comment_type: 'written' | 'in_person' | 'virtual'
  status: 'pending' | 'approved' | 'rejected' | 'read_into_record'
  commenter_name: string
  commenter_email?: string
  commenter_phone?: string
  organization?: string
  is_resident?: boolean
  subject?: string
  comment_text: string
  ip_address?: string
  submitted_at: string
  moderated_at?: string
  moderated_by_id?: number
  moderation_notes?: string
  rejection_reason?: string
  read_at?: string
  read_by_id?: number
  reading_notes?: string
  time_allocated_seconds?: number
  speaker_order?: number
  actual_start_time?: string
  actual_end_time?: string
  staff_response?: string
  staff_response_by_id?: number
  staff_response_at?: string
  created_at: string
  updated_at?: string
}

export interface CommentPeriod {
  id: number
  meeting_id: number
  title: string
  description?: string
  opens_at: string
  closes_at: string
  is_active: boolean
  allow_written: boolean
  allow_in_person: boolean
  allow_virtual: boolean
  max_comments?: number
  max_comment_length?: number
  speaker_time_limit_seconds?: number
  actual_start_time?: string
  actual_end_time?: string
  created_by_id?: number
  created_at: string
  updated_at?: string
}

export interface PublicCommentSubmit {
  commenter_name: string
  commenter_email?: string
  commenter_phone?: string
  organization?: string
  is_resident?: boolean
  subject?: string
  comment_text: string
  agenda_item_id?: number
}

export interface PublicCommentModerate {
  status: 'approved' | 'rejected'
  moderation_notes?: string
  rejection_reason?: string
}

export interface PublicCommentReadIntoRecord {
  reading_notes?: string
  time_allocated_seconds?: number
}

export interface PublicCommentStaffResponse {
  staff_response: string
}

export interface PublicCommentUpdate {
  subject?: string
  comment_text?: string
  speaker_order?: number
}

export interface CommentPeriodCreate {
  title: string
  description?: string
  opens_at: string
  closes_at: string
  is_active?: boolean
  allow_written?: boolean
  allow_in_person?: boolean
  allow_virtual?: boolean
  max_comments?: number
  max_comment_length?: number
  speaker_time_limit_seconds?: number
}

export interface CommentPeriodUpdate {
  title?: string
  description?: string
  opens_at?: string
  closes_at?: string
  is_active?: boolean
  allow_written?: boolean
  allow_in_person?: boolean
  allow_virtual?: boolean
  max_comments?: number
  max_comment_length?: number
  speaker_time_limit_seconds?: number
}

// ==================== Public Endpoints ====================

export async function getMeetingCommentPeriods(
  meetingId: number,
  activeOnly: boolean = true
): Promise<CommentPeriod[]> {
  const params = new URLSearchParams()
  params.set('active_only', String(activeOnly))
  return api.get(`${API_BASE}/board/meetings/${meetingId}/comment-periods?${params}`)
}

export async function getActiveCommentPeriods(): Promise<CommentPeriod[]> {
  return api.get(`${API_BASE}/board/comment-periods/active`)
}

export async function submitPublicComment(
  meetingId: number,
  comment: PublicCommentSubmit
): Promise<PublicComment> {
  return api.post(`${API_BASE}/board/meetings/${meetingId}/public-comments/submit`, comment)
}

// ==================== Staff/Admin Comment Management ====================

export async function getMeetingComments(
  meetingId: number,
  statusFilter?: string,
  commentType?: string
): Promise<PublicComment[]> {
  const params = new URLSearchParams()
  if (statusFilter) params.set('status_filter', statusFilter)
  if (commentType) params.set('comment_type', commentType)
  const query = params.toString()
  return api.get(`${API_BASE}/board/meetings/${meetingId}/public-comments${query ? '?' + query : ''}`)
}

export async function getPendingComments(limit: number = 50): Promise<PublicComment[]> {
  return api.get(`${API_BASE}/board/public-comments/pending?limit=${limit}`)
}

export async function moderateComment(
  commentId: number,
  moderation: PublicCommentModerate
): Promise<PublicComment> {
  return api.post(`${API_BASE}/board/public-comments/${commentId}/moderate`, moderation)
}

export async function markCommentReadIntoRecord(
  commentId: number,
  reading: PublicCommentReadIntoRecord
): Promise<PublicComment> {
  return api.post(`${API_BASE}/board/public-comments/${commentId}/read-into-record`, reading)
}

export async function addStaffResponse(
  commentId: number,
  responseData: PublicCommentStaffResponse
): Promise<PublicComment> {
  return api.post(`${API_BASE}/board/public-comments/${commentId}/staff-response`, responseData)
}

export async function updateComment(
  commentId: number,
  comment: PublicCommentUpdate
): Promise<PublicComment> {
  return api.put(`${API_BASE}/board/public-comments/${commentId}`, comment)
}

export async function deleteComment(commentId: number): Promise<{ message: string }> {
  return api.delete(`${API_BASE}/board/public-comments/${commentId}`)
}

// ==================== In-Person/Virtual Comment Registration ====================

export async function registerSpeaker(
  meetingId: number,
  comment: PublicCommentSubmit,
  commentType: 'in_person' | 'virtual' = 'in_person'
): Promise<PublicComment> {
  return api.post(
    `${API_BASE}/board/meetings/${meetingId}/public-comments/register-speaker?comment_type=${commentType}`,
    comment
  )
}

export async function startSpeaking(
  commentId: number
): Promise<{ message: string; start_time: string }> {
  return api.post(`${API_BASE}/board/public-comments/${commentId}/start-speaking`, {})
}

export async function stopSpeaking(
  commentId: number
): Promise<{ message: string; end_time: string; duration_seconds: number }> {
  return api.post(`${API_BASE}/board/public-comments/${commentId}/stop-speaking`, {})
}

// ==================== Comment Period Management ====================

export async function createCommentPeriod(
  meetingId: number,
  period: CommentPeriodCreate
): Promise<CommentPeriod> {
  return api.post(`${API_BASE}/board/meetings/${meetingId}/comment-periods`, period)
}

export async function updateCommentPeriod(
  periodId: number,
  period: CommentPeriodUpdate
): Promise<CommentPeriod> {
  return api.put(`${API_BASE}/board/comment-periods/${periodId}`, period)
}

export async function startCommentPeriod(
  periodId: number
): Promise<{ message: string; start_time: string }> {
  return api.post(`${API_BASE}/board/comment-periods/${periodId}/start`, {})
}

export async function endCommentPeriod(
  periodId: number
): Promise<{ message: string; end_time: string }> {
  return api.post(`${API_BASE}/board/comment-periods/${periodId}/end`, {})
}

export async function deleteCommentPeriod(periodId: number): Promise<{ message: string }> {
  return api.delete(`${API_BASE}/board/comment-periods/${periodId}`)
}