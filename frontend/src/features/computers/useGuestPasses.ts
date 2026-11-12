/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useCallback } from 'react'
import api from '@/lib/api-client'
import { API_BASE } from '@/api/types'
import type { GuestPass } from '@/types/computer'
import type { GuestPassFormData } from './GuestPassForm'

export function useGuestPasses() {
  const [passes, setPasses] = useState<GuestPass[]>([])
  const [loading, setLoading] = useState(false)

  const list = useCallback(async () => {
    setLoading(true)
    try {
      const data = await api.get(`${API_BASE}/computers/staff/guest-passes`)
      setPasses(data.items || [])
    } finally {
      setLoading(false)
    }
  }, [])

  const create = useCallback(async (data: GuestPassFormData): Promise<GuestPass> => {
    const result = await api.post(`${API_BASE}/computers/guest-passes`, data)
    await list()
    return result
  }, [list])

  return { passes, loading, list, create }
}
