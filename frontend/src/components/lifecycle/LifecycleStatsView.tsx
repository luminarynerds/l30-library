/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { AlertTriangle, BarChart3, Clock } from "lucide-react"
import {
  LIFECYCLE_STAGES,
  formatEventType,
  getLifecycleStats,
  getStageForEventType,
  type LifecycleAlert,
  type LifecycleStage,
  type LifecycleTimeline,
} from "../../api/lifecycle-api"
import { STAGE_COLORS, STAGE_ICONS, formatLifecycleDate } from "./stageStyles"

interface Props {
  timeline: LifecycleTimeline
  alerts: LifecycleAlert[]
  onViewAllEvents: () => void
}

function alertTypeLabel(type: LifecycleAlert["type"]): string {
  if (type === "stuck_stage") return "Stuck in Stage"
  if (type === "overdue_check") return "Overdue Condition Check"
  return "Long Missing"
}

function daysInSystem(timeline: LifecycleTimeline): number {
  if (timeline.events.length === 0) return 0
  const oldest = timeline.events[timeline.events.length - 1]!
  return Math.ceil(
    (new Date().getTime() - new Date(oldest.created_at).getTime()) /
      (1000 * 60 * 60 * 24)
  )
}

export function LifecycleStatsView({ timeline, alerts, onViewAllEvents }: Props): React.ReactElement {
  const stats = getLifecycleStats(timeline)
  const activeStageCount = Object.values(stats).filter(v => v > 0).length

  return (
    <div className="space-y-6">
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

      {alerts.length > 0 && (
        <div className="bg-status-warning-50 dark:bg-status-warning-900/20 border border-status-warning-200 dark:border-status-warning-800 rounded-xl p-6">
          <h3 className="font-semibold text-status-warning-800 dark:text-status-warning-300 mb-4 flex items-center gap-2">
            <AlertTriangle className="w-5 h-5" />
            Attention Needed
          </h3>
          <div className="space-y-3">
            {alerts.map((alert, i) => (
              <div key={i} className="flex items-start gap-3 p-3 bg-white/60 dark:bg-black/20 rounded-xl">
                <AlertTriangle className="w-4 h-4 text-status-warning-600 dark:text-status-warning-400 mt-0.5 shrink-0" />
                <div>
                  <p className="font-medium text-sm text-status-warning-800 dark:text-status-warning-300">
                    {alertTypeLabel(alert.type)}
                  </p>
                  <p className="text-sm text-status-warning-700/80 dark:text-status-warning-400/80">{alert.message}</p>
                  <p className="text-xs text-status-warning-600/60 dark:text-status-warning-500/60 mt-1">Since {new Date(alert.since).toLocaleDateString()}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm">
        <h3 className="font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
          <BarChart3 className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
          Lifecycle Statistics
        </h3>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
          <div className="p-4 bg-lsc-cream dark:bg-lsc-brown/30 rounded-xl text-center">
            <p className="text-3xl font-bold text-lsc-dark dark:text-lsc-cream">{timeline.total_events}</p>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Total Events</p>
          </div>
          <div className="p-4 bg-lsc-cream dark:bg-lsc-brown/30 rounded-xl text-center">
            <p className="text-3xl font-bold text-lsc-dark dark:text-lsc-cream">{activeStageCount}</p>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Active Stages</p>
          </div>
          <div className="p-4 bg-lsc-cream dark:bg-lsc-brown/30 rounded-xl text-center">
            <p className="text-3xl font-bold text-lsc-rose dark:text-lsc-rose-light">{stats.circulation}</p>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Circulation Events</p>
          </div>
          <div className="p-4 bg-lsc-cream dark:bg-lsc-brown/30 rounded-xl text-center">
            <p className="text-3xl font-bold text-lsc-dark dark:text-lsc-cream">{daysInSystem(timeline)}</p>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Days in System</p>
          </div>
        </div>

        <h4 className="font-medium text-lsc-dark dark:text-lsc-cream mb-3">Events by Stage</h4>
        <div className="space-y-2">
          {(Object.entries(LIFECYCLE_STAGES) as [LifecycleStage, typeof LIFECYCLE_STAGES[LifecycleStage]][]).map(([stageKey, stage]) => {
            const count = stats[stageKey]
            const percentage = timeline.total_events > 0 ? (count / timeline.total_events) * 100 : 0
            const colors = STAGE_COLORS[stageKey]
            const Icon = STAGE_ICONS[stageKey]

            return (
              <div key={stageKey} className="flex items-center gap-3">
                <div className={`p-1.5 rounded-lg ${colors.bg}`}>
                  <Icon className={`w-4 h-4 ${colors.text}`} />
                </div>
                <span className="w-24 text-sm text-lsc-dark dark:text-lsc-cream">{stage.label}</span>
                <div className="flex-1 h-4 bg-lsc-cream dark:bg-lsc-brown/30 rounded-full overflow-hidden">
                  <div
                    className={`h-full ${colors.bg.replace("/30", "/60")}`}
                    style={{ width: `${percentage}%` }}
                  />
                </div>
                <span className="w-12 text-right text-sm font-medium text-lsc-dark dark:text-lsc-cream">{count}</span>
              </div>
            )
          })}
        </div>
      </div>

      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm">
        <h3 className="font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
          <Clock className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
          Recent Events
        </h3>
        <div className="space-y-3">
          {timeline.events.slice(0, 5).map((event) => {
            const stageKey = getStageForEventType(event.event_type)
            const colors = STAGE_COLORS[stageKey]
            const Icon = STAGE_ICONS[stageKey]

            return (
              <div
                key={event.id}
                className="flex items-start gap-3 p-3 rounded-xl bg-lsc-cream/50 dark:bg-lsc-brown/20"
              >
                <div className={`p-2 rounded-lg ${colors.bg}`}>
                  <Icon className={`w-4 h-4 ${colors.text}`} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-lsc-dark dark:text-lsc-cream">
                      {formatEventType(event.event_type)}
                    </span>
                    <span className={`px-2 py-0.5 rounded-full text-xs ${colors.bg} ${colors.text}`}>
                      {LIFECYCLE_STAGES[stageKey]!.label}
                    </span>
                  </div>
                  {event.description && (
                    <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                      {event.description}
                    </p>
                  )}
                  <div className="flex items-center gap-4 mt-1 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                    <span>{formatLifecycleDate(event.created_at)}</span>
                    {event.performed_by_name && <span>By: {event.performed_by_name}</span>}
                  </div>
                </div>
              </div>
            )
          })}
        </div>
        {timeline.events.length > 5 && (
          <button
            onClick={onViewAllEvents}
            className="w-full mt-4 py-2 text-center text-sm text-lsc-rose dark:text-lsc-rose-light hover:underline"
          >
            View all {timeline.total_events} events
          </button>
        )}
      </div>
    </div>
  )
}
