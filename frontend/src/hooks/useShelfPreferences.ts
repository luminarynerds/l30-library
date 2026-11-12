/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useQuery, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { useAuth } from '@/contexts/AuthContext'
import {
  getShelfPreferences,
  updateShelfPreferences,
  type ShelfPreferences,
} from '@/api/domains/content/shelf-preferences-api'

export function useShelfPreferences() {
  const { token } = useAuth()
  const queryClient = useQueryClient()

  const { data: preferences } = useQuery({
    queryKey: ['shelf-preferences', token],
    queryFn: () => getShelfPreferences(token!),
    enabled: !!token,
  })

  const handleUpdate = async (data: ShelfPreferences) => {
    if (!token) return
    try {
      await updateShelfPreferences(token, data)
      queryClient.invalidateQueries({ queryKey: ['shelf-preferences'] })
    } catch {
      toast.error('Failed to update preferences')
    }
  }

  return {
    preferences: preferences ?? { show_reading_activity: false, show_pace_stats: false },
    handleUpdate,
  }
}
