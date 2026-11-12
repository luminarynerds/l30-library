/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useQuery } from '@tanstack/react-query'
import { useAuth } from '@/contexts/AuthContext'
import { getReadingActivity } from '@/api/domains/content/reading-activity-api'

export function useReadingActivity(limit = 5, offset = 0) {
  const { token } = useAuth()

  const { data, isLoading } = useQuery({
    queryKey: ['reading-activity', token, limit, offset],
    queryFn: () => getReadingActivity(token!, limit, offset),
    enabled: !!token,
  })

  return {
    activities: data?.items ?? [],
    total: data?.total ?? 0,
    isLoading,
  }
}
