/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect } from "react"
import { Loader2, PieChart, BarChart3, BookOpen } from "lucide-react"
import toast from "react-hot-toast"
import {
  BarChart,
  Bar,
  PieChart as RechartsPieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts"
import { useChartColors, useChartTooltipStyle, getColor } from "../../hooks/useChartColors"
import { AccessibleChartWrapper } from "../charts/AccessibleChartWrapper"
import {
  getAnalyticsCollectionUsage,
  type CollectionUsageData,
} from "../../api/analytics-api"
import { useTranslation } from "@/i18n"
import { formatNumber } from "./analytics-utils"
import type { DateRange } from "./analytics-types"

interface Props {
  token: string
  dateRange: DateRange
}

export function CollectionTab({ token, dateRange }: Props) {
  const { t } = useTranslation()
  const [data, setData] = useState<CollectionUsageData | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const chartColors = useChartColors()
  const tooltipStyle = useChartTooltipStyle()

  useEffect(() => {
    async function fetchData() {
      setIsLoading(true)
      try {
        const result = await getAnalyticsCollectionUsage(token, dateRange.startDate, dateRange.endDate)
        setData(result)
      } catch (_error: unknown) {
        toast.error(t('staffAnalytics.failedToLoadCollectionAnalytics'))
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
        No collection data available
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm border border-lsc-border dark:border-earth-700">
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Total Titles</p>
          <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">
            {formatNumber(data.totalTitles)}
          </p>
        </div>
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm border border-lsc-border dark:border-earth-700">
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Total Copies</p>
          <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">
            {formatNumber(data.totalCopies)}
          </p>
        </div>
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm border border-lsc-border dark:border-earth-700">
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Turnover Rate</p>
          <p className="text-2xl font-bold text-lsc-rose">
            {data.turnoverRate.toFixed(2)}
          </p>
        </div>
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm border border-lsc-border dark:border-earth-700">
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Items Never Circulated</p>
          <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">
            {formatNumber(data.neverCirculated)}
          </p>
        </div>
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        {/* Usage by Category */}
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm border border-lsc-border dark:border-earth-700">
          <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
            <PieChart className="w-5 h-5 text-lsc-rose" aria-hidden="true" />
            Usage by Category
          </h3>
          {(() => {
            const total = data.byCategory.reduce((sum, c) => sum + c.checkouts, 0);
            const tableData = data.byCategory.map(c => ({
              category: c.category,
              checkouts: c.checkouts,
              percentage: total > 0 ? ((c.checkouts / total) * 100).toFixed(1) : "0.0",
            }));
            return (
              <AccessibleChartWrapper
                title="Usage by Category"
                description="Pie chart showing checkout distribution across collection categories."
                data={tableData}
                columns={[
                  { key: "category", label: "Category" },
                  { key: "checkouts", label: "Checkouts" },
                  { key: "percentage", label: "Percentage (%)" },
                ]}
              >
                <ResponsiveContainer width="100%" height={300}>
                  <RechartsPieChart>
                    <Pie
                      data={data.byCategory}
                      cx="50%"
                      cy="50%"
                      outerRadius={100}
                      dataKey="checkouts"
                      nameKey="category"
                      // Percentage labels provide a non-color channel for differentiation (WCAG 1.4.1)

                      label={((entry: { category: string; percent: number }) =>
                        `${entry.category} ${(entry.percent * 100).toFixed(0)}%`) as any}
                    >
                      {data.byCategory.map((_, index) => (
                        <Cell key={`cell-${index}`} fill={getColor(chartColors.primary, index)} />
                      ))}
                    </Pie>
                    <Tooltip contentStyle={tooltipStyle} />
                  </RechartsPieChart>
                </ResponsiveContainer>
              </AccessibleChartWrapper>
            );
          })()}
        </div>

        {/* Turnover by Category */}
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm border border-lsc-border dark:border-earth-700">
          <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-lsc-rose" aria-hidden="true" />
            Turnover Rate by Category
          </h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={data.byCategory} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke={chartColors.grid} />
              <XAxis type="number" stroke={chartColors.axis} fontSize={12} />
              <YAxis type="category" dataKey="category" stroke={chartColors.axis} fontSize={12} width={100} />
              <Tooltip contentStyle={tooltipStyle} />
              <Bar dataKey="turnoverRate" name="Turnover Rate" fill={chartColors.primary[0]} radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Category Details Table */}
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm border border-lsc-border dark:border-earth-700">
        <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
          <BookOpen className="w-5 h-5 text-lsc-rose" aria-hidden="true" />
          Collection Details by Category
        </h3>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-lsc-border dark:border-earth-700">
                <th className="text-left p-3 text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
                  Category
                </th>
                <th className="text-right p-3 text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
                  Titles
                </th>
                <th className="text-right p-3 text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
                  Copies
                </th>
                <th className="text-right p-3 text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
                  Checkouts
                </th>
                <th className="text-right p-3 text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
                  Turnover
                </th>
                <th className="text-right p-3 text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
                  % of Collection
                </th>
              </tr>
            </thead>
            <tbody>
              {data.byCategory.map((category, idx) => (
                <tr
                  key={category.category}
                  className={idx % 2 === 0 ? "bg-lsc-cream/30 dark:bg-earth-700/30" : ""}
                >
                  <td className="p-3 text-lsc-dark dark:text-lsc-cream font-medium">
                    {category.category}
                  </td>
                  <td className="p-3 text-right text-lsc-dark/70 dark:text-lsc-cream/70">
                    {formatNumber(category.titles)}
                  </td>
                  <td className="p-3 text-right text-lsc-dark/70 dark:text-lsc-cream/70">
                    {formatNumber(category.copies)}
                  </td>
                  <td className="p-3 text-right text-lsc-dark/70 dark:text-lsc-cream/70">
                    {formatNumber(category.checkouts)}
                  </td>
                  <td className="p-3 text-right font-medium text-lsc-rose">
                    {category.turnoverRate.toFixed(2)}
                  </td>
                  <td className="p-3 text-right text-lsc-dark/70 dark:text-lsc-cream/70">
                    {category.percentOfCollection.toFixed(1)}%
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
