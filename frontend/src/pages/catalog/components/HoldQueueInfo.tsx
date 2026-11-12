/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useState } from 'react'
import { fetchApi } from '@/api/fetchApi'

interface HoldQueueData {
  queue_size: number
  estimated_wait_days: number
  total_copies: number
}

/**
 * Queue depth + rough wait estimate for an item with active holds.
 * Renders nothing until the data arrives (no spinner); used on the
 * catalog detail page and inside PlaceHoldModal.
 */
export function HoldQueueInfo({ itemId, status }: { itemId: number; status: string }): React.ReactElement | null {
  const [info, setInfo] = useState<HoldQueueData | null>(null)

  useEffect(() => {
    if (status !== 'checked_out' && status !== 'on_hold') return
    fetchApi(`/catalog/items/${itemId}/hold-queue`)
      .then(setInfo)
      .catch(() => setInfo(null))
  }, [itemId, status])

  if (!info) return null

  if (info.total_copies === 0) {
    return (
      <p className="text-xs text-lsc-dark/60 dark:text-lsc-cream/60 mt-1">
        Not currently in our collection -- your hold reserves a spot if a copy is added.
      </p>
    )
  }

  if (info.queue_size === 0) {
    return <p className="text-xs text-status-success-600 dark:text-status-success-400 mt-1">No wait -- you would be first in line!</p>
  }

  const weeks = Math.ceil(info.estimated_wait_days / 7)
  return (
    <p className="text-xs text-lsc-dark/60 dark:text-lsc-cream/60 mt-1">
      {info.queue_size} {info.queue_size === 1 ? 'person' : 'people'} waiting -- roughly {weeks} {weeks === 1 ? 'week' : 'weeks'}, depending on returns
    </p>
  )
}
