/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchApi } from '@/lib/api-client'

export interface ItemAvailabilityInfo {
  item_id: number
  total_copies: number
  available_copies: number
  on_loan: number
  status: 'available' | 'limited' | 'unavailable'
  next_available_date?: string | null
}

/**
 * Batched copy-level availability for the current results page.
 *
 * Mirrors useShelfStatusMap: one request per results page, consumed as a
 * Map keyed by catalog item id. POST /catalog/batch-availability accepts up
 * to 50 ids per request, which comfortably covers a results page.
 */
export function useAvailabilityMap(itemIds: number[]): Map<number, ItemAvailabilityInfo> {
  // React Query hashes array keys by value, so a fresh array keeps the same cache entry.
  const ids = [...new Set(itemIds)].sort((a, b) => a - b).slice(0, 50)

  const { data = [] } = useQuery({
    queryKey: ['batch-availability', ids],
    queryFn: () =>
      fetchApi<ItemAvailabilityInfo[]>('/catalog/batch-availability', {
        method: 'POST',
        body: { item_ids: ids },
      }),
    enabled: ids.length > 0,
    staleTime: 60 * 1000,
  })

  return useMemo(() => {
    const map = new Map<number, ItemAvailabilityInfo>()
    for (const info of data) {
      map.set(info.item_id, info)
    }
    return map
  }, [data])
}
