/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
export interface RoomUtilizationSummary {
  total_reservations: number
  confirmed_reservations: number
  no_show_reservations: number
  total_hours_booked: number
}

export interface RoomUtilizationByRoom {
  room_id: number
  room_name: string
  room_type: string
  total_reservations: number
  confirmed_reservations: number
  hours_booked: number
  utilization_rate: number
  [key: string]: unknown
}

export interface RoomUtilizationResponse {
  summary: RoomUtilizationSummary
  by_room: RoomUtilizationByRoom[]
}

export interface PopularTimesByHour {
  hour: number
  hour_label: string
  bookings: number
}

export interface PopularTimesByDay {
  day_number: number
  day_name: string
  bookings: number
}

export interface PopularTimesResponse {
  by_hour: PopularTimesByHour[]
  by_day: PopularTimesByDay[]
}

export interface NoShowPatron {
  patron_id: number
  patron_name: string | null
  patron_email: string | null
  no_show_count: number
}

export interface NoShowWeeklyTrend {
  week_start: string
  total_reservations: number
  no_show_count: number
  no_show_rate: number
}

export interface NoShowSummary {
  total_reservations: number
  no_show_count: number
  checked_in_count: number
  no_show_rate: number
}

export interface NoShowTrackingResponse {
  summary: NoShowSummary
  top_no_show_patrons: NoShowPatron[]
  weekly_trend: NoShowWeeklyTrend[]
}

export interface RoomReportsResponse {
  utilization: RoomUtilizationResponse
  popularTimes: PopularTimesResponse
  noShows: NoShowTrackingResponse
}
