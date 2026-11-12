/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React, { useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { Search, Loader2, X, HelpCircle, Shuffle, Info } from 'lucide-react'
import { getRandomItem } from '@/api/domains/catalog/catalog-api'
import { type SearchSuggestion } from '@/api/pg-search-api'
import { useTranslation } from '@/i18n/I18nContext'
import { clsx } from '@/utils/helpers'

interface CatalogSearchBarProps {
  searchQuery: string
  onSearchChange: (value: string) => void
  onSubmit: (e: React.FormEvent) => void
  onClearSearch: () => void
  suggestions: SearchSuggestion[]
  showSuggestions: boolean
  onShowSuggestionsChange: (show: boolean) => void
  selectedSuggestionIndex: number
  onSelectedSuggestionIndexChange: (index: number) => void
  onSuggestionSelect: (suggestion: SearchSuggestion) => void
  searchInputRef: React.RefObject<HTMLInputElement>
  suggestionsRef: React.RefObject<HTMLDivElement>
  isLoading: boolean
  reduceMotion: boolean
}

function SearchSyntaxHelp() {
  const [open, setOpen] = useState(false)
  const { t } = useTranslation()

  // Pair each example with its plain-language description so the popover
  // reads top-to-bottom as "you type X, you get Y".
  const examples: Array<{ example: string; desc: string }> = [
    { example: t('catalog.searchSyntaxPhraseExample'), desc: t('catalog.searchSyntaxPhraseDesc') },
    { example: t('catalog.searchSyntaxAuthorExample'), desc: t('catalog.searchSyntaxAuthorDesc') },
    { example: t('catalog.searchSyntaxCombineExample'), desc: t('catalog.searchSyntaxCombineDesc') },
    { example: t('catalog.searchSyntaxExcludeExample'), desc: t('catalog.searchSyntaxExcludeDesc') },
    { example: t('catalog.searchSyntaxOrExample'), desc: t('catalog.searchSyntaxOrDesc') },
  ]

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen(prev => !prev)}
        onBlur={() => setTimeout(() => setOpen(false), 150)}
        className="flex items-center justify-center w-7 h-7 rounded-full text-lsc-dark/70 dark:text-lsc-cream/50 hover:text-lsc-rose hover:bg-lsc-rose/10 transition-colors"
        aria-label={t('catalog.searchSyntaxHelpLabel')}
        aria-expanded={open}
      >
        <Info className="w-4 h-4" aria-hidden="true" />
      </button>
      {open && (
        <div
          className="absolute right-0 top-full mt-2 w-80 bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-xl shadow-lg z-50 p-3"
          role="tooltip"
        >
          <p className="text-xs font-bold text-lsc-dark/70 dark:text-lsc-cream/60 uppercase tracking-wide mb-2">
            {t('catalog.searchSyntaxTitle')}
          </p>
          <ul className="space-y-1.5 text-sm text-lsc-dark dark:text-lsc-cream">
            {examples.map(({ example, desc }) => (
              <li key={example} className="flex flex-col">
                <code className="font-mono text-xs px-1.5 py-0.5 bg-lsc-cream dark:bg-earth-700 border border-lsc-border dark:border-earth-600 rounded self-start">
                  {example}
                </code>
                <span className="text-xs text-lsc-dark/80 dark:text-lsc-cream/70 mt-0.5">
                  {desc}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

function KeyboardShortcutHelp() {
  const [open, setOpen] = useState(false)
  const { t } = useTranslation()

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen(prev => !prev)}
        onBlur={() => setTimeout(() => setOpen(false), 150)}
        className="flex items-center justify-center w-7 h-7 rounded-full text-lsc-dark/70 dark:text-lsc-cream/50 hover:text-lsc-rose hover:bg-lsc-rose/10 transition-colors"
        aria-label={t('catalog.keyboardShortcuts', 'Keyboard shortcuts')}
        aria-expanded={open}
        data-keyboard-shortcuts-help
      >
        <HelpCircle className="w-4 h-4" aria-hidden="true" />
      </button>
      {open && (
        <div
          className="absolute right-0 top-full mt-2 w-56 bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-xl shadow-lg z-50 p-3"
          role="tooltip"
        >
          <p className="text-xs font-bold text-lsc-dark/70 dark:text-lsc-cream/60 uppercase tracking-wide mb-2">
            {t('catalog.keyboardShortcuts', 'Keyboard shortcuts')}
          </p>
          <ul className="space-y-1.5 text-sm text-lsc-dark dark:text-lsc-cream">
            <li className="flex justify-between">
              <span>{t('catalog.shortcutFocusSearch', 'Focus search')}</span>
              <kbd className="px-1.5 py-0.5 bg-lsc-cream dark:bg-earth-700 border border-lsc-border dark:border-earth-600 rounded text-xs">/</kbd>
            </li>
            <li className="flex justify-between">
              <span>{t('catalog.shortcutToggleFilters', 'Toggle filters')}</span>
              <kbd className="px-1.5 py-0.5 bg-lsc-cream dark:bg-earth-700 border border-lsc-border dark:border-earth-600 rounded text-xs">f</kbd>
            </li>
            <li className="flex justify-between">
              <span>{t('catalog.shortcutQuietMode', 'Quiet mode')}</span>
              <kbd className="px-1.5 py-0.5 bg-lsc-cream dark:bg-earth-700 border border-lsc-border dark:border-earth-600 rounded text-xs">q</kbd>
            </li>
            <li className="flex justify-between">
              <span>{t('catalog.shortcutSimplifiedView', 'Simplified view')}</span>
              <kbd className="px-1.5 py-0.5 bg-lsc-cream dark:bg-earth-700 border border-lsc-border dark:border-earth-600 rounded text-xs">s</kbd>
            </li>
          </ul>
        </div>
      )}
    </div>
  )
}

export default function CatalogSearchBar({
  searchQuery,
  onSearchChange,
  onSubmit,
  onClearSearch,
  suggestions,
  showSuggestions,
  onShowSuggestionsChange,
  selectedSuggestionIndex,
  onSelectedSuggestionIndexChange,
  onSuggestionSelect,
  searchInputRef,
  suggestionsRef,
  isLoading,
  reduceMotion,
}: CatalogSearchBarProps) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const [surpriseLoading, setSurpriseLoading] = useState(false)
  const [surpriseError, setSurpriseError] = useState<string | null>(null)

  const suggestionsOpen = showSuggestions && suggestions.length > 0 && searchQuery.trim().length >= 2

  const handleSurprise = async () => {
    setSurpriseLoading(true)
    setSurpriseError(null)
    try {
      const itemType = searchParams.get('item_type')
      // #887: catalog filter URL switched from `status=available` to
      // `available_only=true`; translate back to the backend's status enum
      // for the random-item endpoint, which still takes the original shape.
      const availableOnly = searchParams.get('available_only') === 'true'
      // Honor the rest of the active browse filters so "surprise me" stops
      // surfacing junk when the patron has narrowed the catalog (e.g. an
      // available audiobook from this decade). Only forward values that parse
      // to finite numbers; the API helper drops undefined params.
      const num = (key: string): number | undefined => {
        const raw = searchParams.get(key)
        if (raw === null || raw === '') return undefined
        const n = Number(raw)
        return Number.isFinite(n) ? n : undefined
      }
      const largePrint = searchParams.get('is_large_print') === 'true'
      const result = await getRandomItem({
        ...(itemType && { item_type: itemType }),
        ...(availableOnly && { status: 'available' }),
        ...(num('year_min') !== undefined && { year_min: num('year_min') }),
        ...(num('year_max') !== undefined && { year_max: num('year_max') }),
        ...(largePrint && { is_large_print: true }),
        ...(num('min_lexile') !== undefined && { min_lexile: num('min_lexile') }),
        ...(num('max_lexile') !== undefined && { max_lexile: num('max_lexile') }),
      })
      if (result.item) {
        navigate(`/catalog/${result.item.id}`)
      } else {
        setSurpriseError(t('catalog.surprise.noMatch'))
        setTimeout(() => setSurpriseError(null), 4000)
      }
    } catch {
      setSurpriseError(t('catalog.surprise.noMatch'))
      setTimeout(() => setSurpriseError(null), 4000)
    } finally {
      setSurpriseLoading(false)
    }
  }

  return (
    <div className="sticky top-0 z-40 bg-lsc-cream dark:bg-lsc-dark px-6 py-4 border-b border-lsc-border dark:border-earth-700 shadow-sm">
      <div ref={suggestionsRef} className="max-w-[720px] mx-auto relative">
      <form onSubmit={onSubmit} className="flex flex-wrap gap-2 lg:flex-nowrap">
        <div className="relative basis-full lg:flex-1 lg:basis-auto">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-lsc-dark/80 dark:text-lsc-cream/90" aria-hidden="true" />
          <input
            ref={searchInputRef}
            type="text"
            value={searchQuery}
            onChange={(e) => {
              onSearchChange(e.target.value)
              onShowSuggestionsChange(true)
              onSelectedSuggestionIndexChange(-1)
            }}
            onFocus={() => onShowSuggestionsChange(true)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                if (selectedSuggestionIndex >= 0 && suggestions[selectedSuggestionIndex]) {
                  e.preventDefault()
                  onSuggestionSelect(suggestions[selectedSuggestionIndex])
                } else {
                  onSubmit(e)
                }
                onShowSuggestionsChange(false)
              } else if (e.key === 'ArrowDown') {
                e.preventDefault()
                onSelectedSuggestionIndexChange(Math.min(selectedSuggestionIndex + 1, suggestions.length - 1))
              } else if (e.key === 'ArrowUp') {
                e.preventDefault()
                onSelectedSuggestionIndexChange(Math.max(selectedSuggestionIndex - 1, -1))
              } else if (e.key === 'Escape') {
                onShowSuggestionsChange(false)
              }
            }}
            maxLength={1000}
            placeholder={t('catalog.searchPlaceholder')}
            role="combobox"
            aria-label={t('catalog.searchAriaLabel')}
            aria-autocomplete="list"
            aria-controls={suggestionsOpen ? 'catalog-suggestions' : undefined}
            aria-activedescendant={
              suggestionsOpen && selectedSuggestionIndex >= 0
                ? `catalog-suggestion-${selectedSuggestionIndex}`
                : undefined
            }
            aria-expanded={suggestionsOpen}
            className="w-full pl-10 pr-10 py-3 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream placeholder-earth-600 dark:placeholder-earth-400 focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
          />
          {searchQuery && (
            <button
              type="button"
              onClick={onClearSearch}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream p-2 min-w-[44px] min-h-[44px] flex items-center justify-center touch-manipulation"
              aria-label={t('aria.advancedStaffSearchModal.clearSearch')}
            >
              <X className="w-5 h-5" aria-hidden="true" />
            </button>
          )}
        </div>
        <button
          type="submit"
          disabled={isLoading}
          className={clsx(
            'flex-1 px-5 sm:px-8 py-3 min-h-[48px] rounded-xl bg-forest-800 hover:bg-forest-900 dark:bg-forest-800 dark:hover:bg-forest-900 text-white font-semibold shadow-md hover:shadow-lg active:shadow-sm transition-[background-color,box-shadow,opacity] duration-150 ease-[cubic-bezier(0.23,1,0.32,1)] disabled:opacity-50 touch-manipulation lg:flex-none',
            reduceMotion && 'transition-none',
          )}
        >
          {isLoading ? <Loader2 className="w-5 h-5 motion-safe:animate-spin" aria-label={t('common.loading')} /> : t('common.search')}
        </button>
        <button
          type="button"
          onClick={handleSurprise}
          disabled={surpriseLoading}
          className={clsx(
            'flex-1 px-4 py-3 min-h-[48px] rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream font-medium hover:border-lsc-rose/50 hover:text-lsc-rose transition-colors disabled:opacity-50 touch-manipulation flex items-center justify-center gap-2 lg:flex-none',
            reduceMotion && 'transition-none',
          )}
          aria-label={t('catalog.surprise.buttonAriaLabel')}
        >
          {surpriseLoading ? (
            <Loader2 className="w-5 h-5 motion-safe:animate-spin" aria-hidden="true" />
          ) : (
            <Shuffle className="w-5 h-5" aria-hidden="true" />
          )}
          <span className="hidden sm:inline">{t('catalog.surprise.button')}</span>
        </button>
      </form>
        {surpriseError && (
          <div role="alert" className="mt-2 text-sm text-center text-earth-600 dark:text-earth-400">
            {surpriseError}
          </div>
        )}
      {suggestionsOpen && (
        <div
          id="catalog-suggestions"
          role="listbox"
          aria-label={t('catalog.searchAriaLabel')}
          className="absolute left-0 right-0 top-full mt-1 bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-xl shadow-lg z-50 overflow-hidden max-h-[320px] overflow-y-auto"
        >
          {suggestions.map((suggestion, index) => (
            <button
              key={`${suggestion.title}-${suggestion.author}-${index}`}
              id={`catalog-suggestion-${index}`}
              onClick={() => onSuggestionSelect(suggestion)}
              className={clsx(
                'flex items-center gap-3 w-full px-4 py-3 text-left text-sm transition-colors',
                'hover:bg-lsc-cream dark:hover:bg-earth-700',
                'focus:outline-none focus:bg-lsc-cream dark:focus:bg-earth-700',
                index === selectedSuggestionIndex && 'bg-lsc-cream dark:bg-earth-700'
              )}
              role="option"
              aria-selected={index === selectedSuggestionIndex}
            >
              <div className="flex-1 min-w-0">
                <p className="font-semibold text-lsc-dark dark:text-lsc-cream truncate" title={suggestion.title ?? undefined}>{suggestion.title}</p>
                {suggestion.suggestion_type === 'title' && suggestion.author && (
                  <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60 truncate" title={suggestion.author ?? undefined}>{suggestion.author}</p>
                )}
                {suggestion.suggestion_type === 'author' && suggestion.book_count && (
                  <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60">{t('catalog.suggestionItemsCount', { count: suggestion.book_count })}</p>
                )}
              </div>
              {suggestion.item_type && (
                <span className="text-xs text-earth-600 dark:text-earth-400 flex-shrink-0">
                  {suggestion.item_type}
                </span>
              )}
              {suggestion.is_available && (
                <span className="flex items-center gap-1 flex-shrink-0">
                  <span className="w-2 h-2 rounded-full bg-status-success-700" aria-hidden="true" />
                  <span className="text-xs text-status-success-700 dark:text-status-success-400">
                    {t('catalog.availabilityIndicator', 'Available')}
                  </span>
                </span>
              )}
            </button>
          ))}
        </div>
      )}
      </div>
      {/* Keyboard shortcuts (/ f q s) and search syntax live in these two help
          popovers; the verbose inline tip line was removed to declutter. */}
      <div className="max-w-[720px] mx-auto flex items-center justify-end gap-1 pt-[6px] mt-1">
        <SearchSyntaxHelp />
        <KeyboardShortcutHelp />
      </div>
    </div>
  )
}
