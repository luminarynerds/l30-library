/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react"
import toast from "react-hot-toast"

import { searchPatrons, type Patron } from "../../api/api"
import type { PatronSortField, SortDirection } from "@/api/staff-api/patrons"
import type { StatusFilter } from "./types"

export type { PatronSortField, SortDirection }

export const PAGE_SIZE_OPTIONS = [10, 25, 50, 100] as const
export type PageSize = (typeof PAGE_SIZE_OPTIONS)[number]

interface UsePatronDirectoryParams {
  token: string | null
  isAuthenticated: boolean
}

export function usePatronDirectory({ token, isAuthenticated }: UsePatronDirectoryParams) {
  const [searchQuery, setSearchQuery] = useState("")
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all")
  const [isSearching, setIsSearching] = useState(false)
  const [patrons, setPatrons] = useState<Patron[]>([])
  const [totalPatrons, setTotalPatrons] = useState(0)
  const [currentPage, setCurrentPage] = useState(1)
  const [perPage, setPerPage] = useState<PageSize>(25)
  const [sortBy, setSortBy] = useState<PatronSortField>("name")
  const [sortDirection, setSortDirection] = useState<SortDirection>("asc")

  const fetchPatrons = useCallback(async () => {
    if (!token) return

    setIsSearching(true)
    try {
      const result = await searchPatrons(
        token,
        searchQuery,
        currentPage,
        { sortBy, sortDirection },
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
  }, [token, searchQuery, currentPage, statusFilter, sortBy, sortDirection, perPage])

  useEffect(() => {
    if (token && isAuthenticated) {
      void fetchPatrons()
    }
  }, [token, isAuthenticated, fetchPatrons])

  const handleSearchSubmit = useCallback((e: FormEvent) => {
    e.preventDefault()
    setCurrentPage(1)
    void fetchPatrons()
  }, [fetchPatrons])

  const updateStatusFilter = useCallback((nextStatus: StatusFilter) => {
    setStatusFilter(nextStatus)
    setCurrentPage(1)
  }, [])

  const updatePerPage = useCallback((nextPerPage: PageSize) => {
    setPerPage(nextPerPage)
    setCurrentPage(1)
  }, [])

  const updateSort = useCallback((field: PatronSortField) => {
    setSortBy((prev) => {
      if (prev === field) {
        // Toggle direction when clicking the same column
        setSortDirection((d) => (d === "asc" ? "desc" : "asc"))
      } else {
        setSortDirection("asc")
      }
      return field
    })
    setCurrentPage(1)
  }, [])

  const totalPages = useMemo(() => Math.ceil(totalPatrons / perPage), [totalPatrons, perPage])

  return {
    searchQuery,
    setSearchQuery,
    statusFilter,
    setStatusFilter: updateStatusFilter,
    isSearching,
    patrons,
    setPatrons,
    totalPatrons,
    currentPage,
    setCurrentPage,
    perPage,
    setPerPage: updatePerPage,
    totalPages,
    fetchPatrons,
    handleSearchSubmit,
    sortBy,
    sortDirection,
    updateSort,
  }
}
