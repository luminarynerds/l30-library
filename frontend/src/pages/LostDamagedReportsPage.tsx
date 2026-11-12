/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import React from 'react'
import { useState, useEffect, useCallback } from "react"
import { useAuth } from "../contexts/AuthContext"
import { AdminShell } from '../components/shells/AdminShell'
import {
  Loader2, RefreshCw, DollarSign, Package, AlertTriangle, TrendingUp,
  BarChart3, Download, Calendar, MapPin, Users, XCircle
} from "lucide-react"
import toast from "react-hot-toast"
import { fetchAllLostDamagedReports } from "../api/reports-api"
import type {
  FinancialSummary,
  ChargesByType,
  LostDamagedInventorySummary,
  LostByCategory,
  LostByLocation,
  MonthlyTrend,
  PatronRisk,
} from "../api/reports-api"
import {
  ResponsiveContainer, PieChart, Pie, Cell, Tooltip, Legend,
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  LineChart, Line
} from "recharts"
import {
  AccessibleChartWrapper,
} from "../components/charts/AccessibleChartWrapper"
import { useLostDamagedColors, useChartColors, useChartTooltipStyle } from "../hooks/useChartColors"
import { useTranslation} from '@/i18n'

export default function LostDamagedReportsPage(): React.ReactElement {
  const { t } = useTranslation()
  const { token, isLoading: authLoading, isAuthenticated } = useAuth()
  const [isLoading, setIsLoading] = useState(true)
  const COLORS = useLostDamagedColors()
  const chartColors = useChartColors()
  const tooltipStyle = useChartTooltipStyle()
  const [financialSummary, setFinancialSummary] = useState<FinancialSummary | null>(null)
  const [chargesByType, setChargesByType] = useState<ChargesByType | null>(null)
  const [inventorySummary, setInventorySummary] = useState<LostDamagedInventorySummary | null>(null)
  const [lostByCategory, setLostByCategory] = useState<LostByCategory[]>([])
  const [lostByLocation, setLostByLocation] = useState<LostByLocation[]>([])
  const [monthlyTrend, setMonthlyTrend] = useState<MonthlyTrend[]>([])
  const [patronRisk, setPatronRisk] = useState<PatronRisk[]>([])

  // Date range filtering
  const [startDate, setStartDate] = useState("")
  const [endDate, setEndDate] = useState("")
  const [location, setLocation] = useState("")

  const fetchData = useCallback(async () => {
    if (!token) return
    setIsLoading(true)
    try {
      const reports = await fetchAllLostDamagedReports(
        startDate || undefined,
        endDate || undefined,
        location || undefined
      )
      setFinancialSummary(reports.financialSummary)
      setChargesByType(reports.chargesByType)
      setInventorySummary(reports.inventorySummary)
      setLostByCategory(reports.lostByCategory)
      setLostByLocation(reports.lostByLocation)
      setMonthlyTrend(reports.monthlyTrend)
      setPatronRisk(reports.patronRisk)
    } catch (_err) {
      Sentry.captureException(_err instanceof Error ? _err : new Error(String(_err)))
      toast.error(t('lostDamagedReports.failedToLoadLostDamaged'))
    } finally {
      setIsLoading(false)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, startDate, endDate, location])

  useEffect(() => {
    if (isAuthenticated && token) fetchData()
  }, [isAuthenticated, token, fetchData])

  const formatMoney = (amount: number) => `$${amount.toFixed(2)}`

  const exportToCSV = (data: unknown[], filename: string) => {
    if (data.length === 0) {
      toast.error(t('lostDamagedReports.noDataToExport'))
      return
    }
    const firstRow = data[0] as Record<string, unknown>
    const headers = Object.keys(firstRow).join(",")
    const rows = data.map(row => Object.values(row as Record<string, unknown>).join(",")).join("\n")
    const csv = `${headers}\n${rows}`
    const blob = new Blob([csv], { type: "text/csv" })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = filename
    a.click()
    toast.success(t('toast.lostDamagedReports.reportExportedSuccessfully'))
  }

  const handleApplyFilters = () => {
    fetchData()
    toast.success(t('toast.circulationReports.filtersApplied'))
  }

  const handleResetFilters = () => {
    setStartDate("")
    setEndDate("")
    setLocation("")
    toast.success(t('toast.circulationReports.filtersReset'))
  }

  if (authLoading || isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" />
      </div>
    )
  }

  if (!isAuthenticated) return <></>

  // Prepare chart data
  const chargesTypeData = chargesByType ? [
    { name: "Lost Items", value: chargesByType.lost_item_charges, color: COLORS[0] },
    { name: "Damaged Items", value: chargesByType.damaged_item_charges, color: COLORS[1] },
    { name: "Processing Fees", value: chargesByType.processing_fees, color: COLORS[2] },
  ] : []

  return (
    <AdminShell title={t('lostDamagedReports.lostDamagedItemsReports')}>
          {/* Header */}
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
                Lost & Damaged Items Reports
              </h1>
              <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
                Financial and inventory tracking for lost and damaged materials
              </p>
            </div>
            <button
              onClick={fetchData}
              className="flex items-center gap-2 px-4 py-2 text-lsc-rose hover:bg-lsc-cream dark:hover:bg-lsc-brown/20 rounded-xl transition-colors"
            >
              <RefreshCw aria-hidden="true" className="w-4 h-4" />
              Refresh
            </button>
          </div>

          {/* Date Range Filters */}
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm border border-lsc-border dark:border-earth-700 p-4">
            <div className="grid md:grid-cols-4 gap-4">
              <div>
                <label className="flex items-center gap-2 text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
                  <Calendar className="w-4 h-4 text-lsc-rose" aria-hidden="true" />
                  Start Date
                </label>
                <input
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
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
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                  className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
                />
              </div>
              <div>
                <label className="flex items-center gap-2 text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
                  <MapPin className="w-4 h-4 text-lsc-rose" aria-hidden="true" />
                  Location
                </label>
                <input
                  type="text"
                  placeholder={t('placeholder.lostDamagedReports.filterByLocation')}
                  aria-label={t('aria.lostDamagedReports.filterByLocation')}
                  value={location}
                  onChange={(e) => setLocation(e.target.value)}
                  className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream placeholder:text-lsc-dark/70 focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
                />
              </div>
              <div className="flex items-end gap-2">
                <button
                  onClick={handleApplyFilters}
                  className="flex-1 px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 transition-colors font-medium"
                >
                  Apply
                </button>
                <button
                  onClick={handleResetFilters}
                  className="px-4 py-2 border border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream rounded-lg hover:bg-lsc-cream dark:hover:bg-earth-700 transition-colors"
                >
                  Reset
                </button>
              </div>
            </div>
          </div>

          {/* Financial Summary Cards */}
          {financialSummary && (
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
              <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm border border-lsc-border dark:border-earth-700">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-status-danger-100 dark:bg-status-danger-900/30 rounded-xl flex items-center justify-center">
                    <DollarSign aria-hidden="true" className="w-5 h-5 text-status-danger-600 dark:text-status-danger-400" />
                  </div>
                  <div>
                    <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Total Charges</p>
                    <p className="text-lg font-bold text-lsc-dark dark:text-lsc-cream">
                      {formatMoney(financialSummary.total_charges)}
                    </p>
                  </div>
                </div>
              </div>

              <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm border border-lsc-border dark:border-earth-700">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-status-success-100 dark:bg-status-success-900/30 rounded-xl flex items-center justify-center">
                    <DollarSign aria-hidden="true" className="w-5 h-5 text-status-success-600 dark:text-status-success-400" />
                  </div>
                  <div>
                    <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Collected</p>
                    <p className="text-lg font-bold text-status-success-600 dark:text-status-success-400">
                      {formatMoney(financialSummary.total_collected)}
                    </p>
                  </div>
                </div>
              </div>

              <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm border border-lsc-border dark:border-earth-700">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-status-warning-100 dark:bg-status-warning-900/30 rounded-xl flex items-center justify-center">
                    <DollarSign aria-hidden="true" className="w-5 h-5 text-status-warning-600 dark:text-status-warning-400" />
                  </div>
                  <div>
                    <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Outstanding</p>
                    <p className="text-lg font-bold text-status-warning-600 dark:text-status-warning-400">
                      {formatMoney(financialSummary.total_outstanding)}
                    </p>
                  </div>
                </div>
              </div>

              <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm border border-lsc-border dark:border-earth-700">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-earth-100 dark:bg-earth-800/30 rounded-xl flex items-center justify-center">
                    <DollarSign aria-hidden="true" className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
                  </div>
                  <div>
                    <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Waived</p>
                    <p className="text-lg font-bold text-lsc-rose dark:text-lsc-rose-light">
                      {formatMoney(financialSummary.total_waived)}
                    </p>
                  </div>
                </div>
              </div>

              <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm border border-lsc-border dark:border-earth-700">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-category-100 dark:bg-category-900/30 rounded-xl flex items-center justify-center">
                    <DollarSign aria-hidden="true" className="w-5 h-5 text-category-600 dark:text-category-400" />
                  </div>
                  <div>
                    <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Credits</p>
                    <p className="text-lg font-bold text-category-600 dark:text-category-400">
                      {formatMoney(financialSummary.total_credits)}
                    </p>
                  </div>
                </div>
              </div>

              <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm border border-lsc-border dark:border-earth-700">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-lsc-cream dark:bg-lsc-brown/30 rounded-xl flex items-center justify-center">
                    <BarChart3 aria-hidden="true" className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
                  </div>
                  <div>
                    <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Collection Rate</p>
                    <p className="text-lg font-bold text-lsc-dark dark:text-lsc-cream">
                      {(financialSummary.collection_rate * 100).toFixed(1)}%
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Two Column Layout - Charges by Type and Inventory Summary */}
          <div className="grid md:grid-cols-2 gap-6">
            {/* Charges by Type - Pie Chart */}
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm border border-lsc-border dark:border-earth-700 p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream flex items-center gap-2">
                  <DollarSign className="w-5 h-5 text-lsc-rose" aria-hidden="true" />
                  Charges by Type
                </h2>
                <button
                  onClick={() => chargesByType && exportToCSV([chargesByType], "charges-by-type.csv")}
                  className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-rose flex items-center gap-1"
                  aria-label={t('lostDamagedReports.exportChargesByTypeTo')}
                >
                  <Download aria-hidden="true" className="w-4 h-4" />
                  Export
                </button>
              </div>
              <AccessibleChartWrapper
                title="Charges by Type"
                description="Distribution of charges across lost items, damaged items, and processing fees"
                data={chargesTypeData}
                columns={[
                  { key: "name", label: "Charge Type" },
                  { key: "value", label: "Amount", format: (v) => formatMoney(Number(v)) },
                ]}
                emptyMessage="No charge data available"
                emptyHeight={300}
              >
                <ResponsiveContainer width="100%" height={300}>
                  <PieChart>
                    <Pie
                      data={chargesTypeData}
                      cx="50%"
                      cy="50%"
                      labelLine={false}
                      label={({ name, percent }) => `${name}: ${((percent ?? 0) * 100).toFixed(0)}%`}
                      outerRadius={80}
                      fill={chartColors.primary[0]}
                      dataKey="value"
                    >
                      {chargesTypeData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip formatter={(value) => formatMoney(Number(value))} contentStyle={tooltipStyle} />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              </AccessibleChartWrapper>
            </div>

            {/* Inventory Summary */}
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm border border-lsc-border dark:border-earth-700 p-6">
              <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream flex items-center gap-2 mb-4">
                <Package aria-hidden="true" className="w-5 h-5 text-lsc-rose" />
                Inventory Summary
              </h2>
              {inventorySummary && (
                <div className="grid grid-cols-2 gap-4">
                  <div className="p-3 bg-lsc-cream/50 dark:bg-earth-700/50 rounded-lg">
                    <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Total Lost</p>
                    <p className="text-2xl font-bold text-status-danger-600 dark:text-status-danger-400">{inventorySummary.total_lost}</p>
                  </div>
                  <div className="p-3 bg-lsc-cream/50 dark:bg-earth-700/50 rounded-lg">
                    <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Total Damaged</p>
                    <p className="text-2xl font-bold text-status-warning-600 dark:text-status-warning-400">{inventorySummary.total_damaged}</p>
                  </div>
                  <div className="p-3 bg-lsc-cream/50 dark:bg-earth-700/50 rounded-lg">
                    <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Lost by Patron</p>
                    <p className="text-xl font-semibold text-lsc-dark dark:text-lsc-cream">{inventorySummary.lost_by_patron}</p>
                  </div>
                  <div className="p-3 bg-lsc-cream/50 dark:bg-earth-700/50 rounded-lg">
                    <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Lost in Transit</p>
                    <p className="text-xl font-semibold text-lsc-dark dark:text-lsc-cream">{inventorySummary.lost_in_transit}</p>
                  </div>
                  <div className="p-3 bg-lsc-cream/50 dark:bg-earth-700/50 rounded-lg">
                    <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">In Mending</p>
                    <p className="text-xl font-semibold text-lsc-dark dark:text-lsc-cream">{inventorySummary.in_mending}</p>
                  </div>
                  <div className="p-3 bg-status-success-100 dark:bg-status-success-900/30 rounded-lg">
                    <p className="text-sm text-status-success-800 dark:text-status-success-400">Items Found</p>
                    <p className="text-xl font-semibold text-status-success-600 dark:text-status-success-400">{inventorySummary.items_found}</p>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Lost by Category - Bar Chart */}
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm border border-lsc-border dark:border-earth-700 p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream flex items-center gap-2">
                <BarChart3 className="w-5 h-5 text-lsc-rose" aria-hidden="true" />
                Lost Items by Category
              </h2>
              <button
                onClick={() => exportToCSV(lostByCategory, "lost-by-category.csv")}
                className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-rose flex items-center gap-1"
                aria-label={t('lostDamagedReports.exportLostItemsByCategory')}
              >
                <Download aria-hidden="true" className="w-4 h-4" />
                Export
              </button>
            </div>
            <AccessibleChartWrapper
              title={t('lostDamagedReports.lostItemsByCategory')}
              description="Count and total value of lost items grouped by item type"
              data={lostByCategory as unknown as Record<string, unknown>[]}
              columns={[
                { key: "item_type", label: "Category" },
                { key: "count", label: "Count" },
                { key: "total_value", label: "Total Value", format: (v) => formatMoney(Number(v)) },
              ]}
              emptyMessage="No category data available"
              emptyHeight={300}
            >
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={lostByCategory}>
                  <CartesianGrid strokeDasharray="3 3" stroke={chartColors.grid} />
                  <XAxis dataKey="item_type" stroke={chartColors.axis} />
                  <YAxis stroke={chartColors.axis} />
                  <Tooltip formatter={(value, name) => {
                    if (name === "Total Value") return formatMoney(Number(value))
                    return value
                  }} contentStyle={tooltipStyle} />
                  <Legend />
                  <Bar dataKey="count" fill={COLORS[0]} name="Count" />
                  <Bar dataKey="total_value" fill={COLORS[1]} name="Total Value" />
                </BarChart>
              </ResponsiveContainer>
            </AccessibleChartWrapper>
          </div>

          {/* Lost by Location - Bar Chart (only if multi-branch) */}
          {lostByLocation.length > 0 && (
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm border border-lsc-border dark:border-earth-700 p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream flex items-center gap-2">
                  <MapPin className="w-5 h-5 text-lsc-rose" aria-hidden="true" />
                  Lost Items by Location
                </h2>
                <button
                  onClick={() => exportToCSV(lostByLocation, "lost-by-location.csv")}
                  className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-rose flex items-center gap-1"
                >
                  <Download aria-hidden="true" className="w-4 h-4" />
                  Export
                </button>
              </div>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={lostByLocation}>
                  <CartesianGrid strokeDasharray="3 3" stroke={chartColors.grid} />
                  <XAxis dataKey="location" stroke={chartColors.axis} />
                  <YAxis stroke={chartColors.axis} />
                  <Tooltip formatter={(value, name) => {
                    if (name === "total_value") return formatMoney(Number(value))
                    return value
                  }} contentStyle={tooltipStyle} />
                  <Legend />
                  <Bar dataKey="count" fill={COLORS[2]} name="Count" />
                  <Bar dataKey="total_value" fill={COLORS[3]} name="Total Value" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Monthly Trend - Line Chart */}
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm border border-lsc-border dark:border-earth-700 p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream flex items-center gap-2">
                <TrendingUp className="w-5 h-5 text-lsc-rose" aria-hidden="true" />
                Monthly Trends
              </h2>
              <button
                onClick={() => exportToCSV(monthlyTrend, "monthly-trend.csv")}
                className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-rose flex items-center gap-1"
                aria-label={t('lostDamagedReports.exportMonthlyTrendsToCsv')}
              >
                <Download aria-hidden="true" className="w-4 h-4" />
                Export
              </button>
            </div>
            <AccessibleChartWrapper
              title="Monthly Trends"
              description="Monthly trends showing lost items, damaged items, charges, and net revenue over time"
              data={monthlyTrend as unknown as Record<string, unknown>[]}
              columns={[
                { key: "period", label: "Period" },
                { key: "lost_count", label: "Lost Items" },
                { key: "damaged_count", label: "Damaged Items" },
                { key: "charges", label: "Charges", format: (v) => formatMoney(Number(v)) },
                { key: "net", label: "Net Revenue", format: (v) => formatMoney(Number(v)) },
              ]}
              emptyMessage="No trend data available"
              emptyHeight={300}
            >
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={monthlyTrend}>
                  <CartesianGrid strokeDasharray="3 3" stroke={chartColors.grid} />
                  <XAxis dataKey="period" stroke={chartColors.axis} />
                  <YAxis stroke={chartColors.axis} />
                  <Tooltip formatter={(value, name) => {
                    if (name === "Charges" || name === "Net Revenue") {
                      return formatMoney(Number(value))
                    }
                    return value
                  }} contentStyle={tooltipStyle} />
                  <Legend />
                  <Line type="monotone" dataKey="lost_count" stroke={COLORS[0]} name="Lost Items" strokeWidth={2} dot={{ r: 4 }} />
                  <Line type="monotone" dataKey="damaged_count" stroke={COLORS[1]} name="Damaged Items" strokeWidth={2} strokeDasharray="5 5" dot={{ r: 4 }} />
                  <Line type="monotone" dataKey="charges" stroke={COLORS[2]} name="Charges" strokeWidth={2} dot={{ r: 4 }} />
                  <Line type="monotone" dataKey="net" stroke={COLORS[4]} name="Net Revenue" strokeWidth={2} strokeDasharray="3 3" dot={{ r: 4 }} />
                </LineChart>
              </ResponsiveContainer>
            </AccessibleChartWrapper>
          </div>

          {/* Patron Risk Report - Table */}
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm border border-lsc-border dark:border-earth-700 p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream flex items-center gap-2">
                <Users className="w-5 h-5 text-lsc-rose" aria-hidden="true" />
                High-Risk Patrons
              </h2>
              <button
                onClick={() => exportToCSV(patronRisk, "patron-risk-report.csv")}
                className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-rose flex items-center gap-1"
              >
                <Download aria-hidden="true" className="w-4 h-4" />
                Export
              </button>
            </div>
            {patronRisk.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full" aria-label={t('aria.lostDamagedReports.highriskPatronsReport')}>
                  <caption className="sr-only">
                    High-risk patrons table showing patron name, email, lost items count, damaged items count, claims returned count, total charges, outstanding balance, and risk score
                  </caption>
                  <thead>
                    <tr className="border-b border-lsc-border dark:border-earth-700">
                      <th scope="col" className="text-left py-3 px-4 text-sm font-medium text-lsc-dark dark:text-lsc-cream">Patron</th>
                      <th scope="col" className="text-left py-3 px-4 text-sm font-medium text-lsc-dark dark:text-lsc-cream">Email</th>
                      <th scope="col" className="text-center py-3 px-4 text-sm font-medium text-lsc-dark dark:text-lsc-cream">Lost</th>
                      <th scope="col" className="text-center py-3 px-4 text-sm font-medium text-lsc-dark dark:text-lsc-cream">Damaged</th>
                      <th scope="col" className="text-center py-3 px-4 text-sm font-medium text-lsc-dark dark:text-lsc-cream">Claims</th>
                      <th scope="col" className="text-right py-3 px-4 text-sm font-medium text-lsc-dark dark:text-lsc-cream">Total Charges</th>
                      <th scope="col" className="text-right py-3 px-4 text-sm font-medium text-lsc-dark dark:text-lsc-cream">Outstanding</th>
                      <th scope="col" className="text-center py-3 px-4 text-sm font-medium text-lsc-dark dark:text-lsc-cream">Risk Score</th>
                    </tr>
                  </thead>
                  <tbody>
                    {patronRisk.map((patron) => (
                      <tr key={patron.patron_id} className="border-b border-lsc-border/50 dark:border-earth-700/50 hover:bg-lsc-cream/30 dark:hover:bg-earth-700/30">
                        <td className="py-3 px-4 text-sm text-lsc-dark dark:text-lsc-cream">{patron.patron_name}</td>
                        <td className="py-3 px-4 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{patron.patron_email}</td>
                        <td className="py-3 px-4 text-sm text-center">
                          <span className="inline-flex items-center gap-1 px-2 py-1 bg-status-danger-100 dark:bg-status-danger-900/30 text-status-danger-800 dark:text-status-danger-400 rounded-full">
                            <XCircle className="w-3 h-3" aria-hidden="true" />
                            {patron.lost_item_count}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-sm text-center">
                          <span className="inline-flex items-center gap-1 px-2 py-1 bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-800 dark:text-status-warning-400 rounded-full">
                            <AlertTriangle className="w-3 h-3" aria-hidden="true" />
                            {patron.damaged_item_count}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-sm text-center text-lsc-dark dark:text-lsc-cream">{patron.claims_returned_count}</td>
                        <td className="py-3 px-4 text-sm text-right font-medium text-lsc-dark dark:text-lsc-cream">
                          {formatMoney(patron.total_charges)}
                        </td>
                        <td className="py-3 px-4 text-sm text-right font-medium text-status-danger-600 dark:text-status-danger-400">
                          {formatMoney(patron.outstanding_balance)}
                        </td>
                        <td className="py-3 px-4 text-sm text-center">
                          <span className={`inline-flex px-2 py-1 rounded-full font-medium ${
                            patron.risk_score >= 8
                              ? 'bg-status-danger-100 dark:bg-status-danger-900/30 text-status-danger-800 dark:text-status-danger-400'
                              : patron.risk_score >= 5
                              ? 'bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-800 dark:text-status-warning-400'
                              : 'bg-earth-100 dark:bg-earth-800/30 text-earth-800 dark:text-lsc-rose-light'
                          }`}>
                            {patron.risk_score.toFixed(1)}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="py-8 text-center text-lsc-dark/70 dark:text-lsc-cream/70">
                No high-risk patrons found
              </div>
            )}
          </div>
    </AdminShell>
  )
}
