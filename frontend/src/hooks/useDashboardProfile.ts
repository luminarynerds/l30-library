/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect, useCallback } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import {
  getDashboardProfile,
  updateDashboardProfile,
  DashboardProfile,
  DashboardProfileUpdate,
} from '@/api/staff-api/dashboard-profile'

export function useDashboardProfile() {
  const { token, isAuthenticated } = useAuth()
  const [profile, setProfile] = useState<DashboardProfile | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    if (!isAuthenticated || !token) return
    setIsLoading(true)
    getDashboardProfile(token)
      .then(setProfile)
      .catch(() => setProfile({ dashboard_functions: null, dashboard_tone: 'standard' }))
      .finally(() => setIsLoading(false))
  }, [isAuthenticated, token])

  const saveProfile = useCallback(async (data: DashboardProfileUpdate) => {
    if (!token) return
    const updated = await updateDashboardProfile(token, data)
    setProfile(updated)
    return updated
  }, [token])

  const needsOnboarding = !isLoading && (!profile?.dashboard_functions || profile.dashboard_functions.length === 0)

  return { profile, isLoading, saveProfile, needsOnboarding }
}
