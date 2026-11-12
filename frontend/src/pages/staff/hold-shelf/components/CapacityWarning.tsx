/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { AlertTriangle } from "lucide-react"
import type { CapacityStatus } from "../types"

interface CapacityWarningProps {
  capacityStatus: CapacityStatus
}

export function CapacityWarning({ capacityStatus }: CapacityWarningProps) {
  if (!capacityStatus.is_over_warning) return null

  return (
    <div className="mb-6 rounded-lg bg-status-warning-50 dark:bg-status-warning-900/20 border border-status-warning-200 dark:border-status-warning-800 p-4 flex items-start gap-3">
      <AlertTriangle className="h-5 w-5 text-status-warning-600 mt-0.5" />
      <div>
        <h3 className="font-serif font-semibold text-status-warning-900 dark:text-status-warning-200">
          Hold Shelf Capacity Warning
        </h3>
        <p className="text-sm text-status-warning-800 dark:text-status-warning-300 mt-1">
          {capacityStatus.branch_name} is at {capacityStatus.capacity_percentage}% capacity
          ({capacityStatus.ready_holds_count} of {capacityStatus.capacity_limit} items).
          {(capacityStatus.expiring_today_count ?? 0) > 0 &&
            ` ${capacityStatus.expiring_today_count} expire today.`}
          {(capacityStatus.expiring_tomorrow_count ?? 0) > 0 &&
            ` ${capacityStatus.expiring_tomorrow_count} expire tomorrow.`}
        </p>
      </div>
    </div>
  )
}
