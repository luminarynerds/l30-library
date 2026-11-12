/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { AlertTriangle } from "lucide-react"
import {
  LIFECYCLE_STAGES,
  filterEventsByStage,
  formatEventType,
  getCurrentStage,
  type LifecycleAlert,
  type LifecycleStage,
  type LifecycleTimeline,
} from "../../api/lifecycle-api"
import { STAGE_COLORS, STAGE_ICONS, formatLifecycleDate } from "./stageStyles"

interface Props {
  timeline: LifecycleTimeline
  alerts: LifecycleAlert[]
  onJumpToTimelineForStage: (stage: LifecycleStage) => void
}

export function LifecycleStagesView({ timeline, alerts, onJumpToTimelineForStage }: Props): React.ReactElement {
  const currentStage = getCurrentStage(timeline.events)

  return (
    <div className="space-y-4">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm">
        <h2 className="text-xl font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
          {timeline.item_title || "Unknown Title"}
        </h2>
        {timeline.item_author && (
          <p className="text-lsc-dark/70 dark:text-lsc-cream/80">
            by {timeline.item_author}
          </p>
        )}
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
          Copy ID: {timeline.item_copy_id} | Barcode: {timeline.item_copy_barcode || "N/A"}
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {(Object.entries(LIFECYCLE_STAGES) as [LifecycleStage, typeof LIFECYCLE_STAGES[LifecycleStage]][]).map(([stageKey, stage]) => {
          const stageEvents = filterEventsByStage(timeline.events, stageKey)
          const colors = STAGE_COLORS[stageKey]
          const Icon = STAGE_ICONS[stageKey]
          const isCurrentStage = currentStage === stageKey
          const stageAlerts = alerts.filter(a => a.stage === stageKey)

          return (
            <div
              key={stageKey}
              className={`bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm overflow-hidden ${
                isCurrentStage ? `ring-2 ring-offset-2 dark:ring-offset-earth-900 ring-lsc-rose` : ""
              }`}
            >
              <div className={`p-4 ${colors.bg} border-b ${colors.border}`}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Icon className={`w-5 h-5 ${colors.text}`} />
                    <h3 className={`font-semibold ${colors.text}`}>{stage.label}</h3>
                    {stageAlerts.length > 0 && (
                      <span className="relative group cursor-help">
                        <AlertTriangle className="w-4 h-4 text-status-warning-500" />
                        <span className="absolute left-0 top-full mt-1 hidden group-hover:block group-focus-within:block z-10 w-48 text-xs bg-lsc-white dark:bg-earth-800 rounded-lg shadow-lg border border-lsc-border dark:border-earth-700 p-2 text-lsc-dark dark:text-lsc-cream">
                          {stageAlerts.map(a => a.message).join("; ")}
                        </span>
                      </span>
                    )}
                  </div>
                  <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${colors.bg} ${colors.text}`}>
                    {stageEvents.length} event{stageEvents.length !== 1 ? "s" : ""}
                  </span>
                </div>
                <p className={`text-sm mt-1 ${colors.text} opacity-80`}>{stage.description}</p>
              </div>
              <div className="p-4 max-h-64 overflow-y-auto">
                {stageEvents.length === 0 ? (
                  <p className="text-center text-sm text-lsc-dark/70 dark:text-lsc-cream/70 py-4">
                    No events in this stage
                  </p>
                ) : (
                  <div className="space-y-2">
                    {stageEvents.slice(0, 5).map((event) => (
                      <div
                        key={event.id}
                        className="p-2 rounded-lg bg-lsc-cream/50 dark:bg-lsc-brown/20"
                      >
                        <div className="flex items-center justify-between">
                          <span className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
                            {formatEventType(event.event_type)}
                          </span>
                          <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                            {formatLifecycleDate(event.created_at)}
                          </span>
                        </div>
                        {event.description && (
                          <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1 truncate" title={event.description}>
                            {event.description}
                          </p>
                        )}
                      </div>
                    ))}
                    {stageEvents.length > 5 && (
                      <button
                        onClick={() => onJumpToTimelineForStage(stageKey)}
                        className="w-full text-center text-sm text-lsc-rose dark:text-lsc-rose-light hover:underline py-2"
                      >
                        View all {stageEvents.length} events
                      </button>
                    )}
                  </div>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
