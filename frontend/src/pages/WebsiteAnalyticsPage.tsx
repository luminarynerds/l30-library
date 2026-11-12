/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  BarChart3,
  Users,
  Globe,
  Link2,
  MapPin,
  Eye,
  Activity,
  Download,
} from 'lucide-react'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from 'recharts'
import {
  getWebsiteAnalyticsStats,
  getWebsiteAnalyticsPageviews,
  getWebsiteAnalyticsMetrics,
  getWebsiteAnalyticsActive,
  type WebsiteMetricType,
  type MetricRow,
  type MetricValue,
} from '@/api/website-analytics-api'
import { StatCard } from '@/components/ui/StatCard'
import { StatGrid } from '@/components/ui/StatGrid'
import { AdminShell } from '@/components/shells/AdminShell'

type DayRange = 7 | 30 | 90

const DAY_OPTIONS: DayRange[] = [7, 30, 90]

function csvEscape(value: string | number | null | undefined): string {
  if (value === null || value === undefined) return ''
  const s = String(value)
  if (/[",\n\r]/.test(s)) return `"${s.replace(/"/g, '""')}"`
  return s
}

function csvRow(...cells: Array<string | number | null | undefined>): string {
  return cells.map(csvEscape).join(',')
}

function downloadCsv(filename: string, content: string): void {
  const blob = new Blob([content], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

function deltaPercent(curr: number, prev?: number): number | null {
  if (prev === undefined || prev === null || prev === 0) return null
  return ((curr - prev) / prev) * 100
}

function trendFor(metric?: MetricValue): { value: number } | undefined {
  if (!metric) return undefined
  const pct = deltaPercent(metric.value, metric.prev)
  if (pct === null || !Number.isFinite(pct)) return undefined
  return { value: Math.round(pct * 10) / 10 }
}

function Spinner() {
  return (
    <div className="flex items-center justify-center h-32">
      <div className="motion-safe:animate-spin rounded-full h-8 w-8 border-b-2 border-lsc-rose" />
    </div>
  )
}

function EmptyState({ icon: Icon, message }: { icon: React.ElementType; message: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-10 gap-2">
      <Icon className="w-12 h-12 opacity-50 text-lsc-dark/70 dark:text-lsc-cream/70" />
      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{message}</p>
    </div>
  )
}

function SectionHeader({ title, icon: Icon }: { title: string; icon: React.ElementType }) {
  return (
    <div className="flex items-center gap-2 mb-4">
      <Icon className="w-5 h-5 text-lsc-rose" />
      <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">{title}</h2>
    </div>
  )
}

function MetricList({
  type,
  days,
  title,
  icon,
  labelFormatter,
}: {
  type: WebsiteMetricType
  days: DayRange
  title: string
  icon: React.ElementType
  labelFormatter?: (row: MetricRow) => string
}) {
  const { data, isLoading, error } = useQuery<MetricRow[]>({
    queryKey: ['website-analytics', 'metrics', type, days],
    queryFn: () => getWebsiteAnalyticsMetrics(type, days, 10),
  })

  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm p-6 border border-lsc-border dark:border-earth-700">
      <SectionHeader title={title} icon={icon} />
      {isLoading ? (
        <Spinner />
      ) : error ? (
        <p className="text-sm text-status-danger-600 dark:text-status-danger-400">Failed to load.</p>
      ) : !data || data.length === 0 ? (
        <EmptyState icon={icon} message="No data yet" />
      ) : (
        <ol className="space-y-2">
          {data.map((row, idx) => {
            const label = labelFormatter ? labelFormatter(row) : row.x
            return (
              <li key={`${row.x}-${idx}`} className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-3 min-w-0">
                  <span className="w-6 h-6 flex-shrink-0 rounded-full bg-lsc-rose/20 text-lsc-rose text-xs flex items-center justify-center font-medium">
                    {idx + 1}
                  </span>
                  <span
                    className="text-sm text-lsc-dark dark:text-lsc-cream truncate"
                    title={label}
                  >
                    {label}
                  </span>
                </div>
                <span className="text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 flex-shrink-0">
                  {row.y.toLocaleString()}
                </span>
              </li>
            )
          })}
        </ol>
      )}
    </div>
  )
}

function PageviewsChart({ days }: { days: DayRange }) {
  const { data, isLoading, error } = useQuery({
    queryKey: ['website-analytics', 'pageviews', days],
    queryFn: () => getWebsiteAnalyticsPageviews(days, 'day'),
  })

  const points = data?.pageviews ?? []

  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm p-6 border border-lsc-border dark:border-earth-700">
      <SectionHeader title="Pageviews" icon={BarChart3} />
      {isLoading ? (
        <Spinner />
      ) : error ? (
        <p className="text-sm text-status-danger-600 dark:text-status-danger-400">Failed to load.</p>
      ) : points.length === 0 ? (
        <EmptyState icon={BarChart3} message="No data yet" />
      ) : (
        <div className="h-64 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={points} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="currentColor" className="text-lsc-border dark:text-earth-700" />
              <XAxis dataKey="x" stroke="currentColor" className="text-lsc-dark/70 dark:text-lsc-cream/70" fontSize={11} />
              <YAxis stroke="currentColor" className="text-lsc-dark/70 dark:text-lsc-cream/70" fontSize={11} allowDecimals={false} />
              <Tooltip
                contentStyle={{ background: 'rgba(31,24,18,0.95)', border: 'none', borderRadius: 8, color: '#FFF4E6' }}
                cursor={{ fill: 'rgba(190,107,107,0.15)' }}
              />
              <Bar dataKey="y" name="Pageviews" fill="#BE6B6B" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  )
}

export default function WebsiteAnalyticsPage(): React.ReactElement {
  const [days, setDays] = useState<DayRange>(30)

  const { data: stats, isLoading: loadingStats, error: statsError } = useQuery({
    queryKey: ['website-analytics', 'stats', days],
    queryFn: () => getWebsiteAnalyticsStats(days),
  })

  const { data: active } = useQuery({
    queryKey: ['website-analytics', 'active'],
    queryFn: () => getWebsiteAnalyticsActive(),
    refetchInterval: 30_000,
    refetchIntervalInBackground: false,
  })

  const { data: pageviewsSeries, isLoading: loadingPageviews } = useQuery({
    queryKey: ['website-analytics', 'pageviews', days],
    queryFn: () => getWebsiteAnalyticsPageviews(days, 'day'),
  })

  const { data: topPages, isLoading: loadingPages } = useQuery<MetricRow[]>({
    queryKey: ['website-analytics', 'metrics', 'path', days],
    queryFn: () => getWebsiteAnalyticsMetrics('path', days, 10),
  })

  const { data: topReferrers, isLoading: loadingReferrers } = useQuery<MetricRow[]>({
    queryKey: ['website-analytics', 'metrics', 'referrer', days],
    queryFn: () => getWebsiteAnalyticsMetrics('referrer', days, 10),
  })

  const { data: topCountries, isLoading: loadingCountries } = useQuery<MetricRow[]>({
    queryKey: ['website-analytics', 'metrics', 'country', days],
    queryFn: () => getWebsiteAnalyticsMetrics('country', days, 10),
  })

  const exportDisabled =
    loadingStats || loadingPageviews || loadingPages || loadingReferrers || loadingCountries

  const handleExportCsv = (): void => {
    const rangeLabel = `${days}d`
    const lines: string[] = []
    lines.push('Website Traffic Export')
    lines.push(csvRow('Range', rangeLabel))
    lines.push(csvRow('Generated', new Date().toISOString()))
    lines.push('')
    lines.push('Summary')
    lines.push(csvRow('Pageviews', stats?.pageviews.value ?? 0))
    lines.push(csvRow('Visitors', stats?.visitors.value ?? 0))
    lines.push(csvRow('Visits', stats?.visits.value ?? 0))
    const bounce =
      stats && stats.visits.value > 0
        ? (stats.bounces.value / stats.visits.value) * 100
        : 0
    lines.push(csvRow('Bounce Rate', `${bounce.toFixed(1)}%`))
    lines.push('')
    lines.push('Pageviews by Day')
    lines.push(csvRow('Date', 'Pageviews'))
    for (const p of pageviewsSeries?.pageviews ?? []) {
      lines.push(csvRow(p.x, p.y))
    }
    lines.push('')
    lines.push('Top Pages')
    lines.push(csvRow('Path', 'Views'))
    for (const r of topPages ?? []) {
      lines.push(csvRow(r.x, r.y))
    }
    lines.push('')
    lines.push('Top Referrers')
    lines.push(csvRow('Referrer', 'Views'))
    for (const r of topReferrers ?? []) {
      lines.push(csvRow(r.x || '(direct)', r.y))
    }
    lines.push('')
    lines.push('Top Countries')
    lines.push(csvRow('Country', 'Visits'))
    for (const r of topCountries ?? []) {
      lines.push(csvRow(r.x || 'Unknown', r.y))
    }
    const today = new Date().toISOString().slice(0, 10)
    downloadCsv(`website-traffic-${rangeLabel}-${today}.csv`, lines.join('\n'))
  }

  const bounceRate =
    stats && stats.visits.value > 0
      ? (stats.bounces.value / stats.visits.value) * 100
      : null
  const prevBounceRate =
    stats && stats.visits.prev !== undefined && stats.visits.prev > 0 && stats.bounces.prev !== undefined
      ? (stats.bounces.prev / stats.visits.prev) * 100
      : undefined

  const bounceTrend =
    bounceRate !== null && prevBounceRate !== undefined && prevBounceRate !== 0
      ? {
          // Lower bounce rate is better; surface signed delta in points.
          value: Math.round((bounceRate - prevBounceRate) * 10) / 10,
        }
      : undefined

  const liveBadge = (
    <div
      className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-status-success-100 dark:bg-status-success-900/30 text-status-success-700 dark:text-status-success-400 text-xs font-medium"
      title="Active visitors in the last 5 minutes"
    >
      <span className="relative flex h-2 w-2">
        <span className="motion-safe:animate-ping absolute inline-flex h-full w-full rounded-full bg-status-success-500 opacity-75" />
        <span className="relative inline-flex rounded-full h-2 w-2 bg-status-success-600" />
      </span>
      {active ? `${active.visitors} active now` : 'Live'}
    </div>
  )

  const rangeButtons = (
    <div className="flex items-center gap-1 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 p-1">
      {DAY_OPTIONS.map((d) => (
        <button
          key={d}
          onClick={() => setDays(d)}
          className={`px-3 py-1 rounded-lg text-sm font-medium transition-colors ${
            days === d
              ? 'bg-lsc-rose text-white'
              : 'text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-earth-700'
          }`}
          aria-pressed={days === d}
        >
          {d}d
        </button>
      ))}
    </div>
  )

  return (
    <AdminShell
      title="Website Analytics"
      subtitle="Public site traffic, top pages, and visitor sources"
      actions={
        <div className="flex items-center gap-3">
          {liveBadge}
          {rangeButtons}
          <button
            onClick={handleExportCsv}
            disabled={exportDisabled}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-sm font-medium text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-earth-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <Download className="w-4 h-4" />
            Export CSV
          </button>
        </div>
      }
    >
      <div className="space-y-6">
        {statsError && (
          <p className="text-sm text-status-danger-600 dark:text-status-danger-400">
            Failed to load stats.
          </p>
        )}

        {loadingStats ? (
          <Spinner />
        ) : (
          <StatGrid columns={4}>
            <StatCard
              title="Pageviews"
              value={(stats?.pageviews.value ?? 0).toLocaleString()}
              icon={Eye}
              color="accent"
              {...(trendFor(stats?.pageviews) ? { trend: trendFor(stats?.pageviews)! } : {})}
            />
            <StatCard
              title="Visitors"
              value={(stats?.visitors.value ?? 0).toLocaleString()}
              icon={Users}
              color="success"
              {...(trendFor(stats?.visitors) ? { trend: trendFor(stats?.visitors)! } : {})}
            />
            <StatCard
              title="Visits"
              value={(stats?.visits.value ?? 0).toLocaleString()}
              icon={Activity}
              color="category"
              {...(trendFor(stats?.visits) ? { trend: trendFor(stats?.visits)! } : {})}
            />
            <StatCard
              title="Bounce Rate"
              value={bounceRate !== null ? `${bounceRate.toFixed(1)}%` : '—'}
              icon={BarChart3}
              color="warning"
              {...(bounceTrend ? { trend: bounceTrend } : {})}
            />
          </StatGrid>
        )}

        <PageviewsChart days={days} />

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <MetricList
            type="path"
            days={days}
            title="Top Pages"
            icon={BarChart3}
          />
          <MetricList
            type="referrer"
            days={days}
            title="Top Referrers"
            icon={Link2}
            labelFormatter={(row) => row.x || '(direct)'}
          />
          <MetricList
            type="country"
            days={days}
            title="Top Countries"
            icon={MapPin}
            labelFormatter={(row) => row.x || 'Unknown'}
          />
        </div>

        <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 flex items-center gap-1.5">
          <Globe className="w-3 h-3" />
          Live visitor count refreshes every 30 seconds.
        </p>
      </div>
    </AdminShell>
  )
}
