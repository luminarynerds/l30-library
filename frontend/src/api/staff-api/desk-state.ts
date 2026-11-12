/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { fetchApi } from "@/lib/api-client"

export interface DeskState {
  holds_to_pull: number
  holds_expiring_today: number
  book_drop_estimate: number
  book_drop_last_cleared: string | null
  holds_shelf_count: number
  holds_expiring_tonight: number
  cash_drawer_open: boolean
  cash_drawer_total: number
}

export interface ScheduleItem {
  id: number
  time: string
  title: string
  location: string | null
  desk_note: string | null
  relative_time: string | null
}

export interface ShiftHandoffNote {
  id: number
  author_name: string
  body: string
  created_at: string
}

export async function getDeskState(token: string): Promise<DeskState> {
  return fetchApi<DeskState>("/staff/desk/state", { token })
}

export async function getTodaySchedule(token: string): Promise<{ items: ScheduleItem[] }> {
  return fetchApi<{ items: ScheduleItem[] }>("/staff/schedule/today", { token })
}

export async function getShiftHandoff(token: string): Promise<ShiftHandoffNote | null> {
  return fetchApi<ShiftHandoffNote | null>("/staff/shift/handoff", { token })
}

export async function postShiftHandoff(token: string, body: string): Promise<ShiftHandoffNote> {
  return fetchApi<ShiftHandoffNote>("/staff/shift/handoff", {
    method: "POST",
    token,
    body: { body },
  })
}
