/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { Search, Plus, BookOpen, Loader, Check, Star, Tag } from 'lucide-react'
import { SUCCESS_FEEDBACK_DURATION_MS } from '@/constants/timeouts'
import {
  searchKnowledgeBase,
  createKnowledgeBaseEntry,
} from '../../api/library-agents-api'
import type { KnowledgeBaseEntry, KnowledgeBaseCreateData } from '../../api/library-agents-api'
import { t } from '@/i18n'
import { KBFormModal } from './KBFormModal'

export function KnowledgeTab({
  token,
  onEntryAdded,
}: {
  token: string
  onEntryAdded: () => void
}) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<KnowledgeBaseEntry[]>([])
  const [isSearching, setIsSearching] = useState(false)
  const [hasSearched, setHasSearched] = useState(false)
  const [showForm, setShowForm] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [successMsg, setSuccessMsg] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!query.trim() || query.length < 2) return
    setIsSearching(true)
    setError(null)
    setHasSearched(true)
    try {
      const data = await searchKnowledgeBase(query, { limit: 20 }, token)
      setResults(data)
    } catch {
      setError('Search failed. Please try again.')
      setResults([])
    } finally {
      setIsSearching(false)
    }
  }

  const handleAddEntry = async (data: KnowledgeBaseCreateData) => {
    setIsSaving(true)
    try {
      await createKnowledgeBaseEntry(token, data)
      setShowForm(false)
      setSuccessMsg('Entry added successfully!')
      setTimeout(() => setSuccessMsg(null), SUCCESS_FEEDBACK_DURATION_MS)
      onEntryAdded()
    } catch (_err) {
      setError('Failed to add entry. Please try again.')
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <div className="space-y-4">
      {successMsg && (
        <div className="bg-status-success-50 dark:bg-status-success-900/20 text-status-success-700 dark:text-status-success-300 text-sm px-4 py-3 rounded-lg flex items-center gap-2">
          <Check className="w-4 h-4" aria-hidden="true" />
          {successMsg}
        </div>
      )}

      <div className="flex flex-col sm:flex-row gap-3">
        <form onSubmit={handleSearch} className="flex gap-2 flex-1">
          <input
            type="search"
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder={t('placeholder.adminLibraryAgents.searchKnowledgeBase')}
            aria-label={t('aria.adminLibraryAgents.searchKnowledgeBase')}
            className="flex-1 px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-cream/30 dark:bg-earth-900/50 text-sm text-lsc-dark dark:text-lsc-cream placeholder-earth-500 dark:placeholder-earth-500 focus:outline-none focus:border-lsc-rose"
          />
          <button type="submit" disabled={isSearching || query.length < 2} className="px-3 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 disabled:opacity-50 transition-colors">
            {isSearching ? <Loader className="w-4 h-4 motion-safe:animate-spin" aria-hidden="true" /> : <Search className="w-4 h-4" aria-hidden="true" />}
          </button>
        </form>
        <button
          onClick={() => setShowForm(true)}
          className="px-4 py-2 bg-lsc-rose text-white rounded-lg text-sm font-medium hover:bg-lsc-rose/90 transition-colors flex items-center gap-2 whitespace-nowrap"
        >
          <Plus className="w-4 h-4" aria-hidden="true" />
          Add Entry
        </button>
      </div>

      {error && (
        <p className="text-sm text-status-danger-600 dark:text-status-danger-400">{error}</p>
      )}

      {hasSearched && results.length === 0 && !isSearching && !error && (
        <div className="text-center py-10 text-lsc-dark/70 dark:text-lsc-cream/70 text-sm">
          No entries found for "{query}".
        </div>
      )}

      {!hasSearched && (
        <div className="text-center py-8 text-lsc-dark/70 dark:text-lsc-cream/70 text-sm">
          <BookOpen className="w-10 h-10 mx-auto mb-2 opacity-40" aria-hidden="true" />
          Search the knowledge base above, or add a new entry.
        </div>
      )}

      <div className="space-y-3">
        {results.map(entry => (
          <div key={entry.id} className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-4">
            <div className="flex items-start gap-3">
              <div className="flex-1">
                <div className="flex flex-wrap items-center gap-2 mb-1">
                  {entry.is_frequently_asked && (
                    <Star className="w-3.5 h-3.5 text-lsc-rose flex-shrink-0" aria-label={t('aria.adminLibraryAgents.frequentlyAsked')} />
                  )}
                  <span className="text-xs px-2 py-0.5 rounded-full bg-lsc-cream dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70">
                    {entry.category}
                  </span>
                  {entry.department && (
                    <span className="text-xs px-2 py-0.5 rounded-full bg-lsc-cream dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70">
                      {entry.department}
                    </span>
                  )}
                </div>
                <p className="text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
                  {entry.question}
                </p>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                  {entry.answer}
                </p>
                {entry.tags.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-2">
                    {entry.tags.map(t => (
                      <span key={t} className="text-xs px-1.5 py-0.5 rounded bg-lsc-cream dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70 flex items-center gap-1">
                        <Tag className="w-2.5 h-2.5" aria-hidden="true" /> {t}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>

      {showForm && (
        <KBFormModal onSave={handleAddEntry} onClose={() => setShowForm(false)} isSaving={isSaving} />
      )}
    </div>
  )
}
