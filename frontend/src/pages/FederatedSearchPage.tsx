/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Federated Search Page
 *
 * Patron-facing page for searching across local catalog and partner libraries.
 * Integrates the federated search feature components with ILL request capability.
 */

import { useState, useCallback } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { Search, Library, ArrowRight } from 'lucide-react'
import { useTranslation } from '@/i18n'
import { FederatedSearchBox } from '@/features/federated-search/components/FederatedSearchBox'
import { ResultCard } from '@/features/federated-search/components/ResultCard'
import { SearchLoadingState } from '@/features/federated-search/components/SearchLoadingState'
import { useFederatedSearch } from '@/features/federated-search/hooks/useFederatedSearch'
import type { FederatedSearchResult } from '@/features/federated-search/types/federated-search.types'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'
import PageContainer from '@/components/layout/PageContainer'

export default function FederatedSearchPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const initialQuery = searchParams.get('q') || ''

  const {
    state,
    search,
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    clear: _clear,
    isLoading,
    isError,
  } = useFederatedSearch()

  const [selectedResult, setSelectedResult] = useState<FederatedSearchResult | null>(null)

  const handleResultClick = useCallback(
    (result: FederatedSearchResult) => {
      // If it's a local catalog item, navigate to it
      const localAttribution = result.attribution?.find(
        (a) => a.source === 'local-catalog'
      )
      if (localAttribution) {
        navigate(`/catalog/${result.isbn || result.title}`)
        return
      }

      // For external results, show ILL option
      setSelectedResult(result)
    },
    [navigate]
  )

  const handleRequestILL = useCallback(
    (result: FederatedSearchResult) => {
      // Navigate to ILL request form with pre-filled data
      const params = new URLSearchParams()
      if (result.title) params.set('title', result.title)
      if (result.author) params.set('author', result.author)
      if (result.isbn) params.set('isbn', result.isbn)
      if (result.publisher) params.set('publisher', result.publisher)
      if (result.year) params.set('year', result.year.toString())
      const sourceAttr = result.attribution?.[0]
      if (sourceAttr) params.set('source', sourceAttr.source)

      navigate(`/ill/request?${params}`)
    },
    [navigate]
  )

  return (
    <PageContainer className="py-8">
      {/* Header */}
      <div className="text-center mb-8">
        <div className="flex items-center justify-center gap-3 mb-3">
          <Library className="w-8 h-8 text-lsc-rose" />
          <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
            {t('catalog.federatedSearch.title', 'Search Partner Libraries')}
          </h1>
        </div>
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70 max-w-2xl mx-auto">
          {t(
            'catalog.federatedSearch.subtitle',
            "Search our catalog and partner libraries simultaneously. Can't find it here? Request it via Interlibrary Loan."
          )}
        </p>
      </div>

      {/* Search Box */}
      <div className="mb-6">
        <FederatedSearchBox
          initialQuery={initialQuery}
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          selectedSources={['local-catalog', 'open-library', 'worldcat'] as any}
          onSearch={(query) => {
            search({
              q: query,
              sources: ['local-catalog', 'open-library', 'worldcat'],
            })
          }}
        />
      </div>

      {/* Filters — hidden: backend federated search does not support server-side filtering yet */}

      {/* Loading State */}
      {isLoading && <SearchLoadingState sourceStatus={state.sourceStatus} status="searching" />}

      {/* Error State */}
      {isError && (
        <div className="text-center py-12" role="alert">
          <p className="text-status-danger-600 dark:text-status-danger-400">
            {t('catalog.federatedSearch.error', 'Search failed. Please try again.')}
          </p>
        </div>
      )}

      {/* Results */}
      {state.results.length > 0 && (
        <div className="space-y-4">
          <div className="flex items-center justify-between mb-4">
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
              {t('catalog.federatedSearch.resultCount', {
                count: state.total,
              })}
              {state.sourceStatus.length > 0 && (
                <span className="ml-2">
                  from {state.sourceStatus.filter((s) => s.status === 'success').length} sources
                </span>
              )}
            </p>
          </div>

          {state.results.map((result: FederatedSearchResult, index: number) => (
            <div key={`${result.isbn || result.title}-${index}`} className="relative">
              <ResultCard
                result={result}
                onClick={handleResultClick}
                showAttribution
                showDeduplication
              />

              {/* ILL Request Button for external results */}
              {!result.attribution?.some((a) => a.source === 'local-catalog') && (
                <div className="mt-2 flex justify-end">
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      handleRequestILL(result)
                    }}
                    className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg bg-lsc-rose text-white hover:bg-lsc-rose/90 transition-colors"
                  >
                    <Search className="w-4 h-4" />
                    {t('catalog.federatedSearch.requestILL', 'Request via Interlibrary Loan')}
                    <ArrowRight className="w-4 h-4" />
                  </button>
                </div>
              )}
            </div>
          ))}

          {/* Pagination hidden — backend federated search does not support server-side pagination yet */}
        </div>
      )}

      {/* Empty State */}
      {!isLoading && state.status === 'success' && state.results.length === 0 && (
        <div className="text-center py-12">
          <Search className="w-12 h-12 text-earth-300 dark:text-earth-600 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">
            {t('catalog.federatedSearch.noResults', 'No results found')}
          </h3>
          <p className="text-earth-600 dark:text-earth-400">
            {t(
              'catalog.federatedSearch.noResultsHint',
              'Try different keywords or check your spelling.'
            )}
          </p>
        </div>
      )}

      {/* ILL Detail Modal */}
      {selectedResult && !selectedResult.attribution?.some((a) => a.source === 'local-catalog') && (


        <ModalBackdrop onClose={() => setSelectedResult(null)} title="Interlibrary Loan Request">

          {/* eslint-disable-next-line jsx-a11y/click-events-have-key-events */}
          <div
            className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 max-w-lg w-full mx-4 shadow-lg"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="font-serif text-lg font-semibold mb-2">{selectedResult.title}</h3>
            {selectedResult.author && (
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
                by {selectedResult.author}
              </p>
            )}
            <p className="text-sm text-earth-600 dark:text-earth-400 mb-6">
              This item is available at a partner library. You can request it via Interlibrary Loan.
            </p>
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setSelectedResult(null)}
                className="px-4 py-2 text-sm rounded-lg border border-lsc-border dark:border-earth-600"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  handleRequestILL(selectedResult)
                  setSelectedResult(null)
                }}
                className="px-4 py-2 text-sm font-medium rounded-lg bg-lsc-rose text-white hover:bg-lsc-rose/90"
              >
                Request Interlibrary Loan
              </button>
            </div>
          </div>
        </ModalBackdrop>
      )}
    </PageContainer>
  )
}
