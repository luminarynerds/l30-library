/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect, useCallback } from "react"
import { searchPatrons } from "@/api/api"
import toast from "react-hot-toast"
import { useTranslation } from "@/i18n"
import type { Patron } from "../types"

const RECENT_PATRONS_KEY = "l30_recent_patrons"
const MAX_RECENT = 5

function loadRecentPatrons(): Patron[] {
  try {
    const raw = sessionStorage.getItem(RECENT_PATRONS_KEY)
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}

function saveRecentPatrons(patrons: Patron[]): void {
  try {
    sessionStorage.setItem(RECENT_PATRONS_KEY, JSON.stringify(patrons))
  } catch {
    // sessionStorage full or unavailable - silently ignore
  }
}

interface UsePatronSearchReturn {
  patronQuery: string
  setPatronQuery: (query: string) => void
  searchResults: Patron[]
  selectedResultIndex: number
  isSearching: boolean
  selectedPatron: Patron | null
  recentPatrons: Patron[]
  handlePatronSearch: (e: React.FormEvent) => void
  selectPatron: (patron: Patron, onSelect?: () => void) => void
  clearPatron: () => void
  handleNavigateUp: () => void
  handleNavigateDown: () => void
  handleEnter: () => void
  handleEscape: () => void
}

export function usePatronSearch(token: string | null): UsePatronSearchReturn {
  const { t } = useTranslation()
  const [patronQuery, setPatronQuery] = useState("")
  const [searchResults, setSearchResults] = useState<Patron[]>([])
  const [selectedResultIndex, setSelectedResultIndex] = useState(-1)
  const [isSearching, setIsSearching] = useState(false)
  const [selectedPatron, setSelectedPatron] = useState<Patron | null>(null)
  const [recentPatrons, setRecentPatrons] = useState<Patron[]>(loadRecentPatrons)

  const addToRecent = useCallback((patron: Patron) => {
    setRecentPatrons((prev) => {
      const deduped = prev.filter((p) => p.id !== patron.id)
      const next = [patron, ...deduped].slice(0, MAX_RECENT)
      saveRecentPatrons(next)
      return next
    })
  }, [])

  const handlePatronSearch = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!token || !patronQuery.trim()) return
    setIsSearching(true)
    try {
      const result = await searchPatrons(token, patronQuery)
      setSearchResults(result.patrons)
      if (result.patrons.length === 0) toast(t('staffCirculation.noPatronsFound'))
    } catch { toast.error(t('staffCirculation.searchFailed')) } finally { setIsSearching(false) }
  }

  const selectPatron = useCallback(async (patron: Patron, onSelect?: () => void) => {
    setSelectedPatron(patron)
    setSearchResults([])
    setPatronQuery("")
    addToRecent(patron)
    if (onSelect) onSelect()

  }, [addToRecent])

  const clearPatron = useCallback(() => {
    setSelectedPatron(null)
  }, [])

  // Debounced patron search
  useEffect(() => {
    if (!token || !patronQuery.trim() || patronQuery.length < 2) {
      if (patronQuery.length === 0) setSearchResults([])
      return
    }
    const timer = setTimeout(async () => {
      setIsSearching(true)
      try {
        const result = await searchPatrons(token, patronQuery)
        setSearchResults(result.patrons)
        setSelectedResultIndex(-1)
      } catch {
        // Silent fail for debounced search - user can still submit manually
      } finally {
        setIsSearching(false)
      }
    }, 300)
    return () => clearTimeout(timer)
  }, [patronQuery, token])

  const handleEscape = useCallback(() => {
    if (searchResults.length > 0) {
      setSearchResults([])
      setSelectedResultIndex(-1)
    } else if (selectedPatron) {
      setSelectedPatron(null)
    }
  }, [searchResults.length, selectedPatron])

  const handleNavigateUp = useCallback(() => {
    if (searchResults.length > 0) {
      setSelectedResultIndex((prev: number) => prev > 0 ? prev - 1 : searchResults.length - 1)
    }
  }, [searchResults.length])

  const handleNavigateDown = useCallback(() => {
    if (searchResults.length > 0) {
      setSelectedResultIndex((prev: number) => prev < searchResults.length - 1 ? prev + 1 : 0)
    }
  }, [searchResults.length])

  const handleEnter = useCallback(() => {
    const patron = searchResults[selectedResultIndex]
    if (searchResults.length > 0 && selectedResultIndex >= 0 && patron) {
      selectPatron(patron)
    }
  }, [searchResults, selectedResultIndex, selectPatron])

  return {
    patronQuery,
    setPatronQuery,
    searchResults,
    selectedResultIndex,
    isSearching,
    selectedPatron,
    recentPatrons,
    handlePatronSearch,
    selectPatron,
    clearPatron,
    handleNavigateUp,
    handleNavigateDown,
    handleEnter,
    handleEscape,
  }
}
