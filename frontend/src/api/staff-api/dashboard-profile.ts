/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { fetchApi } from '@/lib/api-client'

export type DashboardFunction = "front_desk" | "board_ops" | "board_president" | "marketing" | "kids_services" | "page_shelver"
export type DashboardTone = 'calm' | 'standard' | 'full'

export interface DashboardProfile {
  dashboard_functions: DashboardFunction[] | null
  dashboard_tone: DashboardTone
}

export interface DashboardProfileUpdate {
  dashboard_functions: DashboardFunction[]
  dashboard_tone: DashboardTone
}

export async function getDashboardProfile(token: string): Promise<DashboardProfile> {
  return fetchApi<DashboardProfile>('/staff/dashboard/profile', { token })
}

export async function updateDashboardProfile(
  token: string,
  data: DashboardProfileUpdate,
): Promise<DashboardProfile> {
  return fetchApi<DashboardProfile>('/staff/dashboard/profile', {
    method: 'PUT',
    token,
    body: data,
  })
}
