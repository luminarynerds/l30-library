/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { fetchApi } from '@/lib/api-client'
import { getAccessToken } from '@/utils/tokenStore'
import { API_BASE } from '@/api/types'

// ==================== Types ====================

export type MarcExportFormat = 'marc21' | 'marcxml'

export interface MarcBatchJobResponse {
  id: number
  job_type: string
  status: string
  file_name: string | null
  file_format: string | null
  total_records: number
  processed: number
  created_count: number
  updated_count: number
  skipped: number
  errors: Array<Record<string, unknown>>
  completed_at: string | null
  created_at: string | null
}

export interface MarcBatchJobList {
  items: MarcBatchJobResponse[]
  total: number
  page: number
  per_page: number
}

export interface MarcExportNowParams {
  format: MarcExportFormat
  item_type?: string
  incremental_since?: string
  catalog_item_id?: number
}

export interface MarcExportJobPayload {
  format: string
  item_type?: string
  date_from?: string
  date_to?: string
  incremental_since?: string
  catalog_item_id?: number
  catalog_item_ids?: number[]
}

// ==================== API Functions ====================

export async function exportMarcNow(params: MarcExportNowParams): Promise<Blob> {
  const qs = new URLSearchParams()
  qs.set('format', params.format)
  if (params.item_type) qs.set('item_type', params.item_type)
  if (params.incremental_since) qs.set('incremental_since', params.incremental_since)
  if (params.catalog_item_id !== undefined) qs.set('catalog_item_id', String(params.catalog_item_id))

  const token = getAccessToken()
  const res = await fetch(`${API_BASE}/marc-batch/export/now?${qs.toString()}`, {
    credentials: 'include',
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  if (!res.ok) throw new Error(`MARC export failed (${res.status})`)
  return res.blob()
}

export function createMarcExportJob(payload: MarcExportJobPayload): Promise<MarcBatchJobResponse> {
  return fetchApi<MarcBatchJobResponse>('/marc-batch/export', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function listMarcExportJobs(perPage = 10): Promise<MarcBatchJobList> {
  return fetchApi<MarcBatchJobList>(
    `/marc-batch/jobs?job_type=export&per_page=${perPage}`,
  )
}

export async function downloadMarcExportJob(jobId: number): Promise<Blob> {
  const token = getAccessToken()
  const res = await fetch(`${API_BASE}/marc-batch/export/${jobId}/download`, {
    credentials: 'include',
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  if (!res.ok) throw new Error(`Download failed (${res.status})`)
  return res.blob()
}
