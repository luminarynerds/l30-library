/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { AlertCircle, Download, Users } from "lucide-react"
import { useTranslation } from "@/i18n"
import type { NoShowTrackingResponse } from "./types"

interface NoShowAnalyticsProps {
  noShows: NoShowTrackingResponse
  onExport: () => void
}

export function NoShowAnalytics({ noShows, onExport }: NoShowAnalyticsProps): React.ReactElement {
  const { t } = useTranslation()

  return (
    <div className="grid md:grid-cols-2 gap-6">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm border border-lsc-border dark:border-earth-700 p-6">
        <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream flex items-center gap-2 mb-4">
          <AlertCircle className="w-5 h-5 text-status-danger-500" aria-hidden="true" />
          No-Show Statistics
        </h2>
        <div className="space-y-4">
          <div className="flex justify-between items-center p-4 bg-lsc-cream/50 dark:bg-earth-700/50 rounded-lg">
            <span className="text-lsc-dark/70 dark:text-lsc-cream/70">No-Show Rate</span>
            <span className="text-2xl font-bold text-status-danger-600 dark:text-status-danger-400">
              {noShows.summary.no_show_rate.toFixed(1)}%
            </span>
          </div>
          <div className="flex justify-between items-center p-4 bg-lsc-cream/50 dark:bg-earth-700/50 rounded-lg">
            <span className="text-lsc-dark/70 dark:text-lsc-cream/70">Total No-Shows</span>
            <span className="text-xl font-semibold text-lsc-dark dark:text-lsc-cream">
              {noShows.summary.no_show_count}
            </span>
          </div>
          <div className="flex justify-between items-center p-4 bg-lsc-cream/50 dark:bg-earth-700/50 rounded-lg">
            <span className="text-lsc-dark/70 dark:text-lsc-cream/70">Checked In</span>
            <span className="text-xl font-semibold text-status-success-600 dark:text-status-success-400">
              {noShows.summary.checked_in_count}
            </span>
          </div>
        </div>
      </div>

      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm border border-lsc-border dark:border-earth-700 p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream flex items-center gap-2">
            <Users className="w-5 h-5 text-lsc-rose" aria-hidden="true" />
            Top No-Show Patrons
          </h2>
          <button
            onClick={onExport}
            className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-rose flex items-center gap-1"
            aria-label={t("aria.roomReservationReports.exportNoshowReport")}
          >
            <Download aria-hidden="true" className="w-4 h-4" />
            Export
          </button>
        </div>
        <div className="space-y-3">
          {noShows.top_no_show_patrons.slice(0, 5).map((patron, idx) => (
            <div
              key={patron.patron_id}
              className="flex items-center gap-3 p-3 bg-lsc-cream/30 dark:bg-earth-700/30 rounded-lg"
            >
              <span className="w-6 h-6 bg-status-danger-100 dark:bg-status-danger-900/30 text-status-danger-600 dark:text-status-danger-400 rounded-full flex items-center justify-center text-xs font-medium">
                {idx + 1}
              </span>
              <div className="flex-1 min-w-0">
                <p
                  className="font-medium text-lsc-dark dark:text-lsc-cream truncate"
                  title={patron.patron_name || "Unknown"}
                >
                  {patron.patron_name || "Unknown"}
                </p>
                <p
                  className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 truncate"
                  title={patron.patron_email || "No email"}
                >
                  {patron.patron_email || "No email"}
                </p>
              </div>
              <span className="text-sm font-semibold text-status-danger-600 dark:text-status-danger-400">
                {patron.no_show_count} no-shows
              </span>
            </div>
          ))}
          {noShows.top_no_show_patrons.length === 0 && (
            <p className="text-center text-lsc-dark/70 dark:text-lsc-cream/70 py-8">
              No no-show data available
            </p>
          )}
        </div>
      </div>
    </div>
  )
}
