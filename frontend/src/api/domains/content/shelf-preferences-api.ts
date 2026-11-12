/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { fetchApi } from '@/lib/api-client'

export interface ShelfPreferences {
  show_reading_activity: boolean
  show_pace_stats: boolean
}

export async function getShelfPreferences(token: string): Promise<ShelfPreferences> {
  return fetchApi<ShelfPreferences>('/shelf-preferences', { token })
}

export async function updateShelfPreferences(
  token: string,
  data: ShelfPreferences,
): Promise<ShelfPreferences> {
  return fetchApi<ShelfPreferences>('/shelf-preferences', {
    method: 'PUT',
    token,
    body: data,
  })
}
