/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect } from 'react'
import { TrendingUp } from 'lucide-react'
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'
import type { TimelineBucket } from '@/hooks/useBanTrackerTimeline'

const SERIES: { key: keyof Omit<TimelineBucket, 'month'>; label: string; color: string }[] = [
  { key: 'banned', label: 'Banned', color: '#dc2626' },
  { key: 'restricted', label: 'Restricted', color: '#ea580c' },
  { key: 'challenged', label: 'Challenged', color: '#ca8a04' },
  { key: 'pending', label: 'Pending', color: '#78716c' },
]

function useIsDark(): boolean {
  const [isDark, setIsDark] = useState(
    typeof document !== 'undefined' &&
      document.documentElement.classList.contains('dark')
  )
  useEffect(() => {
    if (typeof document === 'undefined') return
    const target = document.documentElement
    const obs = new MutationObserver(() => {
      setIsDark(target.classList.contains('dark'))
    })
    obs.observe(target, { attributes: true, attributeFilter: ['class'] })
    return () => obs.disconnect()
  }, [])
  return isDark
}

function formatMonthLabel(ym: string): string {
  // ym is "YYYY-MM"
  const parts = ym.split('-')
  const y = parts[0]
  const m = parts[1]
  if (!y || !m) return ym
  const monthIdx = parseInt(m, 10) - 1
  if (Number.isNaN(monthIdx) || monthIdx < 0 || monthIdx > 11) return ym
  const monthName = new Date(2000, monthIdx, 1).toLocaleString(undefined, { month: 'short' })
  return `${monthName} ${y}`
}

export function TimelineChart({
  buckets,
}: {
  buckets: TimelineBucket[]
}): React.ReactElement | null {
  const isDark = useIsDark()

  if (buckets.length <= 1) return null

  const gridStroke = isDark ? '#3D3B38' : '#ECEAE8'
  const axisStroke = isDark ? '#C5C2BD' : '#6B6762'
  const tooltipBg = isDark ? '#2F2E2C' : '#FAFAF8'
  const tooltipBorder = isDark ? '#3D3B38' : '#EDECEB'
  const tooltipText = isDark ? '#F8F7F6' : '#2D2D2A'

  const totals = SERIES.map((s) => ({
    label: s.label,
    total: buckets.reduce((sum, b) => sum + (b[s.key] ?? 0), 0),
  }))
  const grandTotal = totals.reduce((sum, t) => sum + t.total, 0)
  const first = buckets[0]
  const last = buckets[buckets.length - 1]
  const rangeLabel = first && last
    ? `${formatMonthLabel(first.month)} to ${formatMonthLabel(last.month)}`
    : ''
  const ariaLabel = `Stacked area chart of monthly ban reports from ${rangeLabel}. ${grandTotal} total reports across ${buckets.length} months.`

  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-6">
      <div className="flex items-center gap-2 mb-4">
        <TrendingUp className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" aria-hidden="true" />
        <h3 className="font-serif text-lg font-bold text-lsc-dark dark:text-lsc-cream">
          Bans Over Time
        </h3>
      </div>

      <div
        role="img"
        aria-label={ariaLabel}
        className="w-full h-72"
      >
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={buckets} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
            <XAxis
              dataKey="month"
              tickFormatter={formatMonthLabel}
              stroke={axisStroke}
              tick={{ fill: axisStroke, fontSize: 12 }}
            />
            <YAxis
              allowDecimals={false}
              stroke={axisStroke}
              tick={{ fill: axisStroke, fontSize: 12 }}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: tooltipBg,
                border: `1px solid ${tooltipBorder}`,
                borderRadius: '8px',
                color: tooltipText,
              }}
              labelFormatter={(v) => formatMonthLabel(String(v))}
              cursor={{ stroke: gridStroke }}
            />
            <Legend wrapperStyle={{ color: axisStroke, fontSize: 12 }} />
            {SERIES.map((s) => (
              <Area
                key={s.key}
                type="monotone"
                dataKey={s.key}
                name={s.label}
                stackId="bans"
                stroke={s.color}
                fill={s.color}
                fillOpacity={0.7}
              />
            ))}
          </AreaChart>
        </ResponsiveContainer>
      </div>

      <table className="sr-only">
        <caption>Monthly ban reports by type</caption>
        <thead>
          <tr>
            <th scope="col">Month</th>
            {SERIES.map((s) => (
              <th key={s.key} scope="col">{s.label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {buckets.map((b) => (
            <tr key={b.month}>
              <th scope="row">{formatMonthLabel(b.month)}</th>
              {SERIES.map((s) => (
                <td key={s.key}>{b[s.key]}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
