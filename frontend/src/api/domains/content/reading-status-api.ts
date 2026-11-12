/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { fetchApi } from '@/lib/api-client'
import type { CatalogItem } from '@/api/domains/catalog/catalog-api'

export type ShelfStatus = 'want_to_read' | 'currently_reading' | 'on_hold' | 'finished' | 'did_not_finish'

export interface ReadingStatusRecord {
  id: number
  catalog_item_id: number
  catalog_item: CatalogItem
  status: ShelfStatus
  started_at: string | null
  finished_at: string | null
  private_notes: string | null
  personal_tags: string[]
  created_at: string
  updated_at: string
}

export interface MilestoneEarnedFromStatus {
  id: number
  title: string
  description: string | null
  milestone_key: string
}

export interface ReadingStatusWithMilestone extends ReadingStatusRecord {
  milestone_earned: MilestoneEarnedFromStatus | null
}

export interface ReadingStats {
  want_to_read: number
  currently_reading: number
  on_hold: number
  finished: number
  did_not_finish: number
  finished_this_year: number
}

export async function getMyReadingStatuses(
  token: string,
  status?: ShelfStatus,
  limit = 50,
  offset = 0,
): Promise<ReadingStatusRecord[]> {
   
  const params: Record<string, string | number> = { limit, offset }
  if (status) params.status = status
  return fetchApi<ReadingStatusRecord[]>('/reading-status', { token, params })
}

export async function setReadingStatus(
  token: string,
  catalogItemId: number,
  status: ShelfStatus,
  privateNotes?: string | null,
  personalTags?: string[],
): Promise<ReadingStatusWithMilestone> {
  return fetchApi<ReadingStatusWithMilestone>(`/reading-status/${catalogItemId}`, {
    method: 'PUT',
    token,
    body: { status, private_notes: privateNotes, personal_tags: personalTags ?? [] },
  })
}

export async function removeReadingStatus(
  token: string,
  catalogItemId: number,
): Promise<void> {
  await fetchApi(`/reading-status/${catalogItemId}`, { method: 'DELETE', token })
}

export async function getReadingStats(token: string): Promise<ReadingStats> {
  return fetchApi<ReadingStats>('/reading-status/stats', { token })
}
