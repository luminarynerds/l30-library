/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import type { ElementType } from "react"
import { History, Clock, BarChart3, Layers } from "lucide-react"

export type LifecycleViewMode = "search" | "timeline" | "stages" | "stats" | "bulk"

interface Props {
  viewMode: LifecycleViewMode
  onChange: (mode: LifecycleViewMode) => void
}

const TABS: ReadonlyArray<{ mode: Exclude<LifecycleViewMode, "search">; label: string; icon: ElementType }> = [
  { mode: "timeline", label: "Timeline", icon: History },
  { mode: "stages", label: "Stages View", icon: Clock },
  { mode: "stats", label: "Statistics", icon: BarChart3 },
  { mode: "bulk", label: "Bulk Events", icon: Layers },
]

export function LifecycleViewModeTabs({ viewMode, onChange }: Props): React.ReactElement {
  return (
    <div className="flex gap-2 border-b border-lsc-border dark:border-earth-700 pb-2">
      {TABS.map(({ mode, label, icon: Icon }) => (
        <button
          key={mode}
          onClick={() => onChange(mode)}
          className={`flex items-center gap-2 px-4 py-2 rounded-t-xl font-medium text-sm transition-colors ${
            viewMode === mode
              ? "bg-lsc-cream dark:bg-lsc-brown/30 text-lsc-rose dark:text-lsc-rose-light border-b-2 border-lsc-rose"
              : "text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream/50 dark:hover:bg-lsc-brown/20"
          }`}
        >
          <Icon className="w-4 h-4" />
          {label}
        </button>
      ))}
    </div>
  )
}
