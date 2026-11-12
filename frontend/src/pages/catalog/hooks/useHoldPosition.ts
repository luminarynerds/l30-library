/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useQuery } from '@tanstack/react-query'
import { getMyHolds } from '@/api/api'

export interface HoldPositionInfo {
  hasHold: boolean
  position: number
  totalAhead: number
  estimatedReadyDate: Date | null
  holdStatus: 'pending' | 'ready' | null
}

const STANDARD_CHECKOUT_DAYS = 21

export function useHoldPosition(itemId: number | undefined, token: string | null) {
  const { data: holds } = useQuery({
    queryKey: ['my-holds', token],
    queryFn: () => getMyHolds(token!),
    enabled: !!token && !!itemId,
    staleTime: 30_000,
  })

  const activeHold = holds?.find(
    (h) => h.item_id === itemId && (h.status === 'pending' || h.status === 'ready')
  )

  if (!activeHold) {
    return {
      hasHold: false,
      position: 0,
      totalAhead: 0,
      estimatedReadyDate: null,
      holdStatus: null,
    } as HoldPositionInfo
  }

  const position = activeHold.position
  const totalAhead = Math.max(0, position - 1)
  const estimatedReadyDate = new Date()
  estimatedReadyDate.setDate(estimatedReadyDate.getDate() + totalAhead * STANDARD_CHECKOUT_DAYS)

  return {
    hasHold: true,
    position,
    totalAhead,
    estimatedReadyDate,
    holdStatus: activeHold.status as 'pending' | 'ready',
  } as HoldPositionInfo
}
