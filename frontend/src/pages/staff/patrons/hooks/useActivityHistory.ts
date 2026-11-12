/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Hook for managing patron activity history
 */

import { useState, useCallback } from "react"
import {
  getPatronActivity,
  PatronActivity,
} from "../../../../api/staff-api"
import toast from "react-hot-toast"

interface UseActivityHistoryReturn {
  showActivityTimeline: boolean
  activityHistory: PatronActivity[]
  isLoadingActivity: boolean
  selectedActivity: PatronActivity | null
  setShowActivityTimeline: (show: boolean) => void
  setSelectedActivity: (activity: PatronActivity | null) => void
  loadActivityData: (token: string, patronId: number) => Promise<void>
}

export function useActivityHistory(): UseActivityHistoryReturn {
  const [showActivityTimeline, setShowActivityTimeline] = useState(false)
  const [activityHistory, setActivityHistory] = useState<PatronActivity[]>([])
  const [isLoadingActivity, setIsLoadingActivity] = useState(false)
  const [selectedActivity, setSelectedActivity] = useState<PatronActivity | null>(null)

  const loadActivityData = useCallback(async (token: string, patronId: number) => {
    setIsLoadingActivity(true)
    try {
      const response = await getPatronActivity(token, patronId, { page: 1, perPage: 100 })
      setActivityHistory(response.activities)
    } catch (_err) {
      toast.error("Failed to load activity data")
    } finally {
      setIsLoadingActivity(false)
    }
  }, [])

  return {
    showActivityTimeline,
    activityHistory,
    isLoadingActivity,
    selectedActivity,
    setShowActivityTimeline,
    setSelectedActivity,
    loadActivityData,
  }
}
