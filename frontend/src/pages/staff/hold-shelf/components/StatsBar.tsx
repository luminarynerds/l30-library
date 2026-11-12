/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Navigation, UserX } from "lucide-react"
import type { PullListResponse } from "../types"

interface StatsBarProps {
  pullList: PullListResponse
  onWayCount: number
  noShowCount: number
}

export function StatsBar({ pullList, onWayCount, noShowCount }: StatsBarProps) {
  const expiringTodayCount = pullList.locations.reduce(
    (sum, loc) =>
      sum + loc.items.filter((item) => item.days_until_expiry === 0).length,
    0
  )

  const criticalCount = pullList.locations.reduce(
    (sum, loc) =>
      sum +
      loc.items.filter(
        (item) => item.days_until_expiry !== null && item.days_until_expiry <= 1
      ).length,
    0
  )

  return (
    <div className="mb-6 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
      <div className="rounded-lg bg-lsc-white dark:bg-earth-800 p-4 border border-lsc-border dark:border-earth-700">
        <div className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Total Items</div>
        <div className="text-2xl font-bold mt-1">{pullList.total_items}</div>
      </div>
      <div className="rounded-lg bg-lsc-white dark:bg-earth-800 p-4 border border-lsc-border dark:border-earth-700">
        <div className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Locations</div>
        <div className="text-2xl font-bold mt-1">{pullList.locations.length}</div>
      </div>
      <div className="rounded-lg bg-lsc-white dark:bg-earth-800 p-4 border border-lsc-border dark:border-earth-700">
        <div className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Expiring Today</div>
        <div className="text-2xl font-bold mt-1 text-status-danger-600">{expiringTodayCount}</div>
      </div>
      <div className="rounded-lg bg-lsc-white dark:bg-earth-800 p-4 border border-lsc-border dark:border-earth-700">
        <div className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Critical (&le;1 day)</div>
        <div className="text-2xl font-bold mt-1 text-status-danger-600">{criticalCount}</div>
      </div>
      <div className="rounded-lg bg-lsc-white dark:bg-earth-800 p-4 border border-lsc-border dark:border-earth-700">
        <div className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 flex items-center gap-1">
          <Navigation className="h-3 w-3" /> On Way
        </div>
        <div className="text-2xl font-bold mt-1 text-lsc-rose dark:text-lsc-rose-light">{onWayCount}</div>
      </div>
      <div className="rounded-lg bg-lsc-white dark:bg-earth-800 p-4 border border-lsc-border dark:border-earth-700">
        <div className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 flex items-center gap-1">
          <UserX className="h-3 w-3" /> No-Shows
        </div>
        <div className="text-2xl font-bold mt-1 text-status-warning-600">{noShowCount}</div>
      </div>
    </div>
  )
}
