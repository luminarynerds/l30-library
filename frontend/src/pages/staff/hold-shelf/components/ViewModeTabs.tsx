/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { MapPin, Clock, AlertTriangle } from "lucide-react"
import type { ViewMode } from "../types"

interface ViewModeTabsProps {
  viewMode: ViewMode
  onViewModeChange: (mode: ViewMode) => void
  expiredCount?: number
}

export function ViewModeTabs({ viewMode, onViewModeChange, expiredCount }: ViewModeTabsProps) {
  return (
    <div className="mb-6 flex gap-2 border-b border-lsc-border dark:border-earth-700">
      <button
        onClick={() => onViewModeChange("pull-list")}
        className={`px-4 py-2 -mb-px font-medium transition-colors ${
          viewMode === "pull-list"
            ? "border-b-2 border-lsc-rose text-lsc-rose dark:text-lsc-rose-light"
            : "text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-earth-900"
        }`}
      >
        <span className="flex items-center gap-2">
          <MapPin className="h-4 w-4" />
          Hold Shelf
        </span>
      </button>
      <button
        onClick={() => onViewModeChange("expiring")}
        className={`px-4 py-2 -mb-px font-medium transition-colors ${
          viewMode === "expiring"
            ? "border-b-2 border-status-danger-600 text-status-danger-600"
            : "text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-earth-900"
        }`}
      >
        <span className="flex items-center gap-2">
          <Clock className="h-4 w-4" />
          Expiring Soon
        </span>
      </button>
      <button
        onClick={() => onViewModeChange("expired")}
        className={`px-4 py-2 -mb-px font-medium transition-colors ${
          viewMode === "expired"
            ? "border-b-2 border-status-danger-800 text-status-danger-800"
            : "text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-earth-900"
        }`}
      >
        <span className="flex items-center gap-2">
          <AlertTriangle className="h-4 w-4" />
          Expired
          {expiredCount !== undefined && expiredCount > 0 && (
            <span className="ml-1 px-1.5 py-0.5 text-xs font-bold rounded-full bg-status-danger-100 dark:bg-status-danger-900/30 text-status-danger-700 dark:text-status-danger-300">
              {expiredCount}
            </span>
          )}
        </span>
      </button>
    </div>
  )
}
