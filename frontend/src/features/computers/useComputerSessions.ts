/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useCallback } from 'react'
import api from '@/lib/api-client'
import { API_BASE } from '@/api/types'

interface ComputerStation {
  id: number
  name: string
  computer_number: string
  location: string | null
  computer_type: string
  status: string
  is_active: boolean
  max_session_minutes: number
  is_extendable: boolean
  has_internet: boolean
  installed_software: string[]
  accessibility_features: string[]
}

interface Reservation {
  id: number
  computer_id: number
  patron_id: number | null
  reserved_start_time: string
  reserved_end_time: string
  status: string
  session_duration_minutes: number
  checked_in_at: string | null
  actual_start_time: string | null
  actual_end_time: string | null
  extensions_used: number
  extended_until: string | null
  created_at: string
}

export type { ComputerStation, Reservation }

export function useComputerSessions() {
  const [stations, setStations] = useState<ComputerStation[]>([])
  const [reservations, setReservations] = useState<Reservation[]>([])
  const [currentSession, setCurrentSession] = useState<Reservation | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchStations = useCallback(async () => {
    setLoading(true)
    try {
      const data = await api.get(`${API_BASE}/computers/stations`)
      setStations(data.items || [])
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load stations')
    } finally {
      setLoading(false)
    }
  }, [])

  const fetchReservations = useCallback(async () => {
    try {
      const data = await api.get(`${API_BASE}/computers/reservations/mine`)
      setReservations(data.items || [])
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load reservations')
    }
  }, [])

  const fetchCurrentSession = useCallback(async () => {
    try {
      const data = await api.get(`${API_BASE}/computers/sessions/current`)
      setCurrentSession(data)
    } catch {
      setCurrentSession(null)
    }
  }, [])

  const createReservation = useCallback(async (computerId: number, startTime: string, durationMinutes: number) => {
    return api.post(`${API_BASE}/computers/reservations/book`, {
      computer_id: computerId,
      start_time: startTime,
      duration_minutes: durationMinutes,
    })
  }, [])

  const cancelReservation = useCallback(async (reservationId: number) => {
    await api.delete(`${API_BASE}/computers/reservations/${reservationId}`)
    await fetchReservations()
  }, [fetchReservations])

  const checkIn = useCallback(async (reservationId: number) => {
    await api.post(`${API_BASE}/computers/reservations/${reservationId}/check-in`, {})
    await fetchCurrentSession()
    await fetchReservations()
  }, [fetchCurrentSession, fetchReservations])

  const startSession = useCallback(async (computerId: number, durationMinutes = 60) => {
    const result = await api.post(`${API_BASE}/computers/sessions/start`, {
      computer_id: computerId,
      duration_minutes: durationMinutes,
    })
    setCurrentSession(result)
    return result
  }, [])

  const extendSession = useCallback(async (extraMinutes = 30) => {
    const result = await api.post(`${API_BASE}/computers/sessions/extend`, { extra_minutes: extraMinutes })
    setCurrentSession(result)
    return result
  }, [])

  const endSession = useCallback(async () => {
    await api.post(`${API_BASE}/computers/sessions/end`, {})
    setCurrentSession(null)
  }, [])

  return {
    stations, reservations, currentSession, loading, error,
    fetchStations, fetchReservations, fetchCurrentSession,
    createReservation, cancelReservation, checkIn,
    startSession, extendSession, endSession,
  }
}