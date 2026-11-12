/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Migration project API client — multi-phase library migration.
 */
import { getAccessToken } from '../utils/tokenStore'
import { API_BASE } from '@/api/types'

const BASE = `${API_BASE}/migration-project`

// ── Types ─────────────────────────────────────────────────────────────────

export interface MigrationPhase {
  phase: string
  status: string
  import_job_id: number | null
  total_records: number
  created_records: number
  error_records: number
  skipped_records: number
  progress_percent: number
  started_at: string | null
  completed_at: string | null
}

export interface MigrationProjectData {
  id: number
  name: string
  status: string
  cutover_strategy: string | null
  source_system_name: string | null
  source_system_type: string | null
  estimated_catalog_size: number | null
  estimated_patron_count: number | null
  assessment_report: Record<string, unknown> | null
  phases: MigrationPhase[]
  created_at: string | null
  started_at: string | null
  completed_at: string | null
}

export interface ProjectListResponse {
  items: MigrationProjectData[]
  total: number
  limit: number
  offset: number
}

export interface PhaseUploadResult {
  phase: string
  status: string
  import_job_id?: number
  total_rows?: number
  error_rows?: number
  validation_report?: Record<string, unknown>
  report?: Record<string, unknown>
}

export interface PhaseExecuteResult {
  phase: string
  status: string
  created?: number
  updated?: number
  skipped?: number
  errors?: number
}

// ── Helpers ───────────────────────────────────────────────────────────────

function authHeaders(): Record<string, string> {
  const token = getAccessToken()
  return token ? { Authorization: `Bearer ${token}` } : {}
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Request failed' }))
    throw { status: res.status, message: err.detail || 'Request failed' }
  }
  return res.json()
}

// ── API ───────────────────────────────────────────────────────────────────

export const migrationProjectApi = {
  async createProject(data: {
    name: string
    source_system_name?: string | undefined
    source_system_type?: string | undefined
    cutover_strategy?: string | undefined
    estimated_catalog_size?: number | undefined
    estimated_patron_count?: number | undefined
    notes?: string | undefined
  }): Promise<MigrationProjectData> {
    const res = await fetch(`${BASE}/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeaders() },
      body: JSON.stringify(data),
    })
    return handleResponse<MigrationProjectData>(res)
  },

  async listProjects(limit = 20, offset = 0): Promise<ProjectListResponse> {
    const res = await fetch(`${BASE}/?limit=${limit}&offset=${offset}`, {
      headers: authHeaders(),
    })
    return handleResponse<ProjectListResponse>(res)
  },

  async getProject(projectId: number): Promise<MigrationProjectData> {
    const res = await fetch(`${BASE}/${projectId}`, { headers: authHeaders() })
    return handleResponse<MigrationProjectData>(res)
  },

  async uploadPhaseFile(
    projectId: number,
    phase: string,
    file: File,
    duplicateAction = 'skip',
    errorThreshold = 10.0,
  ): Promise<PhaseUploadResult> {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('duplicate_action', duplicateAction)
    formData.append('error_threshold', String(errorThreshold))

    const res = await fetch(`${BASE}/${projectId}/phases/${phase}/upload`, {
      method: 'POST',
      headers: authHeaders(),
      body: formData,
    })
    return handleResponse<PhaseUploadResult>(res)
  },

  async dryRunPhase(projectId: number, phase: string): Promise<Record<string, unknown>> {
    const res = await fetch(`${BASE}/${projectId}/phases/${phase}/dry-run`, {
      method: 'POST',
      headers: authHeaders(),
    })
    return handleResponse(res)
  },

  async executePhase(
    projectId: number,
    phase: string,
    batchSize = 100,
  ): Promise<PhaseExecuteResult> {
    const res = await fetch(`${BASE}/${projectId}/phases/${phase}/execute?batch_size=${batchSize}`, {
      method: 'POST',
      headers: authHeaders(),
    })
    return handleResponse<PhaseExecuteResult>(res)
  },

  async rollbackPhase(projectId: number, phase: string): Promise<Record<string, unknown>> {
    const res = await fetch(`${BASE}/${projectId}/phases/${phase}/rollback`, {
      method: 'POST',
      headers: authHeaders(),
    })
    return handleResponse(res)
  },

  async getReport(projectId: number): Promise<Record<string, unknown>> {
    const res = await fetch(`${BASE}/${projectId}/report`, { headers: authHeaders() })
    return handleResponse(res)
  },
}
