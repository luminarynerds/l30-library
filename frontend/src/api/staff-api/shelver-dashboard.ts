/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { fetchApi } from '@/lib/api-client'

export interface ShiftInfo {
  shift_date: string
  scheduled_start: string
  scheduled_end: string
  scheduled_hours: number
  status: string
}

export interface ShelverTask {
  id: string
  label: string
  detail: string | null
  count: number | null
}

export interface ShelverDashboardData {
  shift: ShiftInfo | null
  holds_to_pull: number
  tasks: ShelverTask[]
}

export async function getShelverDashboard(token: string): Promise<ShelverDashboardData> {
  return fetchApi<ShelverDashboardData>('/staff/shelver/dashboard', { token })
}
