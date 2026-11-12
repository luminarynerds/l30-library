/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import { fetchApi, isApiError } from '@/lib/api-client'

// ==================== Types ====================

export type SystemStatusLevel =
  | 'operational'
  | 'degraded'
  | 'slow'
  | 'partial_outage'
  | 'major_outage'
  | 'maintenance'

export type HealthLevel = 'healthy' | 'slow' | 'degraded' | 'outage'

export type StatusIndicator = 'green' | 'yellow' | 'orange' | 'red' | 'blue'

export interface ActiveIssue {
  id: number
  component: string | null
  title: string
  description: string
  patron_message: string | null
  status: SystemStatusLevel
  started_at: string | null
  estimated_fix_time: string | null
  available_features: string[] | null
  degraded_features: string[] | null
  offline_alternatives: Array<{ feature: string; alternative: string }> | null
}

export interface SystemStatusResponse {
  status: SystemStatusLevel
  message: string
  active_issues: ActiveIssue[]
  offline_mode_recommended: boolean
}

export interface StatusPageResponse {
  indicator: StatusIndicator
  message: string
  detail: string
  issue_count: number
  issues: Array<{
    title: string
    component: string | null
    status: SystemStatusLevel
    patron_message: string
    estimated_fix_time: string | null
  }>
}

export interface HealthSummaryResponse {
  health: HealthLevel
  message: string
  active_issue_count: number
  response_time_ms: number | null
  last_checked: string | null
}

export interface RecoveryItem {
  id: number
  title: string
  component: string | null
  resolved_at: string | null
  resolution_notes: string | null
  duration_minutes: number | null
}

export interface StaffNotification {
  id: number
  type: string
  title: string
  message: string
  patron_talking_points: string | null
  workaround_instructions: string | null
  created_at: string | null
  acknowledged: boolean
}

export interface HealthMetric {
  recorded_at: string | null
  response_time_p50_ms: number | null
  response_time_p95_ms: number | null
  response_time_p99_ms: number | null
  cpu_usage_percent: number | null
  memory_usage_percent: number | null
  disk_usage_percent: number | null
  db_connection_pool_used: number | null
  db_connection_pool_available: number | null
  db_query_latency_ms: number | null
  cache_hit_rate_percent: number | null
  cache_latency_ms: number | null
  error_rate_percent: number | null
  is_degraded: boolean
  is_slow: boolean
  slow_reason: string | null
}

export interface PaperBackupProcedure {
  id: number
  backup_type: string
  title: string
  description: string
  instructions: string
  form_template: string | null
  trigger_conditions: string | null
  applicable_components: string[] | null
  version: number
  last_reviewed_at: string | null
}

export interface DegradationInfo {
  degraded: boolean
  all_features_available: boolean
  message: string
  degraded_features: string[]
  available_features: string[]
  alternatives: Record<string, string>
}

export interface AutoSaveItem {
  id: number
  context_type: string
  context_id: string | null
  saved_data: Record<string, unknown>
  saved_at: string | null
}

// ==================== Public Endpoints ====================

export async function getSystemStatus(): Promise<SystemStatusResponse> {
  try {
    return await fetchApi<SystemStatusResponse>('/system-status')
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch system status')
    }
    throw error
  }
}

export async function getStatusPage(): Promise<StatusPageResponse> {
  try {
    return await fetchApi<StatusPageResponse>('/system-status/status-page')
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch status page')
    }
    throw error
  }
}

export async function getHealthSummary(): Promise<HealthSummaryResponse> {
  try {
    return await fetchApi<HealthSummaryResponse>('/system-status/health-summary')
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch health summary')
    }
    throw error
  }
}

export async function getRecentRecoveries(hours = 24): Promise<{
  recoveries: RecoveryItem[]
  message: string
}> {
  try {
    return await fetchApi(`/system-status/recent-recoveries?hours=${hours}`)
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch recent recoveries')
    }
    throw error
  }
}

export async function getDegradationInfo(): Promise<DegradationInfo> {
  try {
    return await fetchApi<DegradationInfo>('/system-status/degradation-info')
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch degradation info')
    }
    throw error
  }
}

export async function getOfflineModeStatus(): Promise<{
  offline_mode_active: boolean
  session_id?: number
  started_at?: string
  reason?: string
  pending_transactions?: number
}> {
  try {
    return await fetchApi('/system-status/offline-mode/active')
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to check offline mode')
    }
    throw error
  }
}

// ==================== Staff Endpoints ====================

export async function reportIssue(
  token: string,
  data: {
    status: SystemStatusLevel
    title: string
    description: string
    component?: string
    estimated_fix_time?: string
    is_scheduled?: boolean
    is_public?: boolean
    patron_message?: string
    technical_details?: string
    available_features?: string[]
    degraded_features?: string[]
    offline_alternatives?: Array<{ feature: string; alternative: string }>
  }
): Promise<{ message: string; issue: { id: number; status: string; title: string } }> {
  try {
    return await fetchApi('/system-status/issues', {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to report issue')
    }
    throw error
  }
}

export async function resolveIssue(
  token: string,
  issueId: number,
  data: { resolution_notes: string; send_recovery_alert?: boolean }
): Promise<{ message: string; issue_id: number; resolved_at: string }> {
  try {
    return await fetchApi(`/system-status/issues/${issueId}/resolve`, {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to resolve issue')
    }
    throw error
  }
}

export async function getStaffNotifications(
  token: string,
  unacknowledgedOnly = false,
  limit = 20
): Promise<{ notifications: StaffNotification[] }> {
  try {
    const params = new URLSearchParams()
    if (unacknowledgedOnly) params.set('unacknowledged_only', 'true')
    params.set('limit', String(limit))
    return await fetchApi(`/system-status/staff-notifications?${params}`, { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch staff notifications')
    }
    throw error
  }
}

export async function acknowledgeNotification(
  token: string,
  notificationId: number
): Promise<{ message: string }> {
  try {
    return await fetchApi(`/system-status/staff-notifications/${notificationId}/acknowledge`, {
      method: 'POST',
      token,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to acknowledge notification')
    }
    throw error
  }
}

export async function getHealthMetrics(
  token: string,
  limit = 10
): Promise<{ metrics: HealthMetric[] }> {
  try {
    return await fetchApi(`/system-status/health-metrics?limit=${limit}`, { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch health metrics')
    }
    throw error
  }
}

export async function getPaperBackups(
  token: string,
  component?: string,
  backupType?: string
): Promise<{ procedures: PaperBackupProcedure[] }> {
  try {
    const params = new URLSearchParams()
    if (component) params.set('component', component)
    if (backupType) params.set('backup_type', backupType)
    const qs = params.toString()
    return await fetchApi(`/system-status/paper-backups${qs ? '?' + qs : ''}`, { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch paper backups')
    }
    throw error
  }
}

export async function startOfflineMode(
  token: string,
  reason?: string,
  issueId?: number
): Promise<{ message: string; session_id: number; started_at: string }> {
  try {
    const params = new URLSearchParams()
    if (reason) params.set('reason', reason)
    if (issueId) params.set('issue_id', String(issueId))
    return await fetchApi(`/system-status/offline-mode/start?${params}`, {
      method: 'POST',
      token,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to start offline mode')
    }
    throw error
  }
}

export async function endOfflineMode(
  token: string,
  sessionId: number
): Promise<{ message: string; session_id: number; duration_minutes: number }> {
  try {
    return await fetchApi(`/system-status/offline-mode/${sessionId}/end`, {
      method: 'POST',
      token,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to end offline mode')
    }
    throw error
  }
}

// ==================== Auto-Save Endpoints ====================

export async function autoSave(
  token: string,
  data: { context_type: string; context_id?: string; saved_data: Record<string, unknown> }
): Promise<{ message: string; context_type: string }> {
  try {
    return await fetchApi('/system-status/auto-save', {
      method: 'POST',
      token,
      body: data,
    })
  } catch (_error: unknown) {
    // Auto-save should fail silently - don't throw
    Sentry.captureMessage('Auto-save failed:', 'warning')
    return { message: 'Auto-save failed (offline)', context_type: data.context_type }
  }
}

export async function recoverAutoSaves(
  token: string,
  contextType?: string
): Promise<{ recoverable_items: AutoSaveItem[] }> {
  try {
    const params = contextType ? `?context_type=${contextType}` : ''
    return await fetchApi(`/system-status/auto-save/recover${params}`, { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to recover auto-saves')
    }
    throw error
  }
}

export async function markAutoSaveRecovered(
  token: string,
  entryId: number
): Promise<{ message: string }> {
  try {
    return await fetchApi(`/system-status/auto-save/${entryId}/mark-recovered`, {
      method: 'POST',
      token,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to mark auto-save as recovered')
    }
    throw error
  }
}
