/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from "react"
import {
  Loader2,
  Zap,
  RefreshCw,
  Star,
  BookOpen,
  Calendar,
  Package,
  CheckCircle,
} from "lucide-react"
import toast from "react-hot-toast"
import { fetchApi } from '@/api/fetchApi'
import { t } from '@/i18n'

interface SelectionItem {
  id: number
  title: string
  author: string | null
  isbn: string | null
  cover_url: string | null
  priority: string
  source: string
  status?: string
  estimated_price?: number
  notes?: string
}

interface EnrichmentData {
  publisher?: string
  publication_year?: number
  copies_owned?: number
  holds?: number
  suggested_priority?: string
  priority_source?: "manual" | "auto"
}

interface Props {
  token: string
  items: SelectionItem[]
  onRefresh: () => void
}

export default function SelectionEnrichment({ token: _token, items, onRefresh }: Props) {
  const [enriching, setEnriching] = useState<Record<number, boolean>>({})
  const [enrichmentData, setEnrichmentData] = useState<Record<number, EnrichmentData>>({})
  const [bulkEnriching, setBulkEnriching] = useState(false)

  const enrichItem = async (itemId: number) => {
    setEnriching((prev) => ({ ...prev, [itemId]: true }))
    try {
      const data = await fetchApi(`/acquisition/selection-list/${itemId}/enrich`, {
        method: "POST",
      })
      setEnrichmentData((prev) => ({ ...prev, [itemId]: data }))
      toast.success(t('toast.acquisition.enrichedTitleitem', { titleitem: items.find((i) => i.id === itemId)?.title || "item" }))
    } catch (err) {
      toast.error(err instanceof Error ? err.message : t('toast.acquisition.failedToEnrichItem'))
    } finally {
      setEnriching((prev) => ({ ...prev, [itemId]: false }))
    }
  }

  const autoEnrichAll = async () => {
    setBulkEnriching(true)
    try {
      const data = await fetchApi('/acquisition/selection-list/auto-enrich', {
        method: "POST",
      })
      if (data.enriched && typeof data.enriched === "object") {
        setEnrichmentData((prev) => ({ ...prev, ...data.enriched }))
      }
      toast.success(t('toast.acquisition.autoenrichedLengthItemlength1s', { length: data.count ?? items.length, length1s: (data.count ?? items.length) !== 1 ? "s" : "" }))
      onRefresh()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : t('toast.acquisition.failedToAutoenrichItems'))
    } finally {
      setBulkEnriching(false)
    }
  }

  const getPriorityBadge = (item: SelectionItem, enrichment?: EnrichmentData) => {
    const priority = enrichment?.suggested_priority || item.priority
    const source = enrichment?.priority_source
    const priorityColors: Record<string, string> = {
      high: "bg-status-danger-100 text-status-danger-700 dark:bg-status-danger-900/30 dark:text-status-danger-300",
      medium: "bg-status-warning-100 text-status-warning-700 dark:bg-status-warning-900/30 dark:text-status-warning-300",
      low: "bg-status-success-100 text-status-success-700 dark:bg-status-success-900/30 dark:text-status-success-300",
    }
    const colorClass = priorityColors[priority.toLowerCase()] || priorityColors.medium

    return (
      <span className={`inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-full ${colorClass}`}>
        <Star className="w-3 h-3" />
        {priority.charAt(0).toUpperCase() + priority.slice(1)}
        {source && (
          <span className="ml-1 opacity-70">
            ({source === "auto" ? "auto" : "manual"})
          </span>
        )}
      </span>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
          Selection Enrichment
        </h3>
        <button
          onClick={autoEnrichAll}
          disabled={bulkEnriching || items.length === 0}
          className="inline-flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-xl font-medium text-sm hover:bg-lsc-rose/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {bulkEnriching ? (
            <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
          ) : (
            <Zap className="w-4 h-4" />
          )}
          Auto-Enrich All
        </button>
      </div>

      {items.length === 0 && (
        <div className="text-center py-8 text-lsc-dark/70 dark:text-lsc-cream/60">
          <BookOpen className="w-10 h-10 mx-auto mb-2 opacity-40" />
          <p>No selection items to enrich.</p>
        </div>
      )}

      <div className="space-y-3">
        {items.map((item) => {
          const enrichment = enrichmentData[item.id]
          const isEnriching = enriching[item.id]

          return (
            <div
              key={item.id}
              className="border border-lsc-border dark:border-earth-700 rounded-xl p-4 bg-lsc-white dark:bg-earth-800"
            >
              <div className="flex items-start gap-4">
                {item.cover_url ? (
                  <img
                    src={item.cover_url}
                    alt={item.title}
                    className="w-12 h-16 rounded object-cover flex-shrink-0"
                  />
                ) : (
                  <div className="w-12 h-16 rounded bg-earth-100 dark:bg-earth-700 flex items-center justify-center flex-shrink-0">
                    <BookOpen className="w-5 h-5 text-lsc-dark/30 dark:text-lsc-cream/60" />
                  </div>
                )}

                <div className="flex-1 min-w-0">
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <h4 className="font-medium text-lsc-dark dark:text-lsc-cream truncate" title={item.title}>
                        {item.title}
                      </h4>
                      {item.author && (
                        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/60">
                          {item.author}
                        </p>
                      )}
                      {item.isbn && (
                        <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60 mt-0.5">
                          ISBN: {item.isbn}
                        </p>
                      )}
                    </div>
                    <div className="flex items-center gap-2 flex-shrink-0">
                      {getPriorityBadge(item, enrichment)}
                      <button
                        onClick={() => enrichItem(item.id)}
                        disabled={isEnriching}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-xl border border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream hover:bg-earth-50 dark:hover:bg-earth-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        {isEnriching ? (
                          <Loader2 className="w-3.5 h-3.5 motion-safe:animate-spin" />
                        ) : (
                          <RefreshCw className="w-3.5 h-3.5" />
                        )}
                        Enrich
                      </button>
                    </div>
                  </div>

                  {enrichment && (
                    <div className="mt-3 grid grid-cols-2 sm:grid-cols-4 gap-3">
                      {enrichment.publisher && (
                        <div className="flex items-center gap-1.5 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                          <Package className="w-3.5 h-3.5 flex-shrink-0" />
                          <span className="truncate" title={enrichment.publisher}>{enrichment.publisher}</span>
                        </div>
                      )}
                      {enrichment.publication_year && (
                        <div className="flex items-center gap-1.5 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                          <Calendar className="w-3.5 h-3.5 flex-shrink-0" />
                          <span>{enrichment.publication_year}</span>
                        </div>
                      )}
                      {enrichment.copies_owned !== undefined && (
                        <div className="flex items-center gap-1.5 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                          <BookOpen className="w-3.5 h-3.5 flex-shrink-0" />
                          <span>{enrichment.copies_owned} copies owned</span>
                        </div>
                      )}
                      {enrichment.holds !== undefined && (
                        <div className="flex items-center gap-1.5 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                          <CheckCircle className="w-3.5 h-3.5 flex-shrink-0" />
                          <span>{enrichment.holds} holds</span>
                        </div>
                      )}
                    </div>
                  )}

                  {item.notes && (
                    <p className="mt-2 text-xs text-lsc-dark/70 dark:text-lsc-cream/60 italic">
                      {item.notes}
                    </p>
                  )}
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
