/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect } from "react"
import { Loader2, DollarSign, CheckCircle, Users, TrendingUp, Clock, CreditCard, FileText } from "lucide-react"
import toast from "react-hot-toast"
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  PieChart as RechartsPieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts"
import { useChartColors, useChartTooltipStyle, getColor } from "../../hooks/useChartColors"
import {
  getAnalyticsFinesSummary,
  getAnalyticsFineAging,
  getAnalyticsPaymentMethods,
  getAnalyticsWaivedFines,
  type FinesSummaryData,
  type FineAgingData,
  type PaymentMethodData,
  type WaivedFineData,
} from "../../api/analytics-api"
import { useTranslation } from "@/i18n"
import { ChangeIndicator, formatCurrency, formatNumber, formatDate, formatShortDate } from "./analytics-utils"
import type { DateRange } from "./analytics-types"

interface Props {
  token: string
  dateRange: DateRange
}

export function FinesTab({ token, dateRange }: Props) {
  const { t } = useTranslation()
  const [summary, setSummary] = useState<FinesSummaryData | null>(null)
  const [aging, setAging] = useState<FineAgingData | null>(null)
  const [payments, setPayments] = useState<PaymentMethodData | null>(null)
  const [waivers, setWaivers] = useState<WaivedFineData | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const chartColors = useChartColors()
  const tooltipStyle = useChartTooltipStyle()

  useEffect(() => {
    async function fetchData() {
      setIsLoading(true)
      try {
        const [summaryData, agingData, paymentsData, waiversData] = await Promise.all([
          getAnalyticsFinesSummary(token, dateRange.startDate, dateRange.endDate),
          getAnalyticsFineAging(token),
          getAnalyticsPaymentMethods(token, dateRange.startDate, dateRange.endDate),
          getAnalyticsWaivedFines(token, dateRange.startDate, dateRange.endDate),
        ])
        setSummary(summaryData)
        setAging(agingData)
        setPayments(paymentsData)
        setWaivers(waiversData)
      } catch (_error: unknown) {
        toast.error(t('staffAnalytics.failedToLoadFineAnalytics'))
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

  if (!summary) {
    return (
      <div className="text-center py-12 text-lsc-dark/70 dark:text-lsc-cream/70">
        No fine data available
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm border border-lsc-border dark:border-earth-700">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 bg-status-danger-100 dark:bg-status-danger-900/30 rounded-xl flex items-center justify-center">
              <DollarSign className="w-5 h-5 text-status-danger-600 dark:text-status-danger-400" aria-hidden="true" />
            </div>
            <div>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Outstanding</p>
              <p className="text-2xl font-bold text-status-danger-600 dark:text-status-danger-400">
                {formatCurrency(summary.totalOutstanding)}
              </p>
            </div>
          </div>
        </div>

        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm border border-lsc-border dark:border-earth-700">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 bg-status-success-100 dark:bg-status-success-900/30 rounded-xl flex items-center justify-center">
              <DollarSign className="w-5 h-5 text-status-success-600 dark:text-status-success-400" aria-hidden="true" />
            </div>
            <div>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Collected</p>
              <p className="text-2xl font-bold text-status-success-600 dark:text-status-success-400">
                {formatCurrency(summary.totalCollected)}
              </p>
            </div>
          </div>
          <ChangeIndicator value={summary.collectionChange} />
        </div>

        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm border border-lsc-border dark:border-earth-700">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 bg-lsc-cream dark:bg-lsc-brown/30 rounded-xl flex items-center justify-center">
              <CheckCircle className="w-5 h-5 text-lsc-rose" aria-hidden="true" />
            </div>
            <div>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Waived</p>
              <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">
                {formatCurrency(summary.totalWaived)}
              </p>
            </div>
          </div>
        </div>

        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm border border-lsc-border dark:border-earth-700">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 bg-lsc-cream dark:bg-lsc-brown/30 rounded-xl flex items-center justify-center">
              <Users className="w-5 h-5 text-lsc-rose" aria-hidden="true" />
            </div>
            <div>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Patrons with Fines</p>
              <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">
                {formatNumber(summary.patronsWithFines)}
              </p>
            </div>
          </div>
        </div>
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        {/* Collection Trends */}
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm border border-lsc-border dark:border-earth-700">
          <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-lsc-rose" aria-hidden="true" />
            Collection Trends
          </h3>
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={summary.trends}>
              <CartesianGrid strokeDasharray="3 3" stroke={chartColors.grid} />
              <XAxis dataKey="date" tickFormatter={formatDate} stroke={chartColors.axis} fontSize={12} />
              <YAxis stroke={chartColors.axis} fontSize={12} tickFormatter={(v) => `$${v}`} />
              <Tooltip
                labelFormatter={(value) => formatShortDate(value as string)}
                formatter={(value) => formatCurrency(value as number)}
                contentStyle={tooltipStyle}
              />
              <Legend />
              <Line
                type="monotone"
                dataKey="collected"
                name="Collected"
                stroke={chartColors.primary[3]}
                strokeWidth={2}
              />
              <Line
                type="monotone"
                dataKey="assessed"
                name="New Fines"
                stroke={chartColors.primary[5]}
                strokeWidth={2}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Fine Aging */}
        {aging && (
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm border border-lsc-border dark:border-earth-700">
            <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
              <Clock className="w-5 h-5 text-lsc-rose" aria-hidden="true" />
              Outstanding by Age
            </h3>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={aging.brackets} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke={chartColors.grid} />
                <XAxis type="number" stroke={chartColors.axis} fontSize={12} tickFormatter={(v) => `$${v}`} />
                <YAxis type="category" dataKey="bracket" stroke={chartColors.axis} fontSize={12} width={80} />
                <Tooltip
                  formatter={(value) => formatCurrency(value as number)}
                  contentStyle={tooltipStyle}
                />
                <Bar dataKey="amount" fill={chartColors.primary[0]} radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        {/* Payment Methods */}
        {payments && (
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm border border-lsc-border dark:border-earth-700">
            <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
              <CreditCard className="w-5 h-5 text-lsc-rose" aria-hidden="true" />
              Payment Methods
            </h3>
            <ResponsiveContainer width="100%" height={250}>
              <RechartsPieChart>
                <Pie
                  data={payments.methods}
                  cx="50%"
                  cy="50%"
                  innerRadius={50}
                  outerRadius={90}
                  dataKey="amount"
                  nameKey="method"
                  // eslint-disable-next-line @typescript-eslint/no-explicit-any
                  label={((entry: { method: string; amount: number }) => `${entry.method}: ${formatCurrency(entry.amount)}`) as any}
                  labelLine={false}
                >
                  {payments.methods.map((_, index) => (
                    <Cell key={`cell-${index}`} fill={getColor(chartColors.primary, index)} />
                  ))}
                </Pie>
                <Tooltip
                  formatter={(value) => formatCurrency(value as number)}
                  contentStyle={tooltipStyle}
                />
              </RechartsPieChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* Waiver Summary */}
        {waivers && (
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm border border-lsc-border dark:border-earth-700">
            <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
              <FileText className="w-5 h-5 text-lsc-rose" aria-hidden="true" />
              Waived Fines Summary
            </h3>
            <div className="space-y-4">
              <div className="flex justify-between items-center p-3 bg-lsc-cream/50 dark:bg-earth-700/50 rounded-lg">
                <span className="text-lsc-dark/70 dark:text-lsc-cream/70">Total Waived</span>
                <span className="font-semibold text-lsc-dark dark:text-lsc-cream">
                  {formatCurrency(waivers.totalWaived)}
                </span>
              </div>
              <div className="flex justify-between items-center p-3 bg-lsc-cream/50 dark:bg-earth-700/50 rounded-lg">
                <span className="text-lsc-dark/70 dark:text-lsc-cream/70">Number of Waivers</span>
                <span className="font-semibold text-lsc-dark dark:text-lsc-cream">
                  {formatNumber(waivers.count)}
                </span>
              </div>
              <div className="flex justify-between items-center p-3 bg-lsc-cream/50 dark:bg-earth-700/50 rounded-lg">
                <span className="text-lsc-dark/70 dark:text-lsc-cream/70">Average Waiver</span>
                <span className="font-semibold text-lsc-dark dark:text-lsc-cream">
                  {formatCurrency(waivers.averageAmount)}
                </span>
              </div>
              <div className="mt-4">
                <p className="text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
                  Top Waiver Reasons
                </p>
                <div className="space-y-2">
                  {waivers.topReasons.slice(0, 5).map((reason, idx) => (
                    <div
                      key={idx}
                      className="flex justify-between text-sm text-lsc-dark/70 dark:text-lsc-cream/70"
                    >
                      <span className="truncate flex-1" title={reason.reason}>{reason.reason}</span>
                      <span className="ml-2 font-medium">{reason.count}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
