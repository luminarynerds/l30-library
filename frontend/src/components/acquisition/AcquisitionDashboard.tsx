/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect } from "react"
import {
  Loader2,
  DollarSign,
  ShoppingCart,
  BookOpen,
  Calendar,
  AlertTriangle,
  ArrowRight,
  Activity,
  Clock,
  CheckCircle,
  Package,
  FileText,
  Focus,
} from "lucide-react"
import toast from "react-hot-toast"
import { fetchApi } from '@/api/fetchApi'
import { t, getCurrentLocale } from '@/i18n'
import { useEssentialsMode } from '@/contexts/EssentialsModeContext'

const FOCUS_MODE_STORAGE_KEY = 'l30:acq-dashboard:focus-mode'

interface QueueItem {
  count: number
  label: string
  tab: string
}

const computeQueueItems = (data: DashboardData): QueueItem[] => {
  const pendingApproval = data.order_summary?.pending_approval ?? 0
  const fundsOverUtilized = data.fund_summary?.funds_with_warnings ?? 0
  const staleFromBottleneck = data.bottlenecks?.find(b => b.type === 'stale_selections')?.count
  const staleSelections = staleFromBottleneck ?? (data.selection_summary?.total_pending ?? 0)
  const awaitingReceiving = (data.order_summary?.submitted ?? 0) + (data.order_summary?.partially_received ?? 0)

  return [
    {
      count: pendingApproval,
      label: `${pendingApproval} ${pendingApproval === 1 ? 'purchase order' : 'purchase orders'} awaiting your approval`,
      tab: 'orders',
    },
    {
      count: fundsOverUtilized,
      label: `${fundsOverUtilized} ${fundsOverUtilized === 1 ? 'fund' : 'funds'} above 90% utilization`,
      tab: 'funds',
    },
    {
      count: staleSelections,
      label: staleFromBottleneck !== undefined
        ? `${staleSelections} ${staleSelections === 1 ? 'selection item' : 'selection items'} pending for over 30 days`
        : `${staleSelections} ${staleSelections === 1 ? 'selection item' : 'selection items'} pending review`,
      tab: 'selection',
    },
    {
      count: awaitingReceiving,
      label: `${awaitingReceiving} ${awaitingReceiving === 1 ? 'PO' : 'POs'} awaiting receiving`,
      tab: 'orders',
    },
  ].filter(item => item.count > 0)
}

const BOTTLENECK_LABELS: Record<string, string> = {
  stale_approvals: "Stale approvals",
  stale_selections: "Stale selections",
  low_budget: "Low budget",
  over_budget: "Over budget",
}

const sentenceCase = (s: string): string => {
  const spaced = s.replace(/_/g, " ")
  return spaced.charAt(0).toUpperCase() + spaced.slice(1)
}

const humanizeDescription = (desc: string, count: number): string =>
  desc.replace(/\(s\)/g, count === 1 ? "" : "s")

const BOTTLENECK_TAB_MAP: Record<string, string> = {
  stale_approvals: "orders",
  stale_selections: "selection",
  low_budget: "funds",
  over_budget: "funds",
}

const ACTIVITY_TAB_MAP: Record<string, string> = {
  order: "orders",
  purchase_order: "orders",
  selection: "selection",
  fund: "funds",
  approval: "orders",
  receiving: "orders",
}

interface FundSummary {
  total_allocated: number
  total_spent: number
  total_available: number
  funds_with_warnings: number
}

interface SelectionSummary {
  total_pending: number
  total_approved: number
  total_ordered: number
}

interface OrderStatusCount {
  draft: number
  pending_approval: number
  approved: number
  submitted: number
  partially_received: number
  received: number
}

interface TopVendor {
  vendor_id: number
  vendor_name: string
  order_count: number
}

interface VendorSummaryData {
  total_active_vendors: number
  top_vendors: TopVendor[]
}

interface ReleaseSummary {
  upcoming_count: number
  high_demand_count: number
}

interface Bottleneck {
  type: string
  description: string
  count: number
  severity: string
}

interface RecentAction {
  action: string
  description: string
  timestamp: string
  entity_type: string
  entity_id: number | null
}

interface DashboardData {
  fund_summary: FundSummary
  selection_summary: SelectionSummary
  order_summary: OrderStatusCount
  vendor_summary: VendorSummaryData
  release_summary: ReleaseSummary
  bottlenecks: Bottleneck[]
  recent_activity: RecentAction[]
}

interface Props {
  token: string
  formatMoney: (n: number) => string
  onNavigateTab: (tab: string) => void
}

export default function AcquisitionDashboard({ token, formatMoney, onNavigateTab }: Props) {
  const [data, setData] = useState<DashboardData | null>(null)
  const [loading, setLoading] = useState(true)
  const { isEssentialsMode } = useEssentialsMode()
  const [focusMode, setFocusMode] = useState(false)

  const fetchDashboard = async () => {
    setLoading(true)
    try {
      const json: DashboardData = await fetchApi('/acquisition/dashboard')
      setData(json)
    } catch (err) {
      toast.error(err instanceof Error ? err.message : t('toast.acquisition.failedToLoadDashboard'))
    } finally {
      setLoading(false)
    }
  }


  useEffect(() => {
    fetchDashboard()

  }, [token])

  // Initialize focus-mode pref: explicit localStorage wins; otherwise auto-ON for essentialsMode users.
  useEffect(() => {
    try {
      const stored = localStorage.getItem(FOCUS_MODE_STORAGE_KEY)
      if (stored === 'on') {
        setFocusMode(true)
      } else if (stored === 'off') {
        setFocusMode(false)
      } else if (isEssentialsMode) {
        setFocusMode(true)
      }
    } catch {
      // localStorage may be unavailable (private browsing); ignore
    }
  }, [isEssentialsMode])

  const toggleFocusMode = () => {
    setFocusMode(prev => {
      const next = !prev
      try {
        localStorage.setItem(FOCUS_MODE_STORAGE_KEY, next ? 'on' : 'off')
      } catch {
        // ignore
      }
      return next
    })
  }

  const formatTimestamp = (ts: string): string => {
    const date = new Date(ts)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMs / 3600000)
    const diffDays = Math.floor(diffMs / 86400000)

    if (diffMins < 1) return "Just now"
    if (diffMins < 60) return `${diffMins}m ago`
    if (diffHours < 24) return `${diffHours}h ago`
    if (diffDays < 7) return `${diffDays}d ago`
    return date.toLocaleDateString(getCurrentLocale(), { month: "short", day: "numeric" })
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case "critical":
        return {
          dot: "bg-status-danger-500",
          bg: "bg-status-danger-50 dark:bg-status-danger-900/10",
          border: "border-status-danger-200 dark:border-status-danger-800",
          text: "text-status-danger-700 dark:text-status-danger-300",
        }
      case "warning":
        return {
          dot: "bg-status-warning-500",
          bg: "bg-status-warning-50 dark:bg-status-warning-900/10",
          border: "border-status-warning-200 dark:border-status-warning-800",
          text: "text-status-warning-700 dark:text-status-warning-300",
        }
      default:
        return {
          dot: "bg-status-success-500",
          bg: "bg-lsc-white dark:bg-earth-800",
          border: "border-lsc-border dark:border-earth-700",
          text: "text-status-success-700 dark:text-status-success-300",
        }
    }
  }

  const getActivityIcon = (type: string) => {
    switch (type) {
      case "order":
        return <ShoppingCart className="w-3.5 h-3.5" />
      case "selection":
        return <BookOpen className="w-3.5 h-3.5" />
      case "fund":
        return <DollarSign className="w-3.5 h-3.5" />
      case "approval":
        return <CheckCircle className="w-3.5 h-3.5" />
      case "receiving":
        return <Package className="w-3.5 h-3.5" />
      default:
        return <Activity className="w-3.5 h-3.5" />
    }
  }

  const pipelineStageConfig: Record<string, { label: string; color: string; icon: React.ReactNode }> = {
    selection: {
      label: "Selection",
      color: "bg-earth-700 dark:bg-earth-600",
      icon: <BookOpen className="w-4 h-4" />,
    },
    draft: {
      label: "Draft",
      color: "bg-earth-800 dark:bg-earth-500",
      icon: <FileText className="w-4 h-4" />,
    },
    pending: {
      label: "Pending",
      color: "bg-status-warning-400 dark:bg-status-warning-600",
      icon: <Clock className="w-4 h-4" />,
    },
    approved: {
      label: "Approved",
      color: "bg-lsc-rose",
      icon: <CheckCircle className="w-4 h-4" />,
    },
    submitted: {
      label: "Submitted",
      color: "bg-category-400 dark:bg-category-600",
      icon: <ArrowRight className="w-4 h-4" />,
    },
    received: {
      label: "Received",
      color: "bg-status-success-400 dark:bg-status-success-600",
      icon: <Package className="w-4 h-4" />,
    },
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" />
      </div>
    )
  }

  if (!data) {
    return (
      <div className="text-center py-8 text-lsc-dark/70 dark:text-lsc-cream/60">
        <Activity className="w-10 h-10 mx-auto mb-2 opacity-40" />
        <p>Unable to load dashboard data.</p>
        <button
          onClick={fetchDashboard}
          className="mt-3 inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-xl border border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream hover:bg-earth-50 dark:hover:bg-earth-700 transition-colors"
        >
          Retry
        </button>
      </div>
    )
  }

  const activeOrders = (data.order_summary?.draft ?? 0) +
    (data.order_summary?.pending_approval ?? 0) +
    (data.order_summary?.approved ?? 0) +
    (data.order_summary?.submitted ?? 0) +
    (data.order_summary?.partially_received ?? 0)

  const summaryCards = [
    {
      label: "Total Budget Available",
      value: formatMoney(data.fund_summary?.total_available ?? 0),
      icon: <DollarSign className="w-5 h-5" />,
      color: "text-status-success-600 dark:text-status-success-400",
      onClick: () => onNavigateTab("funds"),
    },
    {
      label: "Active Orders",
      value: String(activeOrders),
      icon: <ShoppingCart className="w-5 h-5" />,
      color: "text-lsc-rose",
      onClick: () => onNavigateTab("orders"),
    },
    {
      label: "Pending Selections",
      value: String(data.selection_summary?.total_pending ?? 0),
      icon: <BookOpen className="w-5 h-5" />,
      color: "text-category-600 dark:text-category-400",
      onClick: () => onNavigateTab("selection"),
    },
    {
      label: "Upcoming Releases",
      value: String(data.release_summary?.upcoming_count ?? 0),
      icon: <Calendar className="w-5 h-5" />,
      color: "text-status-warning-600 dark:text-status-warning-400",
      onClick: () => onNavigateTab("releases"),
    },
  ]

  const visibleQueueItems = computeQueueItems(data)

  const focusToggle = (
    <div className="flex items-center justify-end">
      <button
        type="button"
        role="switch"
        aria-checked={focusMode}
        onClick={toggleFocusMode}
        className="inline-flex items-center gap-2 px-3 py-1.5 text-sm font-medium rounded-xl border border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream hover:bg-earth-50 dark:hover:bg-earth-700/50 focus:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose transition-colors"
      >
        <Focus className="w-4 h-4" aria-hidden="true" />
        <span>Focus mode</span>
        <span
          className={`text-xs font-semibold uppercase tracking-wide ${
            focusMode ? 'text-lsc-rose' : 'text-lsc-dark/60 dark:text-lsc-cream/60'
          }`}
          aria-hidden="true"
        >
          {focusMode ? 'On' : 'Off'}
        </span>
      </button>
    </div>
  )

  if (focusMode) {
    return (
      <div className="space-y-6">
        {focusToggle}
        <div className="space-y-3">
          <h2 className="text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
            Today's queue
          </h2>
          {visibleQueueItems.length === 0 ? (
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/60">
              Nothing needs your attention right now.
            </p>
          ) : (
            <ol className="space-y-2 list-decimal list-inside">
              {visibleQueueItems.map((item) => (
                <li key={`${item.tab}-${item.label}`}>
                  <button
                    type="button"
                    onClick={() => onNavigateTab(item.tab)}
                    className="inline-flex items-center gap-2 text-left text-base font-medium text-lsc-dark dark:text-lsc-cream hover:text-lsc-rose dark:hover:text-lsc-rose focus:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose rounded-lg px-1 py-0.5 transition-colors"
                  >
                    <span>{item.label}</span>
                    <ArrowRight className="w-4 h-4 flex-shrink-0" aria-hidden="true" />
                  </button>
                </li>
              ))}
            </ol>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {focusToggle}
      {/* Summary Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {summaryCards.map((card) => (
          <button
            key={card.label}
            onClick={card.onClick}
            className="text-left border border-lsc-border dark:border-earth-700 rounded-xl p-4 bg-lsc-white dark:bg-earth-800 hover:bg-earth-50 dark:hover:bg-earth-700/50 transition-colors group"
          >
            <div className="flex items-center gap-2 mb-2">
              <span className={card.color}>{card.icon}</span>
              <span className="text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/60 uppercase tracking-wide">
                {card.label}
              </span>
            </div>
            <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">
              {card.value}
            </p>
            <span className="text-xs text-lsc-rose opacity-0 group-hover:opacity-100 focus:opacity-100 transition-opacity inline-flex items-center gap-1 mt-1">
              View details <ArrowRight className="w-3 h-3" />
            </span>
          </button>
        ))}
      </div>

      {/* Fund Overview */}
      {data.fund_summary && (
        <div className="space-y-3">
          <h2 className="text-sm font-semibold text-lsc-dark dark:text-lsc-cream uppercase tracking-wide">
            Fund Overview
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {(() => {
              const fs = data.fund_summary
              const spentPct = fs.total_allocated > 0 ? Math.min((fs.total_spent / fs.total_allocated) * 100, 100) : 0
              const budgetStatus = spentPct >= 90 ? "critical" : spentPct >= 75 ? "warning" : "ok"
              const colors = getStatusColor(budgetStatus)

              return (
                <>
                  <div className={`border rounded-xl p-3 ${colors.border} ${colors.bg}`}>
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">Budget Utilization</span>
                      <span className={`w-2.5 h-2.5 rounded-full flex-shrink-0 ${colors.dot}`} />
                    </div>
                    <p className="text-lg font-bold text-lsc-dark dark:text-lsc-cream">
                      {formatMoney(fs.total_available)}
                    </p>
                    <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60 mb-2">
                      of {formatMoney(fs.total_allocated)} allocated
                    </p>
                    <div className="flex items-center gap-2">
                      <div className="flex-1 h-1.5 bg-earth-100 dark:bg-earth-700 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full transition-all ${
                            budgetStatus === "critical" ? "bg-status-danger-500" : budgetStatus === "warning" ? "bg-status-warning-500" : "bg-status-success-500"
                          }`}
                          style={{ width: `${spentPct}%` }}
                        />
                      </div>
                      <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60">
                        {Math.round(spentPct)}%
                      </span>
                    </div>
                  </div>
                  <div className="border border-lsc-border dark:border-earth-700 rounded-xl p-3 bg-lsc-white dark:bg-earth-800">
                    <span className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">Total Spent</span>
                    <p className="text-lg font-bold text-lsc-dark dark:text-lsc-cream mt-1">{formatMoney(fs.total_spent)}</p>
                  </div>
                  <div className="border border-lsc-border dark:border-earth-700 rounded-xl p-3 bg-lsc-white dark:bg-earth-800">
                    <span className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">Funds with Warnings</span>
                    <p className="text-lg font-bold text-lsc-dark dark:text-lsc-cream mt-1">{fs.funds_with_warnings}</p>
                  </div>
                </>
              )
            })()}
          </div>
        </div>
      )}

      {/* Order Pipeline */}
      {data.order_summary && (
        <div className="space-y-3">
          <h2 className="text-sm font-semibold text-lsc-dark dark:text-lsc-cream uppercase tracking-wide">
            Order Pipeline
          </h2>
          <div className="flex items-center gap-1 overflow-x-auto pb-2">
            {([
              { stage: "draft", count: data.order_summary.draft ?? 0 },
              { stage: "pending", count: data.order_summary.pending_approval ?? 0 },
              { stage: "approved", count: data.order_summary.approved ?? 0 },
              { stage: "submitted", count: data.order_summary.submitted ?? 0 },
              { stage: "received", count: (data.order_summary.partially_received ?? 0) + (data.order_summary.received ?? 0) },
            ] as const).map((stage, index, arr) => {
              const config = pipelineStageConfig[stage.stage] || {
                label: stage.stage.charAt(0).toUpperCase() + stage.stage.slice(1),
                color: "bg-earth-300 dark:bg-earth-500",
                icon: <Package className="w-4 h-4" />,
              }

              return (
                <div key={stage.stage} className="flex items-center gap-1 flex-shrink-0">
                  <div
                    role="group"
                    aria-label={`${config.label}: ${stage.count} ${stage.count === 1 ? 'order' : 'orders'}`}
                    className="flex flex-col items-center gap-1.5 min-w-[80px]"
                  >
                    <div
                      className={`w-12 h-12 rounded-xl flex items-center justify-center text-white ${config.color}`}
                    >
                      <span className="text-lg font-bold" aria-hidden="true">{stage.count}</span>
                    </div>
                    <div className="flex items-center gap-1 text-xs text-lsc-dark/70 dark:text-lsc-cream/60" aria-hidden="true">
                      {config.icon}
                      <span>{config.label}</span>
                    </div>
                  </div>
                  {index < arr.length - 1 && (
                    <ArrowRight className="w-4 h-4 text-lsc-dark/20 dark:text-lsc-cream/20 flex-shrink-0 mx-1" aria-hidden="true" />
                  )}
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Bottleneck Alerts */}
      {(data.bottlenecks?.length ?? 0) > 0 && (
        <div className="space-y-3">
          <h2 className="text-sm font-semibold text-lsc-dark dark:text-lsc-cream uppercase tracking-wide">
            Bottleneck Alerts
          </h2>
          <div
            role="region"
            aria-live="polite"
            aria-label="Bottleneck alerts"
            className="space-y-2"
          >
            {data.bottlenecks.map((alert, index) => {
              const isCritical = alert.severity === "critical" || alert.severity === "error"
              const label = BOTTLENECK_LABELS[alert.type] ?? sentenceCase(alert.type)
              const targetTab = BOTTLENECK_TAB_MAP[alert.type]
              const description = humanizeDescription(alert.description, alert.count)
              return (
                <button
                  key={index}
                  type="button"
                  onClick={() => targetTab && onNavigateTab(targetTab)}
                  className={`w-full text-left flex items-start gap-3 p-3 rounded-xl border transition-colors hover:bg-opacity-80 focus:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose ${
                    isCritical
                      ? "border-status-danger-300 dark:border-status-danger-700 bg-status-danger-50 dark:bg-status-danger-900/10 hover:bg-status-danger-100 dark:hover:bg-status-danger-900/20"
                      : "border-status-warning-300 dark:border-status-warning-700 bg-status-warning-50 dark:bg-status-warning-900/10 hover:bg-status-warning-100 dark:hover:bg-status-warning-900/20"
                  }`}
                >
                  <AlertTriangle
                    className={`w-5 h-5 flex-shrink-0 mt-0.5 ${
                      isCritical ? "text-status-danger-500" : "text-status-warning-500"
                    }`}
                    aria-hidden="true"
                  />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
                      {description}
                    </p>
                    <div className="flex items-center gap-3 mt-1">
                      {alert.count > 0 && (
                        <span
                          className={`inline-flex items-center px-2 py-0.5 text-xs font-medium rounded-full ${
                            isCritical
                              ? "bg-status-danger-100 text-status-danger-700 dark:bg-status-danger-900/30 dark:text-status-danger-300"
                              : "bg-status-warning-100 text-status-warning-700 dark:bg-status-warning-900/30 dark:text-status-warning-300"
                          }`}
                        >
                          {alert.count} affected
                        </span>
                      )}
                      <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60">
                        {label}
                      </span>
                    </div>
                  </div>
                  <ArrowRight
                    className="w-4 h-4 flex-shrink-0 mt-1 text-lsc-dark/40 dark:text-lsc-cream/40"
                    aria-hidden="true"
                  />
                </button>
              )
            })}
          </div>
        </div>
      )}

      {/* Recent Activity */}
      {(data.recent_activity?.length ?? 0) > 0 && (
        <div className="space-y-3">
          <h2 className="text-sm font-semibold text-lsc-dark dark:text-lsc-cream uppercase tracking-wide">
            Recent Activity
          </h2>
          <div className="border border-lsc-border dark:border-earth-700 rounded-xl divide-y divide-lsc-border/50 dark:divide-earth-700/50 bg-lsc-white dark:bg-earth-800 overflow-hidden">
            {data.recent_activity.map((item, index) => {
              const targetTab = ACTIVITY_TAB_MAP[item.entity_type]
              return (
                <button
                  key={item.entity_id ?? index}
                  type="button"
                  onClick={() => targetTab && onNavigateTab(targetTab)}
                  className="w-full text-left flex items-start gap-3 p-3 hover:bg-earth-50 dark:hover:bg-earth-700/50 focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-lsc-rose transition-colors"
                >
                  <span className="mt-0.5 text-lsc-rose" aria-hidden="true">{getActivityIcon(item.entity_type)}</span>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-lsc-dark dark:text-lsc-cream">
                      {item.description}
                    </p>
                    <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60 mt-0.5">
                      {formatTimestamp(item.timestamp)}
                    </p>
                  </div>
                  <ArrowRight
                    className="w-4 h-4 flex-shrink-0 mt-1 text-lsc-dark/40 dark:text-lsc-cream/40"
                    aria-hidden="true"
                  />
                </button>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
