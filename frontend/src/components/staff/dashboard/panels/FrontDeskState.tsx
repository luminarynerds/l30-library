/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useQuery } from "@tanstack/react-query"
import { useAuth } from "@/contexts/AuthContext"
import { getDeskState } from "@/api/staff-api/desk-state"

interface Stat {
  label: string
  value: string | number
  sub: string | null
  warn: boolean
  success: boolean
}

export default function FrontDeskStatePanel() {
  const { token } = useAuth()
  const { data: state } = useQuery({
    queryKey: ["desk-state"],
    queryFn: () => getDeskState(token!),
    enabled: !!token,
    staleTime: 60_000,
  })

  if (!state) return null

  const stats: Stat[] = [
    {
      label: "Holds to pull",
      value: state.holds_to_pull,
      sub: state.holds_expiring_today > 0 ? `${state.holds_expiring_today} expire today` : null,
      warn: state.holds_expiring_today > 0,
      success: false,
    },
    {
      label: "Book drop",
      value: state.book_drop_estimate > 0 ? `~${state.book_drop_estimate}` : "--",
      sub: state.book_drop_last_cleared ? `Last cleared ${state.book_drop_last_cleared}` : null,
      warn: false,
      success: false,
    },
    {
      label: "Holds shelf",
      value: state.holds_shelf_count,
      sub: state.holds_expiring_tonight > 0 ? `${state.holds_expiring_tonight} expire tonight` : null,
      warn: state.holds_expiring_tonight > 0,
      success: false,
    },
    {
      label: "Cash drawer",
      value: state.cash_drawer_open ? "Open" : "Closed",
      sub: state.cash_drawer_open ? `$${state.cash_drawer_total.toFixed(2)}` : null,
      warn: false,
      success: state.cash_drawer_open,
    },
  ]

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
      {stats.map(s => (
        <div
          key={s.label}
          className={`bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm ${
            s.warn ? "ring-1 ring-status-warning-400/50" : ""
          }`}
        >
          <p className="text-xs text-lsc-dark/60 dark:text-lsc-cream/70 mb-1">{s.label}</p>
          <p
            className={`text-xl font-semibold ${
              s.warn
                ? "text-status-warning-600 dark:text-status-warning-400"
                : s.success
                  ? "text-status-success-600 dark:text-status-success-400"
                  : "text-lsc-dark dark:text-lsc-cream"
            }`}
          >
            {s.value}
          </p>
          {s.sub && (
            <p
              className={`text-[11px] mt-1 ${
                s.warn
                  ? "text-status-warning-600/80 dark:text-status-warning-400/80 font-medium"
                  : "text-lsc-dark/50 dark:text-lsc-cream/50"
              }`}
            >
              {s.sub}
            </p>
          )}
        </div>
      ))}
    </div>
  )
}
