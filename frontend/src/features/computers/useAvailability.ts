/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useCallback } from 'react'
import api from '@/lib/api-client'
import { API_BASE } from '@/api/types'

interface AvailabilitySlot {
  start_time: string
  end_time: string
  is_available: boolean
}

export type { AvailabilitySlot }

export function useAvailability() {
  const [slots, setSlots] = useState<AvailabilitySlot[]>([])
  const [loading, setLoading] = useState(false)

  const fetchAvailability = useCallback(async (date: string, computerId?: number) => {
    setLoading(true)
    try {
      let url = `${API_BASE}/computers/availability?date=${date}`
      if (computerId) url += `&computer_id=${computerId}`
      const data = await api.get(url)
      setSlots(data.slots || [])
    } catch {
      setSlots([])
    } finally {
      setLoading(false)
    }
  }, [])

  return { slots, loading, fetchAvailability }
}