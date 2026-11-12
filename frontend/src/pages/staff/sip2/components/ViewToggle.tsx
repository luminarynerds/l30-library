/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Monitor, Activity } from "lucide-react"
import type { ViewMode } from "../types"

interface ViewToggleProps {
  viewMode: ViewMode
  setViewMode: (mode: ViewMode) => void
}

export function ViewToggle({ viewMode, setViewMode }: ViewToggleProps) {
  return (
    <div className="flex items-center gap-2 p-1 bg-lsc-cream dark:bg-earth-800 rounded-xl w-fit">
      <button
        onClick={() => setViewMode("terminals")}
        className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
          viewMode === "terminals"
            ? "bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream shadow-sm"
            : "text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream"
        }`}
      >
        <Monitor className="w-4 h-4" />
        Terminals
      </button>
      <button
        onClick={() => setViewMode("transactions")}
        className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
          viewMode === "transactions"
            ? "bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream shadow-sm"
            : "text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream"
        }`}
      >
        <Activity className="w-4 h-4" />
        Transactions
      </button>
    </div>
  )
}
