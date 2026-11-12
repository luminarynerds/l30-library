/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Hook for managing patron search functionality
 */

import { useState, useCallback, useEffect, useMemo, useRef } from "react"
import { searchPatrons, Patron } from "../../../../api/api"
import type { PatronSortField, SortDirection, PatronAdvancedFilters } from "@/api/staff-api/patrons"
import toast from "react-hot-toast"
import { StatusFilter } from "../types"

export type { PatronSortField, SortDirection }

export const PAGE_SIZE_OPTIONS = [10, 25, 50, 100] as const
export type PageSize = (typeof PAGE_SIZE_OPTIONS)[number]

interface UsePatronSearchReturn {
  patrons: Patron[]
  totalPatrons: number
  currentPage: number
  perPage: PageSize
  totalPages: number
  searchQuery: string
  statusFilter: StatusFilter
  isSearching: boolean
  sortBy: PatronSortField
  sortDirection: SortDirection
  advancedFilters: PatronAdvancedFilters
  activeFilterCount: number
  setSearchQuery: (query: string) => void
  setStatusFilter: (filter: StatusFilter) => void
  setAdvancedFilters: (filters: PatronAdvancedFilters) => void
  clearAdvancedFilters: () => void
  setCurrentPage: (page: number) => void
  setPerPage: (perPage: PageSize) => void
  updateSort: (field: PatronSortField) => void
  performSearch: (options?: { page?: number; query?: string }) => Promise<void>
  handleSearch: (e: React.FormEvent) => void
  updatePatronInList: (patronId: number, updates: Partial<Patron>) => void
}

export function usePatronSearch(
  token: string | null,
  isAuthenticated: boolean,
  initialAdvancedFilters: PatronAdvancedFilters = {}
): UsePatronSearchReturn {
  const [patrons, setPatrons] = useState<Patron[]>([])
  const [totalPatrons, setTotalPatrons] = useState(0)
  const [currentPage, setCurrentPage] = useState(1)
  const [perPage, setPerPageState] = useState<PageSize>(25)
  const [searchQuery, setSearchQuery] = useState("")
  const [statusFilter, setStatusFilterState] = useState<StatusFilter>("all")
  const [isSearching, setIsSearching] = useState(false)
  const [sortBy, setSortBy] = useState<PatronSortField>("name")
  const [sortDirection, setSortDirection] = useState<SortDirection>("asc")
  const [advancedFilters, setAdvancedFilters] = useState<PatronAdvancedFilters>(initialAdvancedFilters)
  const hasSearchedRef = useRef(false)
  const lastExecutedQueryRef = useRef("")

  const runSearch = useCallback(async (page: number, query: string) => {
    if (!token) return

    setIsSearching(true)
    try {
      const result = await searchPatrons(
        token,
        query,
        page,
        { ...advancedFilters, sortBy, sortDirection },
        statusFilter,
        perPage
      )
      setPatrons(result.patrons)
      setTotalPatrons(result.total)
    } catch {
      toast.error("Failed to load patrons")
    } finally {
      setIsSearching(false)
    }
  }, [token, statusFilter, sortBy, sortDirection, perPage, advancedFilters])

  const performSearch = useCallback(async (options?: { page?: number; query?: string }) => {
    hasSearchedRef.current = true

    const pageToLoad = options?.page ?? currentPage
    const queryToLoad = options?.query ?? searchQuery
    lastExecutedQueryRef.current = queryToLoad

    await runSearch(pageToLoad, queryToLoad)
  }, [currentPage, searchQuery, runSearch])

  // Auto-load patrons on mount: only arm the flag here — the sync effect
  // below (which runs after this one in the same pass) performs the single
  // initial fetch. Calling runSearch here too caused a double fetch on mount.
  useEffect(() => {
    if (token && isAuthenticated && !hasSearchedRef.current) {
      hasSearchedRef.current = true
    }
  }, [token, isAuthenticated])

  // After the first explicit search, keep results synchronized with page/filter/sort changes
  useEffect(() => {
    if (token && isAuthenticated && hasSearchedRef.current) {
      void runSearch(currentPage, lastExecutedQueryRef.current)
    }
  }, [token, isAuthenticated, currentPage, statusFilter, sortBy, sortDirection, perPage, advancedFilters, runSearch])

  const handleSearch = useCallback((e: React.FormEvent) => {
    e.preventDefault()

    if (currentPage !== 1) {
      setCurrentPage(1)
      return
    }

    performSearch({ page: 1 })
  }, [currentPage, performSearch])

  const setStatusFilter = useCallback((filter: StatusFilter) => {
    setStatusFilterState(filter)
    setCurrentPage(1)
  }, [])

  const setPerPage = useCallback((nextPerPage: PageSize) => {
    setPerPageState(nextPerPage)
    setCurrentPage(1)
  }, [])

  const updateSort = useCallback((field: PatronSortField) => {
    setSortBy((prev) => {
      if (prev === field) {
        setSortDirection((d) => (d === "asc" ? "desc" : "asc"))
      } else {
        setSortDirection("asc")
      }
      return field
    })
    setCurrentPage(1)
  }, [])

  const updatePatronInList = useCallback((patronId: number, updates: Partial<Patron>) => {
    setPatrons((prev) =>
      prev.map((p) => (p.id === patronId ? { ...p, ...updates } : p))
    )
  }, [])

  const clearAdvancedFilters = useCallback(() => {
    setAdvancedFilters({})
    setCurrentPage(1)
  }, [])

  const activeFilterCount = useMemo(() => {
    let count = 0
    if (advancedFilters.finesMin !== undefined) count++
    if (advancedFilters.finesMax !== undefined) count++
    if (advancedFilters.checkoutCountMin !== undefined) count++
    if (advancedFilters.hasOverdue && advancedFilters.hasOverdue !== "all") count++
    if (advancedFilters.cardStatus && advancedFilters.cardStatus !== "any") count++
    if (advancedFilters.memberSinceFrom) count++
    if (advancedFilters.memberSinceTo) count++
    return count
  }, [advancedFilters])

  const totalPages = useMemo(() => Math.ceil(totalPatrons / perPage), [totalPatrons, perPage])

  return {
    patrons,
    totalPatrons,
    currentPage,
    perPage,
    totalPages,
    searchQuery,
    statusFilter,
    isSearching,
    sortBy,
    sortDirection,
    advancedFilters,
    activeFilterCount,
    setSearchQuery,
    setStatusFilter,
    setAdvancedFilters,
    clearAdvancedFilters,
    setCurrentPage,
    setPerPage,
    updateSort,
    performSearch,
    handleSearch,
    updatePatronInList,
  }
}
