/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Library migration wizard API client.
 */
import { getAccessToken } from '../utils/tokenStore'
import { API_BASE } from '@/api/types'

const BASE = `${API_BASE}/migration`

export interface MigrationJob {
  id: number
  status: string
  source_system: string
  original_filename: string
  total_rows: number
  processed_rows: number
  failed_rows: number
  progress_percent: number
  error_percent: number
  field_mapping: Record<string, string> | null
  options: Record<string, unknown> | null
  analysis_report: Record<string, unknown> | null
  dry_run_report: Record<string, unknown> | null
  error_log: Record<string, unknown> | null
  created_by_id: number | null
  created_at: string | null
  started_at: string | null
  completed_at: string | null
}

export interface MigrationProgress {
  job_id: number
  status: string
  total_rows: number
  processed_rows: number
  failed_rows: number
  progress_percent: number
  started_at: string | null
  completed_at: string | null
  is_complete: boolean
}

export interface MigrationHistoryItem {
  id: number
  source_system: string
  original_filename: string
  status: string
  total_rows: number
  processed_rows: number
  failed_rows: number
  created_at: string
  completed_at: string | null
}

export interface MigrationHistoryResponse {
  items: MigrationHistoryItem[]
  total: number
  limit: number
  offset: number
}

export interface AnalysisReport {
  detected_columns: string[]
  total_rows: number
  sample_rows: Array<Record<string, string>>
  warnings: string[]
  suggested_mapping: Record<string, string>
  source_system_detected: string
}

export interface DryRunReport {
  would_create: number
  would_update: number
  would_skip: number
  sample_records: Array<Record<string, unknown>>
  warnings: string[]
  validation_errors: Array<Record<string, unknown>>
}

function authHeaders(): Record<string, string> {
  const token = getAccessToken()
  return token ? { Authorization: `Bearer ${token}` } : {}
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Request failed' }))
    throw { status: res.status, message: err.detail || err.error?.message || 'Request failed' }
  }
  return res.json()
}

export const migrationApi = {
  async uploadFile(file: File, sourceSystem: string): Promise<MigrationJob> {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('source_system', sourceSystem)

    const res = await fetch(`${BASE}/upload`, {
      method: 'POST',
      headers: authHeaders(),
      body: formData,
    })
    return handleResponse<MigrationJob>(res)
  },

  async getStatus(jobId: number): Promise<MigrationProgress> {
    const res = await fetch(`${BASE}/${jobId}/status`, { headers: authHeaders() })
    return handleResponse<MigrationProgress>(res)
  },

  async getPreview(jobId: number): Promise<{ job_id: number; status: string; analysis_report: AnalysisReport }> {
    const res = await fetch(`${BASE}/${jobId}/preview`, { headers: authHeaders() })
    return handleResponse(res)
  },

  async configure(
    jobId: number,
    fieldMapping: Record<string, string>,
    options: Record<string, unknown>,
  ): Promise<MigrationJob> {
    const res = await fetch(`${BASE}/${jobId}/configure`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeaders() },
      body: JSON.stringify({ field_mapping: fieldMapping, options }),
    })
    return handleResponse<MigrationJob>(res)
  },

  async dryRun(jobId: number): Promise<{ job_id: number; status: string; dry_run_report: DryRunReport }> {
    const res = await fetch(`${BASE}/${jobId}/dry-run`, {
      method: 'POST',
      headers: authHeaders(),
    })
    return handleResponse(res)
  },

  async execute(jobId: number): Promise<MigrationJob> {
    const res = await fetch(`${BASE}/${jobId}/execute`, {
      method: 'POST',
      headers: authHeaders(),
    })
    return handleResponse<MigrationJob>(res)
  },

  async rollback(jobId: number): Promise<{ job_id: number; status: string; rolled_back: boolean }> {
    const res = await fetch(`${BASE}/${jobId}/rollback`, {
      method: 'POST',
      headers: authHeaders(),
    })
    return handleResponse(res)
  },

  async getHistory(limit = 20, offset = 0): Promise<MigrationHistoryResponse> {
    const res = await fetch(`${BASE}/history?limit=${limit}&offset=${offset}`, { headers: authHeaders() })
    return handleResponse<MigrationHistoryResponse>(res)
  },
}