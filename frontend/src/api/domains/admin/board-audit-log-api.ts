/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Board Audit Log API Service
 *
 * Read-only access to the board governance audit trail and CSV/JSON export.
 * All endpoints require DIRECTOR, ADMIN, or SUPER_ADMIN role.
 *
 * Backend: backend/app/api/v1/board/audit_logs.py
 */

import { fetchApi, isApiError } from '@/lib/api-client'
import { getAccessToken } from '../../../utils/tokenStore'

// ==================== Types ====================

export interface BoardAuditLogEntry {
  id: number
  user_id: number | null
  action: string
  entity_type: string
  entity_id: number
  meeting_id: number | null
  details: Record<string, unknown> | null
  ip_address: string | null
  notes: string | null
  created_at: string
}

export interface BoardAuditLogFilters {
  entity_type?: string | undefined
  entity_id?: number | undefined
  action?: string | undefined
  user_id?: number | undefined
  meeting_id?: number | undefined
  date_from?: string | undefined
  date_to?: string | undefined
  skip?: number | undefined
  limit?: number | undefined
}

export type BoardAuditExportFormat = 'csv' | 'json'

// ==================== Action Catalog ====================

/**
 * Subset of board audit action codes commonly filtered by users.
 * Source: backend/app/models/board_audit_log.py BoardAuditAction enum.
 */
export const BOARD_AUDIT_ACTIONS: ReadonlyArray<{ value: string; label: string; group: string }> = [
  // Meeting
  { value: 'meeting_created', label: 'Meeting created', group: 'Meetings' },
  { value: 'meeting_updated', label: 'Meeting updated', group: 'Meetings' },
  { value: 'meeting_cancelled', label: 'Meeting cancelled', group: 'Meetings' },
  { value: 'meeting_deleted', label: 'Meeting deleted', group: 'Meetings' },
  { value: 'meeting_notice_generated', label: 'Notice generated', group: 'Meetings' },
  { value: 'meeting_notice_posted', label: 'Notice posted', group: 'Meetings' },
  { value: 'meeting_notice_published', label: 'Notice published', group: 'Meetings' },
  { value: 'meeting_agenda_published', label: 'Agenda published', group: 'Meetings' },
  // Minutes
  { value: 'minutes_created', label: 'Minutes created', group: 'Minutes' },
  { value: 'minutes_updated', label: 'Minutes updated', group: 'Minutes' },
  { value: 'minutes_approved', label: 'Minutes approved', group: 'Minutes' },
  { value: 'minutes_published', label: 'Minutes published', group: 'Minutes' },
  { value: 'minutes_viewed', label: 'Minutes viewed', group: 'Minutes' },
  { value: 'minutes_deleted', label: 'Minutes deleted', group: 'Minutes' },
  { value: 'minutes_sealed', label: 'Minutes sealed (executive session)', group: 'Minutes' },
  { value: 'minutes_unsealed', label: 'Minutes unsealed', group: 'Minutes' },
  // Voting
  { value: 'vote_created', label: 'Vote created', group: 'Voting' },
  { value: 'vote_opened', label: 'Vote opened', group: 'Voting' },
  { value: 'vote_closed', label: 'Vote closed', group: 'Voting' },
  { value: 'vote_cast', label: 'Vote cast', group: 'Voting' },
  { value: 'vote_locked', label: 'Vote locked', group: 'Voting' },
  { value: 'vote_deleted', label: 'Vote deleted', group: 'Voting' },
  // Motions
  { value: 'motion_created', label: 'Motion created', group: 'Motions' },
  { value: 'motion_seconded', label: 'Motion seconded', group: 'Motions' },
  { value: 'motion_passed', label: 'Motion passed', group: 'Motions' },
  { value: 'motion_failed', label: 'Motion failed', group: 'Motions' },
  { value: 'motion_tabled', label: 'Motion tabled', group: 'Motions' },
  { value: 'motion_withdrawn', label: 'Motion withdrawn', group: 'Motions' },
  { value: 'motion_amended', label: 'Motion amended', group: 'Motions' },
  // Recusal
  { value: 'recusal_declared', label: 'Recusal declared', group: 'Recusal' },
  { value: 'recusal_withdrawn', label: 'Recusal withdrawn', group: 'Recusal' },
  // COI
  { value: 'coi_disclosure_submitted', label: 'COI disclosure submitted', group: 'Conflict of interest' },
  { value: 'coi_disclosure_superseded', label: 'COI disclosure superseded', group: 'Conflict of interest' },
  { value: 'coi_overlap_detected', label: 'COI overlap detected on vote', group: 'Conflict of interest' },
  // Retention
  { value: 'legal_hold_placed', label: 'Legal hold placed', group: 'Retention' },
  { value: 'legal_hold_released', label: 'Legal hold released', group: 'Retention' },
  { value: 'record_disposition', label: 'Record disposition', group: 'Retention' },
  // Documents
  { value: 'document_created', label: 'Document created', group: 'Documents' },
  { value: 'document_published', label: 'Document published', group: 'Documents' },
  { value: 'document_viewed', label: 'Document viewed', group: 'Documents' },
  { value: 'document_archived', label: 'Document archived', group: 'Documents' },
  { value: 'document_deleted', label: 'Document deleted', group: 'Documents' },
  // Attendance
  { value: 'attendance_recorded', label: 'Attendance recorded', group: 'Attendance' },
  { value: 'attendance_checked_in', label: 'Attendance checked in', group: 'Attendance' },
  { value: 'attendance_checked_out', label: 'Attendance checked out', group: 'Attendance' },
  { value: 'attendance_marked_absent', label: 'Attendance marked absent', group: 'Attendance' },
  // Public comment
  { value: 'public_comment_submitted', label: 'Public comment submitted', group: 'Public comment' },
  { value: 'public_comment_approved', label: 'Public comment approved', group: 'Public comment' },
  { value: 'public_comment_rejected', label: 'Public comment rejected', group: 'Public comment' },
  { value: 'public_comment_read_into_record', label: 'Public comment read into record', group: 'Public comment' },
] as const

export function getBoardAuditActionLabel(action: string): string {
  const match = BOARD_AUDIT_ACTIONS.find((a) => a.value === action)
  return match ? match.label : action
}

// ==================== API Functions ====================

function buildParams(filters?: BoardAuditLogFilters): URLSearchParams {
  const params = new URLSearchParams()
  if (!filters) return params
  if (filters.entity_type) params.set('entity_type', filters.entity_type)
  if (filters.entity_id != null) params.set('entity_id', String(filters.entity_id))
  if (filters.action) params.set('action', filters.action)
  if (filters.user_id != null) params.set('user_id', String(filters.user_id))
  if (filters.meeting_id != null) params.set('meeting_id', String(filters.meeting_id))
  if (filters.date_from) params.set('date_from', filters.date_from)
  if (filters.date_to) params.set('date_to', filters.date_to)
  if (filters.skip != null) params.set('skip', String(filters.skip))
  if (filters.limit != null) params.set('limit', String(filters.limit))
  return params
}

export async function getBoardAuditLogs(
  filters?: BoardAuditLogFilters,
): Promise<BoardAuditLogEntry[]> {
  try {
    const qs = buildParams(filters).toString()
    const suffix = qs ? `?${qs}` : ''
    return await fetchApi<BoardAuditLogEntry[]>(`/board/audit-logs${suffix}`)
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch board audit logs')
    }
    throw error
  }
}

export async function downloadBoardAuditLogExport(
  format: BoardAuditExportFormat,
  filters?: BoardAuditLogFilters,
): Promise<void> {
  const params = buildParams({ ...filters, skip: undefined, limit: undefined })
  params.set('format', format)

  const token = getAccessToken()
  const apiBase = import.meta.env.VITE_API_BASE || '/api/v1'
  const url = `${apiBase}/board/audit-logs/export?${params.toString()}`

  const res = await fetch(url, {
    method: 'GET',
    credentials: 'include',
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })

  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`
    try {
      const body = await res.json()
      detail = body.detail || detail
    } catch {
      // ignore parse errors, use status text
    }
    throw new Error(detail)
  }

  const blob = await res.blob()
  const today = new Date().toISOString().slice(0, 10)
  const filename = `board-audit-log-${today}.${format}`

  const objectUrl = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = objectUrl
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(objectUrl)
}
