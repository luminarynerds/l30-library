/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { api } from '@/lib/api-client'

export interface MoodCategory {
  id: number
  label: string
  slug: string
  icon: string
  tags: string[]
  keywords: string[]
  display_order: number
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface MoodCategoryCreatePayload {
  label: string
  slug: string
  icon: string
  tags: string[]
  keywords: string[]
  display_order?: number
  is_active?: boolean
}

export type MoodCategoryUpdatePayload = Partial<MoodCategoryCreatePayload>

export const ALLOWED_MOOD_TAGS = [
  'Calm',
  'Gentle',
  'Funny',
  'Hopeful',
  'Intense',
  'Dark',
  'Mind-bending',
  'Personal',
  'Fast-paced',
] as const

export type MoodTag = (typeof ALLOWED_MOOD_TAGS)[number]

export function getPublicMoodCategories(): Promise<MoodCategory[]> {
  return api.get<MoodCategory[]>('/mood-categories')
}

export function getAllMoodCategories(): Promise<MoodCategory[]> {
  return api.get<MoodCategory[]>('/admin/mood-categories')
}

export function createMoodCategory(
  payload: MoodCategoryCreatePayload
): Promise<MoodCategory> {
  return api.post<MoodCategory>('/admin/mood-categories', payload)
}

export function updateMoodCategory(
  id: number,
  payload: MoodCategoryUpdatePayload
): Promise<MoodCategory> {
  return api.patch<MoodCategory>(`/admin/mood-categories/${id}`, payload)
}

export function deleteMoodCategory(id: number): Promise<void> {
  return api.delete<void>(`/admin/mood-categories/${id}`)
}

export function reorderMoodCategories(ids: number[]): Promise<MoodCategory[]> {
  return api.patch<MoodCategory[]>('/admin/mood-categories/reorder', { ids })
}
