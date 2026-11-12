/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useQuery } from '@tanstack/react-query'
import { useAuth } from '@/contexts/AuthContext'
import { getDigitalActivity } from '@/api/domains/content/digital-activity-api'
import type { DigitalActivitySummary } from '@/api/domains/content/digital-activity-api'

export function useDigitalActivity() {
  const { isAuthenticated, token: authTk } = useAuth()

  const { data, isLoading, error } = useQuery<DigitalActivitySummary>({
    queryKey: ["digital-activity"],
    queryFn: () => getDigitalActivity(authTk!),
    enabled: isAuthenticated && !!authTk,
    staleTime: 5 * 60 * 1000,
  })

  return {
    activity: data ?? null,
    isLoading,
    isAuthenticated,
    error,
  }
}
