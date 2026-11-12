/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useCallback, useEffect, useMemo, useState } from "react"
import toast from "react-hot-toast"
import { fetchApi } from "@/api/fetchApi"
import { useTranslation } from "@/i18n"
import type { DateRange, LibrarianRelease, LibrarianReleasesResponse, SortDir, SortField } from "./types"

const RELEASES_PATH = '/releases'
const PER_PAGE = 25

interface UseReleasesResult {
  releases: LibrarianRelease[]
  filteredAndSorted: LibrarianRelease[]
  total: number
  page: number
  perPage: number
  totalPages: number
  isLoading: boolean
  isRefreshing: boolean
  setPage: (p: number | ((prev: number) => number)) => void
  libraryStatusFilter: string
  setLibraryStatusFilter: (v: string) => void
  sourceFilter: string
  setSourceFilter: (v: string) => void
  ageFilter: string
  setAgeFilter: (v: string) => void
  dateRange: DateRange
  setDateRange: (v: DateRange) => void
  sortField: SortField
  sortDir: SortDir
  toggleSort: (field: SortField) => void
  refreshAll: () => Promise<void>
  featureTitle: (bookId: string, isFeatured: boolean) => Promise<void>
  stats: {
    total: number
    thisWeek: number
    thisMonth: number
    newOnly: number
    highDemand: number
  }
}

export function useReleases(token: string): UseReleasesResult {
  const { t } = useTranslation()
  const [releases, setReleases] = useState<LibrarianRelease[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [isLoading, setIsLoading] = useState(false)
  const [isRefreshing, setIsRefreshing] = useState(false)

  const [libraryStatusFilter, setLibraryStatusFilter] = useState("")
  const [sourceFilter, setSourceFilter] = useState("")
  const [ageFilter, setAgeFilter] = useState("")
  const [dateRange, setDateRange] = useState<DateRange>("all")
  const [sortField, setSortField] = useState<SortField>("release_date")
  const [sortDir, setSortDir] = useState<SortDir>("asc")

  const loadReleases = useCallback(async () => {
    if (!token) return
    setIsLoading(true)
    try {
      const params = new URLSearchParams()
      if (libraryStatusFilter) params.set("library_status", libraryStatusFilter)
      if (sourceFilter) params.set("source", sourceFilter)
      if (ageFilter) params.set("age_rating", ageFilter)
      params.set("page", page.toString())
      params.set("per_page", PER_PAGE.toString())
      const data: LibrarianReleasesResponse = await fetchApi(`${RELEASES_PATH}/librarian/releases?${params}`)
      setReleases(data.items)
      setTotal(data.total)
    } catch (err) {
      toast.error(err instanceof Error ? err.message : t('toast.acquisition.failedToLoadReleases'))
    } finally {
      setIsLoading(false)
    }
  }, [token, libraryStatusFilter, sourceFilter, ageFilter, page, t])

  useEffect(() => {
    loadReleases()
  }, [loadReleases])

  useEffect(() => {
    setPage(1)
  }, [libraryStatusFilter, sourceFilter, ageFilter])

  const filteredAndSorted = useMemo(() => {
    let items = [...releases]

    if (dateRange !== "all") {
      const now = new Date()
      const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
      items = items.filter((r) => {
        if (!r.book.release_date) return false
        const rd = new Date(r.book.release_date)
        switch (dateRange) {
          case "this_week": {
            const weekEnd = new Date(today)
            weekEnd.setDate(weekEnd.getDate() + 7)
            return rd >= today && rd <= weekEnd
          }
          case "this_month": {
            const monthEnd = new Date(today.getFullYear(), today.getMonth() + 1, 0, 23, 59, 59)
            return rd >= today && rd <= monthEnd
          }
          case "next_3_months": {
            const qEnd = new Date(today)
            qEnd.setDate(qEnd.getDate() + 90)
            return rd >= today && rd <= qEnd
          }
          case "past":
            return rd < today
          default:
            return true
        }
      })
    }

    items.sort((a, b) => {
      let cmp = 0
      switch (sortField) {
        case "release_date": {
          const da = a.book.release_date ? new Date(a.book.release_date).getTime() : Infinity
          const db = b.book.release_date ? new Date(b.book.release_date).getTime() : Infinity
          cmp = da - db
          break
        }
        case "demand":
          cmp = a.demand_score - b.demand_score
          break
        case "title":
          cmp = a.book.title.localeCompare(b.book.title)
          break
        case "price": {
          const pa = a.book.list_price ?? 0
          const pb = b.book.list_price ?? 0
          cmp = pa - pb
          break
        }
      }
      return sortDir === "desc" ? -cmp : cmp
    })

    return items
  }, [releases, dateRange, sortField, sortDir])

  const stats = useMemo(() => {
    const now = new Date()
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
    const weekEnd = new Date(today)
    weekEnd.setDate(weekEnd.getDate() + 7)
    const monthEnd = new Date(today)
    monthEnd.setDate(monthEnd.getDate() + 30)

    return {
      total,
      thisWeek: releases.filter((r) => {
        if (!r.book.release_date) return false
        const rd = new Date(r.book.release_date)
        return rd >= today && rd <= weekEnd
      }).length,
      thisMonth: releases.filter((r) => {
        if (!r.book.release_date) return false
        const rd = new Date(r.book.release_date)
        return rd >= today && rd <= monthEnd
      }).length,
      newOnly: releases.filter((r) => r.library_status === "new").length,
      highDemand: releases.filter((r) => r.demand_score >= 3).length,
    }
  }, [releases, total])

  const toggleSort = useCallback((field: SortField) => {
    if (sortField === field) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"))
    } else {
      setSortField(field)
      setSortDir(field === "demand" ? "desc" : "asc")
    }
  }, [sortField])

  const refreshAll = useCallback(async () => {
    setIsRefreshing(true)
    try {
      const data = await fetchApi(`${RELEASES_PATH}/librarian/refresh-all`, {
        method: "POST",
        body: JSON.stringify({ force: false }),
      })
      toast.success(t('toast.acquisition.refreshedBooksadded0AddedBooksupdated0Updated', { booksadded0: data.books_added ?? 0, booksupdated0: data.books_updated ?? 0 }))
      loadReleases()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : t('toast.acquisition.failedToRefresh'))
    } finally {
      setIsRefreshing(false)
    }
  }, [t, loadReleases])

  const featureTitle = useCallback(async (bookId: string, isFeatured: boolean) => {
    try {
      await fetchApi(`${RELEASES_PATH}/librarian/${bookId}/feature`, {
        method: "PATCH",
        body: JSON.stringify({ is_featured: isFeatured }),
      })
      loadReleases()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to update")
    }
  }, [loadReleases])

  const totalPages = Math.ceil(total / PER_PAGE)

  return {
    releases,
    filteredAndSorted,
    total,
    page,
    perPage: PER_PAGE,
    totalPages,
    isLoading,
    isRefreshing,
    setPage,
    libraryStatusFilter,
    setLibraryStatusFilter,
    sourceFilter,
    setSourceFilter,
    ageFilter,
    setAgeFilter,
    dateRange,
    setDateRange,
    sortField,
    sortDir,
    toggleSort,
    refreshAll,
    featureTitle,
    stats,
  }
}
