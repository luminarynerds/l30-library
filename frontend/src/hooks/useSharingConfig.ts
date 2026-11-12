/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useQuery } from '@tanstack/react-query'
import { fetchApi } from '@/lib/api-client'
import type { SharingConfig } from '@/api/utils/share-service'

export function useSharingConfig() {
  return useQuery<SharingConfig | null>({
    queryKey: ['sharing-config'],
    queryFn: async () => {
      try {
        return await fetchApi<SharingConfig>('/sharing/config', { method: 'GET' })
      } catch {
        return null
      }
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
    gcTime: 10 * 60 * 1000,   // 10 minutes
    refetchOnWindowFocus: false,
  })
}
