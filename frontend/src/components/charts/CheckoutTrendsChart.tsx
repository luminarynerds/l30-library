/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from "recharts"
import { useTranslation, getCurrentLocale } from '@/i18n'

interface TrendDataPoint {
  date: string
  checkouts: number
  checkouts_previous?: number
  checkouts_previous_year?: number
}

type Granularity = "hourly" | "daily" | "weekly" | "monthly"

interface CheckoutTrendsChartProps {
  data: TrendDataPoint[]
  formatDate: (dateStr: string) => string
  onDataPointClick?: (date: string) => void
  comparisonMode?: "none" | "previous_period" | "previous_year"
  granularity?: Granularity
}

function formatTickByGranularity(value: string, granularity: Granularity): string {
  const d = new Date(value)
  if (isNaN(d.getTime())) return value
  switch (granularity) {
    case "hourly":
      return d.toLocaleString(getCurrentLocale(), { month: "short", day: "numeric", hour: "numeric" })
    case "weekly":
      return `Week of ${d.toLocaleDateString(getCurrentLocale(), { month: "short", day: "numeric" })}`
    case "monthly":
      return d.toLocaleDateString(getCurrentLocale(), { month: "short", year: "numeric" })
    default:
      return d.toLocaleDateString(getCurrentLocale(), { month: "short", day: "numeric" })
  }
}

// Accessible data table component for screen readers
function AccessibleDataTable({
  data,
  formatDate,
  comparisonMode
}: {
  data: TrendDataPoint[]
  formatDate: (dateStr: string) => string
  comparisonMode: "none" | "previous_period" | "previous_year"
}) {
  const { t } = useTranslation()
  if (data.length === 0) return null

  return (
    <table className="sr-only" aria-label={t('components.charts.checkoutTrendsChart.checkoutTrendsDataTable')}>
      <caption>{t('components.charts.checkoutTrendsChart.checkoutTrendsDataForThe')}</caption>
      <thead>
        <tr>
          <th scope="col">Date</th>
          <th scope="col">Current Period Checkouts</th>
          {comparisonMode === "previous_period" && <th scope="col">Previous Period Checkouts</th>}
          {comparisonMode === "previous_year" && <th scope="col">Previous Year Checkouts</th>}
        </tr>
      </thead>
      <tbody>
        {data.map((point) => (
          <tr key={point.date}>
            <td>{formatDate(point.date)}</td>
            <td>{point.checkouts}</td>
            {comparisonMode === "previous_period" && <td>{point.checkouts_previous ?? "N/A"}</td>}
            {comparisonMode === "previous_year" && <td>{point.checkouts_previous_year ?? "N/A"}</td>}
          </tr>
        ))}
      </tbody>
    </table>
  )
}

function CustomTooltip({ active, payload, label, formatDate, showClickHint }: {
  active?: boolean
  payload?: Array<{ value: number; name: string; color: string }>
  label?: string
  formatDate: (dateStr: string) => string
  showClickHint: boolean
}) {
  if (active && payload && payload.length) {
    return (
      <div className="bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-lg p-3 shadow-lg">
        <p className="font-medium text-lsc-dark dark:text-lsc-cream mb-2">
          {label ? formatDate(label) : ""}
        </p>
        {payload.map((entry, index) => (
          <div key={index} className="flex items-center gap-2 text-sm">
            <div
              className="w-3 h-3 rounded-full"
              style={{ backgroundColor: entry.color }}
            />
            <span className="text-lsc-dark/70 dark:text-lsc-cream/70">{entry.name}:</span>
            <span className="font-semibold text-lsc-dark dark:text-lsc-cream">{entry.value}</span>
          </div>
        ))}
        {showClickHint && (
          <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-2 italic">
            Click for details
          </p>
        )}
      </div>
    )
  }
  return null
}

export default function CheckoutTrendsChart({
  data,
  formatDate,
  onDataPointClick,
  comparisonMode = "none",
  granularity = "daily"
}: CheckoutTrendsChartProps): React.ReactElement {
  const { t } = useTranslation()
  const handleClick = (data: unknown) => {
    if (onDataPointClick && data && typeof data === 'object' && 'activePayload' in data) {
      const payload = data.activePayload as Array<{ payload: { date: string } }>
      if (payload && payload[0] && payload[0].payload) {
        onDataPointClick(payload[0].payload.date)
      }
    }
  }

  // Generate summary for screen readers
  const getSummary = () => {
    if (data.length === 0) return "No checkout data available for the selected period."
    const total = data.reduce((sum, d) => sum + d.checkouts, 0)
    const avg = Math.round(total / data.length)
    const max = Math.max(...data.map(d => d.checkouts))
    const min = Math.min(...data.map(d => d.checkouts))
    return `Checkout trends showing ${data.length} data points. Total: ${total.toLocaleString()} checkouts. Average: ${avg.toLocaleString()} per day. Range: ${min.toLocaleString()} to ${max.toLocaleString()}.`
  }

  if (data.length === 0) {
    return (
      <div
        className="flex items-center justify-center h-[300px] text-lsc-dark/70 dark:text-lsc-cream/70"
        role="img"
        aria-label={t('components.charts.checkoutTrendsChart.noCheckoutTrendsDataAvailable')}
      >
        No checkout data available for the selected period
      </div>
    )
  }

  return (
    <figure
      role="figure"
      aria-label={t('aria.charts.checkoutTrendsChart')}
      className="relative"
    >
      {/* Screen reader accessible summary */}
      <figcaption className="sr-only">
        {getSummary()}
      </figcaption>

      {/* Accessible data table for screen readers */}
      <AccessibleDataTable data={data} formatDate={formatDate} comparisonMode={comparisonMode} />

      {/* Visual chart */}
      <div aria-hidden="true">
        <ResponsiveContainer width="100%" height={300}>
          <LineChart
            data={data}
            onClick={handleClick}
            style={{ cursor: onDataPointClick ? 'pointer' : 'default' }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#F0EDE8" />
            <XAxis
              dataKey="date"
              tickFormatter={(v) => formatTickByGranularity(v, granularity)}
              stroke="#8B7B6A"
              fontSize={12}
              aria-label={t('aria.charts.dateAxis')}
            />
            <YAxis stroke="#8B7B6A" fontSize={12} aria-label={t('aria.charts.checkoutCountAxis')} />
            <Tooltip content={<CustomTooltip formatDate={(v: string) => formatTickByGranularity(v, granularity)} showClickHint={!!onDataPointClick} />} />
            {comparisonMode !== "none" && <Legend />}

            {/* Current period data - solid line with circle markers */}
            <Line
              type="monotone"
              dataKey="checkouts"
              name="Current Period"
              stroke="#4A6B5D"
              strokeWidth={2}
              dot={{ fill: "#4A6B5D", strokeWidth: 2, r: 4 }}
              activeDot={{ r: 6, cursor: onDataPointClick ? 'pointer' : 'default' }}
            />

            {/* Previous period comparison - dashed line with diamond markers */}
            {comparisonMode === "previous_period" && (
              <Line
                type="monotone"
                dataKey="checkouts_previous"
                name="Previous Period"
                stroke="#D97706"
                strokeWidth={2}
                strokeDasharray="5 5"
                dot={{ fill: "#D97706", strokeWidth: 2, r: 3 }}
              />
            )}

            {/* Year-over-year comparison - dashed line with square markers */}
            {comparisonMode === "previous_year" && (
              <Line
                type="monotone"
                dataKey="checkouts_previous_year"
                name="Previous Year"
                stroke="#7C3AED"
                strokeWidth={2}
                strokeDasharray="5 5"
                dot={{ fill: "#7C3AED", strokeWidth: 2, r: 3 }}
              />
            )}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </figure>
  )
}
