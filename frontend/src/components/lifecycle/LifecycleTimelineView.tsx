/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { AlertTriangle } from "lucide-react"
import {
  LIFECYCLE_STAGES,
  getCurrentStage,
  type LifecycleAlert,
  type LifecycleEvent,
  type LifecycleTimeline,
} from "../../api/lifecycle-api"
import { LifecycleTimeline as LifecycleTimelineComponent } from "../LifecycleTimeline"
import { STAGE_COLORS, STAGE_ICONS } from "./stageStyles"

interface Props {
  timeline: LifecycleTimeline
  alerts: LifecycleAlert[]
  filteredEvents: LifecycleEvent[]
  isLoading: boolean
}

function alertTypeLabel(type: LifecycleAlert["type"]): string {
  if (type === "stuck_stage") return "Stuck in Stage"
  if (type === "overdue_check") return "Overdue Check"
  return "Long Missing"
}

export function LifecycleTimelineView({ timeline, alerts, filteredEvents, isLoading }: Props): React.ReactElement {
  const currentStage = timeline.events.length > 0 ? getCurrentStage(timeline.events) : null
  const stageInfo = currentStage ? LIFECYCLE_STAGES[currentStage] : null
  const stageColors = currentStage ? STAGE_COLORS[currentStage] : null
  const StageIcon = currentStage ? STAGE_ICONS[currentStage] : null

  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm overflow-hidden">
      <div className="p-6 border-b border-lsc-border dark:border-earth-700">
        <div className="flex items-start justify-between">
          <div>
            <h2 className="text-xl font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
              {timeline.item_title || "Unknown Title"}
            </h2>
            {timeline.item_author && (
              <p className="text-lsc-dark/70 dark:text-lsc-cream/80">
                by {timeline.item_author}
              </p>
            )}
            <div className="flex items-center gap-4 mt-2 text-sm">
              <span className="text-lsc-dark/70 dark:text-lsc-cream/70">
                Copy ID: <span className="font-medium">{timeline.item_copy_id}</span>
              </span>
              {timeline.item_copy_barcode && (
                <span className="text-lsc-dark/70 dark:text-lsc-cream/70">
                  Barcode: <span className="font-mono">{timeline.item_copy_barcode}</span>
                </span>
              )}
              <span className="text-lsc-dark/70 dark:text-lsc-cream/70">
                Events: <span className="font-medium">{timeline.total_events}</span>
              </span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {alerts.length > 0 && (
              <div className="relative group">
                <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-700 dark:text-status-warning-400 cursor-help">
                  <AlertTriangle className="w-4 h-4" />
                  <span className="font-medium text-sm">{alerts.length} alert{alerts.length !== 1 ? "s" : ""}</span>
                </div>
                <div className="absolute right-0 top-full mt-1 z-10 hidden group-hover:block group-focus-within:block w-72 bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg border border-lsc-border dark:border-earth-700 p-3 space-y-2">
                  {alerts.map((alert, i) => (
                    <div key={i} className="text-sm">
                      <p className="font-medium text-status-warning-700 dark:text-status-warning-400">{alertTypeLabel(alert.type)}</p>
                      <p className="text-lsc-dark/70 dark:text-lsc-cream/80">{alert.message}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
            {stageInfo && stageColors && StageIcon && (
              <div className={`flex items-center gap-2 px-3 py-1.5 rounded-xl ${stageColors.bg} ${stageColors.text}`}>
                <StageIcon className="w-4 h-4" />
                <span className="font-medium text-sm">Current: {stageInfo.label}</span>
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="p-6">
        <LifecycleTimelineComponent events={filteredEvents} loading={isLoading} />
      </div>
    </div>
  )
}
