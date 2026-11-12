/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { useAuth } from '@/contexts/AuthContext'
import { useUnifiedAccessibility } from '@/features/accessibility/hooks/useUnifiedAccessibility'
import {
  getMyReadingStatuses,
  setReadingStatus,
  removeReadingStatus,
  getReadingStats,
  type ShelfStatus,
} from '@/api/domains/content/reading-status-api'

const SHELF_LABELS: Record<ShelfStatus, string> = {
  want_to_read: 'Want to Read',
  currently_reading: 'Currently Reading',
  on_hold: 'On Hold',
  finished: 'Finished',
  did_not_finish: 'Did Not Finish',
}

export function useReadingStatus(catalogItemId?: number) {
  const { token } = useAuth()
  const { announceToScreenReader } = useUnifiedAccessibility()
  const queryClient = useQueryClient()
  const [isUpdating, setIsUpdating] = useState(false)

  const { data: allStatuses = [] } = useQuery({
    queryKey: ['reading-statuses', token],
    queryFn: () => getMyReadingStatuses(token!),
    enabled: !!token,
  })

  const { data: stats } = useQuery({
    queryKey: ['reading-stats', token],
    queryFn: () => getReadingStats(token!),
    enabled: !!token,
  })

  const currentStatus = catalogItemId
    ? allStatuses.find((s) => s.catalog_item_id === catalogItemId)
    : undefined

  const invalidateShelfQueries = () => {
    queryClient.invalidateQueries({ queryKey: ['reading-statuses'] })
    queryClient.invalidateQueries({ queryKey: ['reading-stats'] })
    queryClient.invalidateQueries({ queryKey: ['reading-activity'] })
    queryClient.invalidateQueries({ queryKey: ['reading-milestones'] })
    queryClient.invalidateQueries({ queryKey: ['patron-tags'] })
  }

  const handleSetStatus = async (status: ShelfStatus, privateNotes?: string | null, personalTags?: string[]) => {
    if (!token || !catalogItemId) return null
    setIsUpdating(true)
    try {
      const result = await setReadingStatus(token, catalogItemId, status, privateNotes, personalTags)
      const label = SHELF_LABELS[status]
      toast.success(`Moved to ${label}`)
      announceToScreenReader(`Moved to ${label}`)
      invalidateShelfQueries()
      return result
    } catch {
      toast.error('Failed to update reading status')
      announceToScreenReader('Failed to update reading status')
      return null
    } finally {
      setIsUpdating(false)
    }
  }

  const handleRemove = async () => {
    if (!token || !catalogItemId) return
    setIsUpdating(true)
    try {
      await removeReadingStatus(token, catalogItemId)
      toast.success('Removed from shelves')
      announceToScreenReader('Removed from shelves')
      invalidateShelfQueries()
    } catch {
      toast.error('Failed to remove from shelves')
    } finally {
      setIsUpdating(false)
    }
  }

  const quickAdd = async (itemId: number) => {
    if (!token) return
    setIsUpdating(true)
    try {
      await setReadingStatus(token, itemId, 'want_to_read')
      toast.success('Added to Want to Read')
      announceToScreenReader('Added to Want to Read shelf')
      invalidateShelfQueries()
    } catch {
      toast.error('Failed to add to shelf')
      announceToScreenReader('Failed to add to shelf')
    } finally {
      setIsUpdating(false)
    }
  }

  return {
    currentStatus,
    allStatuses,
    stats,
    isUpdating,
    handleSetStatus,
    handleRemove,
    quickAdd,
    SHELF_LABELS,
  }
}
