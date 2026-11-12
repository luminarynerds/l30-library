/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { getStatisticsSummary } from "@/api/book-drop-api"

export interface StatsDateRange {
  start: string
  end: string
}

const today = () => new Date().toISOString().split("T")[0] ?? ""
const daysAgo = (n: number) =>
  new Date(Date.now() - n * 24 * 60 * 60 * 1000).toISOString().split("T")[0] ?? ""

export const statsQueryKey = (start: string, end: string) =>
  ["book-drop-stats", start, end] as const

export function useBookDropStats(token: string | null) {
  const [statsDateRange, setStatsDateRange] = useState<StatsDateRange>({
    start: daysAgo(30),
    end: today(),
  })

  const summaryQuery = useQuery({
    queryKey: statsQueryKey(statsDateRange.start, statsDateRange.end),
    queryFn: () => getStatisticsSummary(token!, statsDateRange.start, statsDateRange.end),
    enabled: !!token,
  })

  const todayKey = today()
  const todayQuery = useQuery({
    queryKey: statsQueryKey(todayKey, todayKey),
    queryFn: () => getStatisticsSummary(token!, todayKey, todayKey),
    enabled: !!token,
  })

  return {
    statisticsSummary: summaryQuery.data ?? null,
    todaySummary: todayQuery.data ?? null,
    statsDateRange,
    isLoading: summaryQuery.isLoading,
    setStatsDateRange,
  }
}
