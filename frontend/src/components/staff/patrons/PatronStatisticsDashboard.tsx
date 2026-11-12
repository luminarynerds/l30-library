/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import {
  TrendingUp,
  ChevronUp,
  ChevronDown,
  Loader2,
  Users,
  UserPlus,
  DollarSign,
  AlertTriangle,
  Activity,
  UserX,
  CalendarClock,
  Bell,
  ListFilter,
} from "lucide-react"
import type { LucideIcon } from "lucide-react"
import { PatronStatistics } from "../../../api/api"
import type { CardStatusFilter } from "@/api/staff-api/patrons"
import { useTranslation, formatCurrency } from '@/i18n'

type AlertFilter = "none" | "overdue" | "fines" | "inactive"

export type ExpiringCardBand = Extract<CardStatusFilter, 'expiring_30d' | 'expiring_90d' | 'expired'>

interface PatronStatisticsDashboardProps {
  statistics: PatronStatistics | null
  isLoading: boolean
  isDashboardExpanded: boolean
  onExpandChange: (expanded: boolean) => void
  activeAlertFilter: AlertFilter
  onAlertFilterChange: (filter: AlertFilter) => void
  onAlertClick: (filter: AlertFilter) => void
  onOpenPatron: (patronId: number) => void
  onRemindPatron: (patronId: number) => void
  onExpiringCardsClick?: (band: ExpiringCardBand) => void
  formatDate: (date: string) => string
}

type AlertTone = "danger" | "warning" | "neutral"

const ALERT_TONE: Record<AlertTone, {
  icon: string
  title: string
  badge: string
  cardActive: string
  cardIdle: string
}> = {
  danger: {
    icon: "text-status-danger-500",
    title: "text-status-danger-700 dark:text-status-danger-400",
    badge: "bg-status-danger-100 dark:bg-status-danger-900/40 text-status-danger-700 dark:text-status-danger-400",
    cardActive: "border-status-danger-500 bg-status-danger-50 dark:bg-status-danger-900/20",
    cardIdle: "border-transparent bg-status-danger-50/50 dark:bg-status-danger-900/10 hover:border-status-danger-300 dark:border-status-danger-700 dark:hover:border-status-danger-700",
  },
  warning: {
    icon: "text-status-warning-500",
    title: "text-status-warning-700 dark:text-status-warning-400",
    badge: "bg-status-warning-100 dark:bg-status-warning-900/40 text-status-warning-700 dark:text-status-warning-400",
    cardActive: "border-status-warning-500 bg-status-warning-50 dark:bg-status-warning-900/20",
    cardIdle: "border-transparent bg-status-warning-50/50 dark:bg-status-warning-900/10 hover:border-status-warning-300 dark:border-status-warning-700 dark:hover:border-status-warning-700",
  },
  neutral: {
    icon: "text-lsc-dark/70 dark:text-lsc-cream/70",
    title: "text-lsc-dark/70 dark:text-lsc-cream/70",
    badge: "bg-earth-100 dark:bg-earth-800 text-lsc-dark/70 dark:text-lsc-cream/70",
    cardActive: "border-earth-500 bg-earth-50 dark:bg-earth-900/20",
    cardIdle: "border-transparent bg-earth-50/50 dark:bg-earth-900/10 hover:border-lsc-border dark:border-earth-700 dark:hover:border-earth-700",
  },
}

interface AlertPatronRow {
  id: number
  name: string
  sublabel?: string
}

/**
 * One at-risk alert card. Each listed patron is a direct link (opens their
 * record); overdue/fines rows also expose a Send-reminder action. The footer
 * button still filters the patron list to this cohort (the old whole-card
 * "click to filter" behavior, now an explicit control so the rows above can be
 * individually actionable).
 */
function AtRiskAlertCard({
  tone,
  icon: Icon,
  title,
  count,
  isActive,
  viewAllLabel,
  onViewAll,
  patrons,
  extraCount,
  onOpenPatron,
  onRemindPatron,
}: {
  tone: AlertTone
  icon: LucideIcon
  title: string
  count: number
  isActive: boolean
  viewAllLabel: string
  onViewAll: () => void
  patrons: AlertPatronRow[]
  extraCount: number
  onOpenPatron: (patronId: number) => void
  onRemindPatron?: (patronId: number) => void
}) {
  const tn = ALERT_TONE[tone]
  return (
    <div className={`p-4 rounded-xl border-2 transition-all ${isActive ? tn.cardActive : tn.cardIdle}`}>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <Icon className={`w-4 h-4 ${tn.icon}`} aria-hidden="true" />
          <span className={`font-medium ${tn.title}`}>{title}</span>
        </div>
        <span className={`px-2 py-0.5 text-sm font-bold rounded-full ${tn.badge}`}>{count}</span>
      </div>

      {patrons.length > 0 && (
        <ul className="space-y-0.5 mt-2">
          {patrons.map((p) => (
            <li key={p.id} className="flex items-center gap-1">
              <button
                type="button"
                onClick={() => onOpenPatron(p.id)}
                title={`Open ${p.name}${p.sublabel ? ` ${p.sublabel}` : ""}`}
                className="flex-1 min-w-0 text-left text-xs text-lsc-dark/70 dark:text-lsc-cream/70 truncate rounded px-1 py-0.5 hover:bg-lsc-cream/70 dark:hover:bg-earth-700 hover:text-lsc-dark dark:hover:text-lsc-cream focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose transition-colors"
              >
                <span className="font-medium">{p.name}</span>
                {p.sublabel && <span className="ml-1">{p.sublabel}</span>}
              </button>
              {onRemindPatron && (
                <button
                  type="button"
                  onClick={() => onRemindPatron(p.id)}
                  aria-label={`Send reminder to ${p.name}`}
                  title={`Send reminder to ${p.name}`}
                  className="shrink-0 p-1.5 rounded text-lsc-dark/60 dark:text-lsc-cream/60 hover:bg-lsc-cream/70 dark:hover:bg-earth-700 hover:text-lsc-rose dark:hover:text-lsc-rose-light focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose transition-colors"
                >
                  <Bell className="w-3.5 h-3.5" aria-hidden="true" />
                </button>
              )}
            </li>
          ))}
        </ul>
      )}

      <div className="mt-2 flex items-center gap-3">
        <button
          type="button"
          onClick={onViewAll}
          aria-pressed={isActive}
          className="inline-flex items-center gap-1 text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose rounded px-1 py-0.5 transition-colors"
        >
          <ListFilter className="w-3.5 h-3.5" aria-hidden="true" />
          {isActive ? "Showing in list" : viewAllLabel}
        </button>
        {extraCount > 0 && (
          <span className="text-xs text-lsc-dark/60 dark:text-lsc-cream/60">+{extraCount} more</span>
        )}
      </div>
    </div>
  )
}

export function PatronStatisticsDashboard({
  statistics,
  isLoading,
  isDashboardExpanded,
  onExpandChange,
  activeAlertFilter,
  onAlertFilterChange,
  onAlertClick,
  onOpenPatron,
  onRemindPatron,
  onExpiringCardsClick,
  formatDate,
}: PatronStatisticsDashboardProps) {
  const { t, language } = useTranslation()
  const fmt = (amount: number): string => formatCurrency(amount, language, 'USD')
  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm overflow-hidden">
      {/* Dashboard Header */}
      <button
        onClick={() => onExpandChange(!isDashboardExpanded)}
        className="w-full flex items-center justify-between p-4 hover:bg-lsc-cream/50 dark:hover:bg-lsc-brown/30 transition-colors"
      >
        <div className="flex items-center gap-3">
          <div className="p-2 bg-lsc-rose/10 dark:bg-lsc-rose/20 rounded-lg">
            <TrendingUp className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
          </div>
          <div className="text-left">
            <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
              Patron Statistics Dashboard
            </h2>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
              Overview of patron activity and at-risk alerts
            </p>
          </div>
        </div>
        {isDashboardExpanded ? (
          <ChevronUp className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
        ) : (
          <ChevronDown className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
        )}
      </button>

      {isDashboardExpanded && (
        <div className="border-t border-lsc-border dark:border-earth-700">
          {isLoading ? (
            <div className="p-8 flex items-center justify-center">
              <Loader2 className="w-6 h-6 motion-safe:animate-spin text-lsc-rose dark:text-lsc-rose-light" />
            </div>
          ) : statistics ? (
            <div className="p-4 space-y-6">
              {/* Stats Cards Row */}
              <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-4">
                {/* Total Patrons */}
                <div className="bg-gradient-to-br from-lsc-cream to-white dark:from-earth-700 dark:to-earth-800 rounded-xl p-4">
                  <div className="flex items-center justify-between mb-2">
                    <Users className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
                    <span className="text-xs font-medium text-lsc-rose dark:text-lsc-rose-light">Total</span>
                  </div>
                  <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">
                    {statistics.total_patrons.toLocaleString()}
                  </p>
                  <div className="mt-2 flex items-center gap-2">
                    {/* Mini bar chart showing active vs blocked */}
                    <div className="flex-1 h-2 bg-lsc-border dark:bg-earth-600 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-status-success-500 dark:bg-status-success-400 rounded-full"
                        style={{
                          width: `${statistics.total_patrons > 0
                            ? (statistics.active_patrons / statistics.total_patrons) * 100
                            : 0}%`,
                        }}
                      />
                    </div>
                    <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                      {statistics.active_patrons} active
                    </span>
                  </div>
                  {statistics.blocked_patrons > 0 && (
                    <p className="mt-1 text-xs text-status-danger-500 dark:text-status-danger-400">
                      {statistics.blocked_patrons} blocked
                    </p>
                  )}
                </div>

                {/* New Patrons */}
                <div className="bg-gradient-to-br from-green-50 to-white dark:from-green-900/20 dark:to-earth-800 rounded-xl p-4">
                  <div className="flex items-center justify-between mb-2">
                    <UserPlus className="w-5 h-5 text-status-success-500 dark:text-status-success-400" />
                    <span className="text-xs font-medium text-status-success-600 dark:text-status-success-400">New</span>
                  </div>
                  <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">
                    {statistics.new_this_week}
                  </p>
                  <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">This week</p>
                  <div className="mt-2 flex items-center gap-1">
                    {/* Mini trend indicator */}
                    <div className="flex items-end gap-0.5 h-4">
                      {[0.4, 0.6, 0.3, 0.7, 0.5, 0.9, 1].map((h, i) => (
                        <div
                          key={i}
                          className="w-1 bg-status-success-400 dark:bg-status-success-500 rounded-t"
                          style={{ height: `${h * 100}%` }}
                        />
                      ))}
                    </div>
                    <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 ml-2">
                      {statistics.new_this_month} this month
                    </span>
                  </div>
                </div>

                {/* Outstanding Fines */}
                <div className="bg-gradient-to-br from-status-warning-50 to-white dark:from-status-warning-900/20 dark:to-earth-800 rounded-xl p-4">
                  <div className="flex items-center justify-between mb-2">
                    <DollarSign className="w-5 h-5 text-status-warning-500 dark:text-status-warning-400" />
                    <span className="text-xs font-medium text-status-warning-600 dark:text-status-warning-400">Fines</span>
                  </div>
                  <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">
                    {fmt(Number(statistics.total_fines_outstanding))}
                  </p>
                  <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Outstanding balance</p>
                  {/* Visual representation */}
                  <div className="mt-2 flex gap-0.5">
                    {Array.from({ length: 5 }).map((_, i) => (
                      <div
                        key={i}
                        className={`h-1.5 flex-1 rounded ${
                          i < Math.min(5, Math.ceil(Number(statistics.total_fines_outstanding) / 50))
                            ? "bg-status-warning-400 dark:bg-status-warning-500"
                            : "bg-lsc-border dark:bg-earth-600"
                        }`}
                      />
                    ))}
                  </div>
                </div>

                {/* Overdue Items */}
                <div className="bg-gradient-to-br from-red-50 to-white dark:from-red-900/20 dark:to-earth-800 rounded-xl p-4">
                  <div className="flex items-center justify-between mb-2">
                    <AlertTriangle className="w-5 h-5 text-status-danger-500 dark:text-status-danger-400" />
                    <span className="text-xs font-medium text-status-danger-600 dark:text-status-danger-400">Overdue</span>
                  </div>
                  <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">
                    {statistics.total_overdue_items}
                  </p>
                  <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Items past due</p>
                  {/* Progress ring indicator */}
                  <div className="mt-2 flex items-center gap-2">
                    <svg className="w-6 h-6" viewBox="0 0 24 24">
                      <circle
                        cx="12"
                        cy="12"
                        r="10"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2"
                        className="text-lsc-border dark:text-earth-300"
                      />
                      <circle
                        cx="12"
                        cy="12"
                        r="10"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2"
                        strokeDasharray={`${Math.min(100, statistics.total_overdue_items * 2) * 0.628} 62.8`}
                        strokeLinecap="round"
                        className="text-status-danger-500 dark:text-status-danger-400"
                        transform="rotate(-90 12 12)"
                      />
                    </svg>
                    <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Needs attention</span>
                  </div>
                </div>

                {/* At-Risk Summary */}
                <div className="bg-gradient-to-br from-category-50 to-white dark:from-category-900/20 dark:to-earth-800 rounded-xl p-4 col-span-2 md:col-span-1">
                  <div className="flex items-center justify-between mb-2">
                    <Activity className="w-5 h-5 text-category-500 dark:text-category-400" />
                    <span className="text-xs font-medium text-category-600 dark:text-category-400">At Risk</span>
                  </div>
                  <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">
                    {statistics.at_risk_counts.patrons_with_many_overdue +
                      statistics.at_risk_counts.patrons_with_high_fines +
                      statistics.at_risk_counts.inactive_patrons}
                  </p>
                  <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Patrons need attention</p>
                  <div className="mt-2 flex items-center gap-2 flex-wrap">
                    <span className="text-xs px-1.5 py-0.5 bg-status-danger-100 dark:bg-status-danger-900/30 text-status-danger-600 dark:text-status-danger-400 rounded">
                      {statistics.at_risk_counts.patrons_with_many_overdue} overdue
                    </span>
                    <span className="text-xs px-1.5 py-0.5 bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-600 dark:text-status-warning-400 rounded">
                      {statistics.at_risk_counts.patrons_with_high_fines} fines
                    </span>
                    <span className="text-xs px-1.5 py-0.5 bg-earth-100 dark:bg-earth-800 text-lsc-dark/70 dark:text-lsc-cream/70 rounded">
                      {statistics.at_risk_counts.inactive_patrons} inactive
                    </span>
                  </div>
                </div>
              </div>

              {/* Expiring / Lapsed Cards Tile */}
              {statistics.expiring_cards_counts && (
                statistics.expiring_cards_counts.expiring_within_30d > 0 ||
                statistics.expiring_cards_counts.expiring_within_90d > 0 ||
                statistics.expiring_cards_counts.expired > 0
              ) && (
                <div className="border-t border-lsc-border dark:border-earth-700 pt-4">
                  <h3 className="font-medium text-lsc-dark dark:text-lsc-cream mb-3 flex items-center gap-2">
                    <CalendarClock className="w-4 h-4 text-status-info-500 dark:text-status-info-400" />
                    {t('components.staff.patronStatisticsDashboard.expiringCardsTitle')}
                    <span className="text-xs font-normal text-lsc-dark/70 dark:text-lsc-cream/70">
                      {t('components.staff.patronStatisticsDashboard.expiringCardsNestedNote')}
                    </span>
                  </h3>
                  <div
                    className="grid grid-cols-1 md:grid-cols-3 gap-4"
                    data-testid="expiring-cards-tile"
                  >
                    <button
                      type="button"
                      onClick={() => onExpiringCardsClick?.("expiring_30d")}
                      disabled={!onExpiringCardsClick}
                      className="text-left p-4 rounded-xl border-2 border-transparent bg-status-warning-50/50 dark:bg-status-warning-900/10 hover:border-status-warning-300 dark:hover:border-status-warning-700 transition-all disabled:cursor-default"
                      data-testid="expiring-cards-tile-30d"
                    >
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-medium text-status-warning-700 dark:text-status-warning-400">
                          {t('components.staff.patronStatisticsDashboard.expiringWithin30d')}
                        </span>
                        <span className="px-2 py-0.5 text-sm font-bold bg-status-warning-100 dark:bg-status-warning-900/40 text-status-warning-700 dark:text-status-warning-400 rounded-full">
                          {statistics.expiring_cards_counts.expiring_within_30d}
                        </span>
                      </div>
                      <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                        {t('components.staff.patronStatisticsDashboard.expiringClickHint')}
                      </p>
                    </button>

                    <button
                      type="button"
                      onClick={() => onExpiringCardsClick?.("expiring_90d")}
                      disabled={!onExpiringCardsClick}
                      className="text-left p-4 rounded-xl border-2 border-transparent bg-status-info-50/50 dark:bg-status-info-900/10 hover:border-status-info-300 dark:hover:border-status-info-700 transition-all disabled:cursor-default"
                      data-testid="expiring-cards-tile-90d"
                    >
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-medium text-status-info-700 dark:text-status-info-400">
                          {t('components.staff.patronStatisticsDashboard.expiringWithin90d')}
                        </span>
                        <span className="px-2 py-0.5 text-sm font-bold bg-status-info-100 dark:bg-status-info-900/40 text-status-info-700 dark:text-status-info-400 rounded-full">
                          {statistics.expiring_cards_counts.expiring_within_90d}
                        </span>
                      </div>
                      <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                        {t('components.staff.patronStatisticsDashboard.expiringClickHint')}
                      </p>
                    </button>

                    <button
                      type="button"
                      onClick={() => onExpiringCardsClick?.("expired")}
                      disabled={!onExpiringCardsClick}
                      className="text-left p-4 rounded-xl border-2 border-transparent bg-status-danger-50/50 dark:bg-status-danger-900/10 hover:border-status-danger-300 dark:hover:border-status-danger-700 transition-all disabled:cursor-default"
                      data-testid="expiring-cards-tile-expired"
                    >
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-medium text-status-danger-700 dark:text-status-danger-400">
                          {t('components.staff.patronStatisticsDashboard.expiredCards')}
                        </span>
                        <span className="px-2 py-0.5 text-sm font-bold bg-status-danger-100 dark:bg-status-danger-900/40 text-status-danger-700 dark:text-status-danger-400 rounded-full">
                          {statistics.expiring_cards_counts.expired}
                        </span>
                      </div>
                      <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                        {t('components.staff.patronStatisticsDashboard.expiringClickHint')}
                      </p>
                    </button>
                  </div>
                </div>
              )}

              {/* At-Risk Alerts Panel */}
              {(statistics.at_risk_counts.patrons_with_many_overdue > 0 ||
                statistics.at_risk_counts.patrons_with_high_fines > 0 ||
                statistics.at_risk_counts.inactive_patrons > 0) && (
                <div className="border-t border-lsc-border dark:border-earth-700 pt-4">
                  <h3 className="font-medium text-lsc-dark dark:text-lsc-cream mb-3 flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4 text-status-warning-500" />
                    At-Risk Patron Alerts
                    {activeAlertFilter !== "none" && (
                      <button
                        onClick={() => onAlertFilterChange("none")}
                        className="ml-2 text-xs px-2 py-0.5 bg-lsc-cream dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70 rounded hover:bg-lsc-border dark:hover:bg-earth-600"
                      >
                        Clear filter
                      </button>
                    )}
                  </h3>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    {/* Patrons with Many Overdue Items */}
                    <AtRiskAlertCard
                      tone="danger"
                      icon={AlertTriangle}
                      title="3+ Overdue Items"
                      count={statistics.at_risk_counts.patrons_with_many_overdue}
                      isActive={activeAlertFilter === "overdue"}
                      viewAllLabel={t('components.staff.patronStatisticsDashboard.clickToFilterList')}
                      onViewAll={() => onAlertClick("overdue")}
                      patrons={statistics.patrons_with_many_overdue.slice(0, 3).map((patron) => ({
                        id: patron.id,
                        name: `${patron.first_name} ${patron.last_name}`,
                        sublabel: `- ${patron.overdue_count} items`,
                      }))}
                      extraCount={Math.max(0, statistics.patrons_with_many_overdue.length - 3)}
                      onOpenPatron={onOpenPatron}
                      onRemindPatron={onRemindPatron}
                    />

                    {/* Patrons with High Fines */}
                    <AtRiskAlertCard
                      tone="warning"
                      icon={DollarSign}
                      title="Fines Over $25"
                      count={statistics.at_risk_counts.patrons_with_high_fines}
                      isActive={activeAlertFilter === "fines"}
                      viewAllLabel={t('components.staff.patronStatisticsDashboard.clickToFilterList2')}
                      onViewAll={() => onAlertClick("fines")}
                      patrons={statistics.patrons_with_high_fines.slice(0, 3).map((patron) => ({
                        id: patron.id,
                        name: `${patron.first_name} ${patron.last_name}`,
                        sublabel: `- ${fmt(Number(patron.fines_balance))}`,
                      }))}
                      extraCount={Math.max(0, statistics.patrons_with_high_fines.length - 3)}
                      onOpenPatron={onOpenPatron}
                      onRemindPatron={onRemindPatron}
                    />

                    {/* Inactive Patrons */}
                    <AtRiskAlertCard
                      tone="neutral"
                      icon={UserX}
                      title="Inactive 90+ Days"
                      count={statistics.at_risk_counts.inactive_patrons}
                      isActive={activeAlertFilter === "inactive"}
                      viewAllLabel={t('components.staff.patronStatisticsDashboard.clickToFilterList3')}
                      onViewAll={() => onAlertClick("inactive")}
                      patrons={statistics.inactive_patrons.slice(0, 3).map((patron) => ({
                        id: patron.id,
                        name: `${patron.first_name} ${patron.last_name}`,
                        ...(patron.last_activity_date
                          ? { sublabel: `- Last active ${formatDate(patron.last_activity_date)}` }
                          : {}),
                      }))}
                      extraCount={Math.max(0, statistics.inactive_patrons.length - 3)}
                      onOpenPatron={onOpenPatron}
                    />
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="p-8 text-center text-lsc-dark/70 dark:text-lsc-cream/70">
              Unable to load statistics
            </div>
          )}
        </div>
      )}
    </div>
  )
}
