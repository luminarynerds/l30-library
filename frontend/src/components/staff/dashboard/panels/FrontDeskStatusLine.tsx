/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useQuery } from "@tanstack/react-query"
import { useAuth } from "@/contexts/AuthContext"
import { getDeskState } from "@/api/staff-api/desk-state"

type Level = "urgent" | "attention"

interface StatusItem {
  text: string
  level: Level
}

const HOLDS_PULL_THRESHOLD = 20

function holdsExpireLabel(count: number, when: string): string {
  const noun = count === 1 ? "hold" : "holds"
  const verb = count === 1 ? "expires" : "expire"
  return `${count} ${noun} ${verb} ${when}`
}

export default function FrontDeskStatusLine() {
  const { token } = useAuth()
  const { data: state } = useQuery({
    queryKey: ["desk-state"],
    queryFn: () => getDeskState(token!),
    enabled: !!token,
    staleTime: 60_000,
  })

  if (!state) return null

  const items: StatusItem[] = []
  if (state.holds_expiring_today > 0) {
    items.push({ text: holdsExpireLabel(state.holds_expiring_today, "today"), level: "urgent" })
  }
  if (state.holds_to_pull > HOLDS_PULL_THRESHOLD) {
    items.push({ text: `${state.holds_to_pull} holds to pull`, level: "attention" })
  }
  if (state.cash_drawer_open) {
    items.push({ text: "Cash drawer is open", level: "attention" })
  }

  if (items.length === 0) return null

  return (
    <div role="status" aria-label="Front desk alerts" className="flex flex-wrap gap-2">
      {items.map(item => (
        <span
          key={item.text}
          className={
            item.level === "urgent"
              ? "inline-flex items-center rounded-full px-3 py-1 text-sm font-medium bg-status-warning-50 text-status-warning-700 ring-1 ring-status-warning-300 dark:bg-status-warning-900/30 dark:text-status-warning-300 dark:ring-status-warning-600"
              : "inline-flex items-center rounded-full px-3 py-1 text-sm font-medium bg-earth-100 text-lsc-dark/80 ring-1 ring-earth-300 dark:bg-earth-700 dark:text-lsc-cream/80 dark:ring-earth-600"
          }
        >
          {item.text}
        </span>
      ))}
    </div>
  )
}
