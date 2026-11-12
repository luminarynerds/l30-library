/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from "react"
import { Loader2, TrendingUp, Activity, AlertTriangle, DoorOpen, Calendar, Clock, Users } from "lucide-react"
import type { RoomUtilizationReport, PopularTimesReport, NoShowReport } from "../../../../api/staff-rooms-api"
import { t } from "@/i18n"

interface QuickStats {
  totalRooms: number
  activeRooms: number
  totalReservations: number
  pendingCount: number
}

interface RoomStatsPanelProps {
  stats: QuickStats
  reportStartDate: string
  reportEndDate: string
  onReportStartDateChange: (value: string) => void
  onReportEndDateChange: (value: string) => void
  utilizationReport?: RoomUtilizationReport[]
  popularTimesReport?: PopularTimesReport | null
  noShowReport?: NoShowReport | null
  isLoadingUtilization?: boolean
  isLoadingPopularTimes?: boolean
  isLoadingNoShow?: boolean
}

type ReportTab = "utilization" | "popular-times" | "no-shows"

export function RoomStatsPanel({
  stats,
  reportStartDate,
  reportEndDate,
  onReportStartDateChange,
  onReportEndDateChange,
  utilizationReport,
  popularTimesReport,
  noShowReport,
  isLoadingUtilization,
  isLoadingPopularTimes,
  isLoadingNoShow,
}: RoomStatsPanelProps) {
  const [reportTab, setReportTab] = useState<ReportTab>("utilization")
  const isDetailedMode = utilizationReport !== undefined

  return (
    <div className="space-y-4">
      {/* Quick Stats Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 border border-lsc-border dark:border-earth-700">
          <div className="flex items-center gap-2 mb-2">
            <DoorOpen className="w-4 h-4 text-lsc-rose" />
            <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Total Rooms</span>
          </div>
          <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">{stats.totalRooms}</p>
          <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{stats.activeRooms} active</p>
        </div>

        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 border border-lsc-border dark:border-earth-700">
          <div className="flex items-center gap-2 mb-2">
            <Calendar className="w-4 h-4 text-earth-600" />
            <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Reservations</span>
          </div>
          <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">{stats.totalReservations}</p>
          <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">total bookings</p>
        </div>

        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 border border-lsc-border dark:border-earth-700">
          <div className="flex items-center gap-2 mb-2">
            <Clock className="w-4 h-4 text-status-warning-500" />
            <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Pending</span>
          </div>
          <p className="text-2xl font-bold text-status-warning-600 dark:text-status-warning-400">{stats.pendingCount}</p>
          <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">awaiting review</p>
        </div>

        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 border border-lsc-border dark:border-earth-700">
          <div className="flex items-center gap-2 mb-2">
            <Users className="w-4 h-4 text-status-success-500" />
            <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Occupancy</span>
          </div>
          <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">
            {stats.totalRooms > 0 ? Math.round((stats.activeRooms / stats.totalRooms) * 100) : 0}%
          </p>
          <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">rooms active</p>
        </div>
      </div>

      {/* Detailed Reports (only shown in reports tab) */}
      {isDetailedMode && (
        <div className="space-y-4">
          {/* Date Range Picker */}
          <div className="flex flex-wrap items-center gap-3 bg-lsc-white dark:bg-earth-800 rounded-xl p-4 border border-lsc-border dark:border-earth-700">
            <span className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">Report Period:</span>
            <input
              type="date"
              value={reportStartDate}
              onChange={(e) => onReportStartDateChange(e.target.value)}
              aria-label={t('aria.roomStats.reportStartDate', 'Report start date')}
              className="px-3 py-1.5 rounded-lg border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-700 text-sm text-lsc-dark dark:text-lsc-cream"
            />
            <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">to</span>
            <input
              type="date"
              value={reportEndDate}
              onChange={(e) => onReportEndDateChange(e.target.value)}
              aria-label={t('aria.roomStats.reportEndDate', 'Report end date')}
              className="px-3 py-1.5 rounded-lg border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-700 text-sm text-lsc-dark dark:text-lsc-cream"
            />
          </div>

          {/* Report Sub-tabs */}
          <div className="flex gap-2">
            {([
              { id: "utilization" as const, label: "Utilization", icon: TrendingUp },
              { id: "popular-times" as const, label: "Popular Times", icon: Activity },
              { id: "no-shows" as const, label: "No-Shows", icon: AlertTriangle },
            ]).map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                onClick={() => setReportTab(id)}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm transition-colors ${
                  reportTab === id
                    ? "bg-lsc-rose text-white"
                    : "bg-lsc-cream dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream hover:bg-lsc-border dark:hover:bg-earth-700"
                }`}
              >
                <Icon className="w-4 h-4" />
                {label}
              </button>
            ))}
          </div>

          {/* Utilization Report */}
          {reportTab === "utilization" && (
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 border border-lsc-border dark:border-earth-700">
              <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
                <TrendingUp className="w-5 h-5 text-lsc-rose" />
                Room Utilization
              </h3>

              {isLoadingUtilization ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="w-6 h-6 motion-safe:animate-spin text-lsc-rose" />
                </div>
              ) : utilizationReport && utilizationReport.length > 0 ? (
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="text-left text-sm text-lsc-dark/70 dark:text-lsc-cream/70 border-b border-lsc-border dark:border-earth-700">
                        <th className="py-2 font-medium">Room</th>
                        <th className="py-2 font-medium text-right">Reservations</th>
                        <th className="py-2 font-medium text-right">Hours Used</th>
                        <th className="py-2 font-medium text-right">Utilization</th>
                        <th className="py-2 font-medium text-right">No-Show Rate</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-lsc-border dark:divide-earth-700">
                      {utilizationReport.map((report) => (
                        <tr key={report.room_id}>
                          <td className="py-3 text-lsc-dark dark:text-lsc-cream">{report.room_name}</td>
                          <td className="py-3 text-right text-lsc-dark dark:text-lsc-cream">
                            {report.total_reservations}
                          </td>
                          <td className="py-3 text-right text-lsc-dark dark:text-lsc-cream">
                            {report.total_hours_booked.toFixed(1)}h
                          </td>
                          <td className="py-3 text-right">
                            <div className="flex items-center justify-end gap-2">
                              <div className="w-16 h-2 bg-lsc-cream dark:bg-earth-700 rounded overflow-hidden">
                                <div
                                  className={`h-full rounded ${
                                    report.utilization_rate > 70
                                      ? "bg-status-success-500"
                                      : report.utilization_rate > 40
                                        ? "bg-status-warning-500"
                                        : "bg-status-danger-500"
                                  }`}
                                  style={{ width: `${Math.min(100, report.utilization_rate)}%` }}
                                />
                              </div>
                              <span
                                className={`font-medium text-sm ${
                                  report.utilization_rate > 70
                                    ? "text-status-success-600"
                                    : report.utilization_rate > 40
                                      ? "text-status-warning-600"
                                      : "text-status-danger-600"
                                }`}
                              >
                                {report.utilization_rate.toFixed(1)}%
                              </span>
                            </div>
                          </td>
                          <td className="py-3 text-right text-lsc-dark/70 dark:text-lsc-cream/70">
                            {report.no_show_rate.toFixed(1)}%
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p className="text-center text-lsc-dark/70 dark:text-lsc-cream/70 py-8">
                  No utilization data available for the selected period
                </p>
              )}
            </div>
          )}

          {/* Popular Times Report */}
          {reportTab === "popular-times" && (
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 border border-lsc-border dark:border-earth-700">
              <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
                <Activity className="w-5 h-5 text-lsc-rose" />
                Popular Booking Times
              </h3>

              {isLoadingPopularTimes ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="w-6 h-6 motion-safe:animate-spin text-lsc-rose" />
                </div>
              ) : popularTimesReport ? (
                <div className="grid md:grid-cols-2 gap-6">
                  <div className="space-y-3">
                    <div className="bg-lsc-cream dark:bg-earth-700/50 rounded-lg p-4">
                      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Peak Hour</p>
                      <p className="text-xl font-bold text-lsc-dark dark:text-lsc-cream">
                        {popularTimesReport.peak_hour != null
                          ? `${popularTimesReport.peak_hour}:00`
                          : "N/A"}
                      </p>
                    </div>
                    <div className="bg-lsc-cream dark:bg-earth-700/50 rounded-lg p-4">
                      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Busiest Day</p>
                      <p className="text-xl font-bold text-lsc-dark dark:text-lsc-cream">
                        {popularTimesReport.peak_day || "N/A"}
                      </p>
                    </div>
                  </div>

                  <div>
                    <p className="text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">
                      Bookings by Day
                    </p>
                    <div className="space-y-2">
                      {Object.entries(popularTimesReport.day_of_week || {}).map(([day, count]) => {
                        const maxVal = Math.max(...Object.values(popularTimesReport.day_of_week || {}), 1)
                        return (
                          <div key={day} className="flex items-center gap-2">
                            <span className="w-24 text-sm text-lsc-dark dark:text-lsc-cream">{day}</span>
                            <div className="flex-1 h-4 bg-lsc-cream dark:bg-earth-700 rounded overflow-hidden">
                              <div
                                className="h-full bg-lsc-rose rounded"
                                style={{ width: `${Math.min(100, (count / maxVal) * 100)}%` }}
                              />
                            </div>
                            <span className="w-8 text-right text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                              {count}
                            </span>
                          </div>
                        )
                      })}
                    </div>
                  </div>
                </div>
              ) : (
                <p className="text-center text-lsc-dark/70 dark:text-lsc-cream/70 py-8">
                  No popular times data available for the selected period
                </p>
              )}
            </div>
          )}

          {/* No-Show Report */}
          {reportTab === "no-shows" && (
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 border border-lsc-border dark:border-earth-700">
              <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
                <AlertTriangle className="w-5 h-5 text-status-warning-500" />
                No-Show Analysis
              </h3>

              {isLoadingNoShow ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="w-6 h-6 motion-safe:animate-spin text-lsc-rose" />
                </div>
              ) : noShowReport ? (
                <>
                  <div className="grid md:grid-cols-3 gap-4 mb-6">
                    <div className="bg-lsc-cream dark:bg-earth-700/50 rounded-lg p-4 text-center">
                      <p className="text-3xl font-bold text-lsc-dark dark:text-lsc-cream">
                        {noShowReport.total_reservations}
                      </p>
                      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Total Reservations</p>
                    </div>
                    <div className="bg-lsc-cream dark:bg-earth-700/50 rounded-lg p-4 text-center">
                      <p className="text-3xl font-bold text-status-warning-600 dark:text-status-warning-400">
                        {noShowReport.no_show_count}
                      </p>
                      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">No-Shows</p>
                    </div>
                    <div className="bg-lsc-cream dark:bg-earth-700/50 rounded-lg p-4 text-center">
                      <p className="text-3xl font-bold text-status-danger-600 dark:text-status-danger-400">
                        {noShowReport.no_show_rate.toFixed(1)}%
                      </p>
                      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">No-Show Rate</p>
                    </div>
                  </div>

                  {noShowReport.repeat_no_show_patrons && noShowReport.repeat_no_show_patrons.length > 0 && (
                    <div>
                      <h4 className="font-medium text-lsc-dark dark:text-lsc-cream mb-2">
                        Repeat No-Show Patrons
                      </h4>
                      <div className="space-y-2">
                        {noShowReport.repeat_no_show_patrons.slice(0, 5).map((patron, idx) => (
                          <div
                            key={idx}
                            className="flex items-center justify-between p-2 bg-status-danger-50 dark:bg-status-danger-900/20 rounded-lg"
                          >
                            <div>
                              <p className="font-medium text-lsc-dark dark:text-lsc-cream">{patron.name}</p>
                              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{patron.email}</p>
                            </div>
                            <span className="px-2 py-0.5 bg-status-danger-100 dark:bg-status-danger-900/30 text-status-danger-800 dark:text-status-danger-400 rounded text-sm font-medium">
                              {patron.no_show_count} no-shows
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </>
              ) : (
                <p className="text-center text-lsc-dark/70 dark:text-lsc-cream/70 py-8">
                  No no-show data available for the selected period
                </p>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
