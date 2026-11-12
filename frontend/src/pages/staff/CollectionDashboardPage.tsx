/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Collection Intelligence Dashboard
 * Unified health overview pulling stats from inventory, weeding,
 * processing, and lifecycle modules.
 */

import { Link } from "react-router-dom"
import { useQuery } from "@tanstack/react-query"
import {
  BarChart3, AlertTriangle, Package, Leaf,
  ScanLine, ClipboardCheck, TrendingUp, Loader2,
  ArrowRight, Activity} from "lucide-react"
import { AdminShell } from "@/components/shells"
import { useAuth } from "@/contexts/AuthContext"
import { fetchApi } from "@/lib/api-client"

// ============ Types ============

interface CollectionIntelligence {
  total_items: number
  circulation_pct: number
  in_circulation: number
  poor_damaged: number
  condition_breakdown: Record<string, number>
  overdue_shelf_reads: number
  recent_events: LifecycleEvent[]
}

interface WeedingSummary {
  total_candidates: number
  by_status: Record<string, number>
  by_reason: Record<string, number>
  sections_over_capacity: number
  total_duplicates_excess: number
  outdated_items: number
  never_circulated_items: number
  avg_crew_score: number | null
}

interface ProcessingStats {
  total_in_processing: number
}

interface LifecycleEvent {
  id: number
  event_type: string
  description: string | null
  created_at: string | null
  item_copy_id: number
  barcode: string
  title: string
}

// ============ Helpers ============

const CONDITION_COLORS: Record<string, string> = {
  new: "bg-emerald-500",
  good: "bg-status-success-400",
  fair: "bg-status-warning-400",
  poor: "bg-status-warning-400",
  damaged: "bg-status-danger-500",
}

const CONDITION_LABELS: Record<string, string> = {
  new: "New",
  good: "Good",
  fair: "Fair",
  poor: "Poor",
  damaged: "Damaged",
}

const EVENT_TYPE_LABELS: Record<string, string> = {
  ordered: "Ordered",
  received: "Received",
  cataloging_started: "Cataloging started",
  cataloged: "Cataloged",
  copy_created: "Copy created",
  shelved: "Shelved",
  checked_out: "Checked out",
  returned: "Returned",
  renewed: "Renewed",
  hold_placed: "Hold placed",
  hold_filled: "Hold filled",
  condition_changed: "Condition changed",
  damaged: "Damaged",
  repaired: "Repaired",
  inventoried: "Inventoried",
  missing: "Missing",
  found: "Found",
}

function formatRelativeTime(iso: string | null): string {
  if (!iso) return ""
  const diff = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return "just now"
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  const days = Math.floor(hrs / 24)
  return `${days}d ago`
}

// ============ Sub-components ============

function StatCard({
  label,
  value,
  sub,
  icon: Icon,
  href,
  accent = false,
}: {
  label: string
  value: string | number
  sub?: string
  icon: React.ElementType
  href?: string
  accent?: boolean
}) {
  const inner = (
    <div
      className={`rounded-xl border p-5 flex items-start gap-4 transition-colors ${
        accent
          ? "border-lsc-rose/40 bg-lsc-rose/5 dark:bg-lsc-rose/10"
          : "border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800"
      } ${href ? "hover:border-lsc-rose/60 cursor-pointer" : ""}`}
    >
      <div className="bg-lsc-rose/10 dark:bg-lsc-rose/20 p-2.5 rounded-lg flex-shrink-0">
        <Icon className="w-5 h-5 text-lsc-rose" />
      </div>
      <div className="min-w-0">
        <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream leading-none">
          {value}
        </p>
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/60 mt-1">{label}</p>
        {sub && (
          <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-0.5">{sub}</p>
        )}
      </div>
    </div>
  )
  return href ? <Link to={href}>{inner}</Link> : inner
}

function AlertRow({
  icon: Icon,
  label,
  count,
  href,
  color = "text-lsc-rose",
}: {
  icon: React.ElementType
  label: string
  count: number
  href: string
  color?: string
}) {
  if (count === 0) return null
  return (
    <Link
      to={href}
      className="flex items-center justify-between px-4 py-3 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 hover:border-lsc-rose/50 transition-colors group"
    >
      <div className="flex items-center gap-3 min-w-0">
        <Icon className={`w-4 h-4 flex-shrink-0 ${color}`} />
        <span className="text-sm text-lsc-dark dark:text-lsc-cream">{label}</span>
      </div>
      <div className="flex items-center gap-2">
        <span className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
          {count}
        </span>
        <ArrowRight className="w-3.5 h-3.5 text-lsc-dark/30 dark:text-lsc-cream/30 group-hover:text-lsc-rose transition-colors" />
      </div>
    </Link>
  )
}

function ConditionBar({ breakdown }: { breakdown: Record<string, number> }) {
  const total = Object.values(breakdown).reduce((s, v) => s + v, 0)
  if (total === 0) return null

  return (
    <div>
      <div className="flex rounded-full overflow-hidden h-4">
        {Object.entries(breakdown).map(([cond, count]) => {
          const pct = (count / total) * 100
          if (pct === 0) return null
          return (
            <div
              key={cond}
              className={`${CONDITION_COLORS[cond] || "bg-earth-400"} relative group`}
              style={{ width: `${pct}%` }}
              title={`${CONDITION_LABELS[cond] || cond}: ${count} (${pct.toFixed(1)}%)`}
            />
          )
        })}
      </div>
      <div className="flex flex-wrap gap-x-4 gap-y-1 mt-2">
        {Object.entries(breakdown).map(([cond, count]) => (
          <div key={cond} className="flex items-center gap-1.5 text-xs text-lsc-dark/70 dark:text-lsc-cream/60">
            <span className={`w-2.5 h-2.5 rounded-full ${CONDITION_COLORS[cond] || "bg-earth-400"}`} />
            <span>{CONDITION_LABELS[cond] || cond}</span>
            <span className="font-medium text-lsc-dark dark:text-lsc-cream">{count}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

// ============ Main Component ============

export default function CollectionDashboardPage() {
  const { token } = useAuth()

  const { data: intel, isLoading: intelLoading } = useQuery<CollectionIntelligence>({
    queryKey: ["collection-intelligence"],
    queryFn: () => fetchApi("/inventory/collection-intelligence", { token: token! }),
    enabled: !!token,
    refetchInterval: 60_000,
    staleTime: 30_000,
  })

  const { data: weeding, isLoading: weedingLoading } = useQuery<WeedingSummary>({
    queryKey: ["weeding-summary"],
    queryFn: () => fetchApi("/weeding/summary", { token: token! }),
    enabled: !!token,
    refetchInterval: 60_000,
    staleTime: 30_000,
  })

  const { data: processing, isLoading: processingLoading } = useQuery<ProcessingStats>({
    queryKey: ["processing-stats"],
    queryFn: () => fetchApi("/processing/queue/stats", { token: token! }),
    enabled: !!token,
    refetchInterval: 60_000,
    staleTime: 30_000,
  })

  const isLoading = intelLoading || weedingLoading || processingLoading

  const weedingPending =
    (weeding?.by_status?.["candidate"] || 0) + (weeding?.by_status?.["under_review"] || 0)

  return (
    <AdminShell
      title="Collection Intelligence"
      subtitle="Cross-module health overview"
      icon={<BarChart3 className="w-7 h-7 text-lsc-rose" />}
    >
      {isLoading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="w-6 h-6 animate-spin text-lsc-rose" />
          <span className="ml-3 text-sm text-lsc-dark/60 dark:text-lsc-cream/50">
            Loading collection data...
          </span>
        </div>
      ) : (
        <div className="space-y-8">
          {/* ─── Stats Cards ─── */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <StatCard
              label="Total Items"
              value={intel?.total_items?.toLocaleString() ?? "0"}
              sub="Active (excl. withdrawn)"
              icon={Package}
              href="/staff/inventory"
            />
            <StatCard
              label="In Circulation"
              value={`${intel?.circulation_pct ?? 0}%`}
              sub={`${intel?.in_circulation?.toLocaleString() ?? 0} items checked out`}
              icon={TrendingUp}
            />
            <StatCard
              label="Poor / Damaged"
              value={intel?.poor_damaged ?? 0}
              sub="Items needing attention"
              icon={AlertTriangle}
              href="/staff/weeding"
              accent={(intel?.poor_damaged ?? 0) > 0}
            />
            <StatCard
              label="Processing Queue"
              value={processing?.total_in_processing ?? 0}
              sub="Awaiting processing"
              icon={ClipboardCheck}
              href="/staff/processing"
              accent={(processing?.total_in_processing ?? 0) > 10}
            />
          </div>

          {/* ─── Condition Breakdown ─── */}
          {intel?.condition_breakdown && (
            <section>
              <h2 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-3">
                Condition Breakdown
              </h2>
              <div className="rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 p-5">
                <ConditionBar breakdown={intel.condition_breakdown} />
              </div>
            </section>
          )}

          {/* ─── Alerts ─── */}
          <section>
            <h2 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-3">
              Alerts
            </h2>
            <div className="space-y-2">
              <AlertRow
                icon={ScanLine}
                label="Shelf reads overdue"
                count={intel?.overdue_shelf_reads ?? 0}
                href="/staff/shelf-reading"
                color="text-status-warning-500"
              />
              <AlertRow
                icon={Leaf}
                label="Weeding candidates awaiting review"
                count={weedingPending}
                href="/staff/weeding"
                color="text-status-warning-500"
              />
              <AlertRow
                icon={ClipboardCheck}
                label="Items in processing queue"
                count={processing?.total_in_processing ?? 0}
                href="/staff/processing"
              />
              <AlertRow
                icon={AlertTriangle}
                label="Sections over capacity"
                count={weeding?.sections_over_capacity ?? 0}
                href="/staff/weeding"
                color="text-status-danger-500"
              />
              {(intel?.overdue_shelf_reads ?? 0) === 0 &&
                weedingPending === 0 &&
                (processing?.total_in_processing ?? 0) === 0 &&
                (weeding?.sections_over_capacity ?? 0) === 0 && (
                  <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 px-4 py-3">
                    No alerts at this time.
                  </p>
                )}
            </div>
          </section>

          {/* ─── Recent Activity ─── */}
          {intel?.recent_events && intel.recent_events.length > 0 && (
            <section>
              <h2 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-3">
                Recent Activity
              </h2>
              <div className="rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 divide-y divide-lsc-border/50 dark:divide-earth-700/50">
                {intel.recent_events.map((evt) => (
                  <Link
                    key={evt.id}
                    to={`/staff/lifecycle`}
                    className="flex items-center gap-3 px-5 py-3 hover:bg-lsc-cream/50 dark:hover:bg-earth-700/50 transition-colors group"
                  >
                    <Activity className="w-4 h-4 text-lsc-dark/40 dark:text-lsc-cream/40 flex-shrink-0" />
                    <div className="min-w-0 flex-1">
                      <p className="text-sm text-lsc-dark dark:text-lsc-cream truncate">
                        <span className="font-medium">
                          {EVENT_TYPE_LABELS[evt.event_type] || evt.event_type}
                        </span>
                        {" "}
                        <span className="text-lsc-dark/60 dark:text-lsc-cream/50">
                          {evt.title}
                        </span>
                      </p>
                      {evt.description && (
                        <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 truncate">
                          {evt.description}
                        </p>
                      )}
                    </div>
                    <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 flex-shrink-0">
                      {formatRelativeTime(evt.created_at)}
                    </span>
                  </Link>
                ))}
              </div>
            </section>
          )}
        </div>
      )}
    </AdminShell>
  )
}
