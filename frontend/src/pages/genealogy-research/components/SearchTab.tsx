/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import {
  FileText, Users, Search,
  MessageSquare, Loader,
} from 'lucide-react'
import {
  genealogySearchApi,
  type SearchResult,
} from '@/api/genealogy-research-api'
import toast from 'react-hot-toast'
import DOMPurify from 'dompurify'
import { useTranslation} from '@/i18n'

export default function ProjectSearchTab({ projectId }: { projectId: number }) {
  const { t } = useTranslation();
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<SearchResult[]>([])
  const [loading, setLoading] = useState(false)
  const [searched, setSearched] = useState(false)
  const [searchPersons, setSearchPersons] = useState(true)
  const [searchDocuments, setSearchDocuments] = useState(true)
  const [searchNotes, setSearchNotes] = useState(true)

  async function handleSearch() {
    if (!query.trim()) return
    try {
      setLoading(true)
      setSearched(true)
      const response = await genealogySearchApi.search(projectId, query, {
        search_persons: searchPersons,
        search_documents: searchDocuments,
        search_notes: searchNotes,
      }) as { query: string; total_results: number; results: SearchResult[] }
      setResults(response.results || [])
    } catch {
      toast.error(t('toast.selectionList.searchFailed'))
    } finally {
      setLoading(false)
    }
  }

  const typeColors: Record<string, string> = {
    person: 'bg-earth-100 text-lsc-rose dark:bg-earth-800/30 dark:text-lsc-rose-light',
    document: 'bg-status-warning-100 text-status-warning-700 dark:bg-status-warning-900/30 dark:text-status-warning-300',
    note: 'bg-category-100 text-category-700 dark:bg-category-900/30 dark:text-category-300',
  }
  const typeIcons: Record<string, React.ReactNode> = {
    person: <Users className="w-4 h-4 text-earth-600" />,
    document: <FileText className="w-4 h-4 text-status-warning-500" />,
    note: <MessageSquare className="w-4 h-4 text-category-500" />,
  }

  return (
    <div className="space-y-5">
      <div>
        <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-1">Full-Text Search</h2>
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
          Search across all persons, documents (including OCR text), and research notes in this project.
        </p>
      </div>

      {/* Search Input */}
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-5">
        <div className="flex gap-3 mb-4">
          <div className="flex-1 relative">
            <Search className="w-5 h-5 absolute left-3 top-1/2 -translate-y-1/2 text-lsc-dark/70 dark:text-lsc-cream/70" />
            <input
              type="text"
              value={query}
              onChange={e => setQuery(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleSearch()}
              placeholder={t('genealogyResearchPageContent.searchNamesDatesPlacesDocument')}
              aria-label={t('genealogyResearchPageContent.searchNamesDatesPlacesDocument2')}
              className="w-full pl-10 pr-4 py-2.5 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
            />
          </div>
          <button
            onClick={handleSearch}
            disabled={!query.trim() || loading}
            className="px-5 py-2.5 bg-status-warning-600 text-white rounded-lg hover:bg-status-warning-700 disabled:opacity-50 font-medium flex items-center gap-2"
          >
            {loading ? <Loader className="w-4 h-4 motion-safe:animate-spin" /> : <Search className="w-4 h-4" />}
            Search
          </button>
        </div>

        {/* Search Scope */}
        <div className="flex gap-4 text-sm">
          <label className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70 cursor-pointer">
            <input type="checkbox" checked={searchPersons} onChange={e => setSearchPersons(e.target.checked)} className="rounded accent-status-warning-500" />
            Persons
          </label>
          <label className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70 cursor-pointer">
            <input type="checkbox" checked={searchDocuments} onChange={e => setSearchDocuments(e.target.checked)} className="rounded accent-status-warning-500" />
            Documents
          </label>
          <label className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70 cursor-pointer">
            <input type="checkbox" checked={searchNotes} onChange={e => setSearchNotes(e.target.checked)} className="rounded accent-status-warning-500" />
            Notes
          </label>
        </div>
      </div>

      {/* Screen reader announcement */}
      <div aria-live="polite" aria-atomic="true" className="sr-only">
        {loading
          ? 'Searching…'
          : searched && results.length === 0
            ? `No results found for "${query}"`
            : results.length > 0
              ? `${results.length} result${results.length !== 1 ? 's' : ''} for "${query}"`
              : ''}
      </div>

      {/* Results */}
      {loading ? (
        <div className="flex justify-center py-12" aria-busy="true">
          <Loader className="w-6 h-6 motion-safe:animate-spin text-status-warning-500" aria-hidden="true" />
        </div>
      ) : searched && results.length === 0 ? (
        <div className="text-center py-12 bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700">
          <Search className="w-12 h-12 mx-auto text-earth-300 mb-3" />
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">No results found for "{query}"</p>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70 text-sm mt-1">{t('genealogyResearchPageContent.tryDifferentSearchTermsOr')}</p>
        </div>
      ) : results.length > 0 ? (
        <div className="space-y-3">
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{results.length} result{results.length !== 1 ? 's' : ''} for "{query}"</p>
          {results.map((result, i) => (
            <div key={`${result.result_type}-${result.id}-${i}`}
              className="bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700 p-4">
              <div className="flex items-start gap-3">
                <div className="flex-shrink-0 mt-0.5">
                  {typeIcons[result.result_type] || <FileText className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/70" />}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <h4 className="font-medium text-sm text-lsc-dark dark:text-lsc-cream">{result.title}</h4>
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${typeColors[result.result_type] || 'bg-earth-100 dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70'}`}>
                      {result.result_type}
                    </span>
                    {result.relevance_score > 0 && (
                      <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                        {Math.round(result.relevance_score * 100)}% relevance
                      </span>
                    )}
                  </div>
                  {result.snippet && (
                    <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 leading-relaxed"
                      dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(result.snippet).replace(/\*\*(.*?)\*\*/g, '<mark class="bg-status-warning-200 dark:bg-status-warning-900/50 px-0.5 rounded">$1</mark>') }}
                    />
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : null}
    </div>
  )
}
