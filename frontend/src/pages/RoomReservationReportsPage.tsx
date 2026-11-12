/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import { useState, useEffect, useCallback } from "react"
import { useAuth } from "../contexts/AuthContext"
import { AdminShell } from "../components/shells/AdminShell"
import { Loader2, RefreshCw } from "lucide-react"
import toast from "react-hot-toast"
import { useTranslation } from "@/i18n"
import {
  DateRangeFilter,
  NoShowAnalytics,
  NoShowWeeklyTrendChart,
  PopularTimesCharts,
  RoomPerformanceTable,
  RoomUtilizationChart,
  SummaryStatsCards,
  exportToCSV,
  fetchAllRoomReports,
  type NoShowTrackingResponse,
  type PopularTimesResponse,
  type RoomUtilizationResponse,
} from "../components/room-reports"

export default function RoomReservationReportsPage(): React.ReactElement {
  const { t } = useTranslation()
  const { token, isLoading: authLoading, isAuthenticated } = useAuth()
  const [isLoading, setIsLoading] = useState(true)
  const [utilization, setUtilization] = useState<RoomUtilizationResponse | null>(null)
  const [popularTimes, setPopularTimes] = useState<PopularTimesResponse | null>(null)
  const [noShows, setNoShows] = useState<NoShowTrackingResponse | null>(null)

  const [startDate, setStartDate] = useState("")
  const [endDate, setEndDate] = useState("")
  const [appliedStartDate, setAppliedStartDate] = useState("")
  const [appliedEndDate, setAppliedEndDate] = useState("")

  const fetchData = useCallback(async () => {
    if (!token) return
    setIsLoading(true)
    try {
      const params = {
        ...(appliedStartDate && { start_date: appliedStartDate }),
        ...(appliedEndDate && { end_date: appliedEndDate }),
      }
      const reports = await fetchAllRoomReports(token, params)
      setUtilization(reports.utilization)
      setPopularTimes(reports.popularTimes)
      setNoShows(reports.noShows)
    } catch (err) {
      Sentry.captureException(err instanceof Error ? err : new Error(String(err)))
      toast.error(t("roomReservationReports.failedToLoadRoomReports"))
    } finally {
      setIsLoading(false)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, appliedStartDate, appliedEndDate])

  useEffect(() => {
    const end = new Date()
    const start = new Date()
    start.setDate(start.getDate() - 30)

    const formatDate = (date: Date): string => date.toISOString().split("T")[0] || ""
    setStartDate(formatDate(start))
    setEndDate(formatDate(end))
    setAppliedStartDate(formatDate(start))
    setAppliedEndDate(formatDate(end))
  }, [])

  useEffect(() => {
    if (isAuthenticated && token && appliedStartDate && appliedEndDate) {
      fetchData()
    }
  }, [isAuthenticated, token, fetchData, appliedStartDate, appliedEndDate])

  const handleApplyFilters = () => {
    if (!startDate || !endDate) {
      toast.error(t("roomReservationReports.pleaseSelectBothStartAnd"))
      return
    }
    if (new Date(startDate) > new Date(endDate)) {
      toast.error(t("roomReservationReports.startDateMustBeBefore"))
      return
    }
    setAppliedStartDate(startDate)
    setAppliedEndDate(endDate)
    toast.success(t("toast.circulationReports.filtersApplied"))
  }

  const exportUtilizationReport = () => {
    if (!utilization) return
    const data = utilization.by_room.map((room) => ({
      room_name: room.room_name,
      room_type: room.room_type,
      total_reservations: room.total_reservations,
      confirmed_reservations: room.confirmed_reservations,
      hours_booked: room.hours_booked,
      utilization_rate: room.utilization_rate,
    }))
    exportToCSV(data, `room-utilization-${appliedStartDate}-to-${appliedEndDate}.csv`)
  }

  const exportPopularTimesReport = () => {
    if (!popularTimes) return
    const hourlyData = popularTimes.by_hour.map((item) => ({
      hour: item.hour_label,
      bookings: item.bookings,
    }))
    exportToCSV(hourlyData, `popular-booking-times-${appliedStartDate}-to-${appliedEndDate}.csv`)
  }

  const exportNoShowReport = () => {
    if (!noShows) return
    const data = noShows.top_no_show_patrons.map((patron) => ({
      patron_name: patron.patron_name || "Unknown",
      patron_email: patron.patron_email || "Unknown",
      no_show_count: patron.no_show_count,
    }))
    exportToCSV(data, `no-show-report-${appliedStartDate}-to-${appliedEndDate}.csv`)
  }

  if (authLoading || isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" />
      </div>
    )
  }

  if (!isAuthenticated) return <></>

  return (
    <AdminShell title="Room Reservation Reports">
      <div>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
              Room Reservation Reports
            </h1>
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
              Analytics and statistics for room reservations
            </p>
          </div>
          <button
            onClick={fetchData}
            className="flex items-center gap-2 px-4 py-2 text-lsc-rose hover:bg-lsc-cream dark:hover:bg-lsc-brown/20 rounded-xl transition-colors"
            aria-label={t("aria.roomReservationReports.refreshReports")}
          >
            <RefreshCw aria-hidden="true" className="w-4 h-4" />
            Refresh
          </button>
        </div>

        <DateRangeFilter
          startDate={startDate}
          endDate={endDate}
          onStartDateChange={setStartDate}
          onEndDateChange={setEndDate}
          onApply={handleApplyFilters}
        />

        {utilization && <SummaryStatsCards summary={utilization.summary} />}

        {utilization && (
          <RoomUtilizationChart utilization={utilization} onExport={exportUtilizationReport} />
        )}

        {popularTimes && (
          <PopularTimesCharts popularTimes={popularTimes} onExport={exportPopularTimesReport} />
        )}

        {noShows && <NoShowAnalytics noShows={noShows} onExport={exportNoShowReport} />}

        {noShows && noShows.weekly_trend.length > 0 && (
          <NoShowWeeklyTrendChart weeklyTrend={noShows.weekly_trend} />
        )}

        {utilization && <RoomPerformanceTable rooms={utilization.by_room} />}
      </div>
    </AdminShell>
  )
}
