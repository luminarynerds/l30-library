/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useCallback } from 'react'
import api from '@/lib/api-client'
import { API_BASE } from '@/api/types'
import { useTranslation } from '@/i18n'

interface Room {
  id: number
  name: string
  description: string | null
  branch_name: string | null
  room_type: string
  capacity: number
  floor: string | null
  room_number: string | null
  amenities: string[]
  requires_approval: boolean
  max_duration_minutes: number
  min_duration_minutes: number
  advance_booking_days: number
  image_url: string | null
  is_active: boolean
}

interface Booking {
  id: number
  room_id: number
  patron_id: number | null
  start_time: string
  end_time: string
  status: string
  purpose: string | null
  attendee_count: number
  equipment_requested: string[]
  approved_at: string | null
  rejection_reason: string | null
  checked_in_at: string | null
  created_at: string | null
  room_name: string | null
}

export type { Room, Booking }

export function useRoomBookings() {
  const { t, language } = useTranslation()
  const [rooms, setRooms] = useState<Room[]>([])
  const [bookings, setBookings] = useState<Booking[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchRooms = useCallback(async (filters?: { room_type?: string; min_capacity?: number }) => {
    setLoading(true)
    setError(null)
    try {
      let url = `${API_BASE}/rooms?`
      if (filters?.room_type) url += `room_type=${filters.room_type}&`
      if (filters?.min_capacity) url += `min_capacity=${filters.min_capacity}&`
      if (language !== 'en') url += `lang=${encodeURIComponent(language)}&`
      const data = await api.get(url)
      setRooms(data.items || [])
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : t('roomBooking.failedToLoadRooms', 'Failed to load rooms'))
    } finally {
      setLoading(false)
    }
  }, [language]) // eslint-disable-line react-hooks/exhaustive-deps -- t intentionally excluded, matches existing pattern

  const fetchBookings = useCallback(async (page = 1) => {
    try {
      const data = await api.get(`${API_BASE}/rooms/my/reservations?upcoming_only=false&page=${page}`)
      setBookings(data.items || [])
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : t('roomBooking.failedToLoadBookings', 'Failed to load bookings'))
    }
  }, [])

  const cancelBooking = useCallback(async (bookingId: number) => {
    await api.delete(`${API_BASE}/rooms/my/reservations/${bookingId}`)
    await fetchBookings()
  }, [fetchBookings])

  const checkInBooking = useCallback(async (bookingId: number) => {
    const result = await api.post(`${API_BASE}/rooms/my/reservations/${bookingId}/check-in`, {})
    await fetchBookings()
    return result
  }, [fetchBookings])

  const createBooking = useCallback(async (data: {
    room_id: number
    start_time: string
    end_time: string
    purpose?: string
    attendee_count?: number
  }) => {
    const result = await api.post(`${API_BASE}/rooms/${data.room_id}/reservations`, data)
    await fetchBookings()
    return result
  }, [fetchBookings])

  return { rooms, bookings, loading, error, fetchRooms, fetchBookings, cancelBooking, checkInBooking, createBooking }
}
