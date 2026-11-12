/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { BookOpen, Eye, Loader2, MapPin, RefreshCw } from 'lucide-react'
import { banTypeBadgeClasses, formatReason, formatDate } from './ban-tracker-data'
import type { BanReportMatch } from './types'
import { BanReportRationaleViewer } from '@/components/admin/BanReportRationaleViewer'

export function MatchesTab({
  matches,
  loading,
  alertCount,
  onMarkAllSeen,
  onRefresh,
}: {
  matches: BanReportMatch[]
  loading: boolean
  alertCount: number
  onMarkAllSeen: () => void
  onRefresh: () => void
}) {
  if (loading) {
    return (
      <div className="flex items-center justify-center h-48">
        <Loader2 className="h-8 w-8 motion-safe:animate-spin text-lsc-dark/70 dark:text-lsc-cream/70" />
      </div>
    )
  }

  const items = Array.isArray(matches) ? matches : []

  return (
    <div className="space-y-4">
      {/* Actions row */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
          {items.length} book{items.length !== 1 ? 's' : ''} in your catalog have been challenged elsewhere
        </p>
        <div className="flex items-center gap-2">
          {alertCount > 0 && (
            <button
              onClick={onMarkAllSeen}
              className="flex items-center gap-2 px-3 py-1.5 text-sm bg-earth-100 dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream rounded-lg hover:bg-earth-200 dark:hover:bg-earth-600 transition-colors"
            >
              <Eye className="w-4 h-4" />
              Mark All Seen
            </button>
          )}
          <button
            onClick={onRefresh}
            className="flex items-center gap-2 px-3 py-1.5 text-sm bg-earth-100 dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream rounded-lg hover:bg-earth-200 dark:hover:bg-earth-600 transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
            Refresh
          </button>
        </div>
      </div>

      {/* Match cards */}
      {items.length === 0 ? (
        <div className="bg-earth-50 dark:bg-earth-800/20 border border-lsc-border dark:border-earth-700 rounded-xl p-6 text-center">
          <BookOpen className="w-8 h-8 text-earth-600 mx-auto mb-2" />
          <p className="text-earth-800 dark:text-lsc-rose-light font-medium">
            No books in your catalog have been challenged elsewhere
          </p>
          <p className="text-sm text-lsc-rose dark:text-lsc-rose-light mt-1">
            This is good news! We will alert you if any matches are found.
          </p>
        </div>
      ) : (
        <div className="grid gap-3">
          {items.map((match) => (
            <div
              key={match.id}
              className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-4 flex flex-col sm:flex-row sm:items-center gap-3"
            >
              <div className="flex-1 min-w-0">
                <h4 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream truncate">
                  {match.title}
                </h4>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                  by {match.author}
                </p>
              </div>
              <div className="flex items-center gap-3 flex-shrink-0 flex-wrap">
                <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 flex items-center gap-1">
                  <MapPin className="w-3.5 h-3.5" />
                  {match.state}
                </span>
                <span
                  className={`text-xs font-medium px-2.5 py-0.5 rounded-full ${banTypeBadgeClasses(
                    match.ban_type
                  )}`}
                >
                  {match.ban_type}
                </span>
                {match.reason_category && (
                  <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60 bg-earth-100 dark:bg-earth-700 px-2 py-0.5 rounded-full">
                    {formatReason(match.reason_category)}
                  </span>
                )}
                {match.reason_category && (
                  <BanReportRationaleViewer
                    rationalePresent={match.rationale_present ?? false}
                    rationaleAnticipated={match.rationale_anticipated ?? false}
                    primaryUseCase={match.rationale_primary_use_case ?? null}
                    banCategory={match.reason_category}
                  />
                )}
                <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60">
                  {formatDate(match.date_reported)}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
