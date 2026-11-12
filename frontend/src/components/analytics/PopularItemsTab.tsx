/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect } from "react"
import { Loader2, TrendingUp, PieChart, ArrowUpRight } from "lucide-react"
import toast from "react-hot-toast"
import {
  PieChart as RechartsPieChart,
  Pie,
  Cell,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts"
import {
  AccessibleChartWrapper,
} from "../charts/AccessibleChartWrapper"
import { useChartColors, useChartTooltipStyle, getColor } from "../../hooks/useChartColors"
import {
  getAnalyticsPopularItems,
  type PopularItemData,
} from "../../api/analytics-api"
import { useTranslation } from "@/i18n"
import { formatNumber } from "./analytics-utils"
import type { DateRange } from "./analytics-types"

interface Props {
  token: string
  dateRange: DateRange
}

export function PopularItemsTab({ token, dateRange }: Props) {
  const { t } = useTranslation()
  const [data, setData] = useState<PopularItemData | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [viewMode, setViewMode] = useState<"checkouts" | "holds">("checkouts")
  const chartColors = useChartColors()
  const tooltipStyle = useChartTooltipStyle()

  useEffect(() => {
    async function fetchData() {
      setIsLoading(true)
      try {
        const result = await getAnalyticsPopularItems(token, dateRange.startDate, dateRange.endDate)
        setData(result)
      } catch (_error: unknown) {
        toast.error(t('staffAnalytics.failedToLoadPopularItems'))
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
        No popular items data available
      </div>
    )
  }

  const currentItems = viewMode === "checkouts" ? data.topCheckouts : data.topHolds

  return (
    <div className="space-y-6">
      {/* View Toggle */}
      <div className="flex items-center gap-2">
        <button
          onClick={() => setViewMode("checkouts")}
          className={`px-4 py-2 rounded-lg font-medium transition-colors ${
            viewMode === "checkouts"
              ? "bg-lsc-rose text-white"
              : "bg-lsc-cream dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream hover:bg-lsc-rose/20"
          }`}
        >
          Most Checked Out
        </button>
        <button
          onClick={() => setViewMode("holds")}
          className={`px-4 py-2 rounded-lg font-medium transition-colors ${
            viewMode === "holds"
              ? "bg-lsc-rose text-white"
              : "bg-lsc-cream dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream hover:bg-lsc-rose/20"
          }`}
        >
          Most Requested (Holds)
        </button>
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        {/* Top Items List */}
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm border border-lsc-border dark:border-earth-700">
          <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-lsc-rose" aria-hidden="true" />
            Top 10 {viewMode === "checkouts" ? "Checkouts" : "Holds"}
          </h3>
          <div className="space-y-3">
            {currentItems.slice(0, 10).map((item, idx) => (
              <div key={item.itemId} className="flex items-center gap-3">
                <span className="w-7 h-7 bg-lsc-cream dark:bg-earth-700 rounded-full flex items-center justify-center text-sm font-semibold text-lsc-rose">
                  {idx + 1}
                </span>
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-lsc-dark dark:text-lsc-cream truncate" title={item.title}>
                    {item.title}
                  </p>
                  <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 truncate" title={item.author}>
                    {item.author}
                  </p>
                </div>
                <span className="text-sm font-semibold text-lsc-rose">
                  {formatNumber(item.count)}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Category Breakdown */}
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm border border-lsc-border dark:border-earth-700">
          <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
            <PieChart className="w-5 h-5 text-lsc-rose" aria-hidden="true" />
            By Category
          </h3>
          <AccessibleChartWrapper
            title="Items by Category"
            description="Distribution of popular items across categories"
            data={data.byCategory as unknown as Record<string, unknown>[]}
            columns={[
              { key: "category", label: "Category" },
              { key: "count", label: "Count" },
            ]}
            emptyMessage="No category data available"
          >
            <ResponsiveContainer width="100%" height={280}>
              <RechartsPieChart>
                <Pie
                  data={data.byCategory}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={100}
                  dataKey="count"
                  nameKey="category"
                  // eslint-disable-next-line @typescript-eslint/no-explicit-any
                  label={((entry: { category: string }) => entry.category) as any}
                >
                  {data.byCategory.map((_, index) => (
                    <Cell key={`cell-${index}`} fill={getColor(chartColors.primary, index)} />
                  ))}
                </Pie>
                <Tooltip contentStyle={tooltipStyle} />
                <Legend />
              </RechartsPieChart>
            </ResponsiveContainer>
          </AccessibleChartWrapper>
        </div>
      </div>

      {/* Trending Items */}
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm border border-lsc-border dark:border-earth-700">
        <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
          <TrendingUp className="w-5 h-5 text-lsc-rose" aria-hidden="true" />
          Trending (Biggest Growth)
        </h3>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {data.trending.slice(0, 6).map((item) => (
            <div
              key={item.itemId}
              className="p-4 bg-lsc-cream/50 dark:bg-earth-700/50 rounded-xl"
            >
              <p className="font-medium text-lsc-dark dark:text-lsc-cream truncate mb-1" title={item.title}>
                {item.title}
              </p>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 truncate mb-2" title={item.author}>
                {item.author}
              </p>
              <div className="flex items-center justify-between">
                <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                  {formatNumber(item.count)} checkouts
                </span>
                <span className="text-sm font-semibold text-status-success-600 dark:text-status-success-400 flex items-center">
                  <ArrowUpRight className="w-4 h-4" aria-hidden="true" />
                  {item.growthPercent.toFixed(0)}%
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
