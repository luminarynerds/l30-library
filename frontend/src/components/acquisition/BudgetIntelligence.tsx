/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect } from "react"
import {
  Loader2,
  DollarSign,
  TrendingUp,
  AlertTriangle,
  Calendar,
  BarChart3,
} from "lucide-react"
import toast from "react-hot-toast"
import { fetchApi } from '@/api/fetchApi'
import { t, getCurrentLocale } from '@/i18n'

interface FY2025Comparison {
  fy2025_allocated: number
  fy2025_spent: number
  allocation_change_pct: number
  spending_change_pct: number | null
}

interface FundIntelligence {
  fund_id: number
  fund_code: string
  fund_name: string
  fiscal_year: number
  allocated_amount: number
  spent_amount: number
  encumbered_amount: number
  available_amount: number
  spending_velocity: number
  projected_exhaustion_date: string | null
  months_remaining: number | null
  warning_level: "ok" | "warning" | "critical"
  fy2025_comparison: FY2025Comparison | null
}

interface FYComparison {
  fund_name: string
  fy2025_allocated: number
  fy2025_spent: number
  fy2026_allocated: number
  fy2026_spent: number
}

interface IntelligenceResponse {
  funds: FundIntelligence[]
  alerts: string[]
  total_allocated: number
  total_spent: number
  total_available: number
}

interface Props {
  token: string
  formatMoney: (n: number) => string
}

export default function BudgetIntelligence({ token, formatMoney }: Props) {
  const [data, setData] = useState<IntelligenceResponse | null>(null)
  const [loading, setLoading] = useState(true)

  const fetchIntelligence = async () => {
    setLoading(true)
    try {
      const json = await fetchApi('/acquisition/funds/intelligence')
      setData(json)
    } catch (err) {
      toast.error(err instanceof Error ? err.message : t('toast.acquisition.failedToLoadBudgetIntelligence'))
    } finally {
      setLoading(false)
    }
  }


  useEffect(() => {
    fetchIntelligence()

  }, [token])

  const formatDate = (dateStr: string | null): string => {
    if (!dateStr) return "N/A"
    const date = new Date(dateStr)
    return date.toLocaleDateString(getCurrentLocale(), { month: "short", day: "numeric", year: "numeric" })
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case "critical":
        return {
          badge: "bg-status-danger-100 text-status-danger-700 dark:bg-status-danger-900/30 dark:text-status-danger-300",
          bar: "bg-status-danger-500",
          border: "border-status-danger-300 dark:border-status-danger-700",
          bg: "bg-status-danger-50 dark:bg-status-danger-900/10",
        }
      case "warning":
        return {
          badge: "bg-status-warning-100 text-status-warning-700 dark:bg-status-warning-900/30 dark:text-status-warning-300",
          bar: "bg-status-warning-500",
          border: "border-status-warning-300 dark:border-status-warning-700",
          bg: "bg-status-warning-50 dark:bg-status-warning-900/10",
        }
      default:
        return {
          badge: "bg-status-success-100 text-status-success-700 dark:bg-status-success-900/30 dark:text-status-success-300",
          bar: "bg-status-success-500",
          border: "border-lsc-border dark:border-earth-700",
          bg: "bg-lsc-white dark:bg-earth-800",
        }
    }
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
        <DollarSign className="w-10 h-10 mx-auto mb-2 opacity-40" />
        <p>Unable to load budget intelligence data.</p>
      </div>
    )
  }

  const alertFunds = data.funds.filter((f) => f.warning_level === "critical" || f.warning_level === "warning")

  const fyComparison: FYComparison[] = data.funds
    .filter((f) => f.fy2025_comparison)
    .map((f) => ({
      fund_name: f.fund_name,
      fy2025_allocated: f.fy2025_comparison!.fy2025_allocated,
      fy2025_spent: f.fy2025_comparison!.fy2025_spent,
      fy2026_allocated: f.allocated_amount,
      fy2026_spent: f.spent_amount,
    }))

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
          Budget Intelligence
        </h3>
        <button
          onClick={fetchIntelligence}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-xl border border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream hover:bg-earth-50 dark:hover:bg-earth-700 transition-colors"
        >
          <TrendingUp className="w-3.5 h-3.5" />
          Refresh
        </button>
      </div>

      {alertFunds.length > 0 && (
        <div className="space-y-2">
          {alertFunds.map((fund) => {
            const colors = getStatusColor(fund.warning_level)
            return (
              <div
                key={`alert-${fund.fund_id}`}
                className={`flex items-start gap-3 p-3 rounded-xl border ${colors.border} ${colors.bg}`}
              >
                <AlertTriangle
                  className={`w-5 h-5 flex-shrink-0 mt-0.5 ${
                    fund.warning_level === "critical"
                      ? "text-status-danger-500"
                      : "text-status-warning-500"
                  }`}
                />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
                    {fund.fund_name} — {fund.warning_level === "critical" ? "Critical" : "Warning"}
                  </p>
                  <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60 mt-0.5">
                    {formatMoney(fund.available_amount)} remaining at {formatMoney(fund.spending_velocity)}/month.
                    {fund.projected_exhaustion_date
                      ? ` Projected exhaustion: ${formatDate(fund.projected_exhaustion_date)}.`
                      : " Exhaustion date unavailable."}
                  </p>
                </div>
              </div>
            )
          })}
        </div>
      )}

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-lsc-border dark:border-earth-700">
              <th className="text-left py-2 px-3 font-medium text-lsc-dark/70 dark:text-lsc-cream/60 text-xs uppercase tracking-wide">
                Fund
              </th>
              <th className="text-right py-2 px-3 font-medium text-lsc-dark/70 dark:text-lsc-cream/60 text-xs uppercase tracking-wide">
                Allocated
              </th>
              <th className="text-right py-2 px-3 font-medium text-lsc-dark/70 dark:text-lsc-cream/60 text-xs uppercase tracking-wide">
                Spent
              </th>
              <th className="text-right py-2 px-3 font-medium text-lsc-dark/70 dark:text-lsc-cream/60 text-xs uppercase tracking-wide">
                Available
              </th>
              <th className="text-right py-2 px-3 font-medium text-lsc-dark/70 dark:text-lsc-cream/60 text-xs uppercase tracking-wide">
                Velocity
              </th>
              <th className="text-left py-2 px-3 font-medium text-lsc-dark/70 dark:text-lsc-cream/60 text-xs uppercase tracking-wide">
                Exhaustion
              </th>
              <th className="text-center py-2 px-3 font-medium text-lsc-dark/70 dark:text-lsc-cream/60 text-xs uppercase tracking-wide">
                Status
              </th>
              <th className="py-2 px-3 font-medium text-lsc-dark/70 dark:text-lsc-cream/60 text-xs uppercase tracking-wide w-32">
                Burn Rate
              </th>
            </tr>
          </thead>
          <tbody>
            {data.funds.map((fund) => {
              const colors = getStatusColor(fund.warning_level)
              const burnRate = fund.allocated_amount > 0 ? fund.spent_amount / fund.allocated_amount : 0
              const burnPct = Math.min(burnRate * 100, 100)

              return (
                <tr
                  key={fund.fund_id}
                  className="border-b border-lsc-border/50 dark:border-earth-700/50 hover:bg-earth-50 dark:hover:bg-earth-700/30 transition-colors"
                >
                  <td className="py-2.5 px-3 font-medium text-lsc-dark dark:text-lsc-cream">
                    {fund.fund_name}
                  </td>
                  <td className="py-2.5 px-3 text-right text-lsc-dark dark:text-lsc-cream">
                    {formatMoney(fund.allocated_amount)}
                  </td>
                  <td className="py-2.5 px-3 text-right text-lsc-dark dark:text-lsc-cream">
                    {formatMoney(fund.spent_amount)}
                  </td>
                  <td className="py-2.5 px-3 text-right font-medium text-lsc-dark dark:text-lsc-cream">
                    {formatMoney(fund.available_amount)}
                  </td>
                  <td className="py-2.5 px-3 text-right text-lsc-dark/70 dark:text-lsc-cream/70">
                    {formatMoney(fund.spending_velocity)}/mo
                  </td>
                  <td className="py-2.5 px-3 text-lsc-dark/70 dark:text-lsc-cream/70">
                    <span className="inline-flex items-center gap-1">
                      <Calendar className="w-3.5 h-3.5" />
                      {formatDate(fund.projected_exhaustion_date)}
                    </span>
                  </td>
                  <td className="py-2.5 px-3 text-center">
                    <span
                      className={`inline-flex items-center px-2 py-0.5 text-xs font-medium rounded-full ${colors.badge}`}
                    >
                      {fund.warning_level.charAt(0).toUpperCase() + fund.warning_level.slice(1)}
                    </span>
                  </td>
                  <td className="py-2.5 px-3">
                    <div className="flex items-center gap-2">
                      <div className="flex-1 h-2 bg-earth-100 dark:bg-earth-700 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full transition-all ${colors.bar}`}
                          style={{ width: `${burnPct}%` }}
                        />
                      </div>
                      <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60 w-8 text-right">
                        {Math.round(burnPct)}%
                      </span>
                    </div>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {fyComparison.length > 0 && (
        <div className="space-y-3">
          <h4 className="text-sm font-semibold text-lsc-dark dark:text-lsc-cream flex items-center gap-2">
            <BarChart3 className="w-4 h-4 text-lsc-rose" />
            FY2025 vs FY2026 Comparison
          </h4>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-lsc-border dark:border-earth-700">
                  <th className="text-left py-2 px-3 font-medium text-lsc-dark/70 dark:text-lsc-cream/60 text-xs uppercase tracking-wide">
                    Fund
                  </th>
                  <th className="text-right py-2 px-3 font-medium text-lsc-dark/70 dark:text-lsc-cream/60 text-xs uppercase tracking-wide">
                    FY25 Allocated
                  </th>
                  <th className="text-right py-2 px-3 font-medium text-lsc-dark/70 dark:text-lsc-cream/60 text-xs uppercase tracking-wide">
                    FY25 Spent
                  </th>
                  <th className="text-right py-2 px-3 font-medium text-lsc-dark/70 dark:text-lsc-cream/60 text-xs uppercase tracking-wide">
                    FY26 Allocated
                  </th>
                  <th className="text-right py-2 px-3 font-medium text-lsc-dark/70 dark:text-lsc-cream/60 text-xs uppercase tracking-wide">
                    FY26 Spent
                  </th>
                  <th className="text-right py-2 px-3 font-medium text-lsc-dark/70 dark:text-lsc-cream/60 text-xs uppercase tracking-wide">
                    Change
                  </th>
                </tr>
              </thead>
              <tbody>
                {fyComparison.map((row) => {
                  const allocChange =
                    (row.fy2025_allocated ?? 0) > 0
                      ? (((row.fy2026_allocated ?? 0) - (row.fy2025_allocated ?? 0)) / (row.fy2025_allocated ?? 1)) * 100
                      : 0
                  const changeColor =
                    allocChange > 0
                      ? "text-status-success-600 dark:text-status-success-400"
                      : allocChange < 0
                        ? "text-status-danger-600 dark:text-status-danger-400"
                        : "text-lsc-dark/70 dark:text-lsc-cream/60"

                  return (
                    <tr
                      key={row.fund_name}
                      className="border-b border-lsc-border/50 dark:border-earth-700/50"
                    >
                      <td className="py-2.5 px-3 font-medium text-lsc-dark dark:text-lsc-cream">
                        {row.fund_name}
                      </td>
                      <td className="py-2.5 px-3 text-right text-lsc-dark/70 dark:text-lsc-cream/70">
                        {formatMoney(row.fy2025_allocated)}
                      </td>
                      <td className="py-2.5 px-3 text-right text-lsc-dark/70 dark:text-lsc-cream/70">
                        {formatMoney(row.fy2025_spent)}
                      </td>
                      <td className="py-2.5 px-3 text-right text-lsc-dark dark:text-lsc-cream">
                        {formatMoney(row.fy2026_allocated)}
                      </td>
                      <td className="py-2.5 px-3 text-right text-lsc-dark dark:text-lsc-cream">
                        {formatMoney(row.fy2026_spent)}
                      </td>
                      <td className={`py-2.5 px-3 text-right font-medium ${changeColor}`}>
                        {allocChange > 0 ? "+" : ""}
                        {allocChange.toFixed(1)}%
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
