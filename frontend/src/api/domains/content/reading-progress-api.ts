/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { fetchApi } from '@/lib/api-client'

export interface ProgressLogEntry {
  id: number
  catalog_item_id: number
  current_page: number | null
  total_pages: number | null
  percent: number
  note: string | null
  logged_at: string
  created_at: string
}

export interface PaceStats {
  avg_pages_per_day: number
  estimated_finish_date: string | null
  entries_count: number
}

export interface MilestoneEarned {
  id: number
  title: string
  description: string | null
  milestone_key: string
}

export interface ProgressLogWithMilestone extends ProgressLogEntry {
  milestone_earned: MilestoneEarned | null
}

export interface ProgressLogInput {
  current_page?: number | null
  total_pages?: number | null
  percent?: number | null
  note?: string | null
}

export async function logProgress(
  token: string,
  catalogItemId: number,
  data: ProgressLogInput,
): Promise<ProgressLogWithMilestone> {
  return fetchApi<ProgressLogWithMilestone>(`/reading-progress/${catalogItemId}`, {
    method: 'POST',
    token,
    body: data,
  })
}

export async function getProgressHistory(
  token: string,
  catalogItemId: number,
  limit = 20,
): Promise<ProgressLogEntry[]> {
  return fetchApi<ProgressLogEntry[]>(`/reading-progress/${catalogItemId}`, {
    token,
    params: { limit },
  })
}

export async function getReadingPace(
  token: string,
  catalogItemId: number,
): Promise<PaceStats | null> {
  return fetchApi<PaceStats | null>(`/reading-progress/${catalogItemId}/pace`, {
    token,
  })
}

export async function getAllLatestProgress(
  token: string,
): Promise<ProgressLogEntry[]> {
  return fetchApi<ProgressLogEntry[]>('/reading-progress/all/latest', { token })
}
