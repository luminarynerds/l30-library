/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect, useRef } from "react"
import { Search, User, Loader2, Clock, UserPlus } from "lucide-react"
import { useTranslation } from "@/i18n"
import AddPatronModal from "@/components/staff/AddPatronModal"
import type { Patron } from "../types"

function StatusBadge({ patron }: { patron: Patron }): React.ReactElement | null {
  const { t } = useTranslation()
  const status = patron.patron_status ?? (patron.is_active ? "active" : "blocked")
  const config: Record<string, { label: string; className: string }> = {
    active: { label: t("patronStatus.active"), className: "bg-status-success-100 text-status-success-800 dark:bg-status-success-900/30 dark:text-status-success-400" },
    blocked: { label: t("patronStatus.blocked"), className: "bg-status-danger-100 text-status-danger-800 dark:bg-status-danger-900/30 dark:text-status-danger-400" },
    suspended: { label: t("patronStatus.suspended"), className: "bg-status-warning-100 text-status-warning-800 dark:bg-status-warning-900/30 dark:text-status-warning-400" },
    deceased: { label: t("patronStatus.deceased"), className: "bg-earth-100 text-earth-600 dark:bg-earth-800 dark:text-earth-400" },
  }
  const c = config[status]
  if (!c) return null
  return <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded-full whitespace-nowrap ${c.className}`}>{c.label}</span>
}

const INITIAL_RESULTS_LIMIT = 10

interface PatronSearchSectionProps {
  patronQuery: string
  setPatronQuery: (query: string) => void
  searchResults: Patron[]
  selectedResultIndex: number
  isSearching: boolean
  recentPatrons: Patron[]
  handlePatronSearch: (e: React.FormEvent) => void
  selectPatron: (patron: Patron) => void
  handleNavigateUp: () => void
  handleNavigateDown: () => void
  searchInputRef: React.RefObject<HTMLInputElement>
}

export function PatronSearchSection({
  patronQuery,
  setPatronQuery,
  searchResults,
  selectedResultIndex,
  isSearching,
  recentPatrons,
  handlePatronSearch,
  selectPatron,
  handleNavigateUp,
  handleNavigateDown,
  searchInputRef,
}: PatronSearchSectionProps): React.ReactElement {
  const { t } = useTranslation()
  const [isFocused, setIsFocused] = useState(false)
  const [showAll, setShowAll] = useState(false)
  const [isAddPatronOpen, setIsAddPatronOpen] = useState(false)
  const resultRefs = useRef<Array<HTMLButtonElement | null>>([])

  // Keep the highlighted row in view when arrow keys navigate past the visible fold.
  useEffect(() => {
    if (selectedResultIndex < 0) return
    const node = resultRefs.current[selectedResultIndex]
    node?.scrollIntoView({ block: 'nearest' })
  }, [selectedResultIndex])

  const handleInputKeyDown = (e: React.KeyboardEvent<HTMLInputElement>): void => {
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      handleNavigateDown()
      return
    }
    if (e.key === 'ArrowUp') {
      e.preventDefault()
      handleNavigateUp()
      return
    }
    if (e.key === 'Enter' && searchResults.length > 0 && selectedResultIndex >= 0) {
      const patron = searchResults[selectedResultIndex]
      if (patron) {
        e.preventDefault()
        selectPatron(patron)
      }
    }
  }

  const showRecent = isFocused && !patronQuery.trim() && recentPatrons.length > 0 && searchResults.length === 0
  const visibleResults = showAll ? searchResults : searchResults.slice(0, INITIAL_RESULTS_LIMIT)
  const hasMore = searchResults.length > INITIAL_RESULTS_LIMIT && !showAll
  const showEmptyState = !!patronQuery.trim() && !isSearching && searchResults.length === 0

  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 md:p-6 shadow-sm">
      <h2 className="font-serif text-base md:text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-3 md:mb-4">{t('staffCirculation.findPatron')}</h2>
      <form onSubmit={handlePatronSearch} className="flex gap-2">
        <input ref={searchInputRef} type="text" value={patronQuery} onChange={(e) => { setPatronQuery(e.target.value); setShowAll(false) }} onFocus={() => setIsFocused(true)} onBlur={() => setTimeout(() => setIsFocused(false), 200)} onKeyDown={handleInputKeyDown} aria-label={t('staffCirculation.searchPatronsByNameEmail')} placeholder={t('staffCirculation.searchByNameEmailOr')} className="flex-1 px-3 md:px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent text-sm md:text-base" />
        <button type="submit" disabled={isSearching} aria-label={t('staffCirculation.search')} className="px-3 md:px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 disabled:bg-lsc-rose/50 text-white rounded-xl font-medium flex items-center gap-2 text-sm md:text-base">{isSearching ? <Loader2 className="w-4 h-4 motion-safe:animate-spin" /> : <Search aria-hidden="true" className="w-4 h-4" />}<span className="hidden sm:inline">{t('staffCirculation.search')}</span></button>
      </form>
      {/* Screen reader announcement for search results */}
      <div className="sr-only" aria-live="polite" aria-atomic="true">
        {searchResults.length > 0 && (searchResults.length === 1
          ? t('staffCirculation.patronsFoundOne', { count: searchResults.length })
          : t('staffCirculation.patronsFoundOther', { count: searchResults.length }))}
      </div>
      {showRecent && (
        <div className="mt-4 space-y-2">
          <p className="text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 flex items-center gap-1"><Clock aria-hidden="true" className="w-3 h-3" />{t('staffCirculation.recentLabel')}</p>
          <div className="space-y-1" role="listbox" aria-label={t('staffCirculation.recentPatronsListLabel')}>
            {recentPatrons.map((patron) => (
              <button key={patron.id} onClick={() => selectPatron(patron)} role="option" aria-selected={false} className="w-full flex items-center gap-3 p-2.5 rounded-xl transition-colors text-left bg-lsc-cream/50 dark:bg-lsc-brown/30 hover:bg-lsc-cream dark:hover:bg-lsc-brown/50">
                <div className="w-8 h-8 bg-lsc-cream dark:bg-lsc-brown/30 rounded-full flex items-center justify-center flex-shrink-0"><User aria-hidden="true" className="w-4 h-4 text-lsc-rose dark:text-lsc-rose-light" /></div>
                <div className="flex-1 min-w-0"><p className="font-medium text-lsc-dark dark:text-lsc-cream text-sm truncate">{patron.first_name} {patron.last_name}</p></div>
                <StatusBadge patron={patron} />
                <span className="text-xs font-mono text-lsc-dark/70 dark:text-lsc-cream/70 hidden sm:block">{patron.library_card}</span>
              </button>
            ))}
          </div>
        </div>
      )}
      {searchResults.length > 0 && (
        <div className="mt-4 space-y-2" role="listbox" aria-label={t('aria.staffCirculation.patronSearchResults')}>
          {visibleResults.map((patron, index) => (
            <button key={patron.id} ref={(el) => { resultRefs.current[index] = el }} onClick={() => selectPatron(patron)} role="option" aria-selected={index === selectedResultIndex} className={`w-full flex items-center gap-3 p-3 rounded-xl transition-colors text-left ${index === selectedResultIndex ? "bg-lsc-rose/20 dark:bg-lsc-rose/10 ring-2 ring-lsc-rose" : "bg-lsc-cream dark:bg-lsc-brown/50 hover:bg-lsc-cream/80 dark:hover:bg-lsc-brown/30"}`}>
              <div className="w-8 h-8 md:w-10 md:h-10 bg-lsc-cream dark:bg-lsc-brown/30 rounded-full flex items-center justify-center flex-shrink-0"><User aria-hidden="true" className="w-4 h-4 md:w-5 md:h-5 text-lsc-rose dark:text-lsc-rose-light" /></div>
              <div className="flex-1 min-w-0"><p className="font-medium text-lsc-dark dark:text-lsc-cream text-sm md:text-base truncate" title={`${patron.first_name} ${patron.last_name}`}>{patron.first_name} {patron.last_name}</p><p className="text-xs md:text-sm text-lsc-dark/70 dark:text-lsc-cream/70 truncate" title={patron.email ?? patron.email_masked ?? undefined}>{patron.email ?? patron.email_masked ?? ""}</p></div>
              <StatusBadge patron={patron} />
              <span className="text-xs font-mono text-lsc-dark/70 dark:text-lsc-cream/70 hidden sm:block">{patron.library_card}</span>
            </button>
          ))}
          {hasMore && (
            <button type="button" onClick={() => setShowAll(true)} className="w-full text-center text-sm text-lsc-rose hover:text-lsc-rose/80 dark:text-lsc-rose-light py-1.5">{t('staffCirculation.showAllResults', { count: searchResults.length })}</button>
          )}
          <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 text-center pt-1">{t('staffCirculation.useArrowsToNavigateEnter')}</p>
        </div>
      )}
      {showEmptyState && (
        <div className="mt-4 flex flex-col items-center gap-2 py-3">
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{t('staffCirculation.noPatronsFound')}</p>
          <button
            type="button"
            onClick={() => setIsAddPatronOpen(true)}
            className="flex items-center gap-2 px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-xl font-medium text-sm transition-colors"
          >
            <UserPlus aria-hidden="true" className="w-4 h-4" />
            {t('staffCirculation.registerNewPatron')}
          </button>
        </div>
      )}
      <AddPatronModal
        isOpen={isAddPatronOpen}
        onClose={() => setIsAddPatronOpen(false)}
        onSuccess={() => {
          setIsAddPatronOpen(false)
        }}
      />
    </div>
  )
}
