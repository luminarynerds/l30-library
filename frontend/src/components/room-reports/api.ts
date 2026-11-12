/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import {
  getNoShowReport,
  getPopularTimesReport,
  getRoomUtilizationReport,
  getStaffRooms,
  type NoShowReport,
  type PopularTimesReport,
  type RoomUtilizationReport,
} from "../../api/staff-rooms-api"
import type {
  NoShowTrackingResponse,
  PopularTimesResponse,
  RoomReportsResponse,
  RoomUtilizationResponse,
} from "./types"

export async function fetchAllRoomReports(
  token: string,
  params: { start_date?: string; end_date?: string }
): Promise<RoomReportsResponse> {
  if (!params.start_date || !params.end_date) {
    throw new Error("Start and end dates are required")
  }

  const [utilizationData, popularTimesData, noShowsData] = await Promise.all([
    getRoomUtilizationReport(token, params.start_date, params.end_date),
    getPopularTimesReport(token, params.start_date, params.end_date),
    getNoShowReport(token, params.start_date, params.end_date),
  ])

  let roomTypeById = new Map<number, string>()
  try {
    const roomsData = await getStaffRooms(token, { include_inactive: true, per_page: 1000 })
    roomTypeById = new Map(roomsData.items.map((room) => [room.id, room.room_type]))
  } catch {
    // Keep reports usable even if room metadata lookup fails.
    roomTypeById = new Map<number, string>()
  }

  return {
    utilization: normalizeUtilizationResponse(utilizationData, roomTypeById),
    popularTimes: normalizePopularTimesResponse(popularTimesData),
    noShows: normalizeNoShowResponse(noShowsData),
  }
}

function normalizeUtilizationResponse(
  data: Array<RoomUtilizationReport & { room_type?: string }>,
  roomTypeById: Map<number, string>
): RoomUtilizationResponse {
  const totalReservations = data.reduce((sum, room) => sum + room.total_reservations, 0)
  const confirmedReservations = data.reduce((sum, room) => sum + room.completed_reservations, 0)
  const noShowReservations = data.reduce((sum, room) => sum + room.no_show_count, 0)
  const totalHoursBooked = data.reduce((sum, room) => sum + room.total_hours_booked, 0)

  return {
    summary: {
      total_reservations: totalReservations,
      confirmed_reservations: confirmedReservations,
      no_show_reservations: noShowReservations,
      total_hours_booked: totalHoursBooked,
    },
    by_room: data.map((room) => ({
      room_id: room.room_id,
      room_name: room.room_name,
      room_type: room.room_type ?? roomTypeById.get(room.room_id) ?? "Unknown",
      total_reservations: room.total_reservations,
      confirmed_reservations: room.completed_reservations,
      hours_booked: room.total_hours_booked,
      utilization_rate: room.utilization_rate,
    })),
  }
}

function normalizePopularTimesResponse(data: PopularTimesReport): PopularTimesResponse {
  const byHour = Object.entries(data.hourly_distribution)
    .map(([hour, bookings]) => {
      const numericHour = Number(hour)
      return {
        hour: numericHour,
        hour_label: `${numericHour.toString().padStart(2, "0")}:00`,
        bookings,
      }
    })
    .sort((a, b) => a.hour - b.hour)

  const dayOrder = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
  const byDay = dayOrder.map((dayName, index) => ({
    day_number: index + 1,
    day_name: dayName,
    bookings: data.day_of_week[dayName] ?? 0,
  }))

  return {
    by_hour: byHour,
    by_day: byDay,
  }
}

function normalizeNoShowResponse(data: NoShowReport): NoShowTrackingResponse {
  return {
    summary: {
      total_reservations: data.total_reservations,
      no_show_count: data.no_show_count,
      checked_in_count: data.total_reservations - data.no_show_count,
      no_show_rate: data.no_show_rate,
    },
    top_no_show_patrons: data.repeat_no_show_patrons.map((patron) => ({
      patron_id: patron.patron_id,
      patron_name: patron.name,
      patron_email: patron.email,
      no_show_count: patron.no_show_count,
    })),
    weekly_trend: Object.entries(data.by_day_of_week ?? {}).map(([day_name, no_show_count]) => ({
      week_start: day_name,
      total_reservations: 0,
      no_show_count,
      no_show_rate: 0,
    })),
  }
}
