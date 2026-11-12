/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useQuery } from '@tanstack/react-query'
import {
  getAllMoodCategories,
  getPublicMoodCategories,
  type MoodCategory,
} from '@/api/domains/catalog/mood-categories-api'

export function useMoodCategories() {
  return useQuery<MoodCategory[]>({
    queryKey: ['mood-categories', 'public'],
    queryFn: getPublicMoodCategories,
    staleTime: 5 * 60 * 1000,
  })
}

export function useAdminMoodCategories() {
  return useQuery<MoodCategory[]>({
    queryKey: ['mood-categories', 'admin'],
    queryFn: getAllMoodCategories,
    staleTime: 30 * 1000,
  })
}
