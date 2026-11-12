/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React, { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { TrendingDown, TrendingUp, AlertTriangle, Users, Clock, Calendar, Activity } from 'lucide-react'
import { AdminShell } from '../../components/shells/AdminShell'
import { getCurrentLocale } from '@/i18n'
import {
  getCirculationTrends,
  getCirculationAnalytics,
  getPatronEngagement,
  getOverdueItems,
  type CirculationTrend,
} from '@/api/domains/analytics/analytics-api'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface Anomaly {
  date: string
  actual: number
  average: number
  deviation: number
  direction: 'spike' | 'drop'
}

interface OverdueBucket {
  label: string
  count: number
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function detectAnomalies(data: CirculationTrend[]): Anomaly[] {
  if (data.length < 14) return []

  const anomalies: Anomaly[] = []
  const windowSize = 7

  // Build rolling stats for each day starting from index windowSize
  for (let i = windowSize; i < data.length; i++) {
    const current = data[i]
    if (!current) continue
    const window = data.slice(i - windowSize, i)
    const mean = window.reduce((s, d) => s + d.checkouts, 0) / windowSize
    const variance =
      window.reduce((s, d) => s + (d.checkouts - mean) ** 2, 0) / windowSize
    const stdDev = Math.sqrt(variance)

    if (stdDev === 0) continue

    const actual = current.checkouts
    const zScore = (actual - mean) / stdDev

    if (Math.abs(zScore) > 2) {
      const pctChange = mean > 0 ? Math.round(((actual - mean) / mean) * 100) : 0
      anomalies.push({
        date: current.date,
        actual,
        average: Math.round(mean),
        deviation: pctChange,
        direction: actual > mean ? 'spike' : 'drop',
      })
    }
  }
  return anomalies
}

function projectMonthTotal(
  data: CirculationTrend[],
): { projected: number; daysElapsed: number; daysInMonth: number } | null {
  const now = new Date()
  const year = now.getFullYear()
  const month = now.getMonth()
  const daysInMonth = new Date(year, month + 1, 0).getDate()
  const daysElapsed = now.getDate()

  const thisMonthData = data.filter((d) => {
    const dt = new Date(d.date)
    return dt.getFullYear() === year && dt.getMonth() === month
  })

  if (thisMonthData.length === 0) return null

  const totalSoFar = thisMonthData.reduce((s, d) => s + d.checkouts, 0)
  const dailyRate = totalSoFar / thisMonthData.length
  const projected = Math.round(dailyRate * daysInMonth)

  return { projected, daysElapsed, daysInMonth }
}

function getLastMonthTotal(data: CirculationTrend[]): number {
  const now = new Date()
  const lastMonth = now.getMonth() === 0 ? 11 : now.getMonth() - 1
  const lastMonthYear = now.getMonth() === 0 ? now.getFullYear() - 1 : now.getFullYear()

  return data
    .filter((d) => {
      const dt = new Date(d.date)
      return dt.getFullYear() === lastMonthYear && dt.getMonth() === lastMonth
    })
    .reduce((s, d) => s + d.checkouts, 0)
}

function getSameMonthLastYear(data: CirculationTrend[]): number {
  const now = new Date()
  return data
    .filter((d) => {
      const dt = new Date(d.date)
      return dt.getFullYear() === now.getFullYear() - 1 && dt.getMonth() === now.getMonth()
    })
    .reduce((s, d) => s + d.checkouts, 0)
}

function bucketUpcomingDues(items: Array<{ due_date: string | null }>): OverdueBucket[] {
  const now = new Date()
  let in3 = 0
  let in7 = 0
  let in14 = 0

  for (const item of items) {
    if (!item.due_date) continue
    const due = new Date(item.due_date)
    const daysUntil = Math.ceil((due.getTime() - now.getTime()) / 86400000)
    if (daysUntil <= 3 && daysUntil >= 0) in3++
    else if (daysUntil <= 7 && daysUntil > 3) in7++
    else if (daysUntil <= 14 && daysUntil > 7) in14++
  }

  return [
    { label: 'Due in 3 days', count: in3 },
    { label: 'Due in 4-7 days', count: in7 },
    { label: 'Due in 8-14 days', count: in14 },
  ]
}

function formatDate(dateStr: string): string {
  const d = new Date(dateStr)
  return d.toLocaleDateString(getCurrentLocale(), { month: 'short', day: 'numeric' })
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function StatCard({
  title,
  value,
  subtitle,
  icon: Icon,
  color = 'earth',
}: {
  title: string
  value: string | number
  subtitle?: string
  icon: React.ElementType
  color?: 'earth' | 'red' | 'blue' | 'amber' | 'green' | 'success' | 'accent' | 'warning' | 'danger'
}) {
  const colors: Record<NonNullable<typeof color>, string> = {
    earth: 'bg-earth-100 dark:bg-earth-800 text-earth-700 dark:text-earth-300',
    red: 'bg-status-danger-50 dark:bg-status-danger-900/20 text-status-danger-700 dark:text-status-danger-300',
    blue: 'bg-status-info-50 dark:bg-status-info-900/20 text-status-info-700 dark:text-status-info-300',
    amber: 'bg-status-warning-50 dark:bg-status-warning-900/20 text-status-warning-700 dark:text-status-warning-300',
    green: 'bg-status-success-50 dark:bg-status-success-900/20 text-status-success-700 dark:text-status-success-300',
    // Semantic aliases
    success: 'bg-status-success-50 dark:bg-status-success-900/20 text-status-success-700 dark:text-status-success-300',
    accent: 'bg-status-info-50 dark:bg-status-info-900/20 text-status-info-700 dark:text-status-info-300',
    warning: 'bg-status-warning-50 dark:bg-status-warning-900/20 text-status-warning-700 dark:text-status-warning-300',
    danger: 'bg-status-danger-50 dark:bg-status-danger-900/20 text-status-danger-700 dark:text-status-danger-300',
  }

  return (
    <div className={`rounded-xl p-5 ${colors[color]}`}>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm font-medium opacity-80">{title}</p>
          <p className="text-2xl font-serif font-bold mt-1">{value}</p>
          {subtitle && <p className="text-xs mt-1 opacity-70">{subtitle}</p>}
        </div>
        <Icon className="h-5 w-5 opacity-60 flex-shrink-0" />
      </div>
    </div>
  )
}

function SectionHeader({ children }: { children: React.ReactNode }) {
  return (
    <h2 className="text-lg font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4">
      {children}
    </h2>
  )
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

const PredictiveAnalyticsPage: React.FC = () => {
  // Fetch 365 days of daily circulation data for anomaly detection + forecasting
  const trendsQuery = useQuery({
    queryKey: ['predictive', 'circulation-trends'],
    queryFn: () => getCirculationTrends({ days: 365 }),
    staleTime: 300000,
  })

  // Fetch circulation stats for active checkout counts
  const circulationQuery = useQuery({
    queryKey: ['predictive', 'circulation-stats'],
    queryFn: () => getCirculationAnalytics({ days: 90 }),
    staleTime: 300000,
  })

  // Fetch patron engagement for churn indicators
  const engagementQuery = useQuery({
    queryKey: ['predictive', 'patron-engagement'],
    queryFn: () => getPatronEngagement({ days: 60 }),
    staleTime: 300000,
  })

  // Fetch overdue items (large page to get upcoming dues)
  const overdueQuery = useQuery({
    queryKey: ['predictive', 'overdue-items'],
    queryFn: () => getOverdueItems({ per_page: 100 }),
    staleTime: 300000,
  })

  const isLoading =
    trendsQuery.isLoading ||
    circulationQuery.isLoading ||
    engagementQuery.isLoading ||
    overdueQuery.isLoading

  const hasError =
    trendsQuery.isError ||
    circulationQuery.isError

  const errorMessage = hasError
    ? 'Failed to load analytics data. Some sections may be unavailable.'
    : null

  // Computed analytics
  const anomalies = useMemo(() => {
    if (!trendsQuery.data?.data) return []
    return detectAnomalies(trendsQuery.data.data)
  }, [trendsQuery.data])

  const projection = useMemo(() => {
    if (!trendsQuery.data?.data) return null
    return projectMonthTotal(trendsQuery.data.data)
  }, [trendsQuery.data])

  const lastMonthTotal = useMemo(() => {
    if (!trendsQuery.data?.data) return 0
    return getLastMonthTotal(trendsQuery.data.data)
  }, [trendsQuery.data])

  const sameMonthLastYear = useMemo(() => {
    if (!trendsQuery.data?.data) return 0
    return getSameMonthLastYear(trendsQuery.data.data)
  }, [trendsQuery.data])

  const overdueBuckets = useMemo(() => {
    if (!overdueQuery.data?.items) return []
    return bucketUpcomingDues(overdueQuery.data.items)
  }, [overdueQuery.data])

  const recentAnomalies = anomalies.slice(-15).reverse()

  return (
    <AdminShell
      title="Predictive Analytics"
      subtitle="Anomaly detection, trend forecasting, and churn risk indicators"
      icon={<Activity className="h-6 w-6" />}
      loading={isLoading}
      error={errorMessage}
    >
      <div className="space-y-8">
        {/* ---------------------------------------------------------------- */}
        {/* Trend Forecasting */}
        {/* ---------------------------------------------------------------- */}
        <section>
          <SectionHeader>Trend Forecast</SectionHeader>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {projection && (
              <StatCard
                title="Projected This Month"
                value={projection.projected.toLocaleString()}
                subtitle={`${projection.daysElapsed} of ${projection.daysInMonth} days elapsed`}
                icon={TrendingUp}
                color="success"
              />
            )}
            <StatCard
              title="Last Month Total"
              value={lastMonthTotal.toLocaleString()}
              subtitle="Total checkouts"
              icon={Calendar}
              color="earth"
            />
            <StatCard
              title="Same Month Last Year"
              value={sameMonthLastYear > 0 ? sameMonthLastYear.toLocaleString() : 'N/A'}
              subtitle={sameMonthLastYear > 0 ? 'Total checkouts' : 'No data available'}
              icon={Calendar}
              color="earth"
            />
            {circulationQuery.data && (
              <StatCard
                title="Daily Average (90d)"
                value={circulationQuery.data.avg_daily_checkouts}
                subtitle={`${circulationQuery.data.unique_patrons} unique patrons`}
                icon={Activity}
                color="accent"
              />
            )}
          </div>
          {projection && lastMonthTotal > 0 && (
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-3">
              At the current pace, this month will have ~{projection.projected.toLocaleString()} checkouts
              {' '}(last month: {lastMonthTotal.toLocaleString()},{' '}
              {projection.projected > lastMonthTotal ? '+' : ''}
              {Math.round(((projection.projected - lastMonthTotal) / lastMonthTotal) * 100)}% change)
            </p>
          )}
        </section>

        {/* ---------------------------------------------------------------- */}
        {/* Circulation Anomaly Detection */}
        {/* ---------------------------------------------------------------- */}
        <section>
          <SectionHeader>Circulation Anomalies (last 90 days)</SectionHeader>
          {recentAnomalies.length === 0 ? (
            <div className="rounded-xl bg-status-success-50 dark:bg-status-success-900/20 border border-status-success-200 dark:border-status-success-800 p-4">
              <p className="text-sm text-status-success-700 dark:text-status-success-300">
                No significant anomalies detected in recent circulation patterns.
              </p>
            </div>
          ) : (
            <div className="space-y-2">
              {recentAnomalies.map((a) => (
                <div
                  key={a.date}
                  className={`flex items-start gap-3 rounded-xl border p-3 ${
                    a.direction === 'drop'
                      ? 'bg-status-danger-50 dark:bg-status-danger-900/10 border-status-danger-200 dark:border-status-danger-800'
                      : 'bg-status-info-50 dark:bg-status-info-900/10 border-status-info-200 dark:border-status-info-800'
                  }`}
                >
                  {a.direction === 'drop' ? (
                    <TrendingDown className="h-4 w-4 mt-0.5 text-status-danger-600 dark:text-status-danger-400 flex-shrink-0" />
                  ) : (
                    <TrendingUp className="h-4 w-4 mt-0.5 text-status-info-600 dark:text-status-info-400 flex-shrink-0" />
                  )}
                  <div className="text-sm">
                    <span className="font-medium text-lsc-dark dark:text-lsc-cream">
                      {formatDate(a.date)}:
                    </span>{' '}
                    <span className="text-lsc-dark/80 dark:text-lsc-cream/80">
                      {a.actual} checkouts (avg: {a.average})
                    </span>{' '}
                    <span
                      className={`font-medium ${
                        a.direction === 'drop'
                          ? 'text-status-danger-700 dark:text-status-danger-400'
                          : 'text-status-info-700 dark:text-status-info-400'
                      }`}
                    >
                      -- {Math.abs(a.deviation)}% {a.direction === 'drop' ? 'below' : 'above'} normal
                    </span>
                  </div>
                </div>
              ))}
              {anomalies.length > 15 && (
                <p className="text-xs text-lsc-dark/60 dark:text-lsc-cream/60 pl-1">
                  Showing 15 most recent of {anomalies.length} total anomalies
                </p>
              )}
            </div>
          )}
        </section>

        {/* ---------------------------------------------------------------- */}
        {/* Churn Risk Indicators */}
        {/* ---------------------------------------------------------------- */}
        <section>
          <SectionHeader>Patron Churn Risk</SectionHeader>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {engagementQuery.data && (
              <>
                <StatCard
                  title="Dormant Patrons"
                  value={engagementQuery.data.dormant_patrons}
                  subtitle="No activity in 180+ days"
                  icon={Users}
                  color={engagementQuery.data.dormant_patrons > 0 ? 'amber' : 'green'}
                />
                <StatCard
                  title="Engagement Rate"
                  value={`${engagementQuery.data.engagement_rate}%`}
                  subtitle={`${engagementQuery.data.active_patrons} of ${engagementQuery.data.total_patrons} patrons active`}
                  icon={Activity}
                  color={engagementQuery.data.engagement_rate < 20 ? 'red' : 'green'}
                />
                <StatCard
                  title="Retention Rate"
                  value={`${engagementQuery.data.retention_rate}%`}
                  subtitle="Returning from previous period"
                  icon={Users}
                  color={engagementQuery.data.retention_rate < 50 ? 'amber' : 'green'}
                />
              </>
            )}
          </div>
          {engagementQuery.data && (
            <div className="mt-4 rounded-xl bg-earth-50 dark:bg-earth-800/50 border border-earth-200 dark:border-earth-700 p-4 space-y-2">
              <div className="flex items-center gap-2 text-sm text-lsc-dark/80 dark:text-lsc-cream/80">
                <AlertTriangle className="h-4 w-4 text-status-warning-600 dark:text-status-warning-400 flex-shrink-0" />
                <span>
                  {engagementQuery.data.dormant_patrons} patron{engagementQuery.data.dormant_patrons !== 1 ? 's' : ''} haven't
                  visited in 180+ days
                </span>
              </div>
              <div className="flex items-center gap-2 text-sm text-lsc-dark/80 dark:text-lsc-cream/80">
                <Users className="h-4 w-4 text-status-success-600 dark:text-status-success-400 flex-shrink-0" />
                <span>
                  {engagementQuery.data.new_patrons} new patron{engagementQuery.data.new_patrons !== 1 ? 's' : ''} registered
                  in the last 60 days
                </span>
              </div>
            </div>
          )}
        </section>

        {/* ---------------------------------------------------------------- */}
        {/* Overdue Prediction */}
        {/* ---------------------------------------------------------------- */}
        <section>
          <SectionHeader>Overdue Forecast</SectionHeader>
          {circulationQuery.data && (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
              <StatCard
                title="Currently Overdue"
                value={circulationQuery.data.overdue_count}
                subtitle="Items past due date"
                icon={AlertTriangle}
                color={circulationQuery.data.overdue_count > 0 ? 'red' : 'green'}
              />
              <StatCard
                title="Active Checkouts"
                value={circulationQuery.data.active_checkouts}
                subtitle="Items currently out"
                icon={Clock}
                color="earth"
              />
              {overdueBuckets.map((bucket) => (
                <StatCard
                  key={bucket.label}
                  title={bucket.label}
                  value={bucket.count}
                  subtitle="Items approaching due date"
                  icon={Clock}
                  color={bucket.count > 10 ? 'amber' : 'earth'}
                />
              ))}
            </div>
          )}
          {overdueBuckets.length > 0 && (
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
              Projected upcoming returns: {overdueBuckets[0]?.count ?? 0} items due within 3 days,{' '}
              {overdueBuckets[1]?.count ?? 0} items due in 4-7 days,{' '}
              {overdueBuckets[2]?.count ?? 0} items due in 8-14 days.
            </p>
          )}
        </section>
      </div>
    </AdminShell>
  )
}

export default PredictiveAnalyticsPage
