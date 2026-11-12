/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useState } from "react"
import { Loader2, Package, Image, CalendarPlus, ArrowRight } from "lucide-react"
import { StatCard } from "@/components/ui/StatCard"
import { StatGrid } from "@/components/ui/StatGrid"
import { getCatalogStats, type CatalogStatsResponse } from "@/api/staff-api/catalog"
import { t } from "@/i18n"

const STATUS_LABELS: Record<string, string> = {
  uncataloged: "Uncataloged",
  in_progress: "In Progress",
  cataloged: "Cataloged",
}

const STATUS_ORDER = ["uncataloged", "in_progress", "cataloged"]

// Buckets that represent unfinished cataloging work and get a "Work next" action
const WORK_NEXT_STATUSES = ["uncataloged", "in_progress"]

interface CatalogQueuePanelProps {
  activeStatus: string | null
  onStatusClick: (status: string | null) => void
  onWorkNext?: (status: string) => void
  statsRefreshKey?: number
}

export default function CatalogQueuePanel({ activeStatus, onStatusClick, onWorkNext, statsRefreshKey = 0 }: CatalogQueuePanelProps) {
  const [stats, setStats] = useState<CatalogStatsResponse | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    getCatalogStats()
      .then((data) => { if (!cancelled) setStats(data) })
      .catch(() => { /* silent fail */ })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [statsRefreshKey])

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/50 py-4">
        <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
        Loading workflow status...
      </div>
    )
  }

  if (!stats) return null

  const orderedStatuses = STATUS_ORDER.filter((s) => s in stats.status_counts)
  const unknownStatuses = Object.keys(stats.status_counts).filter((s) => !STATUS_ORDER.includes(s))

  return (
    <details className="mb-6" open>
      <summary className="text-sm font-semibold text-lsc-rose cursor-pointer select-none mb-3 hover:text-lsc-rose/80">
        Workflow Status
      </summary>

      <StatGrid columns={3}>
        {[...orderedStatuses, ...unknownStatuses].map((status) => {
          const count = stats.status_counts[status] || 0
          const showWorkNext = !!onWorkNext && WORK_NEXT_STATUSES.includes(status) && count > 0
          return (
            <div key={status} className="flex flex-col gap-2">
              <StatCard
                title={STATUS_LABELS[status] || status.replace(/_/g, " ")}
                value={count}
                icon={Package}
                color={activeStatus === status ? "orange" : "blue"}
                onClick={() => onStatusClick(activeStatus === status ? null : status)}
                className={activeStatus === status ? "ring-2 ring-lsc-rose" : ""}
              />
              {showWorkNext && (
                <button
                  type="button"
                  onClick={() => onWorkNext(status)}
                  className="inline-flex items-center justify-center gap-1.5 px-3 py-2 text-sm font-medium text-lsc-rose hover:bg-lsc-rose/10 rounded-lg focus:outline-none focus:ring-2 focus:ring-lsc-rose transition-colors"
                >
                  {t('staff.cataloging.workNext', 'Work next')}
                  <ArrowRight className="w-4 h-4" aria-hidden="true" />
                </button>
              )}
            </div>
          )
        })}
      </StatGrid>

      {(stats.missing_covers > 0 || stats.added_this_week > 0) && (
        <div className="flex flex-wrap gap-4 mt-3 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
          {stats.missing_covers > 0 && (
            <span className="flex items-center gap-1.5">
              <Image className="w-4 h-4 text-status-warning-500" aria-hidden="true" />
              {stats.missing_covers} missing covers
            </span>
          )}
          {stats.added_this_week > 0 && (
            <span className="flex items-center gap-1.5">
              <CalendarPlus className="w-4 h-4 text-status-success-500" aria-hidden="true" />
              {stats.added_this_week} added this week
            </span>
          )}
        </div>
      )}
    </details>
  )
}
