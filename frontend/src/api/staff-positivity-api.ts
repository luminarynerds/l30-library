/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { API_BASE as API_ROOT } from '@/api/types'
export interface PositivityEntry {
  id: number
  entry_type: string
  text: string
  created_at: string
  updated_at: string
  created_by_name?: string
  source: string
  patron_name?: string
  patron_email?: string
  flagged_for_advocacy: boolean
  flagged_at?: string
  flagged_by_name?: string
  moderation_status: string
  moderated_at?: string
  moderated_by_name?: string
  moderation_note?: string
}

export interface PositivityDigest {
  feedback: number
  win: number
  program: number
  thank_you: number
  compliment: number
  story: number
  appreciation: number
  total: number
  advocacy_flagged: number
  patron_submissions: number
  pending_moderation: number
}

export interface PositivityListResponse {
  entries: PositivityEntry[]
  total: number
  page: number
  per_page: number
  pages: number
}

export interface AdvocacyEntriesResponse {
  entries: PositivityEntry[]
  count: number
  period_days: number
}

const API_BASE = `${API_ROOT}/staff/positivity`

export async function createPositivityEntry(
  entryType: string,
  text: string
): Promise<PositivityEntry> {
  const response = await fetch(`${API_BASE}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      entry_type: entryType,
      text,
    }),
  })

  if (!response.ok) {
    throw new Error(`Failed to create positivity entry: ${response.statusText}`)
  }

  return response.json()
}

export async function listPositivityEntries(
  page: number = 1,
  perPage: number = 20,
  entryType?: string,
  source?: string,
  flaggedOnly?: boolean
): Promise<PositivityListResponse> {
  const params = new URLSearchParams({
    page: page.toString(),
    per_page: perPage.toString(),
  })

  if (entryType) {
    params.append('entry_type', entryType)
  }
  if (source) {
    params.append('source', source)
  }
  if (flaggedOnly) {
    params.append('flagged_only', 'true')
  }

  const response = await fetch(`${API_BASE}?${params}`, {
    method: 'GET',
  })

  if (!response.ok) {
    throw new Error(`Failed to fetch positivity entries: ${response.statusText}`)
  }

  return response.json()
}

export async function getPositivityDigest(days: number = 30): Promise<PositivityDigest> {
  const params = new URLSearchParams({
    days: days.toString(),
  })

  const response = await fetch(`${API_BASE}/digest?${params}`, {
    method: 'GET',
  })

  if (!response.ok) {
    throw new Error(`Failed to fetch positivity digest: ${response.statusText}`)
  }

  return response.json()
}

export async function getPositivityEntry(entryId: number): Promise<PositivityEntry> {
  const response = await fetch(`${API_BASE}/${entryId}`, {
    method: 'GET',
  })

  if (!response.ok) {
    throw new Error(`Failed to fetch positivity entry: ${response.statusText}`)
  }

  return response.json()
}

export async function deletePositivityEntry(entryId: number): Promise<void> {
  const response = await fetch(`${API_BASE}/${entryId}`, {
    method: 'DELETE',
  })

  if (!response.ok) {
    throw new Error(`Failed to delete positivity entry: ${response.statusText}`)
  }
}

export async function toggleAdvocacyFlag(
  entryId: number,
  flagged: boolean
): Promise<PositivityEntry> {
  const response = await fetch(`${API_BASE}/${entryId}/flag`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ flagged }),
  })

  if (!response.ok) {
    throw new Error(`Failed to toggle advocacy flag: ${response.statusText}`)
  }

  return response.json()
}

export async function getAdvocacyEntries(days: number = 90): Promise<AdvocacyEntriesResponse> {
  const params = new URLSearchParams({ days: days.toString() })

  const response = await fetch(`${API_BASE}/advocacy?${params}`, {
    method: 'GET',
  })

  if (!response.ok) {
    throw new Error(`Failed to fetch advocacy entries: ${response.statusText}`)
  }

  return response.json()
}

export async function getModerationQueue(
  page: number = 1,
  perPage: number = 20,
  status?: string
): Promise<PositivityListResponse> {
  const params = new URLSearchParams({
    page: page.toString(),
    per_page: perPage.toString(),
  })

  if (status) {
    params.append('moderation_status', status)
  }

  const response = await fetch(`${API_BASE}/moderation?${params}`, {
    method: 'GET',
  })

  if (!response.ok) {
    throw new Error(`Failed to fetch moderation queue: ${response.statusText}`)
  }

  return response.json()
}

export async function moderateEntry(
  entryId: number,
  action: 'approve' | 'reject',
  note?: string
): Promise<PositivityEntry> {
  const response = await fetch(`${API_BASE}/${entryId}/moderate`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ action, note: note || undefined }),
  })

  if (!response.ok) {
    throw new Error(`Failed to moderate entry: ${response.statusText}`)
  }

  return response.json()
}