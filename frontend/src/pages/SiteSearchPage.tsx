/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { Search, BookOpen, Library, Calendar, Megaphone, User } from "lucide-react"
import {
  logSearchClick,
  siteSearch,
  type SiteSearchResponse,
  type SiteSearchResultItem,
} from '@/api/site-search-api'
import { searchStaticSiteIndex } from '@/utils/site-search-index'

const ENTITY_LABEL: Record<string, string> = {
  catalog: 'Catalog',
  ebook: 'eBook',
  event: 'Event',
  announcement: 'Announcement',
  indie_author: 'Indie Author',
  page: 'Page',
}

export default function SiteSearchPage(): React.ReactElement {
  const [searchParams, setSearchParams] = useSearchParams()
  const query = searchParams.get('q')?.trim() || ''
  const page = Number(searchParams.get('page') || '1')
  const activeType = searchParams.get('type') || ''

  const [result, setResult] = useState<SiteSearchResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const runSearch = () => {
    if (!query) {
      setResult(null)
      return
    }

    setLoading(true)
    setError(null)

    siteSearch(query, {
      page,
      perPage: 20,
      entityTypes: activeType ? [activeType] : undefined,
    })
      .then((response) => {
        const staticResults = activeType && activeType !== 'page'
          ? []
          : searchStaticSiteIndex(query, 20)
        const merged = [...response.results]

        for (const staticResult of staticResults) {
          if (!merged.some((existingResult) => existingResult.url === staticResult.url)) {
            merged.push(staticResult)
          }
        }

        merged.sort((a, b) => b.score - a.score)

        setResult({
          ...response,
          total_results: merged.length,
          results: merged.slice(0, 20),
          has_more: merged.length > 20,
        })
      })
      .catch(() => setError('Unable to search the full site right now. Please try again.'))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- runSearch kicks off an async fetch; the synchronous setLoading/setError/setResult are in-flight request status, not derivable during render
    runSearch()
  }, [query, page, activeType])

  const handleResultClick = (item: SiteSearchResultItem, position: number) => {
    if (!query) return
    void logSearchClick({
      query,
      result_id: item.id,
      entity_type: item.entity_type,
      position,
    })
  }

  const setTypeFilter = (type: string) => {
    const next = new URLSearchParams(searchParams)
    if (!type || type === activeType) {
      next.delete('type')
    } else {
      next.set('type', type)
    }
    next.delete('page')
    setSearchParams(next, { replace: true })
  }

  const applySuggestion = (suggestion: string) => {
    const next = new URLSearchParams(searchParams)
    next.set('q', suggestion)
    next.delete('page')
    next.delete('type')
    setSearchParams(next, { replace: true })
  }

  const facetEntries = useMemo(() => {
    if (!result?.facets) return [] as Array<[string, number]>
    return Object.entries(result.facets).sort(([, a], [, b]) => b - a)
  }, [result?.facets])

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <header className="space-y-2">
        <h1 className="text-2xl font-serif font-bold text-lsc-brown dark:text-lsc-cream">Site Search</h1>
        <p className="text-lsc-brown/70 dark:text-lsc-cream/70">
          Search catalog, events, and announcements from one place.
        </p>
      </header>

      {!query && (
        <div className="rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 p-6 text-sm text-lsc-brown/70 dark:text-lsc-cream/70">
          Enter a query in the header search and select <strong>Site Search</strong>.
        </div>
      )}

      {query && (
        <div className="rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 p-4">
          <p className="text-sm text-lsc-brown/70 dark:text-lsc-cream/70">
            Results for <span className="font-semibold text-lsc-brown dark:text-lsc-cream">&quot;{query}&quot;</span>
            {activeType && (
              <span className="ml-2">
                in <span className="font-semibold">{ENTITY_LABEL[activeType] ?? activeType}</span>
                {' '}<button
                  type="button"
                  onClick={() => setTypeFilter('')}
                  className="ml-1 text-lsc-rose hover:underline"
                >
                  clear
                </button>
              </span>
            )}
          </p>
        </div>
      )}

      {result?.did_you_mean && (
        <div className="rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-cream/40 dark:bg-earth-800 p-4 text-sm">
          <span className="text-lsc-brown/80 dark:text-lsc-cream/80">Did you mean </span>
          <button
            type="button"
            onClick={() => applySuggestion(result.did_you_mean!)}
            className="font-semibold text-lsc-rose hover:underline"
          >
            {result.did_you_mean}
          </button>
          <span className="text-lsc-brown/80 dark:text-lsc-cream/80">?</span>
        </div>
      )}

      {loading && (
        <div className="rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 p-6 text-sm text-lsc-brown/70 dark:text-lsc-cream/70" role="status" aria-live="polite">
          Searching site content...
        </div>
      )}

      {error && (
        <div className="rounded-xl border border-status-danger-300 bg-status-danger-50 p-4 text-sm text-status-danger-700 dark:border-status-danger-700 dark:bg-status-danger-900/20 dark:text-status-danger-300 flex items-center justify-between gap-4" role="alert">
          <span>{error}</span>
          <button
            onClick={runSearch}
            className="shrink-0 rounded-lg bg-status-danger-100 dark:bg-status-danger-800/30 px-3 py-1.5 text-sm font-medium text-status-danger-700 dark:text-status-danger-300 hover:bg-status-danger-200 dark:hover:bg-status-danger-800/50 transition"
          >
            Try Again
          </button>
        </div>
      )}

      {result && !loading && (
        <div className="grid grid-cols-1 lg:grid-cols-[16rem_1fr] gap-6">
          {facetEntries.length > 0 && (
            <aside className="rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 p-4 h-fit">
              <h2 className="font-serif text-sm font-semibold text-lsc-brown dark:text-lsc-cream mb-3">
                Filter by type
              </h2>
              <ul className="space-y-1">
                <li>
                  <button
                    type="button"
                    onClick={() => setTypeFilter('')}
                    className={`w-full flex items-center justify-between rounded-lg px-2 py-1.5 text-sm transition ${
                      !activeType
                        ? 'bg-lsc-rose/10 text-lsc-rose font-medium'
                        : 'text-lsc-brown/80 dark:text-lsc-cream/80 hover:bg-lsc-cream dark:hover:bg-earth-700'
                    }`}
                  >
                    <span>All</span>
                    <span className="text-xs text-lsc-brown/60 dark:text-lsc-cream/60">
                      {facetEntries.reduce((sum, [, n]) => sum + n, 0)}
                    </span>
                  </button>
                </li>
                {facetEntries.map(([type, count]) => (
                  <li key={type}>
                    <button
                      type="button"
                      onClick={() => setTypeFilter(type)}
                      className={`w-full flex items-center justify-between rounded-lg px-2 py-1.5 text-sm transition ${
                        activeType === type
                          ? 'bg-lsc-rose/10 text-lsc-rose font-medium'
                          : 'text-lsc-brown/80 dark:text-lsc-cream/80 hover:bg-lsc-cream dark:hover:bg-earth-700'
                      }`}
                    >
                      <span>{ENTITY_LABEL[type] ?? type}</span>
                      <span className="text-xs text-lsc-brown/60 dark:text-lsc-cream/60">{count}</span>
                    </button>
                  </li>
                ))}
              </ul>
            </aside>
          )}

          <div className="space-y-3">
            <p className="text-sm text-lsc-brown/70 dark:text-lsc-cream/70">
              Found {result.total_results} result{result.total_results === 1 ? '' : 's'}
            </p>

            {result.results.length === 0 ? (
              <div className="rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 p-6 text-sm text-lsc-brown/70 dark:text-lsc-cream/70 space-y-2">
                <p>No results found. Try:</p>
                <ul className="list-disc list-inside space-y-1">
                  <li>Check your spelling or use different keywords</li>
                  <li>Use fewer or broader search terms</li>
                  <li><Link to="/catalog" className="text-lsc-rose hover:underline">Browse the catalog</Link> directly</li>
                </ul>
              </div>
            ) : (
              result.results.map((item, index) => (
                <Link
                  to={item.url}
                  key={item.id}
                  onClick={() => handleResultClick(item, index)}
                  className="block rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 p-4 hover:border-lsc-rose/60 hover:shadow-sm transition"
                >
                  <div className="flex items-start gap-3">
                    <span className="mt-0.5 text-lsc-rose">
                      {item.entity_type === 'ebook' ? <Library className="w-4 h-4" aria-hidden="true" /> :
                       item.entity_type === 'catalog' ? <BookOpen className="w-4 h-4" aria-hidden="true" /> :
                       item.entity_type === 'event' ? <Calendar className="w-4 h-4" aria-hidden="true" /> :
                       item.entity_type === 'announcement' ? <Megaphone className="w-4 h-4" aria-hidden="true" /> :
                       item.entity_type === 'indie_author' ? <User className="w-4 h-4" aria-hidden="true" /> :
                       <Search className="w-4 h-4" aria-hidden="true" />}
                    </span>
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <h2 className="font-serif text-base font-semibold text-lsc-brown dark:text-lsc-cream">{item.title}</h2>
                        <span className="text-xs uppercase tracking-wide px-2 py-0.5 rounded bg-lsc-rose/10 text-lsc-rose">
                          {ENTITY_LABEL[item.entity_type] ?? item.entity_type}
                        </span>
                      </div>
                      {item.snippet && (
                        <p className="mt-1 text-sm text-lsc-brown/75 dark:text-lsc-cream/75 line-clamp-2" title={item.snippet}>{item.snippet}</p>
                      )}
                      <p className="mt-2 text-xs text-lsc-brown/60 dark:text-lsc-cream/70">{item.url}</p>
                    </div>
                  </div>
                </Link>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  )
}
