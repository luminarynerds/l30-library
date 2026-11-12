/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { fetchApi } from "@/lib/api-client"

// ==================== Types ====================

export type ShelfReadingStatus = "in_progress" | "paused" | "completed" | "cancelled"
export type ScanResult = "in_order" | "out_of_order" | "wrong_shelf"

export interface ShelfReadingSession {
  id: number
  name: string
  description: string | null
  branch_id: number
  location: string
  call_number_start: string | null
  call_number_end: string | null
  status: ShelfReadingStatus
  started_at: string
  completed_at: string | null
  paused_at: string | null
  total_items_scanned: number
  items_in_order: number
  items_out_of_order: number
  items_wrong_shelf: number
  accuracy_percentage: number
  points_earned: number
  created_by_id: number
  created_by_name: string | null
  branch_name: string | null
  created_at: string | null
}

export interface ShelfReadingSessionList {
  items: ShelfReadingSession[]
  total: number
  page: number
  per_page: number
}

export interface ShelfReadingScan {
  id: number
  session_id: number
  item_copy_id: number
  scan_order: number
  scanned_call_number: string | null
  previous_call_number: string | null
  result: ScanResult
  expected_location: string | null
  correct_position_after: string | null
  scanned_at: string
  scanned_by_id: number
  barcode: string | null
  catalog_title: string | null
  catalog_author: string | null
}

export interface ShelfReadingScanList {
  items: ShelfReadingScan[]
  total: number
  session_accuracy: number
}

export interface ShelfReadingProgress {
  session_id: number
  session_name: string
  status: ShelfReadingStatus
  total_items_scanned: number
  items_in_order: number
  items_out_of_order: number
  items_wrong_shelf: number
  accuracy_percentage: number
  last_scanned_call_number: string | null
  points_earned: number
}

export interface SessionCreateData {
  name: string
  description?: string
  branch_id: number
  location: string
  call_number_start?: string
  call_number_end?: string
}

// ==================== Sessions ====================

export function listSessions(params?: {
  branch_id?: number
  status?: ShelfReadingStatus
  page?: number
  per_page?: number
}): Promise<ShelfReadingSessionList> {
  return fetchApi<ShelfReadingSessionList>("/shelf-reading/sessions", { params })
}

export function getSession(id: number): Promise<ShelfReadingSession> {
  return fetchApi<ShelfReadingSession>(`/shelf-reading/sessions/${id}`)
}

export function createSession(data: SessionCreateData): Promise<ShelfReadingSession> {
  return fetchApi<ShelfReadingSession>("/shelf-reading/sessions", {
    method: "POST",
    body: JSON.stringify(data),
  })
}

export function getSessionProgress(id: number): Promise<ShelfReadingProgress> {
  return fetchApi<ShelfReadingProgress>(`/shelf-reading/sessions/${id}/progress`)
}

export function completeSession(id: number): Promise<ShelfReadingSession> {
  return fetchApi<ShelfReadingSession>(`/shelf-reading/sessions/${id}/complete`, {
    method: "POST",
  })
}

export function pauseSession(id: number): Promise<ShelfReadingSession> {
  return fetchApi<ShelfReadingSession>(`/shelf-reading/sessions/${id}/pause`, {
    method: "POST",
  })
}

export function resumeSession(id: number): Promise<ShelfReadingSession> {
  return fetchApi<ShelfReadingSession>(`/shelf-reading/sessions/${id}/resume`, {
    method: "POST",
  })
}

export function cancelSession(id: number): Promise<ShelfReadingSession> {
  return fetchApi<ShelfReadingSession>(`/shelf-reading/sessions/${id}/cancel`, {
    method: "POST",
  })
}

// ==================== Scanning ====================

export function scanItem(sessionId: number, barcode: string): Promise<ShelfReadingScan> {
  return fetchApi<ShelfReadingScan>(`/shelf-reading/sessions/${sessionId}/scan`, {
    method: "POST",
    body: JSON.stringify({ barcode }),
  })
}

export function listSessionScans(sessionId: number): Promise<ShelfReadingScanList> {
  return fetchApi<ShelfReadingScanList>(`/shelf-reading/sessions/${sessionId}/scans`)
}
