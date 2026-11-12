/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { BookOpen, Brain, Loader2, X } from 'lucide-react'
import { type AutocompleteSuggestion } from '@/api/domains/catalog/semantic-search-api'
import { clsx } from '@/utils/helpers'
import { t } from '@/i18n'
import { CatalogCover } from '@/pages/catalog/components/CatalogItemThumbnail'
import { SourceBadge } from './SearchResultCard'

export function AutocompleteDropdown({
  suggestions,
  visible,
  loading = false,
  onSelect,
  onClose,
}: {
  suggestions: AutocompleteSuggestion[]
  visible: boolean
  loading?: boolean
  onSelect: (suggestion: AutocompleteSuggestion) => void
  onClose: () => void
}) {
  if (!visible && !loading) return null
  if (!loading && suggestions.length === 0) return null

  return (
    <div
      id="autocomplete-list"
      className="absolute z-50 w-full mt-1 bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-xl shadow-lg max-h-80 overflow-y-auto"
      role="listbox"
      aria-label={t('aria.headerSearch.searchSuggestions')}
    >
      <div className="p-2 border-b border-earth-100 dark:border-earth-700 flex items-center justify-between">
        <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 flex items-center gap-1">
          {loading ? (
            <>
              <Loader2 className="w-3 h-3 motion-safe:animate-spin" />
              Finding suggestions...
            </>
          ) : (
            <>
              <Brain className="w-3 h-3" />
              Intelligent suggestions
            </>
          )}
        </span>
        <button
          onClick={onClose}
          className="p-1 hover:bg-earth-100 dark:bg-earth-700 dark:hover:bg-earth-700 rounded"
          aria-label={t('aria.semanticSearch.closeSuggestions')}
        >
          <X className="w-3 h-3 text-lsc-dark/70 dark:text-lsc-cream/70" />
        </button>
      </div>
      {loading && suggestions.length === 0 && (
        <div className="p-4 text-center text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
          <Loader2 className="w-4 h-4 motion-safe:animate-spin inline-block mr-2" />
          Searching catalog for matches...
        </div>
      )}
      {suggestions.map((s, i) => (
        <button
          key={`${s.id}-${i}`}
          role="option"
          className="w-full text-left px-4 py-2.5 hover:bg-earth-50 dark:bg-earth-900 dark:hover:bg-earth-700 border-b border-earth-100 dark:border-earth-700 last:border-0 flex items-center gap-3 transition-colors"
          onClick={() => onSelect(s)}
        >
          <div className="flex-shrink-0 w-8 h-10 bg-earth-100 dark:bg-earth-700 rounded flex items-center justify-center overflow-hidden">
            {s.cover_url ? (
              <CatalogCover
                coverUrl={s.cover_url}
                alt={`Cover of ${s.title}`}
                title={s.title}
                itemType={s.format}
                size="sm"
              />
            ) : (
              <BookOpen className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/70" />
            )}
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-sm font-medium text-lsc-dark dark:text-lsc-cream truncate" title={s.title}>
              {s.title}
            </div>
            {s.author && (
              <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 truncate" title={s.author}>{s.author}</div>
            )}
          </div>
          <div className="flex items-center gap-1.5 flex-shrink-0">
            <span
              className={clsx(
                'text-xs px-1.5 py-0.5 rounded',
                s.match_type === 'prefix'
                  ? 'bg-status-success-100 text-status-success-700 dark:bg-status-success-900/30 dark:text-status-success-300'
                  : 'bg-status-warning-100 text-status-warning-700 dark:bg-status-warning-900/30 dark:text-status-warning-300'
              )}
            >
              {s.match_type === 'prefix' ? 'exact' : `${Math.round(s.similarity_score * 100)}%`}
            </span>
            <SourceBadge source={s.source} />
          </div>
        </button>
      ))}
    </div>
  )
}
