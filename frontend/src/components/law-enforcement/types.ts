/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
export interface LawEnforcementRequest {
  id: number
  tracking_number: string
  requesting_agency: string
  request_type: string
  date_received: string
  date_due?: string
  patron_name_on_request?: string
  legal_review_status: string
  workflow_status: string
  created_at: string
}

export interface LawEnforcementRequestDetail extends LawEnforcementRequest {
  data_requested: string
  requesting_officer_name?: string
  requesting_officer_badge?: string
  description?: string
  legal_review_notes?: string
  response_summary?: string
  response_date?: string
  patron_notification_date?: string
  denial_reason?: string
}

export interface ChecklistItem {
  id: number
  name: string
  description?: string
  required: boolean
  completed: boolean
  completed_date?: string
  completed_by?: string
}

export interface AuditLogEntry {
  id: number
  timestamp: string
  action: string
  actor: string
  actor_role: string
  details?: Record<string, unknown>
  change_summary?: string
}

export interface LEStats {
  total_requests: number
  pending_review: number
  in_progress: number
  completed: number
  this_year: number
}

export type WorkflowActionType = 'legal_review' | 'workflow_status' | 'response' | 'patron_notification'
