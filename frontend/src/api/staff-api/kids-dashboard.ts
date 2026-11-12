/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { fetchApi } from '@/lib/api-client'

export interface KidsProgramSummary {
  id: number
  title: string
  program_date: string
  start_time: string
  end_time: string | null
  location_name: string | null
  audience: string
  registration_count: number
  capacity: number | null
  notes: string | null
}

export interface KidsReadingStats {
  active_program_count: number
  total_enrollments: number
}

export interface KidsDashboardData {
  next_program: KidsProgramSummary | null
  reading_stats: KidsReadingStats
  upcoming_programs: KidsProgramSummary[]
  school_visits: Record<string, unknown>[]
}

export async function getKidsDashboard(token: string): Promise<KidsDashboardData> {
  return fetchApi<KidsDashboardData>('/staff/kids/dashboard', { token })
}

export interface RecordWalkinResponse {
  registration_count: number
}

export async function recordWalkin(
  token: string,
  programId: number,
): Promise<RecordWalkinResponse> {
  return fetchApi<RecordWalkinResponse>(
    `/staff/kids/programs/${programId}/walkin`,
    { method: 'POST', token },
  )
}
