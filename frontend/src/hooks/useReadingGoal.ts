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
  getReadingGoals,
  getGoalProgress,
  setReadingGoal,
  removeReadingGoal,
  type ReadingGoalProgress,
} from '@/api/domains/content/reading-goals-api'

export function useReadingGoal(year: number) {
  const { token } = useAuth()
  const { announceToScreenReader } = useUnifiedAccessibility()
  const queryClient = useQueryClient()
  const [isSaving, setIsSaving] = useState(false)

  const { data: goals = [] } = useQuery({
    queryKey: ['reading-goals', token],
    queryFn: () => getReadingGoals(token!),
    enabled: !!token,
  })

  const { data: progress } = useQuery({
    queryKey: ['reading-goal-progress', year, token],
    queryFn: () => getGoalProgress(token!, year),
    enabled: !!token && goals.some((g) => g.year === year),
    retry: false,
  })

  const currentGoal = goals.find((g) => g.year === year)

  const handleSetGoal = async (targetBooks: number) => {
    if (!token) return
    setIsSaving(true)
    try {
      await setReadingGoal(token, year, targetBooks)
      toast.success(`Goal set: ${targetBooks} books in ${year}`)
      announceToScreenReader(`Reading goal set to ${targetBooks} books for ${year}`)
      queryClient.invalidateQueries({ queryKey: ['reading-goals'] })
      queryClient.invalidateQueries({ queryKey: ['reading-goal-progress'] })
    } catch {
      toast.error('Failed to save reading goal')
    } finally {
      setIsSaving(false)
    }
  }

  const handleRemoveGoal = async () => {
    if (!token) return
    setIsSaving(true)
    try {
      await removeReadingGoal(token, year)
      toast.success('Reading goal removed')
      announceToScreenReader('Reading goal removed')
      queryClient.invalidateQueries({ queryKey: ['reading-goals'] })
      queryClient.invalidateQueries({ queryKey: ['reading-goal-progress'] })
    } catch {
      toast.error('Failed to remove reading goal')
    } finally {
      setIsSaving(false)
    }
  }

  return {
    currentGoal,
    progress: progress as ReadingGoalProgress | undefined,
    goals,
    isSaving,
    handleSetGoal,
    handleRemoveGoal,
  }
}
