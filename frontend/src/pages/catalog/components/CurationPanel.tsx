/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Pin, PinOff, EyeOff, ArrowUp, ArrowDown, Search, X, Loader2 } from "lucide-react"
import toast from "react-hot-toast"
import { apiClient } from "@/lib/api-client"
import { searchCatalog } from "@/api/domains/catalog/catalog-api"
import { Button } from "@/components/ui/Button"
import type { RecommendationItem, RecommendationsResponse } from "../hooks/useItemReviews"

interface CurationPanelProps {
  itemId: number
  onClose: () => void
}

export function CurationPanel({ itemId, onClose }: CurationPanelProps) {
  const queryClient = useQueryClient()
  const [searchQuery, setSearchQuery] = useState("")
  const [staffNotes, setStaffNotes] = useState<Record<number, string>>({})

  const { data: recommendations, isLoading } = useQuery({
    queryKey: ["recommendations", itemId, 9],
    queryFn: () => apiClient<RecommendationsResponse>(
      `/catalog/${itemId}/recommendations`,
      { params: { limit: 9 } }
    ),
  })

  const { data: searchResults, isFetching: isSearching } = useQuery({
    queryKey: ["curation-search", searchQuery],
    queryFn: () => searchCatalog({ query: searchQuery, per_page: 10 }),
    enabled: searchQuery.length >= 2,
  })

  const invalidateRecs = () => {
    queryClient.invalidateQueries({ queryKey: ["recommendations", itemId] })
  }

  const pinMutation = useMutation({
    mutationFn: (params: { targetItemId: number; action: "pin" | "remove" | "hide"; displayOrder?: number; staffNote?: string }) =>
      apiClient(`/staff/catalog/${itemId}/recommendations`, {
        method: "POST",
        body: JSON.stringify({
          target_item_id: params.targetItemId,
          action: params.action,
          display_order: params.displayOrder,
          staff_note: params.staffNote,
        }),
      }),
    onSuccess: (_data, variables) => {
      invalidateRecs()
      const messages = { pin: "Item pinned", remove: "Item unpinned", hide: "Item hidden" }
      toast.success(messages[variables.action])
    },
    onError: () => {
      toast.error("That didn't work. Please try again, or ask a librarian for help.")
    },
  })

  const reorderMutation = useMutation({
    mutationFn: (itemIds: number[]) =>
      apiClient(`/staff/catalog/${itemId}/recommendations/reorder`, {
        method: "PUT",
        body: JSON.stringify({ item_ids: itemIds }),
      }),
    onSuccess: () => {
      invalidateRecs()
      toast.success("Order updated")
    },
    onError: () => {
      toast.error("Couldn't save the new order. Please try again.")
    },
  })

  const pinnedItems = (recommendations?.items || []).filter(i => i.is_pinned)
  const algorithmItems = (recommendations?.items || []).filter(i => !i.is_pinned)

  const handleReorder = (index: number, direction: "up" | "down") => {
    const ids = pinnedItems.map(i => i.id)
    const newIndex = direction === "up" ? index - 1 : index + 1
    if (newIndex < 0 || newIndex >= ids.length) return
    const swap = ids[index]
    const target = ids[newIndex]
    if (swap === undefined || target === undefined) return
    ids[index] = target
    ids[newIndex] = swap
    reorderMutation.mutate(ids)
  }

  const handlePin = (targetItemId: number) => {
    const note = staffNotes[targetItemId]
    pinMutation.mutate({ targetItemId, action: "pin", staffNote: note || undefined })
  }

  return (
    <div className="mt-4 p-4 bg-status-warning-50 dark:bg-status-warning-900/20 border border-status-warning-200 dark:border-status-warning-800 rounded-xl">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-medium text-lsc-dark dark:text-lsc-cream">Curate Recommendations</h3>
        <Button variant="tertiary" size="sm" onClick={onClose} aria-label="Close curation panel">
          <X className="w-4 h-4" />
        </Button>
      </div>

      {/* Search to add pins */}
      <div className="mb-4">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-earth-600" aria-hidden="true" />
          <input
            type="text"
            placeholder="Search catalog to pin an item..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-3 py-2 text-sm border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream placeholder:text-earth-400 focus:outline-none focus:ring-2 focus:ring-lsc-rose"
          />
          {isSearching && <Loader2 className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 motion-safe:animate-spin text-earth-600" />}
        </div>

        {searchResults?.items && searchResults.items.length > 0 && (
          <div className="mt-2 max-h-48 overflow-y-auto border border-lsc-border dark:border-earth-700 rounded-lg divide-y divide-lsc-border dark:divide-earth-700">
            {searchResults.items
              .filter(sr => sr.id !== itemId)
              .map((result) => (
                <div key={result.id} className="flex items-center justify-between p-2 text-sm">
                  <div className="min-w-0 flex-1">
                    <span className="font-medium text-lsc-dark dark:text-lsc-cream truncate block">{result.title}</span>
                    {result.author && <span className="text-earth-600 dark:text-earth-400 text-xs">{result.author}</span>}
                  </div>
                  <div className="flex items-center gap-2 ml-2 flex-shrink-0">
                    <input
                      type="text"
                      placeholder="Note..."
                      value={staffNotes[result.id] || ""}
                      onChange={(e) => setStaffNotes(prev => ({ ...prev, [result.id]: e.target.value }))}
                      className="w-24 px-2 py-1 text-xs border border-lsc-border dark:border-earth-700 rounded bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
                    />
                    <Button
                      variant="primary"
                      size="sm"
                      onClick={() => handlePin(result.id)}
                      disabled={pinMutation.isPending}
                      aria-label={`Pin ${result.title}`}
                    >
                      <Pin className="w-3 h-3" />
                    </Button>
                  </div>
                </div>
              ))}
          </div>
        )}
      </div>

      {/* Pinned items */}
      {pinnedItems.length > 0 && (
        <div className="mb-4">
          <h4 className="text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
            Pinned ({pinnedItems.length})
          </h4>
          <div className="space-y-2">
            {pinnedItems.map((rec: RecommendationItem, idx: number) => (
              <div key={rec.id} className="flex items-center gap-2 p-2 bg-lsc-white dark:bg-earth-900 rounded-lg border border-lsc-border dark:border-earth-700">
                <div className="flex flex-col gap-0.5">
                  <button
                    onClick={() => handleReorder(idx, "up")}
                    disabled={idx === 0 || reorderMutation.isPending}
                    className="p-0.5 text-earth-600 hover:text-lsc-dark dark:hover:text-lsc-cream disabled:opacity-30"
                    aria-label="Move up"
                  >
                    <ArrowUp className="w-3 h-3" />
                  </button>
                  <button
                    onClick={() => handleReorder(idx, "down")}
                    disabled={idx === pinnedItems.length - 1 || reorderMutation.isPending}
                    className="p-0.5 text-earth-600 hover:text-lsc-dark dark:hover:text-lsc-cream disabled:opacity-30"
                    aria-label="Move down"
                  >
                    <ArrowDown className="w-3 h-3" />
                  </button>
                </div>
                <div className="flex-1 min-w-0">
                  <span className="text-sm font-medium text-lsc-dark dark:text-lsc-cream truncate block">{rec.title}</span>
                  {rec.author && <span className="text-xs text-earth-600 dark:text-earth-400">{rec.author}</span>}
                </div>
                <Button
                  variant="tertiary"
                  size="sm"
                  onClick={() => pinMutation.mutate({ targetItemId: rec.id, action: "remove" })}
                  disabled={pinMutation.isPending}
                  aria-label={`Unpin ${rec.title}`}
                  title="Unpin"
                >
                  <PinOff className="w-3.5 h-3.5" />
                </Button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Algorithm items (can hide) */}
      {isLoading ? (
        <div className="flex justify-center py-4">
          <Loader2 className="w-5 h-5 motion-safe:animate-spin text-earth-600" />
        </div>
      ) : algorithmItems.length > 0 ? (
        <div>
          <h4 className="text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
            Algorithm suggestions
          </h4>
          <div className="space-y-2">
            {algorithmItems.map((rec: RecommendationItem) => (
              <div key={rec.id} className="flex items-center gap-2 p-2 bg-lsc-white dark:bg-earth-900 rounded-lg border border-lsc-border dark:border-earth-700">
                <div className="flex-1 min-w-0">
                  <span className="text-sm text-lsc-dark dark:text-lsc-cream truncate block">{rec.title}</span>
                  {rec.author && <span className="text-xs text-earth-600 dark:text-earth-400">{rec.author}</span>}
                </div>
                <div className="flex gap-1">
                  <Button
                    variant="tertiary"
                    size="sm"
                    onClick={() => handlePin(rec.id)}
                    disabled={pinMutation.isPending}
                    aria-label={`Pin ${rec.title}`}
                    title="Pin"
                  >
                    <Pin className="w-3.5 h-3.5" />
                  </Button>
                  <Button
                    variant="tertiary"
                    size="sm"
                    onClick={() => pinMutation.mutate({ targetItemId: rec.id, action: "hide" })}
                    disabled={pinMutation.isPending}
                    aria-label={`Hide ${rec.title}`}
                    title="Hide"
                  >
                    <EyeOff className="w-3.5 h-3.5" />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  )
}
