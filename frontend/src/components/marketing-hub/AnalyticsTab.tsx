/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useId, useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  BarChart3,
  CheckCircle,
  ExternalLink,
  Loader2,
  Mail,
  TrendingUp,
  Users,
} from 'lucide-react'
import { Link } from 'react-router-dom'
import { getMarketingAnalytics } from '@/api/marketing-api'
import { StatCard } from '@/components/marketing/StatCard'

type DateRange = 7 | 30 | 90

const RANGE_OPTIONS: { value: DateRange; label: string }[] = [
  { value: 7, label: 'Last 7 days' },
  { value: 30, label: 'Last 30 days' },
  { value: 90, label: 'Last 90 days' },
]

const TREND_DAYS = 14

export function AnalyticsTab({ token }: { token: string }): React.ReactElement {
  const [dateRange, setDateRange] = useState<DateRange>(30)
  const selectId = useId()

  const { data: analytics, isLoading, isError } = useQuery({
    queryKey: ['marketing-hub-analytics', dateRange],
    queryFn: () => getMarketingAnalytics(token, { days: dateRange }),
  })

  const trendPoints = useMemo(() => {
    if (!analytics?.subscriber_trend?.length) return []
    return analytics.subscriber_trend.slice(-TREND_DAYS)
  }, [analytics])

  const trendSummary = useMemo(() => {
    const first = trendPoints[0]
    const last = trendPoints[trendPoints.length - 1]
    if (!first || !last) return ''
    const delta = last.count - first.count
    const direction = delta > 0 ? 'grew' : delta < 0 ? 'fell' : 'stayed level'
    return `Subscriber count ${direction} from ${first.count.toLocaleString()} on ${first.date} to ${last.count.toLocaleString()} on ${last.date} over the last ${trendPoints.length} days.`
  }, [trendPoints])

  return (
    <section aria-labelledby="analytics-heading" className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-3">
        <div>
          <h2
            id="analytics-heading"
            className="text-xl font-serif font-semibold text-lsc-dark dark:text-lsc-cream"
          >
            Marketing analytics
          </h2>
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
            Subscriber and email performance at a glance.
          </p>
        </div>
        <div className="flex flex-col gap-1">
          <label
            htmlFor={selectId}
            className="text-sm font-medium text-lsc-dark dark:text-lsc-cream"
          >
            Date range
          </label>
          <select
            id={selectId}
            value={dateRange}
            onChange={(e) => setDateRange(Number(e.target.value) as DateRange)}
            className="px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
          >
            {RANGE_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {isLoading ? (
        <div
          role="status"
          aria-live="polite"
          className="bg-lsc-white dark:bg-earth-800 rounded-xl p-8 border border-lsc-border dark:border-earth-700 flex items-center justify-center min-h-[16rem]"
        >
          <Loader2
            aria-hidden="true"
            className="w-6 h-6 motion-safe:animate-spin text-lsc-rose"
          />
          <span className="sr-only">Loading analytics…</span>
        </div>
      ) : isError || !analytics ? (
        <div
          role={isError ? 'alert' : undefined}
          className="bg-lsc-white dark:bg-earth-800 rounded-xl p-8 border border-lsc-border dark:border-earth-700 text-center"
        >
          <BarChart3
            aria-hidden="true"
            className="w-12 h-12 text-lsc-rose mx-auto mb-4 opacity-50"
          />
          <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-1">
            No analytics yet
          </h3>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
            Send a campaign or grow your subscriber list to see metrics here.
          </p>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <StatCard
              title="Total subscribers"
              value={analytics.total_subscribers.toLocaleString()}
              icon={Users}
              color="accent"
            />
            <StatCard
              title="Active subscribers"
              value={analytics.active_subscribers.toLocaleString()}
              icon={CheckCircle}
              color="success"
            />
            <StatCard
              title="New this month"
              value={`+${analytics.new_subscribers_this_month.toLocaleString()}`}
              icon={TrendingUp}
              color="warning"
              trend={analytics.subscriber_growth_rate}
            />
            <StatCard
              title="Avg open rate"
              value={`${analytics.average_open_rate.toFixed(1)}%`}
              icon={Mail}
              color="accent"
            />
          </div>

          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 border border-lsc-border dark:border-earth-700">
            <div className="flex items-baseline justify-between gap-3 mb-4">
              <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
                Subscriber growth
              </h3>
              <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                Last {trendPoints.length || TREND_DAYS} days
              </p>
            </div>

            {trendPoints.length === 0 ? (
              <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
                Not enough data to show a trend yet.
              </p>
            ) : (
              <>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-3">
                  {trendSummary}
                </p>
                <div
                  className="h-40 flex items-end gap-1"
                  role="img"
                  aria-label={trendSummary}
                >
                  {(() => {
                    const counts = trendPoints.map((p) => p.count)
                    const maxCount = Math.max(...counts)
                    const minCount = Math.min(...counts)
                    const range = maxCount - minCount || 1
                    return trendPoints.map((point) => {
                      const height = ((point.count - minCount) / range) * 80 + 20
                      const label = `${point.date}: ${point.count.toLocaleString()} subscribers`
                      return (
                        <div
                          key={point.date}
                          className="flex-1 bg-lsc-rose/70 rounded-t"
                          style={{ height: `${height}%` }}
                          title={label}
                          aria-label={label}
                        />
                      )
                    })
                  })()}
                </div>
                <div className="flex justify-between mt-2 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                  <span>{trendPoints[0]?.date}</span>
                  <span>{trendPoints[trendPoints.length - 1]?.date}</span>
                </div>
                <details className="mt-4 text-sm">
                  <summary className="cursor-pointer text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose rounded">
                    View daily values
                  </summary>
                  <ul className="mt-2 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-x-4 gap-y-1 text-lsc-dark/70 dark:text-lsc-cream/70">
                    {trendPoints.map((point) => (
                      <li key={point.date}>
                        <span className="text-lsc-dark dark:text-lsc-cream font-medium">
                          {point.count.toLocaleString()}
                        </span>{' '}
                        on {point.date}
                      </li>
                    ))}
                  </ul>
                </details>
              </>
            )}
          </div>
        </>
      )}

      <div className="flex justify-end pt-2">
        <Link
          to="/staff/marketing"
          className="inline-flex items-center gap-2 px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-lg font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-lsc-rose"
        >
          <BarChart3 aria-hidden="true" className="w-4 h-4" />
          Open full analytics
          <ExternalLink aria-hidden="true" className="w-4 h-4" />
        </Link>
      </div>
    </section>
  )
}
