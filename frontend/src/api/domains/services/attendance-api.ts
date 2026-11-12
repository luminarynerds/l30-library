/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Attendance Tracking API module.
 *
 * Handles: sessions, check-ins (QR, library card, walk-in, head count),
 * survey delivery, dashboard, trends, and ROI reporting.
 */

import api from '@/lib/api-client'
import { API_BASE } from '@/api/types'

const BASE = `${API_BASE}/attendance`

// ============================================================================
// Types
// ============================================================================

export interface AttendanceSession {
  id: number
  event_id: number | null
  program_id: number | null
  session_name: string
  session_date: string
  status: string
  qr_code_token: string
  head_count_mode: boolean
  head_count_total: number
  head_count_by_age: Record<string, number> | null
  total_checked_in: number
  total_walk_ins: number
  total_pre_registered: number
  total_card_scans: number
  total_qr_scans: number
  event_cost: number | null
  cost_notes: string | null
  survey_enabled: boolean
  survey_link: string | null
  survey_sent_at: string | null
  opened_by_id: number | null
  closed_by_id: number | null
  closed_at: string | null
  notes: string | null
  created_at: string
  updated_at: string
  effective_total: number
  cost_per_attendee: number | null
}

export interface CheckIn {
  id: number
  session_id: number
  patron_id: number | null
  guest_name: string | null
  guest_email: string | null
  check_in_method: string
  checked_in_at: string
  library_card_number: string | null
  age_range: string
  is_repeat_attendee: boolean
  previous_visit_count: number
  first_visit_date: string | null
  patron_name: string | null
  notes: string | null
}

export interface AttendanceDashboard {
  today_sessions: number
  today_total_attendance: number
  week_total_attendance: number
  month_total_attendance: number
  avg_attendance_per_event: number
  repeat_attendee_rate: number
  top_check_in_method: string
  recent_sessions: AttendanceSession[]
  age_distribution: Record<string, number>
  method_distribution: Record<string, number>
}

export interface ROIReport {
  period_label: string
  total_events: number
  total_attendance: number
  total_cost: number
  cost_per_attendee: number
  repeat_rate: number
  top_programs: Array<{ name: string; attendance: number }>
}

export interface SessionCreateData {
  event_id?: number | null
  program_id?: number | null
  session_name: string
  session_date: string
  head_count_mode?: boolean
  event_cost?: number | null
  cost_notes?: string | null
  survey_enabled?: boolean
  survey_link?: string | null
  notes?: string | null
}

export interface PaginatedSessions {
  data: AttendanceSession[]
  pagination: {
    page: number
    per_page: number
    total: number
    total_pages: number
    has_next: boolean
    has_previous: boolean
  }
}

// ============================================================================
// Session Management
// ============================================================================

export async function createAttendanceSession(data: SessionCreateData): Promise<AttendanceSession> {
  return api.post<AttendanceSession>(`${BASE}/sessions`, data)
}

export async function listAttendanceSessions(params?: {
  status?: string
  start_date?: string
  end_date?: string
  page?: number
  per_page?: number
}): Promise<PaginatedSessions> {
  const query = new URLSearchParams()
  if (params?.status) query.set('status', params.status)
  if (params?.start_date) query.set('start_date', params.start_date)
  if (params?.end_date) query.set('end_date', params.end_date)
  if (params?.page) query.set('page', String(params.page))
  if (params?.per_page) query.set('per_page', String(params.per_page))
  const qs = query.toString()
  return api.get<PaginatedSessions>(`${BASE}/sessions${qs ? `?${qs}` : ''}`)
}

export async function getAttendanceSession(sessionId: number): Promise<AttendanceSession> {
  return api.get<AttendanceSession>(`${BASE}/sessions/${sessionId}`)
}

export async function updateAttendanceSession(
  sessionId: number,
  data: Partial<SessionCreateData>
): Promise<AttendanceSession> {
  return api.put<AttendanceSession>(`${BASE}/sessions/${sessionId}`, data)
}

export async function closeAttendanceSession(sessionId: number): Promise<AttendanceSession> {
  return api.post<AttendanceSession>(`${BASE}/sessions/${sessionId}/close`)
}

export async function finalizeAttendanceSession(sessionId: number): Promise<AttendanceSession> {
  return api.post<AttendanceSession>(`${BASE}/sessions/${sessionId}/finalize`)
}

// ============================================================================
// Check-In Operations
// ============================================================================

export async function checkInQR(data: {
  qr_token: string
  patron_id?: number
  guest_name?: string
  guest_email?: string
  age_range?: string
}): Promise<CheckIn> {
  return api.post<CheckIn>(`${BASE}/check-in/qr`, data)
}

export async function checkInLibraryCard(data: {
  session_id: number
  library_card_number: string
  age_range?: string
}): Promise<CheckIn> {
  return api.post<CheckIn>(`${BASE}/check-in/library-card`, data)
}

export async function checkInWalkIn(data: {
  session_id: number
  guest_name?: string
  guest_email?: string
  guest_phone?: string
  age_range?: string
  notes?: string
}): Promise<CheckIn> {
  return api.post<CheckIn>(`${BASE}/check-in/walk-in`, data)
}

export async function updateHeadCount(data: {
  session_id: number
  total: number
  by_age?: Record<string, number>
}): Promise<AttendanceSession> {
  return api.post<AttendanceSession>(`${BASE}/check-in/head-count`, data)
}

export async function getSessionCheckIns(sessionId: number): Promise<CheckIn[]> {
  return api.get<CheckIn[]>(`${BASE}/sessions/${sessionId}/check-ins`)
}

// ============================================================================
// Surveys
// ============================================================================

export async function sendSurveys(sessionId: number, surveyLink?: string): Promise<{
  session_id: number
  total_eligible: number
  total_sent: number
  total_failed: number
  total_opted_out: number
}> {
  return api.post(`${BASE}/sessions/${sessionId}/send-surveys`, surveyLink ? { survey_link: surveyLink } : undefined)
}

// ============================================================================
// Dashboard & Analytics
// ============================================================================

export async function getAttendanceDashboard(): Promise<AttendanceDashboard> {
  return api.get<AttendanceDashboard>(`${BASE}/dashboard`)
}

export async function getAttendanceTrends(params?: {
  start_date?: string
  end_date?: string
  program_type?: string
  period_type?: string
}): Promise<unknown[]> {
  const query = new URLSearchParams()
  if (params?.start_date) query.set('start_date', params.start_date)
  if (params?.end_date) query.set('end_date', params.end_date)
  if (params?.program_type) query.set('program_type', params.program_type)
  if (params?.period_type) query.set('period_type', params.period_type)
  const qs = query.toString()
  return api.get(`${BASE}/trends${qs ? `?${qs}` : ''}`)
}

export async function getROIReport(params?: {
  start_date?: string
  end_date?: string
}): Promise<ROIReport> {
  const query = new URLSearchParams()
  if (params?.start_date) query.set('start_date', params.start_date)
  if (params?.end_date) query.set('end_date', params.end_date)
  const qs = query.toString()
  return api.get<ROIReport>(`${BASE}/roi${qs ? `?${qs}` : ''}`)
}