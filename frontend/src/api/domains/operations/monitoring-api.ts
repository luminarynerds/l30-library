/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Monitoring API Service
 *
 * Admin endpoints for monitoring and alerting:
 * - Privacy change monitoring and alerts
 * - Moderation queue status and metrics
 * - System health checks
 * - Alert management and acknowledgment
 *
 * All endpoints require ADMIN or SUPER_ADMIN role.
 */

import { fetchApi, isApiError } from '@/lib/api-client'

// ==================== Types ====================

export type AlertSeverity = 'low' | 'medium' | 'high' | 'critical';
export interface AlertResponse {
  id: number
  severity: string
  description: string
  detected_at: string
  is_acknowledged: boolean
}

export interface PrivacyAlertResponse extends AlertResponse {
  user_id: number
  alert_type: string
  change_count: number
  time_window_minutes: number
  resource_type?: string | null
}

export interface PrivacyAlertsResponse {
  total_alerts: number
  critical_alerts: number
  high_alerts: number
  medium_alerts: number
  low_alerts: number
  alerts: PrivacyAlertResponse[]
}

export interface ModerationAlertResponse extends AlertResponse {
  alert_type: string
  pending_count: number
  overdue_count: number
  oldest_item_age_hours: number
  average_turnaround_hours: number
}

export interface ModerationQueueItem {
  type: string
  count: number
  oldest_age_hours: number
}

export interface ModerationQueueStatus {
  pending: number
  approved: number
  rejected: number
  total_processed: number
  average_turnaround_hours: number
  oldest_pending_hours: number
  alerts: ModerationAlertResponse[]
}

export interface SystemHealthMetric {
  name: string
  value: number
  unit: string
  status: 'healthy' | 'degraded' | 'unhealthy'
  threshold?: number | null
}

export interface SystemHealthSnapshot {
  status: 'healthy' | 'degraded' | 'unhealthy'
  status_reason: string
  share_events_last_hour: number
  share_events_last_24h: number
  db_connection_active: number
  db_connection_idle: number
  db_slow_queries: number
  db_query_avg_time_ms: number
  error_count_last_hour: number
  error_count_last_24h: number
  error_rate_percent: number
  api_response_p50_ms: number
  api_response_p95_ms: number
  api_response_p99_ms: number
  cache_hit_rate_percent: number
  created_at: string
}

export interface SystemHealthResponse {
  current?: SystemHealthSnapshot | null
  trend_24h: SystemHealthSnapshot[]
}

export interface AlertAcknowledgmentRequest {
  notes?: string | null
}

export interface AlertThresholdUpdate {
  warning_level: number
  critical_level: number
  enabled: boolean
}

export interface AlertThreshold {
  id: number
  name: string
  category: string
  description: string
  warning_level: number
  critical_level: number
  time_window_minutes: number
  enabled: boolean
}

export interface AlertThresholdsResponse {
  thresholds: AlertThreshold[]
}

export interface MessageResponse {
  message: string
}

export interface AlertAcknowledgmentResponse {
  message: string
  alert_id: number
}

export interface AlertCheckResult {
  message: string
  alerts_detected: number
  high_severity: number
}

export interface PrivacyAlertsParams {
  unacknowledged_only?: boolean
  hours?: number
  limit?: number
  offset?: number
}

// ==================== API Functions ====================

export async function getPrivacyAlerts(
  token: string,
  params?: PrivacyAlertsParams
): Promise<PrivacyAlertsResponse> {
  try {
    const searchParams = new URLSearchParams()
    if (params?.unacknowledged_only !== undefined) {
      searchParams.set('unacknowledged_only', params.unacknowledged_only.toString())
    }
    if (params?.hours !== undefined) {
      searchParams.set('hours', params.hours.toString())
    }
    if (params?.limit !== undefined) {
      searchParams.set('limit', params.limit.toString())
    }
    if (params?.offset !== undefined) {
      searchParams.set('offset', params.offset.toString())
    }

    const queryString = searchParams.toString() ? `?${searchParams.toString()}` : ''
    return await fetchApi<PrivacyAlertsResponse>(
      `/admin/monitoring/privacy-alerts${queryString}`,
      { token }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch privacy alerts')
    }
    throw error
  }
}

export async function acknowledgePrivacyAlert(
  token: string,
  alertId: number,
  request?: AlertAcknowledgmentRequest
): Promise<AlertAcknowledgmentResponse> {
  try {
    return await fetchApi<AlertAcknowledgmentResponse>(
      `/admin/monitoring/privacy-alerts/${alertId}/acknowledge`,
      {
        token,
        method: 'POST',
        body: request || {},
      }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to acknowledge privacy alert')
    }
    throw error
  }
}

export async function getModerationQueueStatus(
  token: string
): Promise<ModerationQueueStatus> {
  try {
    return await fetchApi<ModerationQueueStatus>(
      `/admin/monitoring/moderation-queue-status`,
      { token }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch moderation queue status')
    }
    throw error
  }
}

export async function resolveModerationAlert(
  token: string,
  alertId: number
): Promise<AlertAcknowledgmentResponse> {
  try {
    return await fetchApi<AlertAcknowledgmentResponse>(
      `/admin/monitoring/moderation-alerts/${alertId}/resolve`,
      {
        token,
        method: 'POST',
      }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to resolve moderation alert')
    }
    throw error
  }
}

export async function getSystemHealth(
  token: string
): Promise<SystemHealthResponse> {
  try {
    return await fetchApi<SystemHealthResponse>(
      `/admin/monitoring/system-health`,
      { token }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch system health')
    }
    throw error
  }
}

export async function checkPrivacyAlerts(
  token: string
): Promise<AlertCheckResult> {
  try {
    return await fetchApi<AlertCheckResult>(
      `/admin/monitoring/check-privacy-alerts`,
      {
        token,
        method: 'POST',
      }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to check privacy alerts')
    }
    throw error
  }
}

export async function checkModerationAlerts(
  token: string
): Promise<AlertCheckResult> {
  try {
    return await fetchApi<AlertCheckResult>(
      `/admin/monitoring/check-moderation-alerts`,
      {
        token,
        method: 'POST',
      }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to check moderation alerts')
    }
    throw error
  }
}

export async function sendDailyDigest(
  token: string
): Promise<MessageResponse> {
  try {
    return await fetchApi<MessageResponse>(
      `/admin/monitoring/send-daily-digest`,
      {
        token,
        method: 'POST',
      }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to send daily digest')
    }
    throw error
  }
}

export async function getAlertThresholds(
  token: string,
  category?: string
): Promise<AlertThresholdsResponse> {
  try {
    const queryString = category ? `?category=${encodeURIComponent(category)}` : ''
    return await fetchApi<AlertThresholdsResponse>(
      `/admin/monitoring/thresholds${queryString}`,
      { token }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch alert thresholds')
    }
    throw error
  }
}

export async function updateAlertThreshold(
  token: string,
  thresholdId: number,
  update: AlertThresholdUpdate
): Promise<AlertAcknowledgmentResponse> {
  try {
    return await fetchApi<AlertAcknowledgmentResponse>(
      `/admin/monitoring/thresholds/${thresholdId}`,
      {
        token,
        method: 'PUT',
        body: update,
      }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to update alert threshold')
    }
    throw error
  }
}

// ==================== Utility Functions ====================

export function getSeverityColor(severity: string): string {
  const colors: Record<string, string> = {
    critical: 'bg-status-danger-100 text-status-danger-800 border-status-danger-200',
    high: 'bg-status-warning-100 text-status-warning-800 border-status-warning-200',
    medium: 'bg-status-warning-100 text-status-warning-800 border-status-warning-200',
    low: 'bg-earth-100 text-earth-800 border-earth-200',
  }
  return colors[severity.toLowerCase()] || 'bg-earth-100 text-earth-800 dark:bg-earth-900/30 dark:text-earth-300 border-earth-200'
}

export function getHealthStatusColor(status: string): string {
  const colors: Record<string, string> = {
    healthy: 'bg-status-success-100 text-status-success-800 border-status-success-200',
    degraded: 'bg-status-warning-100 text-status-warning-800 border-status-warning-200',
    unhealthy: 'bg-status-danger-100 text-status-danger-800 border-status-danger-200',
  }
  return colors[status.toLowerCase()] || 'bg-earth-100 text-earth-800 dark:bg-earth-900/30 dark:text-earth-300 border-earth-200'
}

export function formatAlertType(alertType: string): string {
  return alertType
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (l) => l.toUpperCase())
}

export function formatTimeWindow(minutes: number): string {
  if (minutes < 60) {
    return `${minutes} minute${minutes !== 1 ? 's' : ''}`
  }
  const hours = Math.floor(minutes / 60)
  const remainingMinutes = minutes % 60
  if (remainingMinutes === 0) {
    return `${hours} hour${hours !== 1 ? 's' : ''}`
  }
  return `${hours}h ${remainingMinutes}m`
}

/** Threshold categories for filtering */
export const THRESHOLD_CATEGORIES = [
  { value: 'privacy', label: 'Privacy Alerts' },
  { value: 'moderation', label: 'Moderation Alerts' },
  { value: 'system', label: 'System Health' },
]

/** Alert severity options */
export const ALERT_SEVERITIES: AlertSeverity[] = ['critical', 'high', 'medium', 'low']
