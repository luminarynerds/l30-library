/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useMemo, useEffect } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { AdminShell } from '../../components/shells/AdminShell'
import {
  Wrench, Trash2, RefreshCw, DollarSign,
  Loader2, AlertTriangle, Check, X,
} from "lucide-react"
import toast from "react-hot-toast"
import { getInventoryCopies, withdrawCopy, repairCopy } from "../../api/domains/catalog/inventory-api"
import { formatCurrency } from "../../utils/format-utils"

interface RepairQueueItem {
  id: number
  catalog_item_id: number
  barcode: string
  condition: string
  replacement_cost: number | null
  catalog_title: string | null
  catalog_author: string | null
  location: string | null
  notes: string | null
}

type Decision = "repair" | "withdraw_replace" | "withdraw_no_replace" | "keep"

interface ItemDecision {
  decision: Decision | ""
  repairEstimate: string
  repairNotes: string
}

const DRAFTS_KEY = "l30_repair_queue_drafts"

function loadDrafts(): Record<number, ItemDecision> {
  try {
    return JSON.parse(localStorage.getItem(DRAFTS_KEY) || "{}")
  } catch {
    return {}
  }
}

export default function RepairQueuePage() {
  const queryClient = useQueryClient()
  const [decisions, setDecisions] = useState<Record<number, ItemDecision>>(loadDrafts)
  const [dismissed, setDismissed] = useState<Set<number>>(new Set())
  const [conditionFilter, setConditionFilter] = useState<"all" | "damaged" | "poor">("all")

  // Persist triage drafts so they survive an interrupted session.
  useEffect(() => {
    localStorage.setItem(DRAFTS_KEY, JSON.stringify(decisions))
  }, [decisions])

  const clearDraft = (id: number) => {
    setDecisions((prev) => {
      if (!(id in prev)) return prev
      const next = { ...prev }
      delete next[id]
      return next
    })
  }

  // Fetch damaged items
  const damagedQuery = useQuery({
    queryKey: ["repair-queue", "damaged"],
    queryFn: () => getInventoryCopies({ condition: "damaged", per_page: 100 }),
  })

  // Fetch poor items
  const poorQuery = useQuery({
    queryKey: ["repair-queue", "poor"],
    queryFn: () => getInventoryCopies({ condition: "poor", per_page: 100 }),
  })

  const isLoading = damagedQuery.isLoading || poorQuery.isLoading
  const isError = damagedQuery.isError || poorQuery.isError

  // Merge and deduplicate
  const allItems: RepairQueueItem[] = useMemo(() => {
    const damaged = (damagedQuery.data?.items ?? []) as unknown as RepairQueueItem[]
    const poor = (poorQuery.data?.items ?? []) as unknown as RepairQueueItem[]
    const combined = [...damaged, ...poor]
    const seen = new Set<number>()
    return combined.filter((item) => {
      if (seen.has(item.id)) return false
      seen.add(item.id)
      return true
    })
  }, [damagedQuery.data, poorQuery.data])

  // Filter out dismissed items and apply condition filter
  const visibleItems = useMemo(() => {
    return allItems.filter((item) => {
      if (dismissed.has(item.id)) return false
      if (conditionFilter === "damaged") return item.condition === "damaged"
      if (conditionFilter === "poor") return item.condition === "poor"
      return true
    })
  }, [allItems, dismissed, conditionFilter])

  // Stats
  const stats = useMemo(() => {
    const active = allItems.filter((i) => !dismissed.has(i.id))
    const damagedCount = active.filter((i) => i.condition === "damaged").length
    const poorCount = active.filter((i) => i.condition === "poor").length
    const totalReplacementCost = active.reduce(
      (sum, i) => sum + (i.replacement_cost ?? 0),
      0
    )
    return { total: active.length, damaged: damagedCount, poor: poorCount, totalReplacementCost }
  }, [allItems, dismissed])

  // Withdraw mutation
  const withdrawMutation = useMutation({
    mutationFn: ({ copyId, reason }: { copyId: number; reason: string }) =>
      withdrawCopy(copyId, reason),
    onSuccess: (_data, vars) => {
      toast.success("Item withdrawn")
      clearDraft(vars.copyId)
      setDismissed((prev) => new Set(prev).add(vars.copyId))
      queryClient.invalidateQueries({ queryKey: ["repair-queue"] })
    },
    onError: (err: Error) => {
      toast.error(err.message || "Failed to withdraw item")
    },
  })

  // Repair mutation
  const repairMutation = useMutation({
    mutationFn: ({ copyId, notes, cost }: { copyId: number; notes: string; cost?: number }) =>
      repairCopy(copyId, {
        new_condition: "good",
        repair_notes: notes || "Sent to repair from repair queue",
        repair_cost: cost,
      }),
    onSuccess: (_data, vars) => {
      toast.success("Item sent to repair")
      clearDraft(vars.copyId)
      setDismissed((prev) => new Set(prev).add(vars.copyId))
      queryClient.invalidateQueries({ queryKey: ["repair-queue"] })
    },
    onError: (err: Error) => {
      toast.error(err.message || "Failed to send item to repair")
    },
  })

  const getDecision = (id: number): ItemDecision =>
    decisions[id] ?? { decision: "", repairEstimate: "", repairNotes: "" }

  const updateDecision = (id: number, patch: Partial<ItemDecision>) => {
    setDecisions((prev) => ({
      ...prev,
      [id]: { ...getDecision(id), ...patch },
    }))
  }

  const handleAction = (item: RepairQueueItem) => {
    const d = getDecision(item.id)
    const repairCostNum = d.repairEstimate ? parseFloat(d.repairEstimate) : undefined

    switch (d.decision) {
      case "repair":
        repairMutation.mutate({
          copyId: item.id,
          notes: d.repairNotes || "Repair authorized from repair queue",
          cost: repairCostNum,
        })
        break
      case "withdraw_replace":
        withdrawMutation.mutate({
          copyId: item.id,
          reason: "Withdrawn for replacement (damaged/poor condition)",
        })
        break
      case "withdraw_no_replace":
        withdrawMutation.mutate({
          copyId: item.id,
          reason: "Withdrawn without replacement (damaged/poor condition)",
        })
        break
      case "keep":
        clearDraft(item.id)
        setDismissed((prev) => new Set(prev).add(item.id))
        toast.success("Item dismissed from queue")
        break
    }
  }

  const isBusy = withdrawMutation.isPending || repairMutation.isPending

  const conditionBadge = (condition: string) => {
    const colors =
      condition === "damaged"
        ? "bg-status-danger-100 dark:bg-status-danger-900/30 text-status-danger-700 dark:text-status-danger-300"
        : "bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-700 dark:text-status-warning-300"
    return (
      <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${colors}`}>
        {condition}
      </span>
    )
  }

  return (
    <AdminShell
      title="Repair Queue"
      subtitle="Damaged and poor condition items awaiting disposition"
      icon={<Wrench className="w-7 h-7 text-lsc-rose" />}
    >
      {/* Stats bar */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-xl p-4">
          <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 uppercase tracking-wider">Total in Queue</p>
          <p className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mt-1">{stats.total}</p>
        </div>
        <div className="bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-xl p-4">
          <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 uppercase tracking-wider">Damaged</p>
          <p className="text-2xl font-serif font-bold text-status-danger-600 dark:text-status-danger-400 mt-1">{stats.damaged}</p>
        </div>
        <div className="bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-xl p-4">
          <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 uppercase tracking-wider">Poor</p>
          <p className="text-2xl font-serif font-bold text-status-warning-600 dark:text-status-warning-400 mt-1">{stats.poor}</p>
        </div>
        <div className="bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-xl p-4">
          <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 uppercase tracking-wider flex items-center gap-1">
            <DollarSign className="w-3 h-3" /> Est. Replacement
          </p>
          <p className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mt-1">
            {formatCurrency(stats.totalReplacementCost)}
          </p>
        </div>
      </div>

      {/* Filter bar */}
      <div className="flex items-center gap-2 mb-4">
        <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Filter:</span>
        {(["all", "damaged", "poor"] as const).map((f) => (
          <button
            key={f}
            onClick={() => setConditionFilter(f)}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
              conditionFilter === f
                ? "bg-lsc-rose text-lsc-white"
                : "bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream border border-lsc-border dark:border-earth-600 hover:bg-lsc-cream/50 dark:hover:bg-earth-600"
            }`}
          >
            {f === "all" ? "All" : f.charAt(0).toUpperCase() + f.slice(1)}
          </button>
        ))}
        <button
          onClick={() => {
            damagedQuery.refetch()
            poorQuery.refetch()
          }}
          className="ml-auto flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream border border-lsc-border dark:border-earth-600 hover:bg-lsc-cream/50 dark:hover:bg-earth-600 transition-colors"
        >
          <RefreshCw className="w-3.5 h-3.5" /> Refresh
        </button>
      </div>

      {/* Loading state */}
      {isLoading && (
        <div className="flex items-center justify-center py-16">
          <Loader2 className="w-6 h-6 animate-spin text-lsc-rose" />
          <span className="ml-2 text-lsc-dark/70 dark:text-lsc-cream/70">Loading repair queue...</span>
        </div>
      )}

      {/* Error state */}
      {isError && (
        <div className="flex items-center gap-2 p-4 rounded-xl bg-status-danger-50 dark:bg-status-danger-900/20 text-status-danger-700 dark:text-status-danger-300 border border-status-danger-200 dark:border-status-danger-800">
          <AlertTriangle className="w-5 h-5 flex-shrink-0" />
          <p>Failed to load repair queue. Please try again.</p>
        </div>
      )}

      {/* Empty state */}
      {!isLoading && !isError && visibleItems.length === 0 && (
        <div className="text-center py-16">
          <Check className="w-12 h-12 mx-auto text-status-success-500" />
          <p className="mt-4 text-lg font-medium text-lsc-dark dark:text-lsc-cream">Queue is clear</p>
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">No items need repair decisions right now.</p>
        </div>
      )}

      {/* Item cards */}
      {!isLoading && !isError && visibleItems.length > 0 && (
        <div className="space-y-4">
          {visibleItems.map((item) => {
            const d = getDecision(item.id)
            const repairCostNum = d.repairEstimate ? parseFloat(d.repairEstimate) : null

            return (
              <div
                key={item.id}
                className="bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-xl p-5"
              >
                {/* Item header */}
                <div className="flex flex-col sm:flex-row sm:items-start gap-3 mb-4">
                  <div className="flex-1 min-w-0">
                    <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream truncate">
                      {item.catalog_title || "Unknown Title"}
                    </h3>
                    <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                      {item.catalog_author || "Unknown Author"}
                    </p>
                    <div className="flex flex-wrap items-center gap-2 mt-1.5 text-xs text-lsc-dark/60 dark:text-lsc-cream/70">
                      <span className="font-mono">{item.barcode}</span>
                      {item.location && <span>| {item.location}</span>}
                    </div>
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    {conditionBadge(item.condition)}
                  </div>
                </div>

                {/* Cost comparison */}
                <div className="bg-earth-50 dark:bg-earth-900/50 rounded-lg p-3 mb-4">
                  <div className="flex flex-col sm:flex-row sm:items-center gap-3">
                    <div className="flex items-center gap-2">
                      <DollarSign className="w-4 h-4 text-lsc-dark/50 dark:text-lsc-cream/70" />
                      <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Estimated repair:</span>
                      <div className="relative">
                        <span className="absolute left-2 top-1/2 -translate-y-1/2 text-sm text-lsc-dark/50 dark:text-lsc-cream/70">$</span>
                        <input
                          type="number"
                          min="0"
                          step="0.01"
                          placeholder="0.00"
                          value={d.repairEstimate}
                          onChange={(e) => updateDecision(item.id, { repairEstimate: e.target.value })}
                          className="w-24 pl-6 pr-2 py-1 text-sm rounded border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-1 focus:ring-lsc-rose/50"
                        />
                      </div>
                    </div>
                    <span className="text-lsc-dark/30 dark:text-lsc-cream/20 hidden sm:inline">|</span>
                    <div className="flex items-center gap-2">
                      <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Replacement:</span>
                      <span className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
                        {item.replacement_cost != null
                          ? formatCurrency(item.replacement_cost)
                          : "Not set"}
                      </span>
                    </div>
                    {repairCostNum != null && item.replacement_cost != null && (
                      <>
                        <span className="text-lsc-dark/30 dark:text-lsc-cream/20 hidden sm:inline">|</span>
                        <span
                          className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                            repairCostNum <= item.replacement_cost
                              ? "bg-status-success-100 dark:bg-status-success-900/30 text-status-success-700 dark:text-status-success-300"
                              : "bg-status-danger-100 dark:bg-status-danger-900/30 text-status-danger-700 dark:text-status-danger-300"
                          }`}
                        >
                          {repairCostNum <= item.replacement_cost
                            ? `Repair saves ${formatCurrency(item.replacement_cost - repairCostNum)}`
                            : `Replacement saves ${formatCurrency(repairCostNum - item.replacement_cost)}`}
                        </span>
                      </>
                    )}
                  </div>
                </div>

                {/* Repair notes (shown when repair is selected) */}
                {d.decision === "repair" && (
                  <div className="mb-4">
                    <label className="block text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                      Repair notes
                    </label>
                    <input
                      type="text"
                      placeholder="Describe repair needed..."
                      value={d.repairNotes}
                      onChange={(e) => updateDecision(item.id, { repairNotes: e.target.value })}
                      className="w-full px-3 py-1.5 text-sm rounded-lg border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream placeholder:text-lsc-dark/40 dark:placeholder:text-lsc-cream/70 focus:outline-none focus:ring-1 focus:ring-lsc-rose/50"
                    />
                  </div>
                )}

                {/* Decision buttons */}
                <div className="flex flex-wrap gap-2">
                  <button
                    onClick={() => updateDecision(item.id, { decision: "repair" })}
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                      d.decision === "repair"
                        ? "bg-lsc-rose text-lsc-white"
                        : "bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream border border-lsc-border dark:border-earth-600 hover:bg-lsc-cream/50 dark:hover:bg-earth-600"
                    }`}
                  >
                    <Wrench className="w-3.5 h-3.5" /> Send to Repair
                  </button>
                  <button
                    onClick={() => updateDecision(item.id, { decision: "withdraw_replace" })}
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                      d.decision === "withdraw_replace"
                        ? "bg-status-danger-600 text-white"
                        : "bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream border border-lsc-border dark:border-earth-600 hover:bg-lsc-cream/50 dark:hover:bg-earth-600"
                    }`}
                  >
                    <RefreshCw className="w-3.5 h-3.5" /> Withdraw &amp; Replace
                  </button>
                  <button
                    onClick={() => updateDecision(item.id, { decision: "withdraw_no_replace" })}
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                      d.decision === "withdraw_no_replace"
                        ? "bg-status-danger-600 text-white"
                        : "bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream border border-lsc-border dark:border-earth-600 hover:bg-lsc-cream/50 dark:hover:bg-earth-600"
                    }`}
                  >
                    <Trash2 className="w-3.5 h-3.5" /> Withdraw &amp; Don&apos;t Replace
                  </button>
                  <button
                    onClick={() => updateDecision(item.id, { decision: "keep" })}
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                      d.decision === "keep"
                        ? "bg-earth-600 text-white"
                        : "bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream border border-lsc-border dark:border-earth-600 hover:bg-lsc-cream/50 dark:hover:bg-earth-600"
                    }`}
                  >
                    <X className="w-3.5 h-3.5" /> Keep As-Is
                  </button>

                  {/* Confirm button */}
                  {d.decision && (
                    <button
                      onClick={() => handleAction(item)}
                      disabled={isBusy}
                      className="ml-auto flex items-center gap-1.5 px-4 py-1.5 rounded-lg text-sm font-medium bg-status-success-600 hover:bg-status-success-700 text-white transition-colors disabled:opacity-50"
                    >
                      {isBusy ? (
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      ) : (
                        <Check className="w-3.5 h-3.5" />
                      )}
                      Confirm
                    </button>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </AdminShell>
  )
}
