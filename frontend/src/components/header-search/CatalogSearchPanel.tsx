/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * CatalogSearchPanel
 *
 * Catalog-scope panel for HeaderSearch. Owns catalog suggestion state, the
 * trigram-suggestions effect, the facet pills, the listbox combobox a11y
 * model, and the catalog CTA. Communicates combobox state and the sr-only
 * announcement back to the shell via callback props so the shared input can
 * render the correct aria-* attributes and live region.
 */

import { useCallback, useEffect, useMemo, useState, useId } from 'react'
import { useNavigate } from 'react-router-dom'
import { BookOpen, Filter, Search, User } from 'lucide-react'
import { clsx } from '@/utils/helpers'
import { useTranslation } from '../../i18n/I18nContext'
import { getSearchSuggestions, type SearchSuggestion } from '../../api/pg-search-api'

export interface CatalogComboboxState {
  listboxId: string
  activeOptionId?: string
  expanded: boolean
}

export interface CatalogSearchPanelProps {
  query: string
  facetFilter: string | null
  setFacetFilter: (next: string | null) => void
  onClose: () => void
  onClearQuery: () => void
  onConsumeQuery: () => void
  saveRecentSearch: (query: string) => void
  onComboboxStateChange?: (state: CatalogComboboxState | null) => void
  onAnnouncementChange?: (announcement: string) => void
  registerKeyHandler?: (handler: ((e: React.KeyboardEvent<HTMLInputElement>) => void) | null) => void
  registerSubmitHandler?: (handler: (() => void) | null) => void
}

const FACETS: Array<{ value: string | null; label: string }> = [
  { value: null, label: 'All' },
  { value: 'book', label: 'Books' },
  { value: 'ebook', label: 'eBooks' },
  { value: 'audiobook', label: 'Audiobooks' },
  { value: 'dvd', label: 'DVDs' },
  { value: 'cd', label: 'CDs' },
  { value: 'magazine', label: 'Magazines' },
  { value: 'game', label: 'Games' },
  { value: 'kit', label: 'Kits' },
  { value: 'equipment', label: 'Equipment' },
]

export default function CatalogSearchPanel({
  query,
  facetFilter,
  setFacetFilter,
  onClose,
  onClearQuery,
  onConsumeQuery,
  saveRecentSearch,
  onComboboxStateChange,
  onAnnouncementChange,
  registerKeyHandler,
  registerSubmitHandler,
}: CatalogSearchPanelProps): React.ReactElement {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const listboxId = useId()
  const optionIdPrefix = useId()
  const [catalogSuggestions, setCatalogSuggestions] = useState<SearchSuggestion[]>([])
  const [isFetchingSuggestions, setIsFetchingSuggestions] = useState(false)
  const [activeOptionIndex, setActiveOptionIndex] = useState(-1)

  const optionId = useCallback((index: number) => `${optionIdPrefix}option-${index}`, [optionIdPrefix])
  const activeOptionId = activeOptionIndex >= 0 ? optionId(activeOptionIndex) : undefined

  // Fetch catalog search suggestions (trigram similarity) as user types
  useEffect(() => {
    if (query.trim().length < 2) {
      setCatalogSuggestions([])
      return
    }

    setIsFetchingSuggestions(true)
    const timer = window.setTimeout(async () => {
      try {
        const response = await getSearchSuggestions(query.trim(), 8)
        setCatalogSuggestions(response.suggestions)
      } catch {
        setCatalogSuggestions([])
      } finally {
        setIsFetchingSuggestions(false)
      }
    }, 200)

    return () => {
      window.clearTimeout(timer)
      setIsFetchingSuggestions(false)
    }
  }, [query])

  // Reset active option whenever the suggestion set changes.
  useEffect(() => {
    setActiveOptionIndex(-1)
  }, [catalogSuggestions])

  // Notify shell of combobox a11y state so the shared input renders the right aria-* attrs.
  useEffect(() => {
    onComboboxStateChange?.({
      listboxId,
      activeOptionId,
      expanded: catalogSuggestions.length > 0,
    })
    return () => onComboboxStateChange?.(null)
  }, [onComboboxStateChange, listboxId, activeOptionId, catalogSuggestions.length])

  // Polite sr-only announcement of suggestion count, debounced 300ms.
  useEffect(() => {
    if (!query.trim()) {
      onAnnouncementChange?.('')
      return
    }
    const timer = window.setTimeout(() => {
      const n = catalogSuggestions.length
      onAnnouncementChange?.(
        n === 0
          ? t('components.headerSearch.noSuggestions', 'No suggestions.')
          : t('components.headerSearch.suggestionsCount', `${n} suggestions available.`)
              .replace('{count}', String(n))
      )
    }, 300)
    return () => window.clearTimeout(timer)
  }, [catalogSuggestions, query, t, onAnnouncementChange])

  const handleSuggestionClick = useCallback((suggestion: SearchSuggestion) => {
    const searchText = suggestion.suggestion_type === 'author'
      ? suggestion.title ?? ''
      : suggestion.title ?? ''
    saveRecentSearch(searchText)

    if (suggestion.suggestion_type === 'author') {
      navigate(`/catalog?q=${encodeURIComponent(searchText)}`)
    } else if (suggestion.id) {
      navigate(`/catalog/${suggestion.id}`)
    } else {
      navigate(`/catalog?q=${encodeURIComponent(searchText)}`)
    }

    onConsumeQuery()
    setCatalogSuggestions([])
    onClose()
  }, [navigate, saveRecentSearch, onConsumeQuery, onClose])

  const handleSubmit = useCallback(() => {
    if (!query.trim()) return
    saveRecentSearch(query.trim())
    const params = new URLSearchParams({ q: query.trim() })
    if (facetFilter) params.set('item_type', facetFilter)
    navigate(`/catalog?${params.toString()}`)
    onConsumeQuery()
    setCatalogSuggestions([])
    setFacetFilter(null)
    onClose()
  }, [query, facetFilter, saveRecentSearch, navigate, onConsumeQuery, onClose, setFacetFilter])

  // Combobox keyboard handler — registered with shell so the shared input delegates here.
  const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLInputElement>) => {
    if (catalogSuggestions.length === 0) {
      if (e.key === 'Escape' && query) {
        e.preventDefault()
        onClearQuery()
      }
      return
    }

    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setActiveOptionIndex(prev => (prev + 1) % catalogSuggestions.length)
      return
    }
    if (e.key === 'ArrowUp') {
      e.preventDefault()
      setActiveOptionIndex(prev =>
        prev <= 0 ? catalogSuggestions.length - 1 : prev - 1
      )
      return
    }
    if (e.key === 'Home') {
      e.preventDefault()
      setActiveOptionIndex(0)
      return
    }
    if (e.key === 'End') {
      e.preventDefault()
      setActiveOptionIndex(catalogSuggestions.length - 1)
      return
    }
    if (e.key === 'Enter' && activeOptionIndex >= 0) {
      const suggestion = catalogSuggestions[activeOptionIndex]
      if (suggestion) {
        e.preventDefault()
        handleSuggestionClick(suggestion)
      }
      return
    }
    if (e.key === 'Escape') {
      e.preventDefault()
      if (activeOptionIndex >= 0) {
        setActiveOptionIndex(-1)
      } else if (query) {
        onClearQuery()
      } else {
        onClose()
      }
    }
  }, [catalogSuggestions, activeOptionIndex, query, handleSuggestionClick, onClearQuery, onClose])

  useEffect(() => {
    registerKeyHandler?.(handleKeyDown)
    return () => registerKeyHandler?.(null)
  }, [registerKeyHandler, handleKeyDown])

  useEffect(() => {
    registerSubmitHandler?.(handleSubmit)
    return () => registerSubmitHandler?.(null)
  }, [registerSubmitHandler, handleSubmit])

  const facetPills = useMemo(() => (
    <div className="flex gap-2 flex-wrap">
      {FACETS.map((facet) => (
        <button
          key={facet.value ?? 'all'}
          type="button"
          onClick={() => setFacetFilter(facet.value)}
          className={clsx(
            'px-2.5 py-1 rounded-lg text-xs flex items-center gap-1',
            facetFilter === facet.value
              ? 'bg-lsc-rose text-white'
              : 'bg-earth-800 text-earth-300 hover:bg-earth-700'
          )}
        >
          <Filter aria-hidden="true" className="w-3 h-3" />
          {t(`components.headerSearch.facet.${facet.label.toLowerCase()}`, facet.label)}
        </button>
      ))}
    </div>
  ), [facetFilter, t, setFacetFilter])

  if (!query) return <></>

  return (
    <div className="space-y-3">
      {facetPills}

      {catalogSuggestions.length > 0 && (
        <ul
          id={listboxId}
          className="space-y-1"
          role="listbox"
          aria-label={t('aria.headerSearch.searchSuggestions')}
        >
          {catalogSuggestions.map((suggestion, idx) => (
            <li
              key={suggestion.id ?? `sug-${idx}`}
              id={optionId(idx)}
              role="option"
              aria-selected={activeOptionIndex === idx}
            >
              <button
                type="button"
                onClick={() => handleSuggestionClick(suggestion)}
                tabIndex={-1}
                className={clsx(
                  'w-full text-left px-3 py-2 rounded-lg flex items-center gap-3 transition-colors',
                  activeOptionIndex === idx
                    ? 'bg-earth-700 ring-2 ring-brand-300'
                    : 'bg-earth-800 hover:bg-earth-700'
                )}
              >
                {suggestion.suggestion_type === 'author' ? (
                  <User aria-hidden="true" className="w-4 h-4 text-brand-300 shrink-0" />
                ) : (
                  <BookOpen aria-hidden="true" className="w-4 h-4 text-earth-400 shrink-0" />
                )}
                <div className="flex-1 min-w-0">
                  <p className="text-lsc-cream font-medium truncate" title={suggestion.title ?? ''}>{suggestion.title}</p>
                  {suggestion.suggestion_type === 'title' && suggestion.author && (
                    <p className="text-xs text-earth-300 truncate" title={suggestion.author ?? ''}>{suggestion.author}</p>
                  )}
                  {suggestion.suggestion_type === 'author' && suggestion.book_count && (
                    <p className="text-xs text-earth-300">{suggestion.book_count} {t('components.headerSearch.itemsLabel', 'items')}</p>
                  )}
                </div>
                {suggestion.item_type && (
                  <span className="text-xs uppercase tracking-wider text-earth-300 shrink-0">
                    {suggestion.item_type}
                  </span>
                )}
                {suggestion.is_available && (
                  <span className="w-2 h-2 rounded-full bg-status-success-400 shrink-0" title={t('components.headerSearch.availableTitle', 'Available')} />
                )}
              </button>
            </li>
          ))}
        </ul>
      )}

      <button
        onClick={handleSubmit}
        className="w-full flex items-center gap-3 px-4 py-3 bg-earth-800 rounded-lg text-earth-100 hover:bg-earth-700 transition-colors"
      >
        <Search aria-hidden="true" className="w-5 h-5" />
        <span>
          {t('components.headerSearch.searchCatalogFor', 'Search catalog for')} &ldquo;{query}&rdquo;
          {facetFilter && <span className="text-brand-200 ml-1">{t('components.headerSearch.in', 'in')} {facetFilter}s</span>}
        </span>
      </button>

      {isFetchingSuggestions && (
        <p className="text-xs text-earth-300">{t('components.headerSearch.loadingSuggestions', 'Loading suggestions...')}</p>
      )}
    </div>
  )
}
