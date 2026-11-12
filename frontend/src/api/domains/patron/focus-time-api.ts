/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { fetchApi, isApiError } from '@/lib/api-client'
import { getAccessToken } from '@/utils/tokenStore'

// Types
export type FocusWorkType =
  | 'cataloging'
  | 'programming'
  | 'writing'
  | 'analysis'
  | 'research'
  | 'strategic_planning'
  | 'collection_development'
  | 'training'
  | 'system_maintenance'
  | 'content_creation'
  | 'other'

export type FocusTimeStatus =
  | 'PENDING_APPROVAL'
  | 'approved'
  | 'rejected'
  | 'active'
  | 'COMPLETED'
  | 'cancelled'
  | 'OVERRIDDEN'

export type ApprovalStatus = 'pending' | 'approved' | 'rejected' | 'expired'

export type OverrideReason =
  | 'urgent_patron'
  | 'system_issue'
  | 'staffing_emergency'
  | 'emergency_operations'
  | 'critical_incident'
  | 'management_override'
  | 'urgent_meeting'
  | 'other'

export interface FocusTimeBlock {
  id: number
  user_id: number
  organization_id?: number
  start_time: string
  end_time: string
  work_type: FocusWorkType
  description?: string | null
  status: FocusTimeStatus
  requires_approval: boolean
  is_recurring: boolean
  recurrence_rule?: string | null
  backup_contact_id?: number | null
  created_at?: string
  updated_at?: string
  cancelled_at?: string
}

export interface FocusTimeApproval {
  id: number
  focus_block_id: number
  manager_id?: number | null
  status: ApprovalStatus
  decision_comment?: string | null
  conditions?: Record<string, unknown> | null
  requested_at?: string
  decided_at?: string
  expires_at?: string
}

export interface FocusTimeOverride {
  id: number
  focus_block_id: number
  overridden_by_id?: number
  reason: OverrideReason
  description: string
  urgency_level: number
  requires_escalation: boolean
  is_resolved: boolean
  resolved_at?: string | null
  resolution_notes?: string | null
  created_at?: string
}

export interface FocusTimeTracking {
  focus_block_id: number
  interruption_count: number
  work_completed_percentage?: number | null
  quality_rating?: number | null
  productivity_rating?: number | null
  notes?: string | null
}

export interface FocusTimeAnalytics {
  summary: {
    total_blocks: number
    completed_blocks: number
    cancelled_blocks: number
    overridden_blocks: number
    total_hours: number
    completion_rate: number
  }
  period: {
    start_date: string | null
    end_date: string | null
  }
}

export interface FocusTimeSettings {
  requires_manager_approval: boolean
  min_advance_notice_hours: number
  max_duration_hours: number
  min_duration_minutes: number
  max_blocks_per_week: number
  allow_recurring_blocks: boolean
  allow_emergency_override: boolean
  require_backup_contact: boolean
  notification_enabled: boolean
}

export interface UserFocusStatus {
  user_id: number
  in_focus_time: boolean
  block?: {
    id: number
    work_type: FocusWorkType
    end_time: string
    backup_contact_id?: number
  } | null
}

// API Client Functions

export async function createFocusTimeBlock(data: {
  start_time: string
  end_time: string
  work_type: FocusWorkType
  description?: string
  backup_contact_id?: number
  is_recurring?: boolean
  recurrence_rule?: string
}): Promise<{ message: string; block: FocusTimeBlock }> {
  const token = getAccessToken()
  if (!token) throw new Error('Not authenticated')

  const params = new URLSearchParams()
  params.set('start_time', data.start_time)
  params.set('end_time', data.end_time)
  params.set('work_type', data.work_type)
  if (data.description) params.set('description', data.description)
  if (data.backup_contact_id) params.set('backup_contact_id', data.backup_contact_id.toString())
  if (data.is_recurring) params.set('is_recurring', 'true')
  if (data.recurrence_rule) params.set('recurrence_rule', data.recurrence_rule)

  try {
    return await fetchApi<{ message: string; block: FocusTimeBlock }>(
      `/staff/focus-time/blocks?${params.toString()}`,
      {
        method: 'POST',
        token,
      }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to create focus time block')
    }
    throw error
  }
}

export async function getFocusTimeBlocks(params?: {
  start_date?: string
  end_date?: string
  status?: FocusTimeStatus
}): Promise<{ blocks: FocusTimeBlock[] }> {
  const token = getAccessToken()
  if (!token) throw new Error('Not authenticated')

  const searchParams = new URLSearchParams()
  if (params?.start_date) searchParams.set('start_date', params.start_date)
  if (params?.end_date) searchParams.set('end_date', params.end_date)
  if (params?.status) searchParams.set('status', params.status)

  const query = searchParams.toString() ? `?${searchParams.toString()}` : ''

  try {
    return await fetchApi<{ blocks: FocusTimeBlock[] }>(
      `/staff/focus-time/blocks${query}`,
      { token }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch focus time blocks')
    }
    throw error
  }
}

export async function getFocusTimeBlock(
  blockId: number
): Promise<{
  block: FocusTimeBlock
  tracking: FocusTimeTracking | null
  approvals: FocusTimeApproval[]
  overrides: FocusTimeOverride[]
}> {
  const token = getAccessToken()
  if (!token) throw new Error('Not authenticated')

  try {
    return await fetchApi<{
      block: FocusTimeBlock
      tracking: FocusTimeTracking | null
      approvals: FocusTimeApproval[]
      overrides: FocusTimeOverride[]
    }>(`/staff/focus-time/blocks/${blockId}`, { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch focus time block')
    }
    throw error
  }
}

export async function cancelFocusTimeBlock(
  blockId: number,
  reason?: string
): Promise<{ message: string; block_id: number }> {
  const token = getAccessToken()
  if (!token) throw new Error('Not authenticated')

  const params = new URLSearchParams()
  if (reason) params.set('reason', reason)

  try {
    return await fetchApi<{ message: string; block_id: number }>(
      `/staff/focus-time/blocks/${blockId}/cancel?${params.toString()}`,
      {
        method: 'PATCH',
        token,
      }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to cancel focus time block')
    }
    throw error
  }
}

export async function getPendingFocusTimeApprovals(): Promise<{
  pending_approvals: FocusTimeApproval[]
}> {
  const token = getAccessToken()
  if (!token) throw new Error('Not authenticated')

  try {
    return await fetchApi<{ pending_approvals: FocusTimeApproval[] }>(
      '/staff/focus-time/approvals/pending',
      { token }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch pending approvals')
    }
    throw error
  }
}

export async function approveFocusTimeRequest(
  approvalId: number,
  data?: {
    decision_comment?: string
    conditions?: Record<string, unknown>
  }
): Promise<{ message: string; approval_id: number }> {
  const token = getAccessToken()
  if (!token) throw new Error('Not authenticated')

  const params = new URLSearchParams()
  if (data?.decision_comment) params.set('decision_comment', data.decision_comment)
  if (data?.conditions) params.set('conditions', JSON.stringify(data.conditions))

  try {
    return await fetchApi<{ message: string; approval_id: number }>(
      `/staff/focus-time/approvals/${approvalId}/approve?${params.toString()}`,
      {
        method: 'POST',
        token,
      }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to approve focus time request')
    }
    throw error
  }
}

export async function rejectFocusTimeRequest(
  approvalId: number,
  decision_comment: string
): Promise<{ message: string; approval_id: number }> {
  const token = getAccessToken()
  if (!token) throw new Error('Not authenticated')

  const params = new URLSearchParams()
  params.set('decision_comment', decision_comment)

  try {
    return await fetchApi<{ message: string; approval_id: number }>(
      `/staff/focus-time/approvals/${approvalId}/reject?${params.toString()}`,
      {
        method: 'POST',
        token,
      }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to reject focus time request')
    }
    throw error
  }
}

export async function createFocusTimeOverride(data: {
  focus_block_id: number
  reason: OverrideReason
  description: string
  urgency_level: number
  requires_escalation?: boolean
}): Promise<{ message: string; override: FocusTimeOverride }> {
  const token = getAccessToken()
  if (!token) throw new Error('Not authenticated')

  const params = new URLSearchParams()
  params.set('focus_block_id', data.focus_block_id.toString())
  params.set('reason', data.reason)
  params.set('description', data.description)
  params.set('urgency_level', data.urgency_level.toString())
  if (data.requires_escalation) params.set('requires_escalation', 'true')

  try {
    return await fetchApi<{ message: string; override: FocusTimeOverride }>(
      `/staff/focus-time/overrides?${params.toString()}`,
      {
        method: 'POST',
        token,
      }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to create focus time override')
    }
    throw error
  }
}

export async function resolveFocusTimeOverride(
  overrideId: number,
  resolution_notes: string
): Promise<{ message: string; override_id: number }> {
  const token = getAccessToken()
  if (!token) throw new Error('Not authenticated')

  const params = new URLSearchParams()
  params.set('resolution_notes', resolution_notes)

  try {
    return await fetchApi<{ message: string; override_id: number }>(
      `/staff/focus-time/overrides/${overrideId}/resolve?${params.toString()}`,
      {
        method: 'PATCH',
        token,
      }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to resolve focus time override')
    }
    throw error
  }
}

export async function getFocusTimeAnalytics(params?: {
  start_date?: string
  end_date?: string
}): Promise<FocusTimeAnalytics> {
  const token = getAccessToken()
  if (!token) throw new Error('Not authenticated')

  const searchParams = new URLSearchParams()
  if (params?.start_date) searchParams.set('start_date', params.start_date)
  if (params?.end_date) searchParams.set('end_date', params.end_date)

  const query = searchParams.toString() ? `?${searchParams.toString()}` : ''

  try {
    return await fetchApi<FocusTimeAnalytics>(
      `/staff/focus-time/analytics${query}`,
      { token }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch focus time analytics')
    }
    throw error
  }
}

export async function getFocusTimeSettings(): Promise<{ settings: FocusTimeSettings }> {
  const token = getAccessToken()
  if (!token) throw new Error('Not authenticated')

  try {
    return await fetchApi<{ settings: FocusTimeSettings }>(
      '/staff/focus-time/settings',
      { token }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch focus time settings')
    }
    throw error
  }
}

export async function getUserFocusStatus(userId: number): Promise<UserFocusStatus> {
  try {
    return await fetchApi<UserFocusStatus>(`/focus-time/status/${userId}`)
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch user focus status')
    }
    throw error
  }
}
