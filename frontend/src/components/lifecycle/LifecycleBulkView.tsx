/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import type { RefObject } from "react"
import { Layers, Loader2, Barcode, CheckCircle2, XCircle, X } from "lucide-react"
import {
  LIFECYCLE_EVENT_LABELS,
  LIFECYCLE_STAGES,
  type LifecycleEventType,
} from "../../api/lifecycle-api"

export interface BulkQueueItem {
  copy_id: number
  barcode: string | null
  title: string
  author: string | null
  status: "queued" | "success" | "error"
  message?: string
}

interface Props {
  bulkEventType: LifecycleEventType | ""
  bulkDescription: string
  bulkQueue: BulkQueueItem[]
  bulkSubmitting: boolean
  bulkScanRef: RefObject<HTMLInputElement>
  onBulkEventTypeChange: (value: LifecycleEventType | "") => void
  onBulkDescriptionChange: (value: string) => void
  onBulkScan: (barcode: string) => void
  onBulkSubmit: () => void
  onClearQueue: () => void
  onRemoveQueueItem: (index: number) => void
}

export function LifecycleBulkView({
  bulkEventType,
  bulkDescription,
  bulkQueue,
  bulkSubmitting,
  bulkScanRef,
  onBulkEventTypeChange,
  onBulkDescriptionChange,
  onBulkScan,
  onBulkSubmit,
  onClearQueue,
  onRemoveQueueItem,
}: Props): React.ReactElement {
  return (
    <div className="space-y-4">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm">
        <h3 className="font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
          <Layers className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
          Bulk Lifecycle Events
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4">
          <div>
            <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Event Type *</label>
            <select
              value={bulkEventType}
              onChange={(e) => onBulkEventTypeChange(e.target.value as LifecycleEventType | "")}
              className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
            >
              <option value="">Select event type...</option>
              {Object.entries(LIFECYCLE_STAGES).map(([stageKey, stage]) => (
                <optgroup key={stageKey} label={stage.label}>
                  {stage.events.map((eventType) => (
                    <option key={eventType} value={eventType}>
                      {LIFECYCLE_EVENT_LABELS[eventType]}
                    </option>
                  ))}
                </optgroup>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Description (optional)</label>
            <input
              type="text"
              value={bulkDescription}
              onChange={(e) => onBulkDescriptionChange(e.target.value)}
              placeholder="Shared description for all events..."
              className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
            />
          </div>
        </div>

        <div className="relative">
          <Barcode className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-lsc-rose dark:text-lsc-rose-light" />
          <input
            ref={bulkScanRef}
            type="text"
            autoFocus
            onKeyDown={(e) => { if (e.key === "Enter" && e.currentTarget.value.trim()) { onBulkScan(e.currentTarget.value); } }}
            placeholder={bulkEventType ? "Scan barcode to add to queue..." : "Select an event type first..."}
            disabled={!bulkEventType}
            className="w-full pl-10 pr-4 py-2 border-2 border-lsc-rose/50 dark:border-lsc-rose/40 rounded-xl bg-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent font-mono disabled:opacity-50"
          />
        </div>
      </div>

      {bulkQueue.length > 0 && (
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm overflow-hidden">
          <div className="p-4 border-b border-lsc-border dark:border-earth-700 flex items-center justify-between">
            <h3 className="font-semibold text-lsc-dark dark:text-lsc-cream">
              Queue ({bulkQueue.length} item{bulkQueue.length !== 1 ? "s" : ""})
            </h3>
            <div className="flex items-center gap-2">
              <button
                onClick={onClearQueue}
                className="px-3 py-1.5 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-lsc-brown/30 rounded-xl transition-colors"
              >
                Clear
              </button>
              <button
                onClick={onBulkSubmit}
                disabled={bulkSubmitting || !bulkEventType || bulkQueue.every(q => q.status !== "queued")}
                className="flex items-center gap-2 px-4 py-1.5 text-sm bg-lsc-rose text-white rounded-xl hover:bg-lsc-rose/90 transition-colors disabled:opacity-50"
              >
                {bulkSubmitting ? <Loader2 className="w-4 h-4 motion-safe:animate-spin" /> : <CheckCircle2 className="w-4 h-4" />}
                Apply to All
              </button>
            </div>
          </div>
          <div className="divide-y divide-lsc-border dark:divide-earth-700 max-h-96 overflow-y-auto">
            {bulkQueue.map((item, i) => (
              <div key={i} className="flex items-center gap-4 p-3">
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-sm text-lsc-dark dark:text-lsc-cream truncate">{item.title}</p>
                  <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{item.author}{item.barcode ? ` | ${item.barcode}` : ""}</p>
                </div>
                <div className="shrink-0">
                  {item.status === "queued" && (
                    <span className="px-2 py-0.5 text-xs rounded-full bg-lsc-cream dark:bg-lsc-brown/30 text-lsc-dark/70 dark:text-lsc-cream/70">Queued</span>
                  )}
                  {item.status === "success" && (
                    <span className="flex items-center gap-1 px-2 py-0.5 text-xs rounded-full bg-status-success-100 dark:bg-status-success-900/30 text-status-success-700 dark:text-status-success-400">
                      <CheckCircle2 className="w-3 h-3" /> Done
                    </span>
                  )}
                  {item.status === "error" && (
                    <span className="flex items-center gap-1 px-2 py-0.5 text-xs rounded-full bg-status-danger-100 dark:bg-status-danger-900/30 text-status-danger-700 dark:text-status-danger-400" title={item.message}>
                      <XCircle className="w-3 h-3" /> Error
                    </span>
                  )}
                </div>
                {item.status === "queued" && (
                  <button
                    onClick={() => onRemoveQueueItem(i)}
                    className="p-1 text-lsc-dark/70 dark:text-lsc-cream/40 hover:text-status-danger-500 dark:hover:text-status-danger-400"
                  >
                    <X className="w-4 h-4" />
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {bulkQueue.length === 0 && (
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-12 shadow-sm">
          <div className="text-center">
            <Layers className="w-16 h-16 mx-auto text-lsc-dark/20 dark:text-lsc-cream/20 mb-4" />
            <h3 className="text-xl font-semibold text-lsc-dark dark:text-lsc-cream mb-2">
              Bulk Event Mode
            </h3>
            <p className="text-lsc-dark/70 dark:text-lsc-cream/80 max-w-md mx-auto">
              Select an event type above, then scan items to build a queue. All queued items will receive the same lifecycle event when you click Apply.
            </p>
          </div>
        </div>
      )}
    </div>
  )
}
