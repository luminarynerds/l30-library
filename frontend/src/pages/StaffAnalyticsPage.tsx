/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect } from "react"
import { useNavigate } from "react-router-dom"
import { useAuth } from "../contexts/AuthContext"
import { AdminShell } from "../components/shells/AdminShell"
import {
  Download,
  Filter,
  ChevronDown,
  ChevronUp,
  Activity,
  TrendingUp,
  DollarSign,
  Users,
  BookOpen,
  Calendar,
  Share2,
} from "lucide-react"
import toast from "react-hot-toast"
import {
  getAnalyticsCirculationTrends,
  getAnalyticsPopularItems,
  getAnalyticsFinesSummary,
  getAnalyticsPatronStats,
  getAnalyticsCollectionUsage,
  getAnalyticsFineAging,
  getAnalyticsPaymentMethods,
  getAnalyticsWaivedFines,
} from "../api/analytics-api"
import { useTranslation } from "@/i18n"
import { CirculationTab } from "../components/analytics/CirculationTab"
import { PopularItemsTab } from "../components/analytics/PopularItemsTab"
import { FinesTab } from "../components/analytics/FinesTab"
import { PatronsTab } from "../components/analytics/PatronsTab"
import { CollectionTab } from "../components/analytics/CollectionTab"
import type { AnalyticsTab, DateRange } from "../components/analytics/analytics-types"

function downloadCsv(rows: Record<string, string | number | null | undefined>[], filename: string) {
  if (rows.length === 0) return false

  const headers = Object.keys(rows[0] || {})
  const escapeCsv = (value: string | number | null | undefined): string => {
    const safeValue = value == null ? "" : String(value)
    if (/^[=+\-@]/.test(safeValue)) {
      return `"'${safeValue.replace(/"/g, '""')}"`
    }
    return /[",\n\r]/.test(safeValue) ? `"${safeValue.replace(/"/g, '""')}"` : safeValue
  }

  const csv = [
    headers.join(","),
    ...rows.map((row) => headers.map((header) => escapeCsv(row[header])).join(",")),
  ].join("\n")

  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" })
  const url = URL.createObjectURL(blob)
  const link = document.createElement("a")
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
  return true
}

export default function StaffAnalyticsPage(): React.ReactElement {
  const { t } = useTranslation()
  const { token, isLoading: authLoading, user } = useAuth()
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState<AnalyticsTab>("circulation")
  const [showFilters, setShowFilters] = useState(false)

  const [dateRange, setDateRange] = useState<DateRange>(() => {
    const end = new Date()
    const start = new Date()
    start.setDate(start.getDate() - 30)
    return {
      startDate: start.toISOString().split("T")[0] || "",
      endDate: end.toISOString().split("T")[0] || "",
    }
  })

  const applyPreset = (days: number) => {
    const end = new Date()
    const start = new Date()
    start.setDate(start.getDate() - days)
    setDateRange({
      startDate: start.toISOString().split("T")[0] || "",
      endDate: end.toISOString().split("T")[0] || "",
    })
  }

  useEffect(() => {
    if (!authLoading && (!user || user.role === "patron")) {
      toast.error(t('toast.acquisitionManagement.staffAccessRequired'))
      navigate("/account")
    }
  }, [authLoading, user, navigate, t])

  const handleExport = async () => {
    if (!token) {
      toast.error(t('toast.staffAnalytics.signInRequired'))
      return
    }

    const fileSuffix = `${dateRange.startDate}_to_${dateRange.endDate}.csv`

    try {
      if (activeTab === "circulation") {
        const data = await getAnalyticsCirculationTrends(token, dateRange.startDate, dateRange.endDate)
        downloadCsv(
          data.trends.map((point) => ({ date: point.date, checkouts: point.checkouts, returns: point.returns })),
          `circulation_trends_${fileSuffix}`
        )
      } else if (activeTab === "popular") {
        const data = await getAnalyticsPopularItems(token, dateRange.startDate, dateRange.endDate)
        downloadCsv(
          data.topCheckouts.map((item) => ({
            item_id: item.itemId,
            title: item.title,
            author: item.author,
            category: item.category,
            checkout_count: item.count,
          })),
          `popular_items_${fileSuffix}`
        )
      } else if (activeTab === "fines") {
        const [summary, aging, methods, waived] = await Promise.all([
          getAnalyticsFinesSummary(token, dateRange.startDate, dateRange.endDate),
          getAnalyticsFineAging(token),
          getAnalyticsPaymentMethods(token, dateRange.startDate, dateRange.endDate),
          getAnalyticsWaivedFines(token, dateRange.startDate, dateRange.endDate),
        ])
        downloadCsv(
          [
            {
              total_outstanding: summary.totalOutstanding,
              total_collected: summary.totalCollected,
              total_waived: summary.totalWaived,
              patrons_with_fines: summary.patronsWithFines,
              collection_change_pct: summary.collectionChange,
              aging_total_outstanding: aging.totalOutstanding,
              payment_total_amount: methods.totalAmount,
              waived_count: waived.count,
            },
          ],
          `fine_summary_${fileSuffix}`
        )
      } else if (activeTab === "patrons") {
        const data = await getAnalyticsPatronStats(token, dateRange.startDate, dateRange.endDate)
        downloadCsv(
          data.topActivePatrons.map((patron) => ({
            patron_id: patron.patronId,
            name: patron.name,
            checkout_count: patron.checkoutCount,
          })),
          `top_active_patrons_${fileSuffix}`
        )
      } else {
        const data = await getAnalyticsCollectionUsage(token, dateRange.startDate, dateRange.endDate)
        downloadCsv(
          data.byCategory.map((category) => ({
            category: category.category,
            titles: category.titles,
            copies: category.copies,
            checkouts: category.checkouts,
            turnover_rate: category.turnoverRate,
            percent_of_collection: category.percentOfCollection,
          })),
          `collection_usage_${fileSuffix}`
        )
      }

      toast.success(t('toast.staffAnalytics.exportComplete'))
    } catch {
      toast.error(t('staffAnalytics.failedToExportAnalyticsData'))
    }
  }

  const tabs = [
    { id: "circulation" as const, label: "Circulation", icon: Activity },
    { id: "popular" as const, label: "Popular Items", icon: TrendingUp },
    { id: "fines" as const, label: "Fine Analytics", icon: DollarSign },
    { id: "patrons" as const, label: "Patron Analytics", icon: Users },
    { id: "collection" as const, label: "Collection", icon: BookOpen },
  ]

  return (
    <AdminShell
      title="Analytics Dashboard"
      subtitle={t('staffAnalytics.comprehensiveLibraryAnalyticsAndReporting')}
      actions={
        <>
          <button
            onClick={() => navigate("/staff/admin/analytics/sharing")}
            className="flex items-center gap-2 px-4 py-2 text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-lsc-brown/20 rounded-xl transition-colors"
            title={t('staffAnalytics.viewSocialSharingAnalytics')}
          >
            <Share2 className="w-4 h-4" aria-hidden="true" />
            Sharing
          </button>
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl transition-colors ${
              showFilters
                ? "bg-lsc-rose text-white"
                : "text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-lsc-brown/20"
            }`}
          >
            <Filter className="w-4 h-4" aria-hidden="true" />
            Filters
            {showFilters ? (
              <ChevronUp className="w-4 h-4" aria-hidden="true" />
            ) : (
              <ChevronDown className="w-4 h-4" aria-hidden="true" />
            )}
          </button>
          <button
            onClick={() => void handleExport()}
            className="flex items-center gap-2 px-4 py-2 text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-lsc-brown/20 rounded-xl transition-colors"
          >
            <Download className="w-4 h-4" aria-hidden="true" />
            Export
          </button>
        </>
      }
    >
      {/* Filters Panel */}
      {showFilters && (
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm border border-lsc-border dark:border-earth-700">
          <div className="flex flex-col md:flex-row md:items-end gap-4">
            <div className="flex-1">
              <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
                <Calendar className="w-4 h-4 inline mr-2" aria-hidden="true" />
                Date Range
              </label>
              <div className="flex items-center gap-2">
                <input
                  type="date"
                  value={dateRange.startDate}
                  onChange={(e) => setDateRange({ ...dateRange, startDate: e.target.value })}
                  aria-label={t('aria.staffAnalytics.startDate', 'Start date')}
                  className="px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
                />
                <span className="text-lsc-dark/70 dark:text-lsc-cream/70">to</span>
                <input
                  type="date"
                  value={dateRange.endDate}
                  onChange={(e) => setDateRange({ ...dateRange, endDate: e.target.value })}
                  aria-label={t('aria.staffAnalytics.endDate', 'End date')}
                  className="px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
                />
              </div>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Quick:</span>
              {[
                { days: 7, label: "7d" },
                { days: 30, label: "30d" },
                { days: 90, label: "90d" },
                { days: 365, label: "1y" },
              ].map((preset) => (
                <button
                  key={preset.days}
                  onClick={() => applyPreset(preset.days)}
                  className="px-3 py-1 text-sm font-medium rounded-lg bg-lsc-cream dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream hover:bg-lsc-rose hover:text-white transition-colors"
                >
                  {preset.label}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="border-b border-lsc-border dark:border-earth-700">
        <div className="flex gap-1 overflow-x-auto">
          {tabs.map((tab) => {
            const Icon = tab.icon
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-4 py-3 font-medium whitespace-nowrap transition-colors border-b-2 ${
                  activeTab === tab.id
                    ? "border-lsc-rose text-lsc-rose"
                    : "border-transparent text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream"
                }`}
              >
                <Icon className="w-4 h-4" aria-hidden="true" />
                {tab.label}
              </button>
            )
          })}
        </div>
      </div>

      {/* Tab Content */}
      <div className="min-h-[500px]">
        {activeTab === "circulation" && token && (
          <CirculationTab token={token} dateRange={dateRange} />
        )}
        {activeTab === "popular" && token && (
          <PopularItemsTab token={token} dateRange={dateRange} />
        )}
        {activeTab === "fines" && token && (
          <FinesTab token={token} dateRange={dateRange} />
        )}
        {activeTab === "patrons" && token && (
          <PatronsTab token={token} dateRange={dateRange} />
        )}
        {activeTab === "collection" && token && (
          <CollectionTab token={token} dateRange={dateRange} />
        )}
      </div>
    </AdminShell>
  )
}
