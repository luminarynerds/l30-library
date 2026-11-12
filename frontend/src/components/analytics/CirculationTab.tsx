/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect } from "react"
import { Loader2, BookOpen, CheckCircle, TrendingUp, AlertTriangle, Activity, BarChart3 } from "lucide-react"
import toast from "react-hot-toast"
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  AreaChart,
  Area,
} from "recharts"
import {
  AccessibleChartWrapper,
  formatDateValue,
} from "../charts/AccessibleChartWrapper"
import { useChartColors, useChartTooltipStyle } from "../../hooks/useChartColors"
import {
  getAnalyticsCirculationTrends,
  type CirculationTrendData,
} from "../../api/analytics-api"
import { useTranslation } from "@/i18n"
import { ChangeIndicator, formatNumber, formatDate, formatShortDate } from "./analytics-utils"
import type { DateRange } from "./analytics-types"

interface Props {
  token: string
  dateRange: DateRange
}

export function CirculationTab({ token, dateRange }: Props) {
  const { t } = useTranslation()
  const [data, setData] = useState<CirculationTrendData | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const chartColors = useChartColors()
  const tooltipStyle = useChartTooltipStyle()

  useEffect(() => {
    async function fetchData() {
      setIsLoading(true)
      try {
        const result = await getAnalyticsCirculationTrends(token, dateRange.startDate, dateRange.endDate)
        setData(result)
      } catch (_error: unknown) {
        toast.error(t('staffAnalytics.failedToLoadCirculationData'))
      } finally {
        setIsLoading(false)
      }
    }
    fetchData()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, dateRange])

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" />
      </div>
    )
  }

  if (!data) {
    return (
      <div className="text-center py-12 text-lsc-dark/70 dark:text-lsc-cream/70">
        No circulation data available
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm border border-lsc-border dark:border-earth-700">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 bg-lsc-cream dark:bg-lsc-brown/30 rounded-xl flex items-center justify-center">
              <BookOpen className="w-5 h-5 text-lsc-rose" aria-hidden="true" />
            </div>
            <div>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Total Checkouts</p>
              <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">
                {formatNumber(data.totalCheckouts)}
              </p>
            </div>
          </div>
          <ChangeIndicator value={data.checkoutChange} />
        </div>

        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm border border-lsc-border dark:border-earth-700">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 bg-lsc-cream dark:bg-lsc-brown/30 rounded-xl flex items-center justify-center">
              <CheckCircle className="w-5 h-5 text-lsc-rose" aria-hidden="true" />
            </div>
            <div>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Total Returns</p>
              <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">
                {formatNumber(data.totalReturns)}
              </p>
            </div>
          </div>
          <ChangeIndicator value={data.returnChange} />
        </div>

        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm border border-lsc-border dark:border-earth-700">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 bg-lsc-cream dark:bg-lsc-brown/30 rounded-xl flex items-center justify-center">
              <TrendingUp className="w-5 h-5 text-lsc-rose" aria-hidden="true" />
            </div>
            <div>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Daily Average</p>
              <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">
                {formatNumber(Math.round(data.dailyAverage))}
              </p>
            </div>
          </div>
        </div>

        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm border border-lsc-border dark:border-earth-700">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 bg-status-danger-100 dark:bg-status-danger-900/30 rounded-xl flex items-center justify-center">
              <AlertTriangle className="w-5 h-5 text-status-danger-600 dark:text-status-danger-400" aria-hidden="true" />
            </div>
            <div>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Overdue Items</p>
              <p className="text-2xl font-bold text-status-danger-600 dark:text-status-danger-400">
                {formatNumber(data.overdueCount)}
              </p>
            </div>
          </div>
          <ChangeIndicator value={data.overdueChange} inverse />
        </div>
      </div>

      {/* Trend Chart */}
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm border border-lsc-border dark:border-earth-700">
        <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
          <Activity className="w-5 h-5 text-lsc-rose" aria-hidden="true" />
          Circulation Trends
        </h3>
        <AccessibleChartWrapper
          title="Circulation Trends"
          description="Daily checkouts and returns over the selected period"
          data={data.trends as unknown as Record<string, unknown>[]}
          columns={[
            { key: "date", label: "Date", format: formatDateValue },
            { key: "checkouts", label: "Checkouts" },
            { key: "returns", label: "Returns" },
          ]}
          summary={`Circulation trends showing ${data.trends.length} days. Total checkouts: ${formatNumber(data.totalCheckouts)}. Total returns: ${formatNumber(data.totalReturns)}.`}
          emptyMessage="No circulation trend data available"
        >
          <ResponsiveContainer width="100%" height={350}>
            <AreaChart data={data.trends}>
              <CartesianGrid strokeDasharray="3 3" stroke={chartColors.grid} />
              <XAxis
                dataKey="date"
                tickFormatter={formatDate}
                stroke={chartColors.axis}
                fontSize={12}
              />
              <YAxis stroke={chartColors.axis} fontSize={12} />
              <Tooltip
                labelFormatter={(value) => formatShortDate(value as string)}
                contentStyle={tooltipStyle}
              />
              <Legend />
              <Area
                type="monotone"
                dataKey="checkouts"
                name="Checkouts"
                stroke={chartColors.primary[0]}
                fill={chartColors.primary[0]}
                fillOpacity={0.3}
              />
              <Area
                type="monotone"
                dataKey="returns"
                name="Returns"
                stroke={chartColors.primary[1]}
                fill={chartColors.primary[1]}
                fillOpacity={0.3}
              />
            </AreaChart>
          </ResponsiveContainer>
        </AccessibleChartWrapper>
      </div>

      {/* Day of Week Analysis */}
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm border border-lsc-border dark:border-earth-700">
        <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
          <BarChart3 className="w-5 h-5 text-lsc-rose" aria-hidden="true" />
          Activity by Day of Week
        </h3>
        <AccessibleChartWrapper
          title={t('staffAnalytics.activityByDayOfWeek')}
          description="Average checkouts and returns grouped by day of week"
          data={data.byDayOfWeek as unknown as Record<string, unknown>[]}
          columns={[
            { key: "day", label: "Day" },
            { key: "checkouts", label: "Checkouts" },
            { key: "returns", label: "Returns" },
          ]}
          emptyMessage="No day of week data available"
        >
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={data.byDayOfWeek}>
              <CartesianGrid strokeDasharray="3 3" stroke={chartColors.grid} />
              <XAxis dataKey="day" stroke={chartColors.axis} fontSize={12} />
              <YAxis stroke={chartColors.axis} fontSize={12} />
              <Tooltip contentStyle={tooltipStyle} />
              <Legend />
              <Bar dataKey="checkouts" name="Checkouts" fill={chartColors.primary[0]} radius={[4, 4, 0, 0]} />
              <Bar dataKey="returns" name="Returns" fill={chartColors.primary[1]} radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </AccessibleChartWrapper>
      </div>
    </div>
  )
}
