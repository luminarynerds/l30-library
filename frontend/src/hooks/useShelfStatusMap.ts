/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useAuth } from '@/contexts/AuthContext'
import { getMyReadingStatuses, type ShelfStatus } from '@/api/domains/content/reading-status-api'

export function useShelfStatusMap(): Map<number, ShelfStatus> {
  const { token } = useAuth()

  const { data: allStatuses = [] } = useQuery({
    queryKey: ['reading-statuses', token],
    queryFn: () => getMyReadingStatuses(token!),
    enabled: !!token,
  })

  return useMemo(() => {
    const map = new Map<number, ShelfStatus>()
    for (const s of allStatuses) {
      map.set(s.catalog_item_id, s.status)
    }
    return map
  }, [allStatuses])
}

/** Border color class for a shelf status (left border, for list cards). */
export const SHELF_BORDER_COLORS: Record<ShelfStatus, string> = {
  currently_reading: 'border-l-green-500 dark:border-l-green-400',
  want_to_read: 'border-l-blue-500 dark:border-l-blue-400',
  on_hold: 'border-l-status-warning-500 dark:border-l-status-warning-400',
  finished: 'border-l-gray-400 dark:border-l-gray-500',
  did_not_finish: 'border-l-gray-300 dark:border-l-gray-600',
}

/** Top border variant for grid cards. */
export const SHELF_TOP_BORDER_COLORS: Record<ShelfStatus, string> = {
  currently_reading: 'border-t-green-500 dark:border-t-green-400',
  want_to_read: 'border-t-blue-500 dark:border-t-blue-400',
  on_hold: 'border-t-status-warning-500 dark:border-t-status-warning-400',
  finished: 'border-t-gray-400 dark:border-t-gray-500',
  did_not_finish: 'border-t-gray-300 dark:border-t-gray-600',
}

/** Accessible label for shelf status. */
export const SHELF_STATUS_LABELS: Record<ShelfStatus, string> = {
  want_to_read: 'On your Want to Read shelf',
  currently_reading: 'On your Currently Reading shelf',
  on_hold: 'On your On Hold shelf',
  finished: 'On your Finished shelf',
  did_not_finish: 'On your Did Not Finish shelf',
}
