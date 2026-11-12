/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { useAuth } from '@/contexts/AuthContext'
import {
  getMilestones,
  dismissMilestone,
  type ReadingMilestone,
} from '@/api/domains/content/reading-milestones-api'

export function useReadingMilestones() {
  const { token } = useAuth()
  const queryClient = useQueryClient()
  const [justEarned, setJustEarned] = useState<ReadingMilestone | null>(null)

  const { data: milestones = [], isLoading } = useQuery({
    queryKey: ['reading-milestones', token],
    queryFn: () => getMilestones(token!),
    enabled: !!token,
  })

  const handleDismiss = async (milestoneId: number) => {
    if (!token) return
    try {
      await dismissMilestone(token, milestoneId)
      queryClient.invalidateQueries({ queryKey: ['reading-milestones'] })
    } catch {
      toast.error('Failed to dismiss milestone')
    }
  }

  const triggerCelebration = (milestone: ReadingMilestone) => {
    setJustEarned(milestone)
    setTimeout(() => setJustEarned(null), 3000)
  }

  return {
    milestones,
    isLoading,
    justEarned,
    handleDismiss,
    triggerCelebration,
  }
}
