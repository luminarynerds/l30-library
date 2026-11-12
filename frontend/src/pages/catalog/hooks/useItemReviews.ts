/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import { useState, useCallback, useMemo } from "react"
import { useQuery } from "@tanstack/react-query"
import { apiClient } from "@/lib/api-client"

interface SimilarItemsPreferences {
  enabled: boolean
  count: 3 | 6 | 9
  strategy: "subject" | "author" | "type" | "mixed"
}

const DEFAULT_SIMILAR_ITEMS_PREFS: SimilarItemsPreferences = {
  enabled: true,
  count: 3,
  strategy: "mixed",
}

export interface RecommendationItem {
  id: number
  title: string
  author: string | null
  is_pinned: boolean
  cover_image: string | null
  available: boolean
  source?: string
}

export interface RecommendationsResponse {
  items: RecommendationItem[]
  total_pinned: number
  algorithm_used: string
}

export function useItemReviews(item: { id: number } | undefined) {
  const [preferences, setPreferences] = useState<SimilarItemsPreferences>(getSimilarItemsPreferences)
  const [showSettings, setShowSettings] = useState(false)

  const { data: recommendationsData, isLoading } = useQuery({
    queryKey: ["recommendations", item?.id, preferences.count],
    queryFn: async (): Promise<RecommendationsResponse> => {
      if (!item) return { items: [], total_pinned: 0, algorithm_used: "" }
      return apiClient<RecommendationsResponse>(
        `/catalog/${item.id}/recommendations`,
        { params: { limit: preferences.count } }
      )
    },
    enabled: preferences.enabled && !!item?.id,
  })

  const handlePreferenceChange = useCallback((updates: Partial<SimilarItemsPreferences>) => {
    const newPrefs = { ...preferences, ...updates }
    setPreferences(newPrefs)
    saveSimilarItemsPreferences(newPrefs)
  }, [preferences])

  const rawItems = recommendationsData?.items || []
  const sortedItems = useMemo(
    () => [...rawItems].sort((a, b) => {
      if (a.available === b.available) return 0
      return a.available ? -1 : 1
    }),
    [rawItems]
  )
  const availableCount = useMemo(
    () => sortedItems.filter((i) => i.available).length,
    [sortedItems]
  )

  return {
    preferences,
    showSettings,
    setShowSettings,
    similarItems: sortedItems,
    availableCount,
    totalPinned: recommendationsData?.total_pinned || 0,
    algorithmUsed: recommendationsData?.algorithm_used || "",
    isLoading,
    handlePreferenceChange,
  }
}

function getSimilarItemsPreferences(): SimilarItemsPreferences {
  try {
    const stored = localStorage.getItem("similarItemsPreferences")
    if (stored) {
      return { ...DEFAULT_SIMILAR_ITEMS_PREFS, ...JSON.parse(stored) }
    }
  } catch (err: unknown) {
    Sentry.captureException(err instanceof Error ? err : new Error(String(err)))
  }
  return DEFAULT_SIMILAR_ITEMS_PREFS
}

function saveSimilarItemsPreferences(prefs: SimilarItemsPreferences): void {
  try {
    localStorage.setItem("similarItemsPreferences", JSON.stringify(prefs))
  } catch (err: unknown) {
    Sentry.captureException(err instanceof Error ? err : new Error(String(err)))
  }
}

export type { SimilarItemsPreferences }
