/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useQuery } from '@tanstack/react-query'
import api from '../api/api'

export function usePendingFlagCount(enabled: boolean): number {
  const { data } = useQuery({
    queryKey: ['kb-pending-flags'],
    enabled,
    refetchInterval: 60_000,
    queryFn: async () => {
      const res = await api
        .get('/staff-knowledge/flags', { params: { status: 'pending' } })
        .catch(() => ({ data: [] }))
      return Array.isArray(res.data) ? res.data.length : 0
    },
  })
  return data ?? 0
}
