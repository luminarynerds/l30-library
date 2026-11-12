/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * HeaderSearch Component
 *
 * Global search entrypoint. Owns the modal shell, search input, voice input,
 * recent searches, empty state, and scope tabs. Delegates per-scope results
 * rendering and the scope-specific keyboard / submit behavior to the panel
 * components in ./header-search/.
 */

import { useState, useRef, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { Search, X, ArrowLeft, Clock, Mic, MicOff, Trash2 } from 'lucide-react'
import { clsx } from '@/utils/helpers'
import { useTranslation} from '../i18n/I18nContext'
import { useAuth } from '../contexts/AuthContext'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'
import CatalogSearchPanel, { type CatalogComboboxState } from './header-search/CatalogSearchPanel'
import SiteSearchPanel from './header-search/SiteSearchPanel'
import StaffSearchPanel from './header-search/StaffSearchPanel'
import { STAFF_TYPE_FILTERS, type StaffSearchEntityType } from './header-search/staff-search-utils'
import { useScrollLock } from '../hooks/useScrollLock'

interface HeaderSearchProps {
  className?: string
  /** Which trigger button to render. Prevents duplicate buttons in the DOM. */
  variant?: 'desktop' | 'mobile'
}

const RECENT_SEARCHES_KEY = 'lsc_recent_searches'
const MAX_RECENT_SEARCHES = 8

function getRecentSearches(): string[] {
  try {
    const stored = localStorage.getItem(RECENT_SEARCHES_KEY)
    return stored ? JSON.parse(stored) : []
  } catch {
    return []
  }
}

function saveRecentSearch(query: string): void {
  try {
    const searches = getRecentSearches()
    const filtered = searches.filter((s) => s.toLowerCase() !== query.toLowerCase())
    const updated = [query, ...filtered].slice(0, MAX_RECENT_SEARCHES)
    localStorage.setItem(RECENT_SEARCHES_KEY, JSON.stringify(updated))
  } catch {
    // Ignore storage errors
  }
}

function removeRecentSearch(query: string): string[] {
  try {
    const searches = getRecentSearches()
    const updated = searches.filter((s) => s !== query)
    localStorage.setItem(RECENT_SEARCHES_KEY, JSON.stringify(updated))
    return updated
  } catch {
    return []
  }
}

function clearRecentSearches(): void {
  try {
    localStorage.removeItem(RECENT_SEARCHES_KEY)
  } catch {
    // Ignore storage errors
  }
}

const checkSpeechSupport = (): boolean => {
  if (typeof window === 'undefined') return false
  return !!(window.SpeechRecognition || window.webkitSpeechRecognition)
}

export default function HeaderSearch({ className, variant }: HeaderSearchProps): React.ReactElement {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { user } = useAuth()
  const isStaffUser = Boolean(user && ['staff', 'admin', 'super_admin', 'director'].includes(user.role))
  const [isExpanded, setIsExpanded] = useState(false)
  const [query, setQuery] = useState('')
  const [recentSearches, setRecentSearches] = useState<string[]>(getRecentSearches)
  const [isListening, setIsListening] = useState(false)
  const [searchScope, setSearchScope] = useState<'catalog' | 'site' | 'staff'>('catalog')
  const [staffFilter, setStaffFilter] = useState<'all' | StaffSearchEntityType>('all')
  const [catalogFacetFilter, setCatalogFacetFilter] = useState<string | null>(null)
  const speechSupported = checkSpeechSupport()
  const [_isLargeScreen, setIsLargeScreen] = useState(() => window.matchMedia('(min-width: 1024px)').matches)
  // Combobox a11y state populated by the active panel (catalog only).
  const [comboboxState, setComboboxState] = useState<CatalogComboboxState | null>(null)
  // sr-only live region text populated by the active panel (catalog only).
  const [suggestionAnnouncement, setSuggestionAnnouncement] = useState('')

  const inputRef = useRef<HTMLInputElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const recognitionRef = useRef<SpeechRecognition | null>(null)
  // Active panel registers its keydown + submit handlers here so the shared
  // input/form can delegate scope-specific behavior.
  const panelKeyHandlerRef = useRef<((e: React.KeyboardEvent<HTMLInputElement>) => void) | null>(null)
  const panelSubmitHandlerRef = useRef<(() => void) | null>(null)

  useEffect(() => {
    const mq = window.matchMedia('(min-width: 1024px)')
    const handler = (e: MediaQueryListEvent) => setIsLargeScreen(e.matches)
    mq.addEventListener('change', handler)
    return () => mq.removeEventListener('change', handler)
  }, [])

  useEffect(() => {
    if (isExpanded) {
      const timer = setTimeout(() => {
        setRecentSearches(getRecentSearches())
        inputRef.current?.focus()
      }, 50)
      return () => clearTimeout(timer)
    }
  }, [isExpanded])

  useEffect(() => {
    const handleGlobalKeyDown = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement
      if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable) {
        return
      }

      // Bare `/` shortcut removed: it traps screen-reader & switch-control users who
      // need to type a literal slash (WCAG 2.1.4 Character Key Shortcuts). Only
      // modifier-gated Cmd/Ctrl+K remains, and only for non-staff users —
      // staff Cmd+K opens the CommandPalette (see Layout.tsx).
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k' && !isStaffUser) {
        e.preventDefault()
        setIsExpanded(true)
      }

      if (e.key === 'Escape' && isExpanded) {
        setIsExpanded(false)
      }
    }

    document.addEventListener('keydown', handleGlobalKeyDown)
    return () => document.removeEventListener('keydown', handleGlobalKeyDown)
  }, [isExpanded, isStaffUser])

  useScrollLock(isExpanded)

  useEffect(() => {
    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.abort()
      }
    }
  }, [])

  const handleRecentSearchClick = useCallback((searchQuery: string) => {
    saveRecentSearch(searchQuery)
    setQuery(searchQuery)
    if (searchScope === 'catalog') {
      navigate(`/catalog?q=${encodeURIComponent(searchQuery)}`)
      setIsExpanded(false)
    } else if (searchScope === 'site') {
      navigate(`/search?q=${encodeURIComponent(searchQuery)}`)
      setIsExpanded(false)
    }
  }, [navigate, searchScope])

  const handleRemoveRecentSearch = useCallback((searchQuery: string, e: React.MouseEvent) => {
    e.stopPropagation()
    const updated = removeRecentSearch(searchQuery)
    setRecentSearches(updated)
  }, [])

  const handleClearAllRecent = useCallback(() => {
    clearRecentSearches()
    setRecentSearches([])
  }, [])

  const stopListening = useCallback(() => {
    if (recognitionRef.current) {
      recognitionRef.current.stop()
      setIsListening(false)
    }
  }, [])

  const handleClear = useCallback(() => {
    setQuery('')
    setCatalogFacetFilter(null)
    inputRef.current?.focus()
  }, [])

  const handleConsumeQuery = useCallback(() => {
    setQuery('')
  }, [])

  const handleClose = useCallback(() => {
    setQuery('')
    setCatalogFacetFilter(null)
    setIsExpanded(false)
    stopListening()
  }, [stopListening])

  const handleSubmit = useCallback((e?: React.FormEvent) => {
    e?.preventDefault()
    if (!query.trim()) return
    panelSubmitHandlerRef.current?.()
  }, [query])

  const handleInputKeyDown = useCallback((e: React.KeyboardEvent<HTMLInputElement>) => {
    panelKeyHandlerRef.current?.(e)
  }, [])

  const registerKeyHandler = useCallback((handler: ((e: React.KeyboardEvent<HTMLInputElement>) => void) | null) => {
    panelKeyHandlerRef.current = handler
  }, [])

  const registerSubmitHandler = useCallback((handler: (() => void) | null) => {
    panelSubmitHandlerRef.current = handler
  }, [])

  const startListening = () => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
    if (!SpeechRecognition) return

    const recognition = new SpeechRecognition()
    recognition.continuous = false
    recognition.interimResults = true
    recognition.lang = 'en-US'

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    ;(recognition as any).onstart = () => setIsListening(true)

    recognition.onresult = (event: SpeechRecognitionEvent) => {
      const transcript = Array.from(event.results)
        .map((result) => result[0]?.transcript ?? '')
        .join('')
      setQuery(transcript)
    }

    recognition.onerror = () => setIsListening(false)
    recognition.onend = () => setIsListening(false)

    recognitionRef.current = recognition
    recognition.start()
  }

  const toggleVoice = () => {
    if (isListening) stopListening()
    else startListening()
  }

  const placeholderForScope = (): string => {
    if (searchScope === 'staff') {
      return t('components.headerSearch.staffPlaceholder', 'Search barcode, ISBN, patron ID, phone, email, name...')
    }
    if (searchScope === 'site') {
      return t('components.headerSearch.sitePlaceholder', 'Search catalog, events, announcements...')
    }
    return t('catalog.searchPlaceholder')
  }

  const emptyStatePlaceholder = (): string => {
    if (searchScope === 'staff') {
      return t('components.headerSearch.staffEmptyState', 'Find anything in under 5 seconds.')
    }
    if (searchScope === 'site') {
      return t('components.headerSearch.siteEmptyState', 'Search the catalog, events, pages, and announcements.')
    }
    return t('catalog.searchPlaceholder')
  }

  return (
    <>
      {variant !== 'mobile' && (
        <div ref={containerRef} className={clsx('relative', !variant && 'hidden lg:block', className)}>
          <button
            type="button"
            onClick={() => setIsExpanded(true)}
            className="flex items-center justify-center w-11 h-11 rounded-xl text-earth-600 dark:text-earth-300 hover:bg-earth-50 dark:hover:bg-earth-800/10 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose dark:focus-visible:ring-lsc-rose-light"
            aria-label={t('catalog.searchButton')}
            aria-expanded={isExpanded}
          >
            <Search aria-hidden="true" className="w-5 h-5" />
          </button>
        </div>
      )}

      {variant !== 'desktop' && (
        <button
          type="button"
          onClick={() => setIsExpanded(true)}
          className={clsx(
            'flex items-center justify-center w-11 h-11 rounded-xl text-earth-600 dark:text-earth-300 hover:bg-earth-50 dark:hover:bg-earth-800/10 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose dark:focus-visible:ring-lsc-rose-light',
            !variant && 'lg:hidden'
          )}
          aria-label={t('catalog.searchButton')}
        >
          <Search aria-hidden="true" className="w-6 h-6" />
        </button>
      )}

      {isExpanded && (
        // ``role="dialog"`` with a real accessible name. The previous
        // ``alertdialog`` + ``title="Dialog"`` combination was wrong on
        // both axes: search is not an urgent interrupt (so the alert
        // semantic mis-announces in screen readers), and ``"Dialog"`` is
        // a meaningless accessible name.
        <ModalBackdrop onClose={handleClose} title={t('catalog.search.modalLabel', 'Search')} role="dialog">
          <div className="mx-auto max-w-4xl px-3 py-2 sm:py-3 lg:pt-20">
            {/* header-search-panel: always-dark chrome; index.css flips it light under light high-contrast */}
            <div className="header-search-panel rounded-xl border border-earth-700 bg-earth-900 shadow-lg overflow-hidden">
              <div className="flex items-center gap-2 px-2 py-2 border-b border-earth-700">
                <button
                  type="button"
                  onClick={handleClose}
                  className="flex items-center justify-center w-10 h-10 rounded-full text-earth-100 hover:bg-earth-700 transition-colors"
                  aria-label={t('common.back')}
                >
                  <ArrowLeft aria-hidden="true" className="w-5 h-5" />
                </button>
                <form onSubmit={handleSubmit} className="flex-1" role="search">
                  <div className="relative">
                    <Search aria-hidden="true" className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-earth-400 pointer-events-none" />
                    <input
                      ref={inputRef}
                      type="search"
                      value={query}
                      onChange={(e) => setQuery(e.target.value)}
                      onKeyDown={handleInputKeyDown}
                      placeholder={placeholderForScope()}
                      className={clsx(
                        'w-full pl-10 py-3 bg-earth-800 text-lsc-cream placeholder:text-earth-300 text-base rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-300 min-h-[44px]',
                        query ? 'pr-10' : 'pr-12'
                      )}
                      aria-label={t('catalog.searchButton')}
                      role="combobox"
                      aria-expanded={searchScope === 'catalog' && (comboboxState?.expanded ?? false)}
                      aria-controls={comboboxState?.listboxId}
                      aria-autocomplete="list"
                      aria-activedescendant={searchScope === 'catalog' ? comboboxState?.activeOptionId : undefined}
                      autoFocus
                    />
                    {query ? (
                      <button
                        type="button"
                        onClick={handleClear}
                        className="absolute right-3 top-1/2 -translate-y-1/2 p-1 text-earth-300 hover:text-lsc-cream transition-colors"
                        aria-label={t('common.clear')}
                      >
                        <X aria-hidden="true" className="w-5 h-5" />
                      </button>
                    ) : speechSupported && (
                      <button
                        type="button"
                        onClick={toggleVoice}
                        className={clsx(
                          'absolute right-3 top-1/2 -translate-y-1/2 p-1 transition-colors',
                          isListening ? 'text-status-danger-400 motion-safe:animate-pulse' : 'text-earth-300 hover:text-lsc-cream'
                        )}
                        aria-label={isListening ? t('components.headerSearch.stopListening', 'Stop listening') : t('components.headerSearch.voiceSearch', 'Voice search')}
                      >
                        {isListening ? <MicOff aria-hidden="true" className="w-5 h-5" /> : <Mic aria-hidden="true" className="w-5 h-5" />}
                      </button>
                    )}
                  </div>
                </form>
              </div>

              <div className="px-4 pt-3 pb-2 border-b border-earth-700 flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={() => setSearchScope('catalog')}
                  aria-pressed={searchScope === 'catalog'}
                  className={clsx('px-3 py-1.5 rounded-lg text-sm', searchScope === 'catalog' ? 'bg-lsc-rose text-white' : 'bg-earth-800 text-earth-200')}
                >
                  {t('components.headerSearch.catalogSearchTab', 'Catalog Search')}
                </button>
                <button
                  type="button"
                  onClick={() => setSearchScope('site')}
                  aria-pressed={searchScope === 'site'}
                  className={clsx('px-3 py-1.5 rounded-lg text-sm', searchScope === 'site' ? 'bg-lsc-rose text-white' : 'bg-earth-800 text-earth-200')}
                >
                  {t('components.headerSearch.siteSearchTab', 'Site Search')}
                </button>
                {isStaffUser && (
                  <button
                    type="button"
                    onClick={() => setSearchScope('staff')}
                    aria-pressed={searchScope === 'staff'}
                    className={clsx('px-3 py-1.5 rounded-lg text-sm', searchScope === 'staff' ? 'bg-lsc-rose text-white' : 'bg-earth-800 text-earth-200')}
                  >
                    {t('components.headerSearch.staffEverythingSearch', 'Staff Everything Search')}
                  </button>
                )}
              </div>

              {searchScope === 'staff' && (
                <div className="px-4 py-2 border-b border-earth-700 flex gap-2 flex-wrap">
                  {STAFF_TYPE_FILTERS.map((filter) => (
                    <button
                      key={filter.value}
                      type="button"
                      onClick={() => setStaffFilter(filter.value)}
                      aria-pressed={staffFilter === filter.value}
                      className={clsx('px-2.5 py-1 rounded-lg text-xs', staffFilter === filter.value ? 'bg-earth-600 text-white' : 'bg-earth-800 text-earth-300')}
                    >
                      {t(`components.headerSearch.filter.${filter.value}`, filter.label)}
                    </button>
                  ))}
                </div>
              )}

              <div className="max-h-[60vh] overflow-y-auto px-4 py-4">
                {!query && recentSearches.length > 0 && (
                  <div>
                    <div className="flex items-center justify-between mb-3">
                      <h3 className="text-sm font-medium text-earth-300 flex items-center gap-2">
                        <Clock aria-hidden="true" className="w-4 h-4" />
                        {t('components.headerSearch.recentSearches', 'Recent searches')}
                      </h3>
                      <button onClick={handleClearAllRecent} className="text-xs text-earth-300 hover:text-earth-100 transition-colors flex items-center gap-1">
                        <Trash2 aria-hidden="true" className="w-3 h-3" />
                        {t('components.headerSearch.clearAll', 'Clear all')}
                      </button>
                    </div>
                    <ul className="space-y-1">
                      {recentSearches.map((search) => (
                        <li key={search} className="w-full flex items-center gap-2 px-2 py-1.5 bg-earth-800 rounded-lg text-earth-100 hover:bg-earth-700 transition-colors group">
                          <button type="button" onClick={() => handleRecentSearchClick(search)} className="flex-1 flex items-center gap-3 text-left">
                            <Clock aria-hidden="true" className="w-4 h-4 text-earth-400" />
                            <span className="flex-1 truncate" title={search}>{search}</span>
                          </button>
                          <button
                            type="button"
                            onClick={(e) => handleRemoveRecentSearch(search, e)}
                            className="p-1 text-earth-400 hover:text-earth-200 opacity-0 group-hover:opacity-100 focus:opacity-100 transition-opacity"
                            aria-label={`Remove ${search} from recent searches`}
                          >
                            <X aria-hidden="true" className="w-4 h-4" />
                          </button>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {searchScope === 'catalog' && (
                  <CatalogSearchPanel
                    query={query}
                    facetFilter={catalogFacetFilter}
                    setFacetFilter={setCatalogFacetFilter}
                    onClose={handleClose}
                    onClearQuery={handleClear}
                    onConsumeQuery={handleConsumeQuery}
                    saveRecentSearch={saveRecentSearch}
                    onComboboxStateChange={setComboboxState}
                    onAnnouncementChange={setSuggestionAnnouncement}
                    registerKeyHandler={registerKeyHandler}
                    registerSubmitHandler={registerSubmitHandler}
                  />
                )}

                {searchScope === 'site' && (
                  <SiteSearchPanel
                    query={query}
                    onClose={handleClose}
                    onClearQuery={handleClear}
                    onConsumeQuery={handleConsumeQuery}
                    saveRecentSearch={saveRecentSearch}
                    registerKeyHandler={registerKeyHandler}
                    registerSubmitHandler={registerSubmitHandler}
                  />
                )}

                {searchScope === 'staff' && (
                  <StaffSearchPanel
                    query={query}
                    setQuery={setQuery}
                    isStaffUser={isStaffUser}
                    staffFilter={staffFilter}
                    onClose={handleClose}
                    onClearQuery={handleClear}
                    onConsumeQuery={handleConsumeQuery}
                    saveRecentSearch={saveRecentSearch}
                    registerKeyHandler={registerKeyHandler}
                    registerSubmitHandler={registerSubmitHandler}
                  />
                )}

                {!query && recentSearches.length === 0 && (
                  <div className="text-center text-earth-300 mt-8">
                    <Search aria-hidden="true" className="w-12 h-12 mx-auto mb-3 opacity-30" />
                    <p className="text-sm">{emptyStatePlaceholder()}</p>
                    {speechSupported && <p className="text-xs mt-2 text-earth-300">{t('components.headerSearch.tipTapTheMicrophoneTo')}</p>}
                  </div>
                )}
                {/* Polite sr-only live region announcing suggestion count after debounce. */}
                <div className="sr-only" aria-live="polite" aria-atomic="true">
                  {suggestionAnnouncement}
                </div>
              </div>
            </div>
          </div>
        </ModalBackdrop>
      )}
    </>
  )
}

declare global {
  interface Window {
    SpeechRecognition: typeof SpeechRecognition
    webkitSpeechRecognition: typeof SpeechRecognition
  }
}
