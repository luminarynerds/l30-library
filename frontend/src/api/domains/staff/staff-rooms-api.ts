/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Staff Room Management API
 *
 * API functions for managing rooms, reservations, equipment, and reports.
 * Corresponds to backend endpoints in /staff/rooms/*
 */

import { fetchApi, isApiError } from '@/lib/api-client'

// ==================== Types ====================

export interface StaffRoom {
  id: number
  name: string
  room_type: string
  capacity: number
  description?: string
  location?: string
  floor?: string
  building?: string
  branch_id?: number
  amenities?: string[]
  photos?: string[]
  is_active: boolean
  requires_approval: boolean
  max_booking_hours?: number
  advance_booking_days?: number
  min_notice_hours?: number
  operating_hours?: OperatingHours
  available_equipment?: RoomEquipmentItem[]
  created_at?: string
  updated_at?: string
}

export interface OperatingHours {
  monday?: DayHours
  tuesday?: DayHours
  wednesday?: DayHours
  thursday?: DayHours
  friday?: DayHours
  saturday?: DayHours
  sunday?: DayHours
}

export interface DayHours {
  open: string  // HH:MM format
  close: string // HH:MM format
  is_open: boolean
}

export interface RoomEquipmentItem {
  name: string
  quantity: number
}

export interface StaffRoomCreate {
  name: string
  room_type: string
  capacity: number
  description?: string
  location?: string
  floor?: string
  building?: string
  branch_id?: number
  amenities?: string[]
  photos?: string[]
  is_active?: boolean
  requires_approval?: boolean
  max_booking_hours?: number
  advance_booking_days?: number
  min_notice_hours?: number
  operating_hours?: OperatingHours
  available_equipment?: RoomEquipmentItem[]
}

export type StaffRoomUpdate = Partial<StaffRoomCreate>

export interface StaffRoomListResponse {
  items: StaffRoom[]
  total: number
  page: number
  per_page: number
}

// Reservation Types
export interface StaffReservation {
  id: number
  room_id: number
  patron_id?: number
  start_time: string
  end_time: string
  status: string
  purpose?: string
  attendee_count?: number
  contact_name?: string
  contact_email?: string
  contact_phone?: string
  room_name?: string
  patron_name?: string
  approver_name?: string
  is_recurring?: boolean
  recurrence_pattern?: string
  is_staff_override?: boolean
  override_reason?: string
  internal_notes?: string
  created_at?: string
}

export interface StaffReservationDetail extends StaffReservation {
  room?: StaffRoom
  checked_in_at?: string
  cancelled_at?: string
  cancelled_by?: number
  cancellation_reason?: string
  approved_by?: number
  approved_at?: string
  rejection_reason?: string
  child_reservations?: ChildReservation[]
}

export interface ChildReservation {
  id: number
  start_time: string
  end_time: string
  status: string
}

export interface ReservationListResponse {
  items: StaffReservation[]
  total: number
  page: number
  per_page: number
}

export interface ReservationApproval {
  approved: boolean
  rejection_reason?: string
  rejection_reason_code?: string
  internal_notes?: string
}

export interface ReservationCancellation {
  reason: string
}

export interface StaffOverrideCreate {
  room_id: number
  patron_id?: number
  start_time: string
  end_time: string
  purpose: string
  override_reason: string
  contact_name?: string
  contact_email?: string
  internal_notes?: string
}

// Equipment Types
export interface StaffEquipment {
  id: number
  name: string
  equipment_code: string
  description?: string
  category?: string
  room_id?: number
  is_active: boolean
  requires_checkout: boolean
  created_at?: string
  updated_at?: string
}

export interface StaffEquipmentCreate {
  name: string
  equipment_code: string
  description?: string
  category?: string
  room_id?: number
  is_active?: boolean
  requires_checkout?: boolean
}

export type StaffEquipmentUpdate = Partial<StaffEquipmentCreate>

// Patron Reservation Types (for public room booking endpoints)
export interface PatronReservationCreate {
  room_id: number
  start_time: string
  end_time: string
  purpose: string
  attendee_count: number
  equipment_requested?: string[]
  contact_name?: string
  contact_email?: string
  contact_phone?: string
  is_recurring?: boolean
  recurrence_pattern?: 'weekly' | 'biweekly' | 'monthly'
  recurrence_end_date?: string
}

export type PatronReservationUpdate = Partial<PatronReservationCreate>

export interface PatronReservation {
  id: number
  room_id: number
  patron_id?: number
  start_time: string
  end_time: string
  status: string
  purpose?: string
  attendee_count?: number
  equipment_requested?: string[]
  contact_name?: string
  contact_email?: string
  contact_phone?: string
  room_name?: string
  patron_name?: string
  is_recurring?: boolean
  recurrence_pattern?: string
  checked_in_at?: string
  created_at?: string
}

export interface PatronReservationListResponse {
  items: PatronReservation[]
  total: number
  page: number
  per_page: number
}

// Report Types
export interface RoomUtilizationReport {
  room_id: number
  room_name: string
  period_start: string
  period_end: string
  total_reservations: number
  completed_reservations: number
  cancelled_reservations: number
  no_show_count: number
  no_show_rate: number
  total_hours_available: number
  total_hours_booked: number
  utilization_rate: number
  average_booking_duration_minutes: number
  total_attendees: number
  average_attendees_per_booking: number
}

export interface PopularTimesReport {
  room_id?: number
  room_name?: string
  day_of_week: Record<string, number>
  hourly_distribution: Record<number, number>
  peak_hour?: number
  peak_day?: string
}

export interface NoShowReport {
  period_start: string
  period_end: string
  total_reservations: number
  no_show_count: number
  no_show_rate: number
  by_room: RoomNoShowData[]
  by_day_of_week: Record<string, number>
  repeat_no_show_patrons: RepeatNoShowPatron[]
}

export interface RoomNoShowData {
  room_id: number
  room_name: string
  no_show_count: number
}

export interface RepeatNoShowPatron {
  patron_id: number
  name: string
  email: string
  no_show_count: number
}

// ==================== Room Management ====================

export async function getStaffRooms(
  token: string,
  options?: {
    include_inactive?: boolean
    room_type?: string
    branch_id?: number
    page?: number
    per_page?: number
  }
): Promise<StaffRoomListResponse> {
  try {
    const params = new URLSearchParams()
    if (options?.include_inactive) params.set('include_inactive', 'true')
    if (options?.room_type) params.set('room_type', options.room_type)
    if (options?.branch_id) params.set('branch_id', options.branch_id.toString())
    if (options?.page) params.set('page', options.page.toString())
    if (options?.per_page) params.set('per_page', options.per_page.toString())

    const queryString = params.toString()
    const url = `/staff/rooms${queryString ? `?${queryString}` : ''}`

    return await fetchApi<StaffRoomListResponse>(url, { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch rooms')
    }
    throw error
  }
}

export async function getStaffRoom(token: string, roomId: number): Promise<StaffRoom> {
  try {
    return await fetchApi<StaffRoom>(`/staff/rooms/${roomId}`, { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch room')
    }
    throw error
  }
}

export async function createStaffRoom(token: string, data: StaffRoomCreate): Promise<StaffRoom> {
  try {
    return await fetchApi<StaffRoom>('/staff/rooms', {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to create room')
    }
    throw error
  }
}

export async function updateStaffRoom(
  token: string,
  roomId: number,
  data: StaffRoomUpdate
): Promise<StaffRoom> {
  try {
    return await fetchApi<StaffRoom>(`/staff/rooms/${roomId}`, {
      method: 'PUT',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to update room')
    }
    throw error
  }
}

export async function deactivateStaffRoom(token: string, roomId: number): Promise<void> {
  try {
    await fetchApi<void>(`/staff/rooms/${roomId}`, {
      method: 'DELETE',
      token,
      skipJsonParse: true,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to deactivate room')
    }
    throw error
  }
}

export async function activateStaffRoom(token: string, roomId: number): Promise<{ message: string }> {
  try {
    return await fetchApi<{ message: string }>(`/staff/rooms/${roomId}/activate`, {
      method: 'POST',
      token,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to activate room')
    }
    throw error
  }
}

// ==================== Reservation Management ====================

export async function getPendingReservations(
  token: string,
  options?: {
    room_id?: number
    page?: number
    per_page?: number
  }
): Promise<ReservationListResponse> {
  try {
    const params = new URLSearchParams()
    if (options?.room_id) params.set('room_id', options.room_id.toString())
    if (options?.page) params.set('page', options.page.toString())
    if (options?.per_page) params.set('per_page', options.per_page.toString())

    const queryString = params.toString()
    const url = `/staff/rooms/reservations/pending${queryString ? `?${queryString}` : ''}`

    return await fetchApi<ReservationListResponse>(url, { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch pending reservations')
    }
    throw error
  }
}

export async function getAllReservations(
  token: string,
  options?: {
    room_id?: number
    status_filter?: string
    patron_id?: number
    start_date?: string
    end_date?: string
    page?: number
    per_page?: number
  }
): Promise<ReservationListResponse> {
  try {
    const params = new URLSearchParams()
    if (options?.room_id) params.set('room_id', options.room_id.toString())
    if (options?.status_filter) params.set('status_filter', options.status_filter)
    if (options?.patron_id) params.set('patron_id', options.patron_id.toString())
    if (options?.start_date) params.set('start_date', options.start_date)
    if (options?.end_date) params.set('end_date', options.end_date)
    if (options?.page) params.set('page', options.page.toString())
    if (options?.per_page) params.set('per_page', options.per_page.toString())

    const queryString = params.toString()
    const url = `/staff/rooms/reservations/all${queryString ? `?${queryString}` : ''}`

    return await fetchApi<ReservationListResponse>(url, { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch reservations')
    }
    throw error
  }
}

export async function getReservationDetails(
  token: string,
  reservationId: number
): Promise<StaffReservationDetail> {
  try {
    return await fetchApi<StaffReservationDetail>(
      `/staff/rooms/reservations/${reservationId}`,
      { token }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch reservation details')
    }
    throw error
  }
}

export async function approveReservation(
  token: string,
  reservationId: number,
  approval: ReservationApproval
): Promise<StaffReservation> {
  try {
    return await fetchApi<StaffReservation>(
      `/staff/rooms/reservations/${reservationId}/approve`,
      {
        method: 'POST',
        token,
        body: approval,
      }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to process reservation approval')
    }
    throw error
  }
}

export async function cancelReservation(
  token: string,
  reservationId: number,
  reason: string,
  cancelFuture: boolean = false
): Promise<StaffReservation> {
  try {
    const params = new URLSearchParams()
    if (cancelFuture) params.set('cancel_future', 'true')

    const queryString = params.toString()
    const url = `/staff/rooms/reservations/${reservationId}/cancel${queryString ? `?${queryString}` : ''}`

    return await fetchApi<StaffReservation>(url, {
      method: 'POST',
      token,
      body: { reason },
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to cancel reservation')
    }
    throw error
  }
}

export async function createOverrideBooking(
  token: string,
  data: StaffOverrideCreate
): Promise<StaffReservation> {
  try {
    return await fetchApi<StaffReservation>('/staff/rooms/reservations/override', {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to create override booking')
    }
    throw error
  }
}

export async function checkInReservation(
  token: string,
  reservationId: number
): Promise<StaffReservation> {
  try {
    return await fetchApi<StaffReservation>(
      `/staff/rooms/reservations/${reservationId}/check-in`,
      {
        method: 'POST',
        token,
      }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to check in')
    }
    throw error
  }
}

// ==================== Equipment Management ====================

export async function getStaffEquipment(
  token: string,
  includeInactive: boolean = false
): Promise<StaffEquipment[]> {
  try {
    const params = new URLSearchParams()
    if (includeInactive) params.set('include_inactive', 'true')

    const queryString = params.toString()
    const url = `/staff/rooms/equipment${queryString ? `?${queryString}` : ''}`

    return await fetchApi<StaffEquipment[]>(url, { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch equipment')
    }
    throw error
  }
}

export async function createStaffEquipment(
  token: string,
  data: StaffEquipmentCreate
): Promise<StaffEquipment> {
  try {
    return await fetchApi<StaffEquipment>('/staff/rooms/equipment', {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to create equipment')
    }
    throw error
  }
}

export async function updateStaffEquipment(
  token: string,
  equipmentId: number,
  data: StaffEquipmentUpdate
): Promise<StaffEquipment> {
  try {
    return await fetchApi<StaffEquipment>(`/staff/rooms/equipment/${equipmentId}`, {
      method: 'PUT',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to update equipment')
    }
    throw error
  }
}

// ==================== Reports ====================

export async function getRoomUtilizationReport(
  token: string,
  startDate: string,
  endDate: string,
  roomId?: number
): Promise<RoomUtilizationReport[]> {
  try {
    const params = new URLSearchParams()
    params.set('start_date', startDate)
    params.set('end_date', endDate)
    if (roomId) params.set('room_id', roomId.toString())

    return await fetchApi<RoomUtilizationReport[]>(
      `/staff/rooms/reports/utilization?${params}`,
      { token }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch utilization report')
    }
    throw error
  }
}

export async function getPopularTimesReport(
  token: string,
  startDate: string,
  endDate: string,
  roomId?: number
): Promise<PopularTimesReport> {
  try {
    const params = new URLSearchParams()
    params.set('start_date', startDate)
    params.set('end_date', endDate)
    if (roomId) params.set('room_id', roomId.toString())

    return await fetchApi<PopularTimesReport>(
      `/staff/rooms/reports/popular-times?${params}`,
      { token }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch popular times report')
    }
    throw error
  }
}

export async function getNoShowReport(
  token: string,
  startDate: string,
  endDate: string
): Promise<NoShowReport> {
  try {
    const params = new URLSearchParams()
    params.set('start_date', startDate)
    params.set('end_date', endDate)

    return await fetchApi<NoShowReport>(
      `/staff/rooms/reports/no-shows?${params}`,
      { token }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch no-show report')
    }
    throw error
  }
}

// ==================== Patron Reservation Functions ====================

export async function createPatronReservation(
  token: string,
  roomId: number,
  data: PatronReservationCreate
): Promise<PatronReservation> {
  try {
    return await fetchApi<PatronReservation>(`/rooms/${roomId}/reservations`, {
      method: 'POST',
      token,
      body: { ...data, room_id: roomId },
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to create reservation')
    }
    throw error
  }
}

export async function updatePatronReservation(
  token: string,
  reservationId: number,
  data: PatronReservationUpdate
): Promise<PatronReservation> {
  try {
    return await fetchApi<PatronReservation>(
      `/rooms/my/reservations/${reservationId}`,
      {
        method: 'PUT',
        token,
        body: data,
      }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to update reservation')
    }
    throw error
  }
}

export async function cancelPatronReservation(
  token: string,
  reservationId: number,
  options?: {
    reason?: string
    cancel_future?: boolean
  }
): Promise<void> {
  try {
    const params = new URLSearchParams()
    if (options?.reason) params.set('reason', options.reason)
    if (options?.cancel_future) params.set('cancel_future', 'true')

    const queryString = params.toString()
    const url = `/rooms/my/reservations/${reservationId}${queryString ? `?${queryString}` : ''}`

    await fetchApi<void>(url, {
      method: 'DELETE',
      token,
      skipJsonParse: true,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to cancel reservation')
    }
    throw error
  }
}

export async function checkInPatronReservation(
  token: string,
  reservationId: number
): Promise<PatronReservation> {
  try {
    return await fetchApi<PatronReservation>(
      `/rooms/my/reservations/${reservationId}/check-in`,
      {
        method: 'POST',
        token,
      }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to check in to reservation')
    }
    throw error
  }
}
