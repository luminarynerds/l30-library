/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect, useCallback } from 'react'
import { Landmark, Search, ExternalLink, Loader2 } from 'lucide-react'
import StandardPageLayout from '@/components/StandardPageLayout'
import {
  getRecentFilings,
  searchFilings,
  getBankruptcyCourts,
  type BankruptcyFiling,
  type BankruptcyCourt,
  type BankruptcySearchResponse,
} from '@/api/domains/reference/bankruptcy-api'
import { t, getCurrentLocale } from '@/i18n'

const DATE_RANGE_OPTIONS = [
  { label: '7 days', value: 7 },
  { label: '14 days', value: 14 },
  { label: '30 days', value: 30 },
] as const

export default function BankruptcyFilingsPage(): React.ReactElement {
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedCourt, setSelectedCourt] = useState('')
  const [selectedDays, setSelectedDays] = useState(7)
  const [courts, setCourts] = useState<BankruptcyCourt[]>([])
  const [filings, setFilings] = useState<BankruptcyFiling[]>([])
  const [source, setSource] = useState('CourtListener / RECAP Archive')
  const [sourceUrl, setSourceUrl] = useState('https://www.courtlistener.com/recap/')
  const [isLoading, setIsLoading] = useState(true)
  const [hasSearched, setHasSearched] = useState(false)

  const applyResponse = (resp: BankruptcySearchResponse) => {
    setFilings(resp.filings)
    setSource(resp.source)
    setSourceUrl(resp.source_url)
  }

  // Load courts on mount
  useEffect(() => {
    getBankruptcyCourts().then(setCourts)
  }, [])

  // Load recent filings on mount and when court/days change
  const loadRecent = useCallback(async () => {
    setIsLoading(true)
    setHasSearched(false)
    try {
      const resp = await getRecentFilings(selectedCourt || undefined, selectedDays)
      applyResponse(resp)
    } finally {
      setIsLoading(false)
    }
  }, [selectedCourt, selectedDays])

  useEffect(() => {
    if (!hasSearched) {
      loadRecent()
    }
  }, [loadRecent]) // eslint-disable-line react-hooks/exhaustive-deps

  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      loadRecent()
      return
    }
    setIsLoading(true)
    setHasSearched(true)
    try {
      const resp = await searchFilings(searchQuery.trim(), selectedCourt || undefined)
      applyResponse(resp)
    } finally {
      setIsLoading(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') handleSearch()
  }

  const formatDate = (dateStr: string | null): string => {
    if (!dateStr) return 'N/A'
    return new Date(dateStr).toLocaleDateString(getCurrentLocale(), {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    })
  }

  return (
    <StandardPageLayout
      title="Bankruptcy Filing Search"
      subtitle="Search recent federal bankruptcy filings for free. Powered by CourtListener and the RECAP Archive."
      icon={Landmark}
    >
      {/* Controls */}
      <section aria-label={t('aria.bankruptcyFilings.searchControls')}>
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 border border-lsc-border dark:border-earth-700">
          <div className="flex flex-col gap-4">
            {/* Search input row */}
            <div className="flex flex-col sm:flex-row gap-4">
              <div className="flex-1 relative">
                <Search
                  className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70"
                  aria-hidden="true"
                />
                <input
                  type="text"
                  placeholder={t('placeholder.bankruptcyFilings.searchByPartyName')}
                  aria-label={t('aria.bankruptcyFilings.searchBankruptcyFilings')}
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyDown={handleKeyDown}
                  className="w-full pl-10 pr-4 py-2.5 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-earth-50 placeholder-earth-500 focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
                />
              </div>
              <button
                onClick={handleSearch}
                disabled={isLoading}
                className="px-6 py-2.5 bg-lsc-rose text-white rounded-xl font-medium hover:bg-lsc-rose/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                {isLoading ? (
                  <Loader2 className="w-4 h-4 motion-safe:animate-spin" aria-hidden="true" />
                ) : (
                  <Search className="w-4 h-4" aria-hidden="true" />
                )}
                Search
              </button>
            </div>

            {/* Filters row */}
            <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center">
              {/* Court selector */}
              <div className="w-full sm:w-64">
                <select
                  value={selectedCourt}
                  onChange={(e) => setSelectedCourt(e.target.value)}
                  aria-label={t('aria.bankruptcyFilings.filterByCourt')}
                  className="w-full px-4 py-2.5 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-earth-50 focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
                >
                  <option value="">All Courts</option>
                  {courts.map((court) => (
                    <option key={court.id} value={court.id}>
                      {court.short_name}
                    </option>
                  ))}
                </select>
              </div>

              {/* Date range buttons */}
              <div className="flex gap-2">
                {DATE_RANGE_OPTIONS.map((opt) => (
                  <button
                    key={opt.value}
                    onClick={() => {
                      setSelectedDays(opt.value)
                      setHasSearched(false)
                    }}
                    className={`px-4 py-2 rounded-xl text-sm font-medium border transition-colors ${
                      selectedDays === opt.value && !hasSearched
                        ? 'bg-lsc-rose text-white border-lsc-rose'
                        : 'bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream/80 border-lsc-border dark:border-earth-700 hover:border-earth-400'
                    }`}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Results */}
      <section aria-label={t('aria.bankruptcyFilings.searchResults')}>
        {isLoading ? (
          <div className="flex items-center justify-center py-16">
            <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" aria-hidden="true" />
          </div>
        ) : filings.length > 0 ? (
          <div className="space-y-4">
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
              {filings.length} filing{filings.length !== 1 ? 's' : ''} found
            </p>
            {filings.map((filing) => (
              <div
                key={filing.docket_id}
                className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 border border-lsc-border dark:border-earth-700"
              >
                <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <h3 className="font-serif font-semibold text-lsc-dark dark:text-earth-50 truncate" title={filing.case_name}>
                      {filing.case_name}
                    </h3>
                    <div className="flex flex-wrap gap-x-4 gap-y-1 mt-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                      <span>Docket: {filing.docket_number}</span>
                      <span>Filed: {formatDate(filing.date_filed)}</span>
                      <span>{filing.court_name}</span>
                    </div>
                    {filing.trustee && (
                      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                        Trustee: {filing.trustee}
                      </p>
                    )}
                  </div>
                  <div className="flex items-center gap-3 flex-shrink-0">
                    {filing.chapter && (
                      <span className="px-2 py-0.5 rounded text-xs font-medium bg-sage-100 dark:bg-sage-900/30 text-sage-700 dark:text-sage-400">
                        Chapter {filing.chapter}
                      </span>
                    )}
                    <a
                      href={filing.courtlistener_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 text-sm text-lsc-rose hover:text-lsc-rose/80 font-medium whitespace-nowrap"
                    >
                      View on CourtListener
                      <ExternalLink className="w-3 h-3" aria-hidden="true" />
                    </a>
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-16">
            <Landmark
              className="w-16 h-16 mx-auto text-lsc-border dark:text-lsc-cream/70 mb-4"
              aria-hidden="true"
            />
            <h3 className="text-lg font-medium text-lsc-dark dark:text-earth-50 mb-2">
              No filings found
            </h3>
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
              {hasSearched
                ? 'Try adjusting your search query or filters.'
                : 'No recent bankruptcy filings were found for the selected criteria.'}
            </p>
          </div>
        )}
      </section>

      {/* Attribution footer */}
      <div className="mt-8 text-center text-sm text-lsc-dark/70 dark:text-lsc-cream/50">
        Data provided by{' '}
        <a
          href={sourceUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="text-lsc-rose hover:underline"
        >
          {source}
        </a>
        {' '}&mdash; a project of{' '}
        <a
          href="https://free.law/"
          target="_blank"
          rel="noopener noreferrer"
          className="text-lsc-rose hover:underline"
        >
          Free Law Project
        </a>
      </div>
    </StandardPageLayout>
  )
}
