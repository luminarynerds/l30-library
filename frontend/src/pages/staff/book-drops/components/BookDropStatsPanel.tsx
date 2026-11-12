/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React from "react"
import { Loader2, BarChart3, TrendingUp, Users, DollarSign, AlertCircle } from "lucide-react"
import { StatisticsSummary, formatCurrency } from "@/api/book-drop-api"

interface BookDropStatsPanelProps {
  summary: StatisticsSummary | null
  isLoading: boolean
  dateRange: { start: string; end: string }
  onDateRangeChange: (range: { start: string; end: string }) => void
  onUpdate: () => void
}

export const BookDropStatsPanel: React.FC<BookDropStatsPanelProps> = ({
  summary,
  isLoading,
  dateRange,
  onDateRangeChange,
  onUpdate,
}) => {
  return (
    <>
      <div className="flex flex-wrap items-center gap-4">
        <div className="flex items-center gap-2">
          <label htmlFor="bookdrop-stats-from" className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">From:</label>
          <input
            id="bookdrop-stats-from"
            type="date"
            value={dateRange.start}
            onChange={(e) => onDateRangeChange({ ...dateRange, start: e.target.value })}
            className="px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
          />
        </div>
        <div className="flex items-center gap-2">
          <label htmlFor="bookdrop-stats-to" className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">To:</label>
          <input
            id="bookdrop-stats-to"
            type="date"
            value={dateRange.end}
            onChange={(e) => onDateRangeChange({ ...dateRange, end: e.target.value })}
            className="px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
          />
        </div>
        <button
          onClick={onUpdate}
          className="flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 transition-colors"
        >
          <BarChart3 className="w-4 h-4" />
          Update
        </button>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose dark:text-lsc-rose-light" />
        </div>
      ) : summary ? (
        <div className="space-y-6">
          {/* Summary Cards */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm">
              <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                <TrendingUp className="w-4 h-4" />
                <span className="text-xs uppercase">Total Check-ins</span>
              </div>
              <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">
                {summary.total_checkins.toLocaleString()}
              </p>
              <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                Avg {summary.avg_daily_checkins.toFixed(0)}/day
              </p>
            </div>
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm">
              <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                <Users className="w-4 h-4" />
                <span className="text-xs uppercase">Holds Trapped</span>
              </div>
              <p className="text-2xl font-bold text-lsc-rose dark:text-lsc-rose-light">
                {summary.holds_trapped_total.toLocaleString()}
              </p>
            </div>
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm">
              <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                <DollarSign className="w-4 h-4" />
                <span className="text-xs uppercase">Fines Collected</span>
              </div>
              <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">
                {formatCurrency(summary.total_fines)}
              </p>
            </div>
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm">
              <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                <AlertCircle className="w-4 h-4" />
                <span className="text-xs uppercase">Exceptions</span>
              </div>
              <p className="text-2xl font-bold text-status-danger-600 dark:text-status-danger-400">
                {summary.exceptions_total.toLocaleString()}
              </p>
            </div>
          </div>

          {/* Check-in Sources */}
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm p-6">
            <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4">
              Check-in Sources
            </h3>
            <div className="grid grid-cols-3 gap-4">
              <div className="text-center p-4 bg-lsc-cream dark:bg-earth-700 rounded-lg">
                <p className="text-3xl font-bold text-lsc-dark dark:text-lsc-cream">
                  {summary.staff_checkins_pct.toFixed(1)}%
                </p>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Staff</p>
              </div>
              <div className="text-center p-4 bg-lsc-cream dark:bg-earth-700 rounded-lg">
                <p className="text-3xl font-bold text-lsc-dark dark:text-lsc-cream">
                  {summary.book_drop_checkins_pct.toFixed(1)}%
                </p>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Book Drop</p>
              </div>
              <div className="text-center p-4 bg-lsc-cream dark:bg-earth-700 rounded-lg">
                <p className="text-3xl font-bold text-lsc-dark dark:text-lsc-cream">
                  {summary.self_service_checkins_pct.toFixed(1)}%
                </p>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Self-Service</p>
              </div>
            </div>
          </div>

          {/* Peak Info */}
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm p-6">
            <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4">
              Peak Activity
            </h3>
            <div className="grid grid-cols-2 gap-6">
              <div>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                  Busiest Hour
                </p>
                <p className="text-xl font-bold text-lsc-dark dark:text-lsc-cream">
                  {summary.peak_hour}:00 - {summary.peak_hour + 1}:00
                </p>
              </div>
              <div>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                  Busiest Day
                </p>
                <p className="text-xl font-bold text-lsc-dark dark:text-lsc-cream">
                  {["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"][
                    summary.peak_day_of_week
                  ]}
                </p>
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm p-8 text-center">
          <BarChart3 className="w-12 h-12 mx-auto text-lsc-dark/30 dark:text-lsc-cream/60 mb-4" />
          <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-2">
            No Statistics Available
          </h3>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
            Select a date range and click Update to view statistics
          </p>
        </div>
      )}
    </>
  )
}
