/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { fetchApi } from "@/lib/api-client"

export interface PIIAccessLogEntry {
  id: number
  user_id: number
  user_name: string | null
  user_role: string
  endpoint: string
  fields_accessed: string[]
  fields_redacted: string[]
  patron_ids_accessed: number[]
  ip_address: string | null
  additional_context: Record<string, unknown> | null
  timestamp: string
}

export interface PIIAccessLogListResponse {
  entries: PIIAccessLogEntry[]
  total: number
  limit: number
  offset: number
}

export interface PIIAccessLogQuery {
  patron_id?: number
  user_id?: number
  endpoint?: string
  since?: string
  until?: string
  limit?: number
  offset?: number
}

export async function fetchPiiAccessLog(
  token: string,
  query: PIIAccessLogQuery,
): Promise<PIIAccessLogListResponse> {
  const params = new URLSearchParams()
  for (const [k, v] of Object.entries(query)) {
    if (v !== undefined && v !== null && v !== "") {
      params.append(k, String(v))
    }
  }
  const qs = params.toString()
  const url = `/staff/pii-access-log${qs ? `?${qs}` : ""}`
  return fetchApi<PIIAccessLogListResponse>(url, {
    method: "GET",
    headers: { Authorization: `Bearer ${token}` },
  })
}
