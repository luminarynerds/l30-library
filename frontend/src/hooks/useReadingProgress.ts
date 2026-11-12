/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { useAuth } from '@/contexts/AuthContext'
import {
  logProgress,
  getAllLatestProgress,
  getProgressHistory,
  getReadingPace,
  type ProgressLogEntry,
  type ProgressLogInput,
} from '@/api/domains/content/reading-progress-api'

export function useReadingProgress(catalogItemId?: number) {
  const { token } = useAuth()
  const queryClient = useQueryClient()
  const [isLogging, setIsLogging] = useState(false)

  // Latest progress for all books (for hero zone)
  const { data: allLatest = [] } = useQuery({
    queryKey: ['reading-progress-latest', token],
    queryFn: () => getAllLatestProgress(token!),
    enabled: !!token,
  })

  // Progress history for a specific book
  const { data: history = [] } = useQuery({
    queryKey: ['reading-progress-history', token, catalogItemId],
    queryFn: () => getProgressHistory(token!, catalogItemId!),
    enabled: !!token && !!catalogItemId,
  })

  // Pace stats for a specific book
  const { data: paceStats } = useQuery({
    queryKey: ['reading-progress-pace', token, catalogItemId],
    queryFn: () => getReadingPace(token!, catalogItemId!),
    enabled: !!token && !!catalogItemId,
  })

  // Build a map: catalogItemId -> latest progress entry
  const progressMap = new Map<number, ProgressLogEntry>()
  for (const entry of allLatest) {
    progressMap.set(entry.catalog_item_id, entry)
  }

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const handleLogProgress = async (itemId: number, data: ProgressLogInput): Promise<any> => {
    if (!token) return null
    setIsLogging(true)
    try {
      const result = await logProgress(token, itemId, data)
      toast.success('Progress logged!')
      queryClient.invalidateQueries({ queryKey: ['reading-progress-latest'] })
      queryClient.invalidateQueries({ queryKey: ['reading-progress-history'] })
      queryClient.invalidateQueries({ queryKey: ['reading-progress-pace'] })
      queryClient.invalidateQueries({ queryKey: ['reading-milestones'] })
      queryClient.invalidateQueries({ queryKey: ['reading-activity'] })
      return result
    } catch {
      toast.error('Failed to log progress')
      return null
    } finally {
      setIsLogging(false)
    }
  }

  return {
    allLatest,
    history,
    paceStats,
    progressMap,
    isLogging,
    handleLogProgress,
  }
}
