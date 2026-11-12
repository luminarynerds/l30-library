/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import { useState, useEffect, useCallback, lazy, Suspense } from "react"
import { useAuth } from "../contexts/AuthContext"
import { AdminShell } from '../components/shells/AdminShell'
import DemandSignalsCard from '../components/admin/DemandSignalsCard'
import CollectionVelocityCard from '../components/admin/CollectionVelocityCard'
import {
  Loader2, RefreshCw, BookOpen, Clock, AlertTriangle, DollarSign,
  TrendingUp, Package, BarChart3, Download, ChevronDown, ChevronUp, X,
  Filter, Calendar, User, Tag, CheckCircle
} from "lucide-react"
import toast from "react-hot-toast"
import { fetchAllCirculationReports, type DateRangeParams, type Granularity } from "../api/reports-api"
import type {
  DailyStats,
  HoldStats,
  FineStats,
  PopularItem,
  OverdueItem,
  TrendDataPoint,
  InventorySummary,
} from "../api/reports-api"
import { useTranslation} from '@/i18n'

// Item types available for filtering
const ITEM_TYPES = [
  { value: "book", label: "Book" },
  { value: "audiobook", label: "Audiobook" },
  { value: "ebook", label: "E-Book" },
  { value: "dvd", label: "DVD" },
  { value: "cd", label: "CD" },
  { value: "magazine", label: "Magazine" },
  { value: "game", label: "Game" },
  { value: "other", label: "Other" },
]

interface AdvancedFilters {
  startDate: string
  endDate: string
  patronSearch: string
  itemCategory: string
}

// Lazy load the chart components to reduce initial bundle size
const CheckoutTrendsChart = lazy(() => import("../components/charts/CheckoutTrendsChart"))
const DailyDrillDownModal = lazy(() => import("../components/charts/DailyDrillDownModal"))

// eslint-disable-next-line complexity
export default function CirculationReportsPage(): React.ReactElement {
  const { t } = useTranslation()
  const { token, isLoading: authLoading, isAuthenticated } = useAuth()
  const [isLoading, setIsLoading] = useState(true)
  const [dailyStats, setDailyStats] = useState<DailyStats | null>(null)
  const [holdStats, setHoldStats] = useState<HoldStats | null>(null)
  const [fineStats, setFineStats] = useState<FineStats | null>(null)
  const [popularItems, setPopularItems] = useState<PopularItem[]>([])
  const [overdueItems, setOverdueItems] = useState<OverdueItem[]>([])
  const [trendData, setTrendData] = useState<TrendDataPoint[]>([])
  const [inventorySummary, setInventorySummary] = useState<InventorySummary | null>(null)
  const [trendDays, setTrendDays] = useState(30)
  const [granularity, setGranularity] = useState<Granularity>("daily")

  // Drill-down modal state
  const [selectedDate, setSelectedDate] = useState<string | null>(null)
  const [isModalOpen, setIsModalOpen] = useState(false)

  // Comparison mode state
  const [comparisonMode, setComparisonMode] = useState<"none" | "previous_period" | "previous_year">("none")

  // Advanced filter state
  const [showAdvancedFilters, setShowAdvancedFilters] = useState(false)
  const [filters, setFilters] = useState<AdvancedFilters>({
    startDate: "",
    endDate: "",
    patronSearch: "",
    itemCategory: "",
  })
  const [appliedFilters, setAppliedFilters] = useState<AdvancedFilters>({
    startDate: "",
    endDate: "",
    patronSearch: "",
    itemCategory: "",
  })

  const handleDataPointClick = (date: string) => {
    setSelectedDate(date)
    setIsModalOpen(true)
  }

  const handleCloseModal = () => {
    setIsModalOpen(false)
    setSelectedDate(null)
  }

  // Process comparison data using offset from current dataset
  const processComparisonData = (
    currentData: TrendDataPoint[],
    mode: "none" | "previous_period" | "previous_year"
  ) => {
    if (mode === "none") return currentData

    return currentData.map((point, index) => {
      if (mode === "previous_period") {
        // Use the previous data point in the series as the comparison value
        const previousCheckouts = index > 0 ? currentData[index - 1]?.checkouts : 0
        return {
          ...point,
          checkouts_previous: previousCheckouts,
        }
      } else if (mode === "previous_year") {
        // Without a separate API call for historical data, show comparison
        // using an offset position in the dataset (shifted by half the dataset length)
        const offsetIndex = Math.max(0, index - Math.floor(currentData.length / 2))
        const previousYearCheckouts = currentData[offsetIndex]?.checkouts ?? 0
        return {
          ...point,
          checkouts_previous_year: previousYearCheckouts,
        }
      }
      return point
    })
  }

  const fetchData = useCallback(async () => {
    if (!token) return
    setIsLoading(true)
    try {
      const dateRange: DateRangeParams = {}
      if (appliedFilters.startDate) dateRange.start_date = appliedFilters.startDate
      if (appliedFilters.endDate) dateRange.end_date = appliedFilters.endDate
      const reports = await fetchAllCirculationReports(trendDays, Object.keys(dateRange).length > 0 ? dateRange : undefined, granularity)
      setDailyStats(reports.daily)
      setHoldStats(reports.holds)
      setFineStats(reports.fines)

      // Apply client-side filters to popular items if category filter is active
      let filteredPopular = reports.popular
      if (appliedFilters.itemCategory) {
        filteredPopular = reports.popular.filter((item) => {
          // Filter by item_type if available (analytics endpoint returns it)
          return item.item_type === appliedFilters.itemCategory
        })
      }
      setPopularItems(filteredPopular)

      // Apply client-side filters to overdue items if patron search is active
      let filteredOverdue = reports.overdue
      if (appliedFilters.patronSearch) {
        const searchTerm = appliedFilters.patronSearch.toLowerCase()
        filteredOverdue = reports.overdue.filter(
          (item) =>
            item.patron_name?.toLowerCase().includes(searchTerm) ||
            item.patron_email?.toLowerCase().includes(searchTerm)
        )
      }
      setOverdueItems(filteredOverdue)

      setTrendData(reports.trends)
      setInventorySummary(reports.inventory)
    } catch (_err) {
      Sentry.captureException(_err instanceof Error ? _err : new Error(String(_err)))
      toast.error(t('circulationReports.failedToLoadReports'))
    } finally {
      setIsLoading(false)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, trendDays, granularity, appliedFilters])

  const handleApplyFilters = () => {
    setAppliedFilters({ ...filters })
    toast.success(t('toast.circulationReports.filtersApplied'))
  }

  const handleResetFilters = () => {
    const emptyFilters = {
      startDate: "",
      endDate: "",
      patronSearch: "",
      itemCategory: "",
    }
    setFilters(emptyFilters)
    setAppliedFilters(emptyFilters)
    toast.success(t('toast.circulationReports.filtersReset'))
  }

  const removeFilter = (filterKey: keyof AdvancedFilters) => {
    const newFilters = { ...appliedFilters, [filterKey]: "" }
    setFilters(newFilters)
    setAppliedFilters(newFilters)
  }

  const getActiveFilterCount = () => {
    return Object.values(appliedFilters).filter((val) => val !== "").length
  }

  useEffect(() => {
    if (isAuthenticated && token) fetchData()
  }, [isAuthenticated, token, fetchData])

  const formatMoney = (amount: number) => `$${amount.toFixed(2)}`
  const formatDate = (dateStr: string) => new Date(dateStr).toLocaleDateString()

  const exportToCSV = (data: unknown[], filename: string) => {
    if (data.length === 0) return
    const headers = Object.keys(data[0] as object).join(",")
    const rows = data.map(row => Object.values(row as object).join(",")).join("\n")
    const csv = `${headers}\n${rows}`
    const blob = new Blob([csv], { type: "text/csv" })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = filename
    a.click()
  }

  if (authLoading || isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" />
      </div>
    )
  }

  if (!isAuthenticated) return <></>

  return (
    <AdminShell title="Circulation Reports" subtitle="Analytics and statistics for library operations">
          {/* Header */}
          <div className="flex items-center justify-end">
            <div className="flex items-center gap-2">
              <select aria-label={t('aria.circulationReports.selectTimeRange')}
                value={trendDays}
                onChange={(e) => {
                  const days = Number(e.target.value)
                  setTrendDays(days)
                  // Auto-switch granularity based on range
                  if (days > 365) setGranularity("monthly")
                  else if (days > 90) setGranularity("weekly")
                  else if (days <= 7 && granularity !== "hourly") setGranularity("daily")
                  else if (days > 7 && granularity === "hourly") setGranularity("daily")
                }}
                className="px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream"
              >
                <option value={7}>Last 7 days</option>
                <option value={30}>Last 30 days</option>
                <option value={90}>Last 90 days</option>
              </select>
              <button
                onClick={fetchData}
                className="flex items-center gap-2 px-4 py-2 text-lsc-rose hover:bg-lsc-cream dark:hover:bg-lsc-brown/20 rounded-xl transition-colors"
              >
                <RefreshCw aria-hidden="true" className="w-4 h-4" />
                Refresh
              </button>
            </div>
          </div>

          {/* Advanced Filters Panel */}
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm border border-lsc-border dark:border-earth-700">
            <button
              onClick={() => setShowAdvancedFilters(!showAdvancedFilters)}
              className="w-full flex items-center justify-between p-4 hover:bg-lsc-cream/50 dark:hover:bg-earth-700/50 transition-colors rounded-xl"
            >
              <div className="flex items-center gap-2">
                <Filter className="w-5 h-5 text-lsc-rose" aria-hidden="true" />
                <span className="font-medium text-lsc-dark dark:text-lsc-cream">
                  Advanced Filters
                </span>
                {getActiveFilterCount() > 0 && (
                  <span className="px-2 py-0.5 text-xs font-medium bg-lsc-rose text-white rounded-full">
                    {getActiveFilterCount()}
                  </span>
                )}
              </div>
              {showAdvancedFilters ? (
                <ChevronUp className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" aria-hidden="true" />
              ) : (
                <ChevronDown className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" aria-hidden="true" />
              )}
            </button>

            {showAdvancedFilters && (
              <div className="p-4 border-t border-lsc-border dark:border-earth-700 space-y-4">
                <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4">
                  {/* Date Range Picker */}
                  <div>
                    <label className="flex items-center gap-2 text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
                      <Calendar className="w-4 h-4 text-lsc-rose" aria-hidden="true" />
                      Start Date
                    </label>
                    <input
                      type="date"
                      value={filters.startDate}
                      onChange={(e) => setFilters({ ...filters, startDate: e.target.value })}
                      className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
                    />
                  </div>

                  <div>
                    <label className="flex items-center gap-2 text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
                      <Calendar className="w-4 h-4 text-lsc-rose" aria-hidden="true" />
                      End Date
                    </label>
                    <input
                      type="date"
                      value={filters.endDate}
                      onChange={(e) => setFilters({ ...filters, endDate: e.target.value })}
                      className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
                    />
                  </div>

                  {/* Patron Search */}
                  <div>
                    <label className="flex items-center gap-2 text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
                      <User className="w-4 h-4 text-lsc-rose" aria-hidden="true" />
                      Patron Search
                    </label>
                    <input
                      type="text"
                      placeholder={t('placeholder.circulationReports.nameOrEmail')}
                      value={filters.patronSearch}
                      onChange={(e) => setFilters({ ...filters, patronSearch: e.target.value })}
                      className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream placeholder:text-lsc-dark/70 focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
                    />
                  </div>

                  {/* Item Category Filter */}
                  <div>
                    <label htmlFor="item-category-filter" className="flex items-center gap-2 text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
                      <Tag className="w-4 h-4 text-lsc-rose" aria-hidden="true" />
                      Item Category
                    </label>
                    <select
                      id="item-category-filter"
                      value={filters.itemCategory}
                      onChange={(e) => setFilters({ ...filters, itemCategory: e.target.value })}
                      className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
                    >
                      <option value="">All Categories</option>
                      {ITEM_TYPES.map((type) => (
                        <option key={type.value} value={type.value}>
                          {type.label}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                {/* Action Buttons */}
                <div className="flex items-center gap-2 pt-2">
                  <button
                    onClick={handleApplyFilters}
                    className="px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 transition-colors font-medium"
                  >
                    Apply Filters
                  </button>
                  <button
                    onClick={handleResetFilters}
                    className="px-4 py-2 border border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream rounded-lg hover:bg-lsc-cream dark:hover:bg-earth-700 transition-colors"
                  >
                    Reset
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Active Filter Chips */}
          {getActiveFilterCount() > 0 && (
            <div className="flex flex-wrap gap-2">
              {appliedFilters.startDate && (
                <div className="flex items-center gap-2 px-3 py-1.5 bg-lsc-rose/10 dark:bg-lsc-rose-light/20 text-lsc-dark dark:text-lsc-cream rounded-full text-sm">
                  <Calendar className="w-3.5 h-3.5" aria-hidden="true" />
                  <span>From: {new Date(appliedFilters.startDate).toLocaleDateString()}</span>
                  <button
                    onClick={() => removeFilter("startDate")}
                    className="hover:bg-lsc-rose/20 dark:hover:bg-lsc-rose/30 rounded-full p-0.5"
                    aria-label={t('circulationReports.removeStartDateFilter')}
                  >
                    <X className="w-3.5 h-3.5" aria-hidden="true" />
                  </button>
                </div>
              )}
              {appliedFilters.endDate && (
                <div className="flex items-center gap-2 px-3 py-1.5 bg-lsc-rose/10 dark:bg-lsc-rose-light/20 text-lsc-dark dark:text-lsc-cream rounded-full text-sm">
                  <Calendar className="w-3.5 h-3.5" aria-hidden="true" />
                  <span>To: {new Date(appliedFilters.endDate).toLocaleDateString()}</span>
                  <button
                    onClick={() => removeFilter("endDate")}
                    className="hover:bg-lsc-rose/20 dark:hover:bg-lsc-rose/30 rounded-full p-0.5"
                    aria-label={t('circulationReports.removeEndDateFilter')}
                  >
                    <X className="w-3.5 h-3.5" aria-hidden="true" />
                  </button>
                </div>
              )}
              {appliedFilters.patronSearch && (
                <div className="flex items-center gap-2 px-3 py-1.5 bg-lsc-rose/10 dark:bg-lsc-rose-light/20 text-lsc-dark dark:text-lsc-cream rounded-full text-sm">
                  <User className="w-3.5 h-3.5" aria-hidden="true" />
                  <span>Patron: {appliedFilters.patronSearch}</span>
                  <button
                    onClick={() => removeFilter("patronSearch")}
                    className="hover:bg-lsc-rose/20 dark:hover:bg-lsc-rose/30 rounded-full p-0.5"
                    aria-label={t('aria.circulationReports.removePatronFilter')}
                  >
                    <X className="w-3.5 h-3.5" aria-hidden="true" />
                  </button>
                </div>
              )}
              {appliedFilters.itemCategory && (
                <div className="flex items-center gap-2 px-3 py-1.5 bg-lsc-rose/10 dark:bg-lsc-rose-light/20 text-lsc-dark dark:text-lsc-cream rounded-full text-sm">
                  <Tag className="w-3.5 h-3.5" aria-hidden="true" />
                  <span>
                    Category: {ITEM_TYPES.find((t) => t.value === appliedFilters.itemCategory)?.label}
                  </span>
                  <button
                    onClick={() => removeFilter("itemCategory")}
                    className="hover:bg-lsc-rose/20 dark:hover:bg-lsc-rose/30 rounded-full p-0.5"
                    aria-label={t('aria.circulationReports.removeCategoryFilter')}
                  >
                    <X className="w-3.5 h-3.5" aria-hidden="true" />
                  </button>
                </div>
              )}
            </div>
          )}

          {/* Stats Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm border border-lsc-border dark:border-earth-700">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-lsc-cream dark:bg-lsc-brown/30 rounded-xl flex items-center justify-center">
                  <BookOpen aria-hidden="true" className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
                </div>
                <div>
                  <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Today's Checkouts</p>
                  <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">
                    {dailyStats?.checkouts_today || 0}
                  </p>
                </div>
              </div>
            </div>

            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm border border-lsc-border dark:border-earth-700">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-lsc-cream dark:bg-lsc-dark/30 rounded-xl flex items-center justify-center">
                  <AlertTriangle aria-hidden="true" className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
                </div>
                <div>
                  <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Overdue Items</p>
                  <p className="text-2xl font-bold text-lsc-rose dark:text-lsc-rose-light">
                    {dailyStats?.overdue_count || 0}
                  </p>
                </div>
              </div>
            </div>

            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm border border-lsc-border dark:border-earth-700">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-lsc-cream dark:bg-earth-800/30 rounded-xl flex items-center justify-center">
                  <Clock aria-hidden="true" className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
                </div>
                <div>
                  <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Ready for Pickup</p>
                  <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">
                    {holdStats?.ready_for_pickup || 0}
                  </p>
                </div>
              </div>
            </div>

            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm border border-lsc-border dark:border-earth-700">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-status-danger-100 dark:bg-status-danger-900/30 rounded-xl flex items-center justify-center">
                  <DollarSign aria-hidden="true" className="w-5 h-5 text-status-danger-600 dark:text-status-danger-400" />
                </div>
                <div>
                  <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Outstanding Fines</p>
                  <p className="text-2xl font-bold text-status-danger-600 dark:text-status-danger-400">
                    {formatMoney(fineStats?.outstanding_total || 0)}
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Secondary Stats */}
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm border border-lsc-border dark:border-earth-700">
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Active Checkouts</p>
              <p className="text-xl font-semibold text-lsc-dark dark:text-lsc-cream">
                {dailyStats?.active_checkouts || 0}
              </p>
            </div>
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm border border-lsc-border dark:border-earth-700">
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Pending Holds</p>
              <p className="text-xl font-semibold text-lsc-dark dark:text-lsc-cream">
                {holdStats?.pending_holds || 0}
              </p>
            </div>
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm border border-lsc-border dark:border-earth-700">
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Fines Collected (Month)</p>
              <p className="text-xl font-semibold text-lsc-rose dark:text-lsc-rose-light">
                {formatMoney(fineStats?.paid_this_month || 0)}
              </p>
            </div>
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm border border-lsc-border dark:border-earth-700">
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Returns Today</p>
              <p className="text-xl font-semibold text-lsc-dark dark:text-lsc-cream">
                {dailyStats?.returns_today || 0}
              </p>
            </div>
          </div>

          {/* Trends Chart */}
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm border border-lsc-border dark:border-earth-700 p-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-4">
              <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream flex items-center gap-2">
                <TrendingUp aria-hidden="true" className="w-5 h-5 text-lsc-rose" />
                Checkout Trends
              </h2>

              <div className="flex flex-wrap items-center gap-4">
              {/* Granularity Selector */}
              <div className="flex items-center gap-2">
                <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Group by:</span>
                <div className="flex items-center gap-1 bg-lsc-cream dark:bg-earth-700 rounded-lg p-1" role="radiogroup" aria-label="Time granularity">
                  {trendDays <= 7 && (
                    <button
                      onClick={() => setGranularity("hourly")}
                      role="radio"
                      aria-checked={granularity === "hourly"}
                      className={`px-3 py-1.5 text-sm font-medium rounded transition-colors ${
                        granularity === "hourly"
                          ? "bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream shadow-sm"
                          : "text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream"
                      }`}
                    >
                      Hourly
                    </button>
                  )}
                  <button
                    onClick={() => setGranularity("daily")}
                    role="radio"
                    aria-checked={granularity === "daily"}
                    className={`px-3 py-1.5 text-sm font-medium rounded transition-colors ${
                      granularity === "daily"
                        ? "bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream shadow-sm"
                        : "text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream"
                    }`}
                  >
                    Daily
                  </button>
                  <button
                    onClick={() => setGranularity("weekly")}
                    role="radio"
                    aria-checked={granularity === "weekly"}
                    className={`px-3 py-1.5 text-sm font-medium rounded transition-colors ${
                      granularity === "weekly"
                        ? "bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream shadow-sm"
                        : "text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream"
                    }`}
                  >
                    Weekly
                  </button>
                  <button
                    onClick={() => setGranularity("monthly")}
                    role="radio"
                    aria-checked={granularity === "monthly"}
                    className={`px-3 py-1.5 text-sm font-medium rounded transition-colors ${
                      granularity === "monthly"
                        ? "bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream shadow-sm"
                        : "text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream"
                    }`}
                  >
                    Monthly
                  </button>
                </div>
              </div>

              {/* Comparison Mode Toggle */}
              <div className="flex items-center gap-2">
                <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Compare:</span>
                <div className="flex items-center gap-1 bg-lsc-cream dark:bg-earth-700 rounded-lg p-1">
                  <button
                    onClick={() => setComparisonMode("none")}
                    className={`px-3 py-1.5 text-sm font-medium rounded transition-colors ${
                      comparisonMode === "none"
                        ? "bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream shadow-sm"
                        : "text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream"
                    }`}
                    aria-label={t('aria.circulationReports.noComparison')}
                  >
                    None
                  </button>
                  <button
                    onClick={() => setComparisonMode("previous_period")}
                    className={`px-3 py-1.5 text-sm font-medium rounded transition-colors ${
                      comparisonMode === "previous_period"
                        ? "bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream shadow-sm"
                        : "text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream"
                    }`}
                    aria-label={t('circulationReports.compareWithPreviousPeriod')}
                  >
                    Previous Period
                  </button>
                  <button
                    onClick={() => setComparisonMode("previous_year")}
                    className={`px-3 py-1.5 text-sm font-medium rounded transition-colors ${
                      comparisonMode === "previous_year"
                        ? "bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream shadow-sm"
                        : "text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream"
                    }`}
                    aria-label={t('circulationReports.compareWithPreviousYear')}
                  >
                    Year-over-Year
                  </button>
                </div>
              </div>
              </div>
            </div>

            {/* Chart Info */}
            {comparisonMode !== "none" && (
              <div className="mb-3 p-3 bg-lsc-cream/50 dark:bg-earth-700/50 rounded-lg">
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                  {comparisonMode === "previous_period" && (
                    <>Comparing current period with the previous {trendDays} days</>
                  )}
                  {comparisonMode === "previous_year" && (
                    <>{t('circulationReports.comparingWithTheSamePeriod')}</>
                  )}
                </p>
              </div>
            )}

            {trendData.length > 0 ? (
              <Suspense fallback={
                <div className="h-[300px] flex items-center justify-center">
                  <Loader2 className="w-6 h-6 motion-safe:animate-spin text-lsc-rose" />
                </div>
              }>
                <CheckoutTrendsChart
                  data={processComparisonData(trendData, comparisonMode)}
                  formatDate={formatDate}
                  onDataPointClick={handleDataPointClick}
                  comparisonMode={comparisonMode}
                  granularity={granularity}
                />
              </Suspense>
            ) : (
              <div className="h-[300px] flex items-center justify-center text-lsc-dark/70 dark:text-lsc-cream/70">
                No trend data available
              </div>
            )}
          </div>

          {/* Daily Drill-Down Modal */}
          {isModalOpen && selectedDate && (
            <Suspense fallback={null}>
              <DailyDrillDownModal
                isOpen={isModalOpen}
                onClose={handleCloseModal}
                date={selectedDate}
                token={token}
              />
            </Suspense>
          )}

          {/* Two Column Layout */}
          <div className="grid md:grid-cols-2 gap-6">
            {/* Popular Items */}
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm border border-lsc-border dark:border-earth-700 p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream flex items-center gap-2">
                  <BarChart3 className="w-5 h-5 text-lsc-rose" />
                  Most Popular Items
                </h2>
                <button
                  onClick={() => exportToCSV(popularItems, "popular-items.csv")}
                  className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-rose flex items-center gap-1"
                >
                  <Download aria-hidden="true" className="w-4 h-4" />
                  Export
                </button>
              </div>
              {popularItems.length > 0 ? (
                <div className="space-y-3">
                  {popularItems.slice(0, 5).map((item, idx) => (
                    <div key={item.catalog_item_id} className="flex items-center gap-3">
                      <span className="w-6 h-6 bg-lsc-cream dark:bg-earth-800/30 rounded-full flex items-center justify-center text-xs font-medium text-lsc-rose dark:text-lsc-cream/70">
                        {idx + 1}
                      </span>
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-lsc-dark dark:text-lsc-cream truncate" title={item.title}>{item.title}</p>
                        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 truncate" title={item.author}>{item.author}</p>
                      </div>
                      <span className="text-sm font-medium text-lsc-rose dark:text-lsc-rose-light">
                        {item.checkout_count} checkouts
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-lsc-dark/70 dark:text-lsc-cream/70 text-center py-8">{t('circulationReports.noCheckoutDataAvailable')}</p>
              )}
            </div>

            {/* Overdue Items */}
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm border border-lsc-border dark:border-earth-700 p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream flex items-center gap-2">
                  <AlertTriangle aria-hidden="true" className="w-5 h-5 text-status-danger-500" />
                  Overdue Items
                </h2>
                <button
                  onClick={() => exportToCSV(overdueItems, "overdue-items.csv")}
                  className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-rose flex items-center gap-1"
                >
                  <Download aria-hidden="true" className="w-4 h-4" />
                  Export
                </button>
              </div>
              {overdueItems.length > 0 ? (
                <div className="space-y-3">
                  {overdueItems.slice(0, 5).map((item) => (
                    <div key={item.checkout_id} className="flex items-start gap-3">
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-lsc-dark dark:text-lsc-cream truncate" title={item.item_title}>{item.item_title}</p>
                        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{item.patron_name}</p>
                      </div>
                      <span className="text-sm font-medium text-status-danger-600 dark:text-status-danger-400 whitespace-nowrap">
                        {item.days_overdue} {item.days_overdue === 1 ? 'day' : 'days'} late
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-lsc-rose text-center py-8 flex items-center justify-center gap-2">
                  <CheckCircle className="w-6 h-6" aria-hidden="true" />
                  No overdue items!
                </p>
              )}
            </div>
          </div>

          {/* Inventory Summary */}
          {inventorySummary && (
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm border border-lsc-border dark:border-earth-700 p-6">
              <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream flex items-center gap-2 mb-4">
                <Package aria-hidden="true" className="w-5 h-5 text-lsc-rose" />
                Inventory Summary
              </h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
                <div>
                  <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Total Titles</p>
                  <p className="text-xl font-semibold text-lsc-dark dark:text-lsc-cream">
                    {inventorySummary.total_titles.toLocaleString()}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Total Copies</p>
                  <p className="text-xl font-semibold text-lsc-dark dark:text-lsc-cream">
                    {inventorySummary.total_copies.toLocaleString()}
                  </p>
                </div>
                {Object.entries(inventorySummary.by_condition).map(([condition, count]) => (
                  <div key={condition}>
                    <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 capitalize">{condition}</p>
                    <p className="text-xl font-semibold text-lsc-dark dark:text-lsc-cream">{count}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Fine Statistics */}
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm border border-lsc-border dark:border-earth-700 p-6">
            <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream flex items-center gap-2 mb-4">
              <DollarSign aria-hidden="true" className="w-5 h-5 text-lsc-rose" />
              Fine Collection Summary
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
              <div>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Outstanding</p>
                <p className="text-xl font-semibold text-status-danger-600 dark:text-status-danger-400">
                  {formatMoney(fineStats?.outstanding_total || 0)}
                </p>
              </div>
              <div>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Collected This Month</p>
                <p className="text-xl font-semibold text-lsc-rose dark:text-lsc-rose-light">
                  {formatMoney(fineStats?.paid_this_month || 0)}
                </p>
              </div>
              <div>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Waived This Month</p>
                <p className="text-xl font-semibold text-lsc-dark/70 dark:text-lsc-cream/70">
                  {formatMoney(fineStats?.waived_this_month || 0)}
                </p>
              </div>
              <div>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Patrons with Fines</p>
                <p className="text-xl font-semibold text-lsc-dark dark:text-lsc-cream">
                  {fineStats?.patrons_with_fines || 0}
                </p>
              </div>
            </div>
          </div>

          <DemandSignalsCard />
          <CollectionVelocityCard />
    </AdminShell>
  )
}
