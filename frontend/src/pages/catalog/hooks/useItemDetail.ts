/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useQuery } from '@tanstack/react-query'
import { getCatalogItem } from '@/api/api'

export function useItemDetail(id: number | undefined) {
  const {
    data: item,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ['catalog-item', id],
    queryFn: () => getCatalogItem(Number(id)),
    enabled: !!id,
    refetchInterval: 60_000,
  })

  return { item, isLoading, error, refetch }
}
