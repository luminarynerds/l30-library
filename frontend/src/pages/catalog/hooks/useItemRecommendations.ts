/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getItemRecommendations, type ItemRecommendation } from '@/api/api'

export function useItemRecommendations(id: number | undefined) {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['item-recommendations', id],
    queryFn: () => getItemRecommendations(Number(id)),
    enabled: !!id,
    staleTime: 60_000,
    retry: false,
  })

  // Available-first, otherwise preserve backend order (pins, then semantic rank)
  const items: ItemRecommendation[] = useMemo(() => {
    if (!data?.items) return []
    return [...data.items].sort((a, b) => {
      if (a.available && !b.available) return -1
      if (b.available && !a.available) return 1
      return 0
    })
  }, [data])

  return { items, isLoading, isError }
}
