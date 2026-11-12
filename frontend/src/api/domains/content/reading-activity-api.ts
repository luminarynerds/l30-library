/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { fetchApi } from '@/lib/api-client'

export interface ReadingActivityEntry {
  id: number
  catalog_item_id: number | null
  activity_type: string
  summary: string
  metadata_json: string | null
  occurred_at: string
}

export interface ReadingActivityList {
  items: ReadingActivityEntry[]
  total: number
}

export async function getReadingActivity(
  token: string,
  limit = 5,
  offset = 0,
): Promise<ReadingActivityList> {
  return fetchApi<ReadingActivityList>('/reading-activity', {
    token,
    params: { limit, offset },
  })
}
