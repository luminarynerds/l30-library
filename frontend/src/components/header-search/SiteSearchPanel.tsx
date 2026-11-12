/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * SiteSearchPanel
 *
 * Site-scope panel for HeaderSearch. Owns live site-search suggestions,
 * the debounced fetch effect, the results list, the loading/no-match
 * states, and the CTA that opens the full /search page.
 */

import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { BookOpen, Search } from 'lucide-react'
import { useTranslation } from '../../i18n/I18nContext'
import { siteSearch, type SiteSearchResultItem } from '../../api/site-search-api'

export interface SiteSearchPanelProps {
  query: string
  onClose: () => void
  onClearQuery: () => void
  onConsumeQuery: () => void
  saveRecentSearch: (query: string) => void
  registerKeyHandler?: (handler: ((e: React.KeyboardEvent<HTMLInputElement>) => void) | null) => void
  registerSubmitHandler?: (handler: (() => void) | null) => void
}

const ENTITY_TYPE_LABELS: Record<string, string> = {
  catalog: 'Catalog',
  ebook: 'Ebook',
  event: 'Event',
  page: 'Page',
  announcement: 'Announcement',
  indie_author: 'Indie author',
}

export default function SiteSearchPanel({
  query,
  onClose,
  onClearQuery,
  onConsumeQuery,
  saveRecentSearch,
  registerKeyHandler,
  registerSubmitHandler,
}: SiteSearchPanelProps): React.ReactElement {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [siteSuggestions, setSiteSuggestions] = useState<SiteSearchResultItem[]>([])
  const [isFetchingSiteSuggestions, setIsFetchingSiteSuggestions] = useState(false)

  // Fetch live site-search results as user types.
  useEffect(() => {
    if (query.trim().length < 2) {
      setSiteSuggestions([])
      return
    }

    setIsFetchingSiteSuggestions(true)
    const timer = window.setTimeout(async () => {
      try {
        const response = await siteSearch(query.trim(), { perPage: 8 })
        setSiteSuggestions(response.results)
      } catch {
        setSiteSuggestions([])
      } finally {
        setIsFetchingSiteSuggestions(false)
      }
    }, 200)

    return () => {
      window.clearTimeout(timer)
      setIsFetchingSiteSuggestions(false)
    }
  }, [query])

  const handleSiteSuggestionClick = useCallback((result: SiteSearchResultItem) => {
    saveRecentSearch(query.trim() || result.title)
    navigate(result.url)
    onConsumeQuery()
    setSiteSuggestions([])
    onClose()
  }, [navigate, query, saveRecentSearch, onConsumeQuery, onClose])

  const handleSubmit = useCallback(() => {
    if (!query.trim()) return
    saveRecentSearch(query.trim())
    const params = new URLSearchParams({ q: query.trim() })
    navigate(`/search?${params.toString()}`)
    onConsumeQuery()
    setSiteSuggestions([])
    onClose()
  }, [query, saveRecentSearch, navigate, onConsumeQuery, onClose])

  const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Escape' && query) {
      e.preventDefault()
      onClearQuery()
    }
  }, [query, onClearQuery])

  useEffect(() => {
    registerKeyHandler?.(handleKeyDown)
    return () => registerKeyHandler?.(null)
  }, [registerKeyHandler, handleKeyDown])

  useEffect(() => {
    registerSubmitHandler?.(handleSubmit)
    return () => registerSubmitHandler?.(null)
  }, [registerSubmitHandler, handleSubmit])

  if (!query) return <></>

  return (
    <div className="space-y-3">
      {siteSuggestions.length > 0 && (
        <ul className="space-y-1" aria-label={t('aria.headerSearch.siteSearchResults', 'Site search results')}>
          {siteSuggestions.map((result) => (
            <li key={`${result.entity_type}-${result.id}`}>
              <button
                type="button"
                onClick={() => handleSiteSuggestionClick(result)}
                className="w-full text-left px-3 py-2 rounded-lg flex items-start gap-3 bg-earth-800 hover:bg-earth-700 transition-colors"
              >
                <BookOpen aria-hidden="true" className="w-4 h-4 text-earth-400 shrink-0 mt-0.5" />
                <div className="flex-1 min-w-0">
                  <p className="text-lsc-cream font-medium truncate" title={result.title}>{result.title}</p>
                  {result.snippet && (
                    <p className="text-xs text-earth-300 truncate" title={result.snippet}>{result.snippet}</p>
                  )}
                </div>
                <span className="text-xs uppercase tracking-wider text-earth-300 shrink-0">
                  {t(
                    `components.headerSearch.siteType.${result.entity_type}`,
                    ENTITY_TYPE_LABELS[result.entity_type] ?? result.entity_type
                  )}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}

      {!isFetchingSiteSuggestions && siteSuggestions.length === 0 && query.trim().length >= 2 && (
        <p className="text-xs text-earth-300">
          {t('components.headerSearch.siteNoLiveResults', 'No quick matches. Press Enter to run a full search.')}
        </p>
      )}

      <button
        type="button"
        onClick={handleSubmit}
        className="w-full flex items-center gap-3 px-4 py-3 bg-earth-800 rounded-lg text-earth-100 hover:bg-earth-700 transition-colors"
      >
        <Search aria-hidden="true" className="w-5 h-5" />
        <span>
          {siteSuggestions.length > 0
            ? t('components.headerSearch.seeAllSiteResultsFor', 'See all results for')
            : t('components.headerSearch.searchSiteFor', 'Search site for')}
          {' '}&ldquo;{query}&rdquo;
        </span>
      </button>

      {isFetchingSiteSuggestions && (
        <p className="text-xs text-earth-300">{t('components.headerSearch.loadingSuggestions', 'Loading suggestions...')}</p>
      )}
    </div>
  )
}
