/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Link } from 'react-router-dom'
import { ShieldAlert, BarChart3, Library, Flame, ChevronRight } from 'lucide-react'
import { US_STATES_MAP } from '@/components/ban-tracker/ban-tracker-data'
import type { BanStats, MostBannedBook } from '@/components/ban-tracker/types'

interface BanContextSectionsProps {
  banStats: BanStats | null
  mostBanned: MostBannedBook[]
  loading: boolean
}

export default function BanContextSections({
  banStats,
  mostBanned,
  loading,
}: BanContextSectionsProps): React.ReactElement | null {
  if (loading) return null
  return (
    <>
      {banStats && banStats.total_reports > 0 && <ImpactStats banStats={banStats} />}
      {mostBanned.length > 0 && <MostTargetedBooks mostBanned={mostBanned} />}
      {banStats && banStats.by_state.length > 0 && <StateBansBreakdown banStats={banStats} />}
    </>
  )
}

function ImpactStats({ banStats }: { banStats: BanStats }): React.ReactElement {
  return (
    <section aria-labelledby="ban-stats-heading" className="mb-8">
      <div className="flex items-center gap-2 mb-4">
        <ShieldAlert className="w-5 h-5 text-status-danger-500 dark:text-status-danger-400" aria-hidden="true" />
        <h2 id="ban-stats-heading" className="font-serif text-xl font-bold text-lsc-dark dark:text-lsc-cream">
          The Scale of the Problem
        </h2>
      </div>
      <div className="grid grid-cols-3 gap-4">
        <StatCard
          icon={<ShieldAlert className="w-5 h-5" aria-hidden="true" />}
          iconClass="bg-status-danger-100 dark:bg-status-danger-900/30 text-status-danger-600 dark:text-status-danger-400"
          value={banStats.total_reports.toLocaleString()}
          label="Ban Reports"
        />
        <StatCard
          icon={<BarChart3 className="w-5 h-5" aria-hidden="true" />}
          iconClass="bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-600 dark:text-status-warning-400"
          value={String(banStats.total_states)}
          label="States Affected"
        />
        <StatCard
          icon={<Library className="w-5 h-5" aria-hidden="true" />}
          iconClass="bg-lsc-rose/10 dark:bg-lsc-rose/20 text-lsc-rose dark:text-lsc-rose-light"
          value={String(banStats.total_has_in_cataloges)}
          label="In Our Catalog"
        />
      </div>
    </section>
  )
}

function StatCard({
  icon,
  iconClass,
  value,
  label,
}: {
  icon: React.ReactNode
  iconClass: string
  value: string
  label: string
}): React.ReactElement {
  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-5 text-center">
      <div className="flex justify-center mb-2">
        <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${iconClass}`}>{icon}</div>
      </div>
      <div className="text-3xl font-bold text-lsc-dark dark:text-lsc-cream mb-1">{value}</div>
      <div className="text-sm text-lsc-dark/70 dark:text-lsc-cream/60">{label}</div>
    </div>
  )
}

function MostTargetedBooks({ mostBanned }: { mostBanned: MostBannedBook[] }): React.ReactElement {
  return (
    <section aria-labelledby="most-targeted-heading" className="mb-8">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Flame className="w-5 h-5 text-status-danger-500 dark:text-status-danger-400" aria-hidden="true" />
          <h2 id="most-targeted-heading" className="font-serif text-xl font-bold text-lsc-dark dark:text-lsc-cream">
            Most Targeted Books
          </h2>
        </div>
        <Link
          to="/ban-tracker"
          className="text-sm text-lsc-rose dark:text-lsc-rose-light hover:underline font-medium flex items-center gap-1"
        >
          View full tracker
          <ChevronRight className="w-4 h-4" aria-hidden="true" />
        </Link>
      </div>
      <div className="flex gap-3 overflow-x-auto pb-2">
        {mostBanned.map((book, idx) => (
          <div
            key={`${book.title}-${idx}`}
            className="flex-shrink-0 w-56 bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-4"
          >
            <div className="flex items-start gap-3">
              <span className="flex-shrink-0 w-7 h-7 rounded-full bg-status-danger-100 dark:bg-status-danger-900/30 text-status-danger-700 dark:text-status-danger-300 text-xs font-bold flex items-center justify-center">
                {idx + 1}
              </span>
              <div className="min-w-0">
                <p className="font-bold text-sm text-lsc-dark dark:text-lsc-cream leading-tight truncate" title={book.title}>
                  {book.title}
                </p>
                <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60 mt-0.5 truncate" title={book.author}>
                  {book.author}
                </p>
                <p className="text-xs text-status-danger-600 dark:text-status-danger-400 font-semibold mt-1.5">
                  {book.report_count} report{book.report_count !== 1 ? 's' : ''} &middot; {book.state_count} state
                  {book.state_count !== 1 ? 's' : ''}
                </p>
              </div>
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}

function StateBansBreakdown({ banStats }: { banStats: BanStats }): React.ReactElement {
  const maxCount = banStats.by_state[0]?.count ?? 1
  return (
    <section aria-labelledby="state-bans-heading" className="mb-8">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <BarChart3 className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" aria-hidden="true" />
          <h2 id="state-bans-heading" className="font-serif text-xl font-bold text-lsc-dark dark:text-lsc-cream">
            Where to Focus Your Letters
          </h2>
        </div>
      </div>
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-5">
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/60 mb-4">
          States with the most ban activity — your letters matter most here.
        </p>
        <div className="space-y-2.5">
          {banStats.by_state.slice(0, 8).map((entry) => {
            const pct = Math.round((entry.count / maxCount) * 100)
            return (
              <div key={entry.state} className="flex items-center gap-3">
                <span className="w-8 text-sm font-bold text-lsc-dark dark:text-lsc-cream text-right flex-shrink-0">
                  {entry.state}
                </span>
                <div className="flex-1 h-5 bg-earth-100 dark:bg-earth-700 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-lsc-rose to-red-500 rounded-full transition-all"
                    style={{ width: `${Math.max(pct, 8)}%` }}
                  />
                </div>
                <span className="w-8 text-sm font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 text-right flex-shrink-0">
                  {entry.count}
                </span>
                <span
                  className="hidden sm:inline text-xs text-lsc-dark/70 dark:text-lsc-cream/60 w-28 truncate"
                  title={US_STATES_MAP[entry.state] ?? entry.state}
                >
                  {US_STATES_MAP[entry.state] ?? entry.state}
                </span>
              </div>
            )
          })}
        </div>
      </div>
    </section>
  )
}
