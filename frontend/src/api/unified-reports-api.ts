/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import { fetchApi, isApiError } from '@/lib/api-client'
import { getAccessToken } from '@/utils/tokenStore'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type ReportType = 'circulation' | 'financial' | 'patron_activity' | 'collection' | 'compliance' | 'community_outcomes'
export type OutputFormat = 'json' | 'csv' | 'excel' | 'pdf'

export interface ReportTypesResponse {
  report_types: ReportType[]
  output_formats: OutputFormat[]
}

export interface GenerateReportParams {
  report_type: ReportType
  format?: OutputFormat
  start_date?: string
  end_date?: string
  fiscal_year?: number
  state_code?: string
  branch_id?: number
  use_cache?: boolean
  cache_ttl?: number
}

export interface AsyncReportResponse {
  report_id: string
  report_type: string
  format: string
  status: string
  progress_url: string
  result_url: string
}

export interface ReportProgress {
  report_id: string
  status: 'pending' | 'in_progress' | 'completed' | 'failed'
  progress: number
  message?: string
  error?: string
}

export interface CacheInvalidateResponse {
  status: string
  invalidated: number
  scope: string
}

// ---------------------------------------------------------------------------
// API Functions
// ---------------------------------------------------------------------------

function buildQueryString(params?: Record<string, unknown>): string {
  if (!params || Object.keys(params).length === 0) return ''
  const sp = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null) {
      sp.set(key, String(value))
    }
  })
  return sp.toString() ? `?${sp}` : ''
}

export async function getReportTypes(): Promise<ReportTypesResponse> {
  const token = getAccessToken()
  try {
    return await fetchApi<ReportTypesResponse>('/unified-reports/types', { ...(token ? { token } : {}) })
  } catch (error: unknown) {
    if (isApiError(error)) throw new Error(error.detail || `Request failed with status ${error.status}`)
    throw error
  }
}

export async function generateReport(params: GenerateReportParams): Promise<unknown> {
  const token = getAccessToken()
  const { report_type, ...queryParams } = params
  const query = buildQueryString(queryParams as Record<string, unknown>)
  try {
    return await fetchApi<unknown>(`/unified-reports/generate/${report_type}${query}`, { ...(token ? { token } : {}) })
  } catch (error: unknown) {
    if (isApiError(error)) throw new Error(error.detail || `Request failed with status ${error.status}`)
    throw error
  }
}

export interface GenerateJsonReportResult {
  data: unknown
  cacheHit: boolean
  bytes: number
}

export async function generateJsonReport(params: GenerateReportParams): Promise<GenerateJsonReportResult> {
  const token = getAccessToken()
  const API_BASE = import.meta.env.VITE_API_URL || '/api/v1'
  const { report_type, ...queryParams } = params
  const query = buildQueryString({ ...queryParams, format: 'json' })

  const res = await fetch(`${API_BASE}/unified-reports/generate/${report_type}${query}`, {
    headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}) },
  })
  if (!res.ok) {
    let detail = `Request failed with status ${res.status}`
    try {
      const body = await res.json() as { detail?: string }
      if (body?.detail) detail = body.detail
    } catch { /* non-JSON error body */ }
    throw new Error(detail)
  }
  const text = await res.text()
  return {
    data: text ? JSON.parse(text) : null,
    cacheHit: res.headers.get('X-Cache-Hit') === '1',
    bytes: new Blob([text]).size,
  }
}

export async function generateReportAsync(params: GenerateReportParams): Promise<AsyncReportResponse> {
  const token = getAccessToken()
  const { report_type, ...queryParams } = params
  const query = buildQueryString(queryParams as Record<string, unknown>)
  try {
    return await fetchApi<AsyncReportResponse>(`/unified-reports/generate-async/${report_type}${query}`, {
      method: 'POST',
      ...(token ? { token } : {}),
    })
  } catch (error: unknown) {
    if (isApiError(error)) throw new Error(error.detail || `Request failed with status ${error.status}`)
    throw error
  }
}

export async function getReportProgress(reportId: string): Promise<ReportProgress> {
  const token = getAccessToken()
  try {
    return await fetchApi<ReportProgress>(`/unified-reports/progress/${reportId}`, { ...(token ? { token } : {}) })
  } catch (error: unknown) {
    if (isApiError(error)) throw new Error(error.detail || `Request failed with status ${error.status}`)
    throw error
  }
}

export async function getReportResult(reportId: string): Promise<Blob> {
  const token = getAccessToken()
  const API_BASE = import.meta.env.VITE_API_URL || '/api/v1'
  const res = await fetch(`${API_BASE}/unified-reports/result/${reportId}`, {
    headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}) },
  })
  if (!res.ok) throw new Error(`Failed to download report: ${res.status}`)
  return res.blob()
}

export async function invalidateReportCache(reportType?: ReportType): Promise<CacheInvalidateResponse> {
  const token = getAccessToken()
  const query = reportType ? `?report_type=${reportType}` : ''
  try {
    return await fetchApi<CacheInvalidateResponse>(`/unified-reports/cache/invalidate${query}`, {
      method: 'POST',
      ...(token ? { token } : {}),
    })
  } catch (error: unknown) {
    if (isApiError(error)) throw new Error(error.detail || `Request failed with status ${error.status}`)
    throw error
  }
}

export async function refreshReportData(reportType: ReportType): Promise<CacheInvalidateResponse> {
  const token = getAccessToken()
  try {
    return await fetchApi<CacheInvalidateResponse>(`/unified-reports/cache/${reportType}`, {
      method: 'DELETE',
      ...(token ? { token } : {}),
    })
  } catch (error: unknown) {
    if (isApiError(error)) throw new Error(error.detail || `Request failed with status ${error.status}`)
    throw error
  }
}

export async function downloadReport(params: GenerateReportParams): Promise<void> {
  const token = getAccessToken()
  const API_BASE = import.meta.env.VITE_API_URL || '/api/v1'
  const { report_type, ...queryParams } = params
  const query = buildQueryString(queryParams as Record<string, unknown>)

  try {
    const res = await fetch(`${API_BASE}/unified-reports/generate/${report_type}${query}`, {
      headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    })
    if (!res.ok) throw new Error(`Download failed: ${res.status}`)

    const blob = await res.blob()
    const disposition = res.headers.get('Content-Disposition')
    const filenameMatch = disposition?.match(/filename="(.+)"/)
    const filename = filenameMatch?.[1] || `${report_type}_report.${params.format || 'json'}`

    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  } catch (error) {
    Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
    throw error
  }
}
