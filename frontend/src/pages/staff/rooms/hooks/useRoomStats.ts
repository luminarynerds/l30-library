/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useQuery } from "@tanstack/react-query"
import { useMemo } from "react"
import {
  getRoomUtilizationReport,
  getPopularTimesReport,
  getNoShowReport,
  type StaffRoom,
  type StaffReservation,
} from "../../../../api/staff-rooms-api"

interface UseRoomStatsOptions {
  token: string | null
  enabled: boolean
  rooms: StaffRoom[] | undefined
  allReservations: StaffReservation[] | undefined
  pendingReservations: StaffReservation[] | undefined
  reportStartDate: string
  reportEndDate: string
}

export function useRoomStats({
  token,
  enabled,
  rooms,
  allReservations,
  pendingReservations,
  reportStartDate,
  reportEndDate,
}: UseRoomStatsOptions) {
  const quickStats = useMemo(() => {
    const totalRooms = rooms?.length ?? 0
    const activeRooms = rooms?.filter(r => r.is_active).length ?? 0
    const totalReservations = allReservations?.length ?? 0
    const pendingCount = pendingReservations?.length ?? 0
    return { totalRooms, activeRooms, totalReservations, pendingCount }
  }, [rooms, allReservations, pendingReservations])

  const { data: utilizationReport, isLoading: isLoadingUtilization } = useQuery({
    queryKey: ["room-utilization", reportStartDate, reportEndDate],
    queryFn: async () => {
      if (!token) return []
      return await getRoomUtilizationReport(token, reportStartDate, reportEndDate)
    },
    enabled: !!token && enabled,
  })

  const { data: popularTimesReport, isLoading: isLoadingPopularTimes } = useQuery({
    queryKey: ["room-popular-times", reportStartDate, reportEndDate],
    queryFn: async () => {
      if (!token) return null
      return await getPopularTimesReport(token, reportStartDate, reportEndDate)
    },
    enabled: !!token && enabled,
  })

  const { data: noShowReport, isLoading: isLoadingNoShow } = useQuery({
    queryKey: ["room-no-shows", reportStartDate, reportEndDate],
    queryFn: async () => {
      if (!token) return null
      return await getNoShowReport(token, reportStartDate, reportEndDate)
    },
    enabled: !!token && enabled,
  })

  return {
    quickStats,
    utilizationReport,
    isLoadingUtilization,
    popularTimesReport,
    isLoadingPopularTimes,
    noShowReport,
    isLoadingNoShow,
  }
}
