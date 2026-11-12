/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Search, X } from 'lucide-react';
import { useTranslation } from '@/i18n'

interface KnowledgeBaseSearchProps {
  query: string;
  onQueryChange: (query: string) => void;
  onSubmit?: () => void;
}

export default function KnowledgeBaseSearch({
  query,
  onQueryChange,
  onSubmit,
}: KnowledgeBaseSearchProps) {
  const { t } = useTranslation()
  return (
    <form
      role="search"
      onSubmit={(e) => { e.preventDefault(); onSubmit?.(); }}
    >
      <div className="relative">
        <Search className="absolute left-3 top-3 w-5 h-5 text-earth-600 dark:text-earth-400" aria-hidden="true" />
        <input
          type="search"
          value={query}
          onChange={e => onQueryChange(e.target.value)}
          placeholder={t('components.knowledgeBase.knowledgeBaseSearch.searchPoliciesProceduresHowTo')}
          aria-label={t('aria.staffKnowledgeBase.searchKb', 'Search the knowledge base')}
          className="w-full pl-10 pr-10 py-2 border border-lsc-border dark:border-earth-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-lsc-rose dark:focus:ring-lsc-rose-light bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream"
        />
        {query && (
          <button
            type="button"
            onClick={() => onQueryChange('')}
            aria-label={t('components.knowledgeBase.knowledgeBaseSearch.clearSearch', 'Clear search')}
            className="absolute right-3 top-3 text-earth-600 dark:text-earth-400 hover:text-earth-800 dark:hover:text-earth-200"
          >
            <X className="w-5 h-5" aria-hidden="true" />
          </button>
        )}
      </div>
    </form>
  );
}
