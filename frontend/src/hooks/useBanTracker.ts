/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect, useCallback, useRef } from 'react'
import { useSearchParams } from 'react-router-dom'
import { API_BASE } from '@/api/types'
import api from '@/lib/api-client'
import { normalizeStats } from '@/components/ban-tracker/ban-tracker-data'
import type { BanStats, BanStatsRaw, BanReport, BanReportsResponse, MostBannedBook } from '@/components/ban-tracker/types'

const PER_PAGE = 20

// URL param keys
const P_Q = 'q'
const P_STATE = 'state'
const P_BAN_TYPE = 'ban_type'
const P_REASON = 'reason'
const P_SOURCE = 'source'
const P_PAGE = 'page'

export function useBanTracker() {
  const [searchParams, setSearchParams] = useSearchParams()

  // Initial values are read once from URL; subsequent updates flow through local setters,
  // which write to both local state AND searchParams. We do NOT echo searchParams back into
  // local state on every render — that would create a write/read loop.
  const initial = useRef({
    q: searchParams.get(P_Q) ?? '',
    state: searchParams.get(P_STATE) ?? '',
    banType: searchParams.get(P_BAN_TYPE) ?? '',
    reason: searchParams.get(P_REASON) ?? '',
    source: searchParams.get(P_SOURCE) ?? '',
    page: (() => {
      const n = parseInt(searchParams.get(P_PAGE) ?? '1', 10)
      return Number.isFinite(n) && n > 0 ? n : 1
    })(),
  })

  const [stats, setStats] = useState<BanStats | null>(null)
  const [statsLoading, setStatsLoading] = useState(true)
  const [statsError, setStatsError] = useState<string | null>(null)

  const [reports, setReports] = useState<BanReport[]>([])
  const [reportsLoading, setReportsLoading] = useState(true)
  const [reportsError, setReportsError] = useState<string | null>(null)
  const [page, setPage] = useState(initial.current.page)
  const [totalPages, setTotalPages] = useState(1)
  const [totalReports, setTotalReports] = useState(0)

  const [catalogMatches, setCatalogMatches] = useState<BanReport[]>([])
  const [mostBanned, setMostBanned] = useState<MostBannedBook[]>([])

  const [searchQuery, setSearchQuery] = useState(initial.current.q)
  const [selectedState, setSelectedState] = useState(initial.current.state)
  const [selectedBanType, setSelectedBanType] = useState(initial.current.banType)
  const [selectedReason, setSelectedReason] = useState(initial.current.reason)
  const [selectedSource, setSelectedSource] = useState(initial.current.source)
  const [searchDebounced, setSearchDebounced] = useState(initial.current.q)

  useEffect(() => {
    const timer = setTimeout(() => {
      setSearchDebounced(searchQuery)
    }, 350)
    return () => clearTimeout(timer)
  }, [searchQuery])

  // Reset page to 1 when filters change (other than page itself).
  useEffect(() => {
    setPage(1)
  }, [searchDebounced, selectedState, selectedBanType, selectedReason, selectedSource])

  // Sync URL params from debounced filter values + current page.
  // Skip the first render so we don't churn the URL on mount with already-present params.
  const didMountSync = useRef(false)
  useEffect(() => {
    if (!didMountSync.current) {
      didMountSync.current = true
      return
    }
    const next = new URLSearchParams()
    if (searchDebounced.trim()) next.set(P_Q, searchDebounced.trim())
    if (selectedState) next.set(P_STATE, selectedState)
    if (selectedBanType) next.set(P_BAN_TYPE, selectedBanType)
    if (selectedReason) next.set(P_REASON, selectedReason)
    if (selectedSource) next.set(P_SOURCE, selectedSource)
    if (page > 1) next.set(P_PAGE, String(page))
    setSearchParams(next, { replace: true })
  }, [searchDebounced, selectedState, selectedBanType, selectedReason, selectedSource, page, setSearchParams])

  useEffect(() => {
    let cancelled = false
    const loadStats = async () => {
      setStatsLoading(true)
      setStatsError(null)
      try {
        const raw: BanStatsRaw = await api.get(`${API_BASE}/ban-tracker/public/stats`)
        if (!cancelled) setStats(normalizeStats(raw))
      } catch (err: unknown) {
        if (!cancelled) {
          const e = err as { message?: string }
          setStatsError(e?.message ?? 'Failed to load statistics')
        }
      } finally {
        if (!cancelled) setStatsLoading(false)
      }
    }
    loadStats()
    return () => { cancelled = true }
  }, [])

  useEffect(() => {
    let cancelled = false
    const loadCatalogMatches = async () => {
      try {
        const data: BanReport[] = await api.get(`${API_BASE}/ban-tracker/public/catalog-matches`)
        if (!cancelled) setCatalogMatches(data)
      } catch {
        // Non-critical — section simply won't render
      }
    }
    loadCatalogMatches()
    return () => { cancelled = true }
  }, [])

  useEffect(() => {
    let cancelled = false
    const loadMostBanned = async () => {
      try {
        const data: MostBannedBook[] = await api.get(`${API_BASE}/ban-tracker/public/most-banned`)
        if (!cancelled) setMostBanned(data)
      } catch {
        // Non-critical — section simply won't render
      }
    }
    loadMostBanned()
    return () => { cancelled = true }
  }, [])

  const loadReports = useCallback(async () => {
    setReportsLoading(true)
    setReportsError(null)
    try {
      const params = new URLSearchParams()
      params.set('page', String(page))
      params.set('per_page', String(PER_PAGE))
      if (selectedState) params.set('state', selectedState)
      if (selectedBanType) params.set('ban_type', selectedBanType)
      if (selectedReason) params.set('reason_category', selectedReason)
      if (selectedSource) params.set('source', selectedSource)
      if (searchDebounced.trim()) params.set('search', searchDebounced.trim())

      const data: BanReportsResponse = await api.get(
        `${API_BASE}/ban-tracker/public/reports?${params.toString()}`
      )
      setReports(data.items)
      setTotalPages(data.pages)
      setTotalReports(data.total)
    } catch (err: unknown) {
      const e = err as { message?: string }
      setReportsError(e?.message ?? 'Failed to load reports')
    } finally {
      setReportsLoading(false)
    }
  }, [page, selectedState, selectedBanType, selectedReason, selectedSource, searchDebounced])

  useEffect(() => {
    loadReports()
  }, [loadReports])

  const hasActiveFilters = !!(selectedState || selectedBanType || selectedReason || selectedSource || searchQuery)

  const clearFilters = () => {
    setSearchQuery('')
    setSelectedState('')
    setSelectedBanType('')
    setSelectedReason('')
    setSelectedSource('')
  }

  const handlePageChange = (newPage: number) => {
    setPage(newPage)
    document.getElementById('book-list-heading')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  return {
    stats,
    statsLoading,
    statsError,
    reports,
    reportsLoading,
    reportsError,
    loadReports,
    page,
    totalPages,
    totalReports,
    catalogMatches,
    mostBanned,
    searchQuery,
    setSearchQuery,
    selectedState,
    setSelectedState,
    selectedBanType,
    setSelectedBanType,
    selectedReason,
    setSelectedReason,
    selectedSource,
    setSelectedSource,
    hasActiveFilters,
    clearFilters,
    handlePageChange,
  }
}
