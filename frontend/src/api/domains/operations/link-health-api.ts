/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Link Health Monitoring API Service
 *
 * Provides functions for:
 * - Viewing link health status and summaries
 * - Managing alerts
 * - Running manual checks
 * - Configuration management
 *
 * All endpoints require STAFF or ADMIN role.
 */

import { fetchApi, isApiError } from '@/lib/api-client'

// ==================== Types ====================

export type LinkStatus = 'healthy' | 'degraded' | 'broken' | 'timeout' | 'dns_error' | 'ssl_error' | 'redirect_loop' | 'unknown'
export type LinkSource = 'palace' | 'external_resource' | 'catalog_link' | 'lesson_resource' | 'digital_collection' | 'vendor' | 'other'
export type AlertSeverity = 'info' | 'warning' | 'critical';
export type AlertStatus = 'open' | 'acknowledged' | 'resolved';
export interface LinkHealthCheck {
  id: number
  url: string
  status: string
  http_status_code: number | null
  response_time_ms: number | null
  error_message: string | null
  final_url: string | null
  redirect_count: number
  ssl_valid: boolean | null
  ssl_expires_at: string | null
  checked_at: string
}

export interface LinkHealthSummary {
  id: number
  url: string
  source: string
  source_name: string | null
  source_id: number | null
  current_status: string
  last_http_status: number | null
  last_error_message: string | null
  avg_response_time_ms: number | null
  last_response_time_ms: number | null
  total_checks: number
  successful_checks: number
  failed_checks: number
  uptime_percentage: number | null
  consecutive_failures: number
  last_successful_at: string | null
  last_failed_at: string | null
  last_checked_at: string | null
  is_monitored: boolean
  alert_sent: boolean
}

export interface LinkHealthAlert {
  id: number
  url: string
  source: string
  alert_type: string
  severity: AlertSeverity
  message: string
  status: AlertStatus
  acknowledged_by: number | null
  acknowledged_at: string | null
  resolved_at: string | null
  resolution_notes: string | null
  created_at: string
}

export interface LinkHealthStats {
  total_monitored: number
  by_status: Record<string, number>
  by_source: Record<string, number>
  open_alerts: number
  avg_uptime_percentage: number
  last_checked_at?: string | null
}

export interface BulkCheckResponse {
  total: number
  healthy: number
  degraded: number
  broken: number
  errors: number
}

export interface PlatformStatus {
  platforms: Record<string, {
    status: string
    response_time_ms?: number
    error?: string
    last_checked?: string
  }>
}

export interface LinkHealthConfig {
  default_timeout_seconds: number
  default_check_interval_minutes: number
  max_redirects: number
  alert_on_consecutive_failures: number
  alert_on_response_time_ms: number
  degraded_response_time_ms: number
  keep_history_days: number
  monitoring_enabled: boolean
  ssl_check_enabled: boolean
  notify_on_broken: boolean
  notify_on_recovered: boolean
  notification_emails: string[]
  max_concurrent_checks: number
  delay_between_checks_ms: number
}

export interface CheckUrlRequest {
  url: string
  source?: string
  source_name?: string
}

export interface UpdateConfigRequest {
  default_timeout_seconds?: number
  default_check_interval_minutes?: number
  max_redirects?: number
  alert_on_consecutive_failures?: number
  alert_on_response_time_ms?: number
  degraded_response_time_ms?: number
  keep_history_days?: number
  monitoring_enabled?: boolean
  ssl_check_enabled?: boolean
  notify_on_broken?: boolean
  notify_on_recovered?: boolean
  notification_emails?: string[]
}

export interface CleanupResponse {
  deleted_checks: number
  deleted_summaries: number
}

// ==================== Dashboard & Stats ====================

export async function getLinkHealthStats(token: string): Promise<LinkHealthStats> {
  try {
    return await fetchApi<LinkHealthStats>('/link-health/stats', { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch link health stats')
    }
    throw error
  }
}

export async function getBrokenLinks(
  token: string,
  options?: {
    source?: string
    limit?: number
    offset?: number
    includeUnmonitored?: boolean
  }
): Promise<LinkHealthSummary[]> {
  try {
    const params = new URLSearchParams()
    if (options?.source) params.set('source', options.source)
    if (options?.limit) params.set('limit', options.limit.toString())
    if (options?.offset) params.set('offset', options.offset.toString())
    if (options?.includeUnmonitored) params.set('include_unmonitored', 'true')

    const queryString = params.toString() ? `?${params.toString()}` : ''
    return await fetchApi<LinkHealthSummary[]>(`/link-health/broken${queryString}`, { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch broken links')
    }
    throw error
  }
}

export async function getDegradedLinks(
  token: string,
  options?: {
    min_response_time_ms?: number
    limit?: number
    includeUnmonitored?: boolean
  }
): Promise<LinkHealthSummary[]> {
  try {
    const params = new URLSearchParams()
    if (options?.min_response_time_ms) params.set('min_response_time_ms', options.min_response_time_ms.toString())
    if (options?.limit) params.set('limit', options.limit.toString())
    if (options?.includeUnmonitored) params.set('include_unmonitored', 'true')

    const queryString = params.toString() ? `?${params.toString()}` : ''
    return await fetchApi<LinkHealthSummary[]>(`/link-health/degraded${queryString}`, { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch degraded links')
    }
    throw error
  }
}

// ==================== Single URL Operations ====================

export async function checkSingleUrl(
  token: string,
  request: CheckUrlRequest
): Promise<LinkHealthCheck> {
  try {
    return await fetchApi<LinkHealthCheck>('/link-health/check', {
      method: 'POST',
      body: request,
      token,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to check URL')
    }
    throw error
  }
}

export async function getUrlHistory(
  token: string,
  url: string,
  options?: {
    days?: number
    limit?: number
  }
): Promise<LinkHealthCheck[]> {
  try {
    const params = new URLSearchParams()
    params.set('url', url)
    if (options?.days) params.set('days', options.days.toString())
    if (options?.limit) params.set('limit', options.limit.toString())

    return await fetchApi<LinkHealthCheck[]>(`/link-health/history?${params.toString()}`, { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch URL history')
    }
    throw error
  }
}

// ==================== Monitoring Control ====================

export async function setLinkMonitoring(
  summaryId: number,
  isMonitored: boolean,
  token: string
): Promise<LinkHealthSummary> {
  try {
    return await fetchApi<LinkHealthSummary>(`/link-health/links/${summaryId}`, {
      method: 'PATCH',
      body: { is_monitored: isMonitored },
      token,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to update monitoring')
    }
    throw error
  }
}

// ==================== Bulk Operations ====================

export async function checkAllExternalResources(token: string): Promise<BulkCheckResponse> {
  try {
    return await fetchApi<BulkCheckResponse>('/link-health/check/external-resources', {
      method: 'POST',
      token,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to check external resources')
    }
    throw error
  }
}

export async function checkAllLessonResources(token: string): Promise<BulkCheckResponse> {
  try {
    return await fetchApi<BulkCheckResponse>('/link-health/check/lesson-resources', {
      method: 'POST',
      token,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to check lesson resources')
    }
    throw error
  }
}

export async function checkAllCatalogLinks(token: string): Promise<BulkCheckResponse> {
  try {
    return await fetchApi<BulkCheckResponse>('/link-health/check/catalog-links', {
      method: 'POST',
      token,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to check catalog links')
    }
    throw error
  }
}

export async function checkDigitalPlatforms(token: string): Promise<PlatformStatus> {
  try {
    return await fetchApi<PlatformStatus>('/link-health/check/platforms', {
      method: 'POST',
      token,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to check digital platforms')
    }
    throw error
  }
}

// ==================== Alerts ====================

export async function getOpenAlerts(
  token: string,
  options?: {
    severity?: AlertSeverity
    limit?: number
  }
): Promise<LinkHealthAlert[]> {
  try {
    const params = new URLSearchParams()
    if (options?.severity) params.set('severity', options.severity)
    if (options?.limit) params.set('limit', options.limit.toString())

    const queryString = params.toString() ? `?${params.toString()}` : ''
    return await fetchApi<LinkHealthAlert[]>(`/link-health/alerts${queryString}`, { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch alerts')
    }
    throw error
  }
}

export async function acknowledgeAlert(
  token: string,
  alertId: number,
  notes?: string
): Promise<LinkHealthAlert> {
  try {
    return await fetchApi<LinkHealthAlert>(`/link-health/alerts/${alertId}/acknowledge`, {
      method: 'POST',
      body: { notes },
      token,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to acknowledge alert')
    }
    throw error
  }
}

export async function resolveAlert(
  token: string,
  alertId: number,
  notes?: string
): Promise<LinkHealthAlert> {
  try {
    return await fetchApi<LinkHealthAlert>(`/link-health/alerts/${alertId}/resolve`, {
      method: 'POST',
      body: { notes },
      token,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to resolve alert')
    }
    throw error
  }
}

// ==================== Configuration ====================

export async function getLinkHealthConfig(token: string): Promise<LinkHealthConfig> {
  try {
    return await fetchApi<LinkHealthConfig>('/link-health/config', { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch config')
    }
    throw error
  }
}

export async function updateLinkHealthConfig(
  token: string,
  config: UpdateConfigRequest
): Promise<{ message: string; config: LinkHealthConfig }> {
  try {
    return await fetchApi<{ message: string; config: LinkHealthConfig }>('/link-health/config', {
      method: 'PATCH',
      body: config,
      token,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to update config')
    }
    throw error
  }
}

// ==================== Maintenance ====================

export async function cleanupOldData(
  token: string,
  days?: number
): Promise<CleanupResponse> {
  try {
    const params = days ? `?days=${days}` : ''
    return await fetchApi<CleanupResponse>(`/link-health/cleanup${params}`, {
      method: 'POST',
      token,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to cleanup old data')
    }
    throw error
  }
}

// ==================== Utility Functions ====================

export function getStatusColor(status: string): string {
  switch (status.toLowerCase()) {
    case 'healthy':
      return 'text-status-success-600 dark:text-status-success-400 bg-status-success-100 dark:bg-status-success-900/30'
    case 'degraded':
      return 'text-status-warning-600 dark:text-status-warning-400 bg-status-warning-100 dark:bg-status-warning-900/30'
    case 'broken':
      return 'text-status-danger-600 dark:text-status-danger-400 bg-status-danger-100 dark:bg-status-danger-900/30'
    case 'unknown':
    case 'timeout':
    case 'dns_error':
    case 'ssl_error':
    case 'redirect_loop':
      return 'text-earth-600 dark:text-earth-300 bg-earth-100 dark:bg-earth-700'
    default:
      return 'text-earth-600 dark:text-earth-300 bg-earth-100 dark:bg-earth-700'
  }
}

/**
 * Returns Tailwind class pairs for alert severity badges.
 * - info    → blue (neutral informational)
 * - warning → amber (caution)
 * - critical → red (immediate attention)
 * All combinations pass WCAG AA contrast on their respective backgrounds.
 */
export function getSeverityColor(severity: AlertSeverity): string {
  switch (severity) {
    case 'critical':
      return 'text-status-danger-700 dark:text-status-danger-300 bg-status-danger-100 dark:bg-status-danger-900/40'
    case 'warning':
      return 'text-status-warning-700 dark:text-status-warning-300 bg-status-warning-100 dark:bg-status-warning-900/40'
    case 'info':
      return 'text-blue-700 dark:text-blue-300 bg-blue-100 dark:bg-blue-900/40'
  }
}

export function formatResponseTime(ms: number | null): string {
  if (ms === null) return 'N/A'
  if (ms < 1000) return `${Math.round(ms)}ms`
  return `${(ms / 1000).toFixed(2)}s`
}

export function getSourceLabel(source: string): string {
  const labels: Record<string, string> = {
    palace: 'Palace',
    external_resource: 'External Resource',
    catalog_link: 'Catalog Link',
    lesson_resource: 'Lesson Resource',
    digital_collection: 'Digital Collection',
    vendor: 'Vendor',
    other: 'Other',
  }
  return labels[source] || source.replace(/_/g, ' ')
}

/**
 * Available link sources for filtering — aligned to backend LinkSource enum
 */
export const LINK_SOURCES = [
  { value: 'palace', label: 'Palace' },
  { value: 'external_resource', label: 'External Resource' },
  { value: 'catalog_link', label: 'Catalog Link' },
  { value: 'lesson_resource', label: 'Lesson Resource' },
  { value: 'digital_collection', label: 'Digital Collection' },
  { value: 'vendor', label: 'Vendor' },
  { value: 'other', label: 'Other' },
]

/**
 * Alert severity options — aligned to backend LinkHealthAlert severity values
 */
export const ALERT_SEVERITIES: AlertSeverity[] = ['critical', 'warning', 'info']
