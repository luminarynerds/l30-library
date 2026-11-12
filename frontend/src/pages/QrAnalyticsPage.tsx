/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * QrAnalyticsPage
 *
 * Staff dashboard for QR poster scan attribution. Renders a single table
 * (Slug | This month | Last month | All time | Last 6 months) over the
 * selected period. Backed by the existing Umami integration; if Umami
 * isn't configured the API returns 503 and we show an empty state instead
 * of crashing.
 *
 * Intentionally simple: no charts library yet, text-only sparkline as the
 * trend column. First iteration; richer viz can come later.
 */
import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { QrCode } from 'lucide-react'

import StandardPageLayout from '@/components/StandardPageLayout'
import { ApiError } from '@/lib/api-client'
import {
  getQrAnalytics,
  getQrAnalyticsByMonth,
  type QrAnalyticsRow,
  type QrAnalyticsByMonth,
} from '@/api/qr-analytics-api'

type DayRange = 30 | 60 | 90 | 365
const DAY_OPTIONS: DayRange[] = [30, 60, 90, 365]
const TREND_MONTHS = 6

function formatCount(n: number): string {
  return n.toLocaleString()
}

function isUmamiUnavailable(err: unknown): boolean {
  return err instanceof ApiError && err.status === 503
}

function isForbidden(err: unknown): boolean {
  return err instanceof ApiError && err.status === 403
}

export default function QrAnalyticsPage(): React.ReactElement {
  const [days, setDays] = useState<DayRange>(30)

  const allTimeQ = useQuery<QrAnalyticsRow[]>({
    queryKey: ['qr-analytics', 'totals', days],
    queryFn: () => getQrAnalytics(days),
    retry: false,
  })

  const monthlyQ = useQuery<QrAnalyticsByMonth>({
    queryKey: ['qr-analytics', 'by-month', TREND_MONTHS],
    queryFn: () => getQrAnalyticsByMonth(TREND_MONTHS),
    retry: false,
  })

  // Each query may 503 independently; only treat as "Umami not configured"
  // when at least one fetch reports 503.
  const umamiUnavailable =
    isUmamiUnavailable(allTimeQ.error) || isUmamiUnavailable(monthlyQ.error)
  const forbidden = isForbidden(allTimeQ.error) || isForbidden(monthlyQ.error)

  // Build the per-slug "this month" / "last month" lookup from the by-month
  // payload. months[] is oldest -> newest, so the last two indices are last
  // month and this month.
  const monthLookup = useMemo(() => {
    const data = monthlyQ.data
    if (!data || data.months.length === 0) {
      return { thisMonth: new Map<string, number>(), lastMonth: new Map<string, number>() }
    }
    const lastIdx = data.months.length - 1
    const prevIdx = data.months.length >= 2 ? data.months.length - 2 : -1
    const thisMonth = new Map<string, number>()
    const lastMonth = new Map<string, number>()
    for (const s of data.series) {
      thisMonth.set(s.slug, s.counts[lastIdx] ?? 0)
      lastMonth.set(s.slug, prevIdx >= 0 ? s.counts[prevIdx] ?? 0 : 0)
    }
    return { thisMonth, lastMonth }
  }, [monthlyQ.data])

  const trendBySlug = useMemo(() => {
    const map = new Map<string, number[]>()
    if (monthlyQ.data) {
      for (const s of monthlyQ.data.series) {
        map.set(s.slug, s.counts)
      }
    }
    return map
  }, [monthlyQ.data])

  const rows: QrAnalyticsRow[] = allTimeQ.data ?? []
  const loading = allTimeQ.isLoading || monthlyQ.isLoading

  return (
    <StandardPageLayout
      title="QR Poster Scans"
      subtitle="Which physical posters are driving traffic, sourced from Umami pageviews."
      icon={QrCode}
    >
      {umamiUnavailable ? (
        <EmptyState
          headline="Analytics not available"
          body="Umami integration is not configured for this site. Once UMAMI_URL and UMAMI_WEBSITE_ID are set, QR-scan counts will appear here automatically."
        />
      ) : forbidden ? (
        <EmptyState
          headline="Insufficient permissions"
          body="Your account doesn't have access to QR analytics. Ask an admin if you need this view."
        />
      ) : (
        <div className="space-y-4">
          <PeriodSelector value={days} onChange={setDays} />

          {loading ? (
            <Spinner />
          ) : allTimeQ.isError || monthlyQ.isError ? (
            <ErrorBanner
              message={
                (allTimeQ.error instanceof ApiError && allTimeQ.error.message) ||
                (monthlyQ.error instanceof ApiError && monthlyQ.error.message) ||
                'Failed to load QR analytics.'
              }
            />
          ) : rows.length === 0 ? (
            <EmptyState
              headline="No QR scans yet"
              body="Once patrons start scanning the posters, attributed pageviews will show up here."
            />
          ) : (
            <ScansTable
              rows={rows}
              thisMonth={monthLookup.thisMonth}
              lastMonth={monthLookup.lastMonth}
              trends={trendBySlug}
              months={monthlyQ.data?.months ?? []}
              days={days}
            />
          )}
        </div>
      )}
    </StandardPageLayout>
  )
}

// ---------------------------------------------------------------------------
// Sub-components (kept in-file; this page is self-contained.)
// ---------------------------------------------------------------------------

function PeriodSelector({
  value,
  onChange,
}: {
  value: DayRange
  onChange: (d: DayRange) => void
}) {
  return (
    <div
      role="radiogroup"
      aria-label="Time period for top table"
      className="flex gap-2 flex-wrap"
    >
      {DAY_OPTIONS.map((d) => {
        const active = d === value
        return (
          <button
            key={d}
            type="button"
            role="radio"
            aria-checked={active}
            onClick={() => onChange(d)}
            className={[
              'min-h-[40px] px-3 py-1.5 text-sm rounded-lg border',
              'focus:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose',
              active
                ? 'border-lsc-rose bg-lsc-rose text-white'
                : 'border-earth-300 bg-lsc-cream hover:bg-earth-100 text-lsc-dark dark:border-earth-700 dark:bg-lsc-dark dark:text-lsc-cream dark:hover:bg-earth-900',
            ].join(' ')}
          >
            Last {d} days
          </button>
        )
      })}
    </div>
  )
}

function ScansTable({
  rows,
  thisMonth,
  lastMonth,
  trends,
  months,
  days,
}: {
  rows: QrAnalyticsRow[]
  thisMonth: Map<string, number>
  lastMonth: Map<string, number>
  trends: Map<string, number[]>
  months: string[]
  days: DayRange
}) {
  return (
    <div className="overflow-x-auto">
      <table
        data-testid="qr-analytics-table"
        className="w-full text-sm border-collapse"
      >
        <caption className="sr-only">
          QR poster scan counts. Last {days} days in the all-time column; per-month
          breakdown spans {months.length} months.
        </caption>
        <thead>
          <tr className="text-left border-b border-earth-300 dark:border-earth-700">
            <th scope="col" className="py-2 pr-3 font-medium">Slug</th>
            <th scope="col" className="py-2 px-3 font-medium text-right">This month</th>
            <th scope="col" className="py-2 px-3 font-medium text-right">Last month</th>
            <th scope="col" className="py-2 px-3 font-medium text-right">Last {days}d</th>
            <th scope="col" className="py-2 pl-3 font-medium">Trend (last {months.length || TREND_MONTHS} months)</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const tm = thisMonth.get(row.slug) ?? 0
            const lm = lastMonth.get(row.slug) ?? 0
            const trend = trends.get(row.slug) ?? []
            return (
              <tr
                key={row.slug}
                data-testid={`qr-analytics-row-${row.slug}`}
                className="border-b border-earth-200 dark:border-earth-800"
              >
                <td className="py-2 pr-3 font-mono text-xs break-all">{row.slug}</td>
                <td className="py-2 px-3 text-right tabular-nums">{formatCount(tm)}</td>
                <td className="py-2 px-3 text-right tabular-nums">{formatCount(lm)}</td>
                <td className="py-2 px-3 text-right tabular-nums">{formatCount(row.pageviews)}</td>
                <td className="py-2 pl-3 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                  {trend.length === 0
                    ? '-'
                    : trend.map((n, i) => (months[i] ? `${months[i]}: ${n}` : String(n))).join('  ')}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

function EmptyState({ headline, body }: { headline: string; body: string }) {
  return (
    <div
      data-testid="qr-analytics-empty"
      className="flex flex-col items-center justify-center text-center py-12 gap-2"
    >
      <QrCode className="w-10 h-10 opacity-50 text-lsc-dark/70 dark:text-lsc-cream/70" aria-hidden="true" />
      <h2 className="font-semibold text-lsc-dark dark:text-lsc-cream">{headline}</h2>
      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 max-w-md">{body}</p>
    </div>
  )
}

function ErrorBanner({ message }: { message: string }) {
  return (
    <div
      role="alert"
      data-testid="qr-analytics-error"
      className="rounded-lg border border-status-danger-300 bg-status-danger-50 dark:bg-status-danger-900/20 text-status-danger-700 dark:text-status-danger-300 p-3 text-sm"
    >
      {message}
    </div>
  )
}

function Spinner() {
  return (
    <div className="flex items-center justify-center py-12" data-testid="qr-analytics-loading">
      <div className="motion-safe:animate-spin rounded-full h-8 w-8 border-b-2 border-lsc-rose" />
      <span className="sr-only">Loading QR analytics</span>
    </div>
  )
}
