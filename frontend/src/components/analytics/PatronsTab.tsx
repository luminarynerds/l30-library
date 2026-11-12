/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect } from "react"
import { Loader2, Users, Activity, AlertTriangle, TrendingUp, BarChart3 } from "lucide-react"
import toast from "react-hot-toast"
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  AreaChart,
  Area,
} from "recharts"
import { useChartColors, useChartTooltipStyle } from "../../hooks/useChartColors"
import {
  getAnalyticsPatronStats,
  type PatronStatsData,
} from "../../api/analytics-api"
import { useTranslation } from "@/i18n"
import { ChangeIndicator, formatNumber, formatDate, formatShortDate } from "./analytics-utils"
import type { DateRange } from "./analytics-types"

interface Props {
  token: string
  dateRange: DateRange
}

export function PatronsTab({ token, dateRange }: Props) {
  const { t } = useTranslation()
  const [data, setData] = useState<PatronStatsData | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const chartColors = useChartColors()
  const tooltipStyle = useChartTooltipStyle()

  useEffect(() => {
    async function fetchData() {
      setIsLoading(true)
      try {
        const result = await getAnalyticsPatronStats(token, dateRange.startDate, dateRange.endDate)
        setData(result)
      } catch (_error: unknown) {
        toast.error(t('staffAnalytics.failedToLoadPatronAnalytics'))
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
        No patron data available
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
              <Users className="w-5 h-5 text-lsc-rose" aria-hidden="true" />
            </div>
            <div>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Total Patrons</p>
              <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">
                {formatNumber(data.totalPatrons)}
              </p>
            </div>
          </div>
        </div>

        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm border border-lsc-border dark:border-earth-700">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 bg-status-success-100 dark:bg-status-success-900/30 rounded-xl flex items-center justify-center">
              <Users className="w-5 h-5 text-status-success-600 dark:text-status-success-400" aria-hidden="true" />
            </div>
            <div>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">New Registrations</p>
              <p className="text-2xl font-bold text-status-success-600 dark:text-status-success-400">
                {formatNumber(data.newRegistrations)}
              </p>
            </div>
          </div>
          <ChangeIndicator value={data.registrationChange} />
        </div>

        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm border border-lsc-border dark:border-earth-700">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 bg-lsc-cream dark:bg-lsc-brown/30 rounded-xl flex items-center justify-center">
              <Activity className="w-5 h-5 text-lsc-rose" aria-hidden="true" />
            </div>
            <div>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Active (30 days)</p>
              <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">
                {formatNumber(data.activePatrons)}
              </p>
            </div>
          </div>
          <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
            {(data.totalPatrons > 0 ? (data.activePatrons / data.totalPatrons) * 100 : 0).toFixed(1)}% engagement
          </span>
        </div>

        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm border border-lsc-border dark:border-earth-700">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 bg-status-danger-100 dark:bg-status-danger-900/30 rounded-xl flex items-center justify-center">
              <AlertTriangle className="w-5 h-5 text-status-danger-600 dark:text-status-danger-400" aria-hidden="true" />
            </div>
            <div>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Blocked</p>
              <p className="text-2xl font-bold text-status-danger-600 dark:text-status-danger-400">
                {formatNumber(data.blockedPatrons)}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Registration Trends */}
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm border border-lsc-border dark:border-earth-700">
        <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
          <TrendingUp className="w-5 h-5 text-lsc-rose" aria-hidden="true" />
          Registration Trends
        </h3>
        <ResponsiveContainer width="100%" height={300}>
          <AreaChart data={data.registrationTrends}>
            <CartesianGrid strokeDasharray="3 3" stroke={chartColors.grid} />
            <XAxis dataKey="date" tickFormatter={formatDate} stroke={chartColors.axis} fontSize={12} />
            <YAxis stroke={chartColors.axis} fontSize={12} />
            <Tooltip
              labelFormatter={(value) => formatShortDate(value as string)}
              contentStyle={tooltipStyle}
            />
            <Area
              type="monotone"
              dataKey="registrations"
              name="New Registrations"
              stroke={chartColors.primary[0]}
              fill={chartColors.primary[0]}
              fillOpacity={0.3}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        {/* Activity Distribution */}
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm border border-lsc-border dark:border-earth-700">
          <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-lsc-rose" aria-hidden="true" />
            Patron Activity Distribution
          </h3>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={data.activityDistribution}>
              <CartesianGrid strokeDasharray="3 3" stroke={chartColors.grid} />
              <XAxis dataKey="range" stroke={chartColors.axis} fontSize={12} />
              <YAxis stroke={chartColors.axis} fontSize={12} />
              <Tooltip contentStyle={tooltipStyle} />
              <Bar dataKey="count" name="Patrons" fill={chartColors.primary[0]} radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Top Active Patrons */}
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm border border-lsc-border dark:border-earth-700">
          <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
            <Users className="w-5 h-5 text-lsc-rose" aria-hidden="true" />
            Top Active Patrons
          </h3>
          <div className="space-y-3">
            {data.topActivePatrons.slice(0, 10).map((patron, idx) => (
              <div key={patron.patronId} className="flex items-center gap-3">
                <span className="w-7 h-7 bg-lsc-cream dark:bg-earth-700 rounded-full flex items-center justify-center text-sm font-semibold text-lsc-rose">
                  {idx + 1}
                </span>
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-lsc-dark dark:text-lsc-cream truncate" title={patron.name}>
                    {patron.name}
                  </p>
                </div>
                <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                  {formatNumber(patron.checkoutCount)} checkouts
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
