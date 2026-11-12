/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect, useCallback } from "react"
import { useAuth } from "../contexts/AuthContext"
import { AdminShell } from '../components/shells/AdminShell'
import {
  Loader2, Package, Tag, Wifi, BookOpen, ArrowRight,
  CheckCircle, RefreshCw, BarChart3, User, Clock, Barcode,
  ChevronDown, ChevronRight,
} from "lucide-react"
import toast from "react-hot-toast"
import type { ProcessingQueueItem, QueueResponse } from "../api/processing-api"
import * as processingApi from "../api/processing-api"
import { useTranslation} from '@/i18n'

// ============ Constants ============

const COLUMNS = [
  { id: "received", label: "Received", icon: Package, color: "blue" },
  { id: "labeling", label: "Labeling", icon: Tag, color: "amber" },
  { id: "rfid_tagging", label: "RFID Tagging", icon: Wifi, color: "purple" },
  { id: "ready_to_shelve", label: "Ready to Shelve", icon: BookOpen, color: "green" },
] as const

const COLUMN_COLORS: Record<string, { bg: string; border: string; badge: string; header: string }> = {
  blue: {
    bg: "bg-earth-50 dark:bg-earth-800/10",
    border: "border-lsc-border dark:border-earth-700",
    badge: "bg-earth-100 dark:bg-earth-800/30 text-lsc-rose dark:text-lsc-rose-light",
    header: "text-lsc-rose dark:text-lsc-rose-light",
  },
  amber: {
    bg: "bg-status-warning-50 dark:bg-status-warning-900/10",
    border: "border-status-warning-200 dark:border-status-warning-800",
    badge: "bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-700 dark:text-status-warning-300",
    header: "text-status-warning-700 dark:text-status-warning-300",
  },
  purple: {
    bg: "bg-category-50 dark:bg-category-900/10",
    border: "border-category-200 dark:border-category-800",
    badge: "bg-category-100 dark:bg-category-900/30 text-category-700 dark:text-category-300",
    header: "text-category-700 dark:text-category-300",
  },
  green: {
    bg: "bg-status-success-50 dark:bg-status-success-900/10",
    border: "border-status-success-200 dark:border-status-success-800",
    badge: "bg-status-success-100 dark:bg-status-success-900/30 text-status-success-700 dark:text-status-success-300",
    header: "text-status-success-700 dark:text-status-success-300",
  },
}

// ============ Main Component ============

export default function StaffProcessingQueuePage() {
  const { t } = useTranslation()
  const { token } = useAuth()
  const [queue, setQueue] = useState<QueueResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [advancingIds, setAdvancingIds] = useState<Set<number>>(new Set())
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set())
  const [expandedCard, setExpandedCard] = useState<number | null>(null)

  const fetchQueue = useCallback(async () => {
    if (!token) return
    try {
      const data = await processingApi.getProcessingQueue(token)
      setQueue(data)
    } catch (_err) {
      toast.error(t('staffProcessingQueue.failedToLoadProcessingQueue'))
    } finally {
      setLoading(false)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token])

  useEffect(() => {
    fetchQueue()
    const interval = setInterval(fetchQueue, 30000)
    return () => clearInterval(interval)
  }, [fetchQueue])

  const handleAdvance = async (copyId: number) => {
    if (!token) return
    setAdvancingIds((prev) => new Set(prev).add(copyId))
    try {
      const result = await processingApi.advanceItem(token, copyId)
      toast.success(result.message)
      await fetchQueue()
      setSelectedIds((prev) => {
        const next = new Set(prev)
        next.delete(copyId)
        return next
      })
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : t('toast.staffProcessingQueue.failedToAdvanceItem'))
    } finally {
      setAdvancingIds((prev) => {
        const next = new Set(prev)
        next.delete(copyId)
        return next
      })
    }
  }

  const handleBulkAdvance = async () => {
    if (!token || selectedIds.size === 0) return
    const ids = Array.from(selectedIds)
    try {
      const result = await processingApi.bulkAdvance(token, ids)
      const succeeded = result.results.filter((r) => !r.error).length
      const failed = result.results.filter((r) => r.error).length
      if (succeeded > 0) toast.success(t('toast.staffProcessingQueue.advancedSucceededItemsucceeded1s', { succeeded: succeeded, succeeded1s: succeeded > 1 ? "s" : "" }))
      if (failed > 0) toast.error(t('toast.staffProcessingQueue.failedItemfailed1sFailed', { failed: failed, failed1s: failed > 1 ? "s" : "" }))
      setSelectedIds(new Set())
      await fetchQueue()
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : t('toast.staffProcessingQueue.bulkAdvanceFailed'))
    }
  }

  const toggleSelect = (copyId: number) => {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (next.has(copyId)) next.delete(copyId)
      else next.add(copyId)
      return next
    })
  }

  const totalItems = queue
    ? Object.values(queue.totals).reduce((sum, n) => sum + n, 0)
    : 0

  const getColumnItems = (columnId: string): ProcessingQueueItem[] => {
    if (!queue) return []
    return queue[columnId as keyof QueueResponse] as ProcessingQueueItem[] || []
  }

  return (
    <AdminShell title="Processing Queue">
        {/* Header */}
        <div className="mb-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
                Processing Queue
              </h1>
              <p className="text-sm text-earth-600 dark:text-earth-400 mt-1">
                Track items from receiving through shelving
              </p>
            </div>
            <div className="flex items-center gap-3">
              {selectedIds.size > 0 && (
                <button
                  onClick={handleBulkAdvance}
                  className="flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 transition-colors"
                >
                  <ArrowRight className="w-4 h-4" />
                  Advance {selectedIds.size} selected
                </button>
              )}
              <button
                onClick={() => { setLoading(true); fetchQueue() }}
                className="flex items-center gap-2 px-3 py-2 border border-lsc-border dark:border-earth-600 rounded-lg text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-earth-100 dark:hover:bg-earth-800 transition-colors"
              >
                <RefreshCw className={`w-4 h-4 ${loading ? "motion-safe:animate-spin" : ""}`} />
                Refresh
              </button>
              <div className="flex items-center gap-2 px-3 py-2 bg-earth-100 dark:bg-earth-800 rounded-lg">
                <BarChart3 className="w-4 h-4 text-earth-600" />
                <span className="text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">
                  {totalItems} item{totalItems !== 1 ? "s" : ""} in processing
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Loading state */}
        {loading && !queue && (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="w-8 h-8 motion-safe:animate-spin text-earth-600" />
          </div>
        )}

        {/* Empty state */}
        {!loading && queue && totalItems === 0 && (
          <div className="text-center py-20">
            <CheckCircle className="w-16 h-16 text-status-success-400 mx-auto mb-4" />
            <h2 className="font-serif text-lg font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">
              All caught up!
            </h2>
            <p className="text-earth-600 dark:text-earth-400">
              No items currently in processing. New items will appear here after cataloging.
            </p>
          </div>
        )}

        {/* Kanban Board */}
        {queue && totalItems > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
            {COLUMNS.map((col) => {
              const items = getColumnItems(col.id)
              const colors = COLUMN_COLORS[col.color]!
              const Icon = col.icon
              const isLastColumn = col.id === "ready_to_shelve"

              return (
                <div
                  key={col.id}
                  className={`rounded-xl border ${colors.border} ${colors.bg} min-h-[400px] flex flex-col`}
                >
                  {/* Column Header */}
                  <div className="p-4 border-b border-lsc-border dark:border-earth-700">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Icon className={`w-5 h-5 ${colors.header}`} />
                        <h3 className={`font-semibold ${colors.header}`}>{col.label}</h3>
                      </div>
                      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${colors.badge}`}>
                        {items.length}
                      </span>
                    </div>
                  </div>

                  {/* Column Items */}
                  <div className="p-3 flex-1 space-y-2 overflow-y-auto max-h-[600px]">
                    {items.length === 0 && (
                      <p className="text-sm text-earth-600 dark:text-earth-400 text-center py-6">
                        No items
                      </p>
                    )}
                    {items.map((item) => {
                      const isAdvancing = advancingIds.has(item.copy_id)
                      const isSelected = selectedIds.has(item.copy_id)
                      const isExpanded = expandedCard === item.copy_id

                      return (
                        <div
                          key={item.copy_id}
                          className={`bg-lsc-white dark:bg-earth-800 rounded-lg border transition-all ${
                            isSelected
                              ? "border-earth-400 dark:border-lsc-rose/50 ring-1 ring-earth-200 dark:ring-earth-700"
                              : "border-lsc-border dark:border-earth-700 hover:border-lsc-border dark:hover:border-earth-600"
                          }`}
                        >
                          <div className="p-3">
                            {/* Card Header */}
                            <div className="flex items-start gap-2">
                              <input
                                type="checkbox"
                                checked={isSelected}
                                onChange={() => toggleSelect(item.copy_id)}
                                className="mt-1 rounded border-lsc-border text-lsc-rose dark:text-lsc-rose-light focus:ring-lsc-rose"
                              />
                              <div className="flex-1 min-w-0">
                                <p className="text-sm font-medium text-lsc-dark dark:text-lsc-cream truncate" title={item.title}>
                                  {item.title}
                                </p>
                                {item.author && (
                                  <p className="text-xs text-earth-600 dark:text-earth-400 truncate" title={item.author}>
                                    {item.author}
                                  </p>
                                )}
                              </div>
                              <button
                                onClick={() => setExpandedCard(isExpanded ? null : item.copy_id)}
                                aria-label={isExpanded ? t('aria.staffProcessingQueue.collapseDetails', 'Collapse details') : t('aria.staffProcessingQueue.expandDetails', 'Expand details')}
                                className="text-earth-600 hover:text-earth-600 dark:text-earth-200 dark:hover:text-earth-300"
                              >
                                {isExpanded ? (
                                  <ChevronDown className="w-4 h-4" />
                                ) : (
                                  <ChevronRight className="w-4 h-4" />
                                )}
                              </button>
                            </div>

                            {/* Expanded Details */}
                            {isExpanded && (
                              <div className="mt-2 pt-2 border-t border-earth-100 dark:border-earth-700 space-y-1">
                                {item.barcode && (
                                  <div className="flex items-center gap-1.5 text-xs text-earth-600 dark:text-earth-400">
                                    <Barcode className="w-3 h-3" />
                                    <span>{item.barcode}</span>
                                  </div>
                                )}
                                {item.call_number && (
                                  <div className="flex items-center gap-1.5 text-xs text-earth-600 dark:text-earth-400">
                                    <BookOpen className="w-3 h-3" />
                                    <span>{item.call_number}</span>
                                  </div>
                                )}
                                {item.received_at && (
                                  <div className="flex items-center gap-1.5 text-xs text-earth-600 dark:text-earth-400">
                                    <Clock className="w-3 h-3" />
                                    <span>Received {new Date(item.received_at).toLocaleDateString()}</span>
                                  </div>
                                )}
                                {item.assigned_staff_name && (
                                  <div className="flex items-center gap-1.5 text-xs text-earth-600 dark:text-earth-400">
                                    <User className="w-3 h-3" />
                                    <span>{item.assigned_staff_name}</span>
                                  </div>
                                )}
                              </div>
                            )}

                            {/* Advance Button */}
                            <div className="mt-2 flex justify-end">
                              <button
                                onClick={() => handleAdvance(item.copy_id)}
                                disabled={isAdvancing}
                                className={`flex items-center gap-1 px-2.5 py-1 rounded text-xs font-medium transition-colors ${
                                  isLastColumn
                                    ? "bg-status-success-100 dark:bg-status-success-900/30 text-status-success-700 dark:text-status-success-300 hover:bg-status-success-200 dark:hover:bg-status-success-900/50"
                                    : "bg-earth-100 dark:bg-earth-800/30 text-lsc-rose dark:text-lsc-rose-light hover:bg-earth-200 dark:hover:bg-earth-800/50"
                                }`}
                              >
                                {isAdvancing ? (
                                  <Loader2 className="w-3 h-3 motion-safe:animate-spin" />
                                ) : isLastColumn ? (
                                  <>
                                    <CheckCircle className="w-3 h-3" />
                                    Shelve
                                  </>
                                ) : (
                                  <>
                                    <ArrowRight className="w-3 h-3" />
                                    Advance
                                  </>
                                )}
                              </button>
                            </div>
                          </div>
                        </div>
                      )
                    })}
                  </div>
                </div>
              )
            })}
          </div>
        )}
    </AdminShell>
  )
}
