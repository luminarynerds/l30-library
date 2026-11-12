/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { api } from '@/lib/api-client'
import { getAccessToken } from '@/utils/tokenStore'

const API_BASE = import.meta.env.VITE_API_BASE || '/api/v1'

export interface TableCount {
  table: string
  rows: number
}

export interface ExportManifest {
  library_system_id: number
  library_system_name: string
  library_system_code: string
  generated_at: string
  counts: TableCount[]
  notes: string[]
}

export interface LibrarySystemSummary {
  id: number
  code: string
  name: string
  legal_name: string | null
  email: string | null
  website: string | null
  is_active: boolean
}

export interface LibrarySystemExport {
  generated_at: string
  schema_version: string
  library_system: LibrarySystemSummary
  regions: Record<string, unknown>[]
  branches: Record<string, unknown>[]
  manifest: ExportManifest
  wipe_instructions: string
}

export async function getDataExportManifest(): Promise<ExportManifest> {
  return api.get('/admin/data-export/manifest')
}

export async function exportLibrarySystem(): Promise<LibrarySystemExport> {
  return api.post('/admin/data-export/library-system')
}

export interface DataExportBundle {
  blob: Blob
  sha256: string | null
  filename: string | null
}

function parseFilename(disposition: string | null): string | null {
  if (!disposition) return null
  // RFC 5987 filename*=UTF-8''... takes precedence, then plain filename="..."
  const star = disposition.match(/filename\*=(?:UTF-8'')?["']?([^"';]+)/i)
  if (star?.[1]) {
    try {
      return decodeURIComponent(star[1])
    } catch {
      return star[1]
    }
  }
  const plain = disposition.match(/filename=["']?([^"';]+)/i)
  return plain?.[1] ?? null
}

export async function exportDataBundle(passphrase: string): Promise<DataExportBundle> {
  const token = getAccessToken()
  const res = await fetch(`${API_BASE}/admin/data-export/bundle`, {
    method: 'POST',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ passphrase }),
  })
  if (!res.ok) {
    throw new Error(`Bundle export failed: ${res.status}`)
  }
  return {
    blob: await res.blob(),
    sha256: res.headers.get('X-Export-SHA256'),
    filename: parseFilename(res.headers.get('Content-Disposition')),
  }
}
