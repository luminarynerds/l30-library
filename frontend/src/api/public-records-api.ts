/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */

const API_BASE = import.meta.env.VITE_API_BASE || '/api/v1'
const BASE = `${API_BASE}/public-records`

// ==================== Types ====================

export interface PublicRecordsSubmitPayload {
  requester_name: string
  requester_email: string
  description: string
  preferred_format?: string
  jurisdiction?: string
  meeting_id?: number | null
  committee_id?: number | null
  turnstile_token: string
}

export interface PublicRecordsSubmissionAck {
  tracking_number: string
  response_deadline: string
  status: string
}

export interface PublicRecordsDisclosureLogEntry {
  id: number
  tracking_number: string
  request_type: string
  jurisdiction: string
  requester_name: string
  description: string
  preferred_format: string | null
  date_received: string
  response_deadline: string
  status: string
  response_date: string | null
  response_summary: string | null
  records_provided_count: number | null
  denial_reason: string | null
}

// ==================== API calls ====================

export async function submitPublicRecordsRequest(
  payload: PublicRecordsSubmitPayload,
): Promise<PublicRecordsSubmissionAck> {
  const res = await fetch(`${BASE}/public/submit`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Request failed' }))
    throw { status: res.status, message: err.detail || 'Request failed' }
  }
  return res.json()
}

export async function getPublicDisclosureLog(
  year?: number,
): Promise<PublicRecordsDisclosureLogEntry[]> {
  const url = new URL(`${BASE}/public/disclosure-log`, window.location.origin)
  if (year != null) url.searchParams.set('year', String(year))
  const res = await fetch(url.toString())
  if (!res.ok) {
    throw { status: res.status, message: 'Failed to load disclosure log' }
  }
  return res.json()
}
