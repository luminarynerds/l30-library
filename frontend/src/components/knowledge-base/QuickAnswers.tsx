/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React, { useState, useRef } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Zap, Search, ChevronRight, ArrowLeft, ThumbsUp, Clock } from 'lucide-react';
import api from '../../api/api';
import { useTranslation } from '@/i18n'
import { useFocusAndAnnounce } from '@/hooks/useFocusAndAnnounce'
import { MarkdownContent } from '../learning/MarkdownContent'

interface QuickAnswer {
  id: number;
  title: string;
  description: string;
  content: string;
  content_type: string;
  category: string;
  helpful_count: number;
  view_count: number;
}

const COMMON_QUESTIONS = [
  { query: 'patron lost card', label: 'Patron lost their card' },
  { query: 'overdue fine waive', label: 'Waive an overdue fine' },
  { query: 'interlibrary loan', label: 'Process an ILL request' },
  { query: 'hold shelf', label: 'Manage hold shelf' },
  { query: 'new patron register', label: 'Register a new patron' },
  { query: 'computer reservation', label: 'Computer reservation help' },
  { query: 'meeting room', label: 'Book a meeting room' },
  { query: 'damaged item', label: 'Handle a damaged item' },
  { query: 'closing procedure', label: 'Closing procedures' },
  { query: 'emergency', label: 'Emergency procedures' },
  { query: 'printer copier', label: 'Printer/copier issues' },
  { query: 'patron complaint', label: 'Handle a patron complaint' },
];

export default function QuickAnswers() {
  const { t } = useTranslation()
  const [searchQuery, setSearchQuery] = useState('');
  const [activeQuery, setActiveQuery] = useState('');
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const answerHeadingRef = useRef<HTMLHeadingElement>(null);

  // The search endpoint returns lightweight results (no content/helpful_count),
  // so on drill-in we re-fetch the full article by id (mirrors ArticleViewer).
  const { data: selectedAnswer, isLoading: isLoadingAnswer } = useQuery({
    queryKey: ['quick-answer', selectedId],
    queryFn: async () => {
      return await api.get<QuickAnswer>(`/staff-knowledge/articles/${selectedId}`);
    },
    enabled: selectedId != null,
  });

  // On drill-in to an answer, move focus to its heading and announce the swap.
  // Gated so it neither steals focus on the list view nor announces on drill-out.
  // Fires once the full article resolves (keyed on the fetched id).
  useFocusAndAnnounce(
    answerHeadingRef,
    selectedAnswer
      ? `${t('components.knowledgeBase.quickAnswers.opened', 'Opened answer')}: ${selectedAnswer.title}`
      : '',
    selectedAnswer?.id,
    selectedId != null,
  );

  const { data: results, isLoading } = useQuery({
    queryKey: ['quick-answers', activeQuery],
    queryFn: async () => {
      const response = await api.get<{ results: QuickAnswer[] }>('/staff-knowledge/articles/search', {
        params: { q: activeQuery },
      });
      return response.results;
    },
    enabled: activeQuery.length >= 2,
  });

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchQuery.trim().length >= 2) {
      setActiveQuery(searchQuery.trim());
      setSelectedId(null);
    }
  };

  const handleQuickQuestion = (query: string) => {
    setSearchQuery(query);
    setActiveQuery(query);
    setSelectedId(null);
  };

  if (selectedId != null) {
    return (
      <div>
        <button
          onClick={() => setSelectedId(null)}
          className="flex items-center gap-2 text-lsc-rose dark:text-lsc-rose-light hover:opacity-80 mb-4 font-medium"
        >
          <ArrowLeft className="w-4 h-4" />
          {t('components.knowledgeBase.quickAnswers.backToResults', 'Back to results')}
        </button>

        {isLoadingAnswer && (
          <div className="text-center py-8" role="status">
            <div className="inline-block motion-safe:animate-spin rounded-full h-6 w-6 border-b-2 border-lsc-rose"></div>
            <p className="mt-2 text-earth-600 dark:text-earth-400 text-sm">{t('components.knowledgeBase.quickAnswers.searching', 'Searching...')}</p>
          </div>
        )}

        {!isLoadingAnswer && !selectedAnswer && (
          <div className="bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-200 dark:border-status-danger-800 rounded-lg p-4 text-status-danger-800 dark:text-status-danger-300">
            {t('components.knowledgeBase.quickAnswers.answerNotFound', 'Answer not found.')}
          </div>
        )}

        {selectedAnswer && (

        <div className="bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-lg p-6">
          <div className="flex items-center gap-2 mb-3">
            <span className="px-2 py-1 bg-status-success-100 dark:bg-status-success-900/30 text-status-success-800 dark:text-status-success-300 text-xs font-medium rounded">
              {selectedAnswer.content_type.replace('_', ' ')}
            </span>
            <span className="px-2 py-1 bg-earth-100 dark:bg-earth-700 text-earth-800 dark:text-earth-100 text-xs font-medium rounded">
              {selectedAnswer.category}
            </span>
          </div>
          <h3 ref={answerHeadingRef} tabIndex={-1} className="font-serif text-xl font-bold text-lsc-dark dark:text-lsc-cream mb-4 outline-none">
            {selectedAnswer.title}
          </h3>
          {selectedAnswer.description && (
            <p className="text-earth-600 dark:text-earth-400 mb-4 italic">{selectedAnswer.description}</p>
          )}
          <MarkdownContent
            content={selectedAnswer.content}
            className="prose prose-sm max-w-none text-lsc-dark dark:text-lsc-cream dark:prose-invert"
          />
          <div className="flex items-center gap-4 mt-6 pt-4 border-t border-lsc-border dark:border-earth-700 text-sm text-earth-600 dark:text-earth-400">
            <span className="flex items-center gap-1">
              <ThumbsUp className="w-4 h-4" /> {`${selectedAnswer.helpful_count} ${t('components.knowledgeBase.quickAnswers.foundHelpful', 'found helpful')}`}
            </span>
            <span className="flex items-center gap-1">
              <Clock className="w-4 h-4" /> {`${selectedAnswer.view_count} ${t('components.knowledgeBase.quickAnswers.views', 'views')}`}
            </span>
          </div>
        </div>
        )}
      </div>
    );
  }

  return (
    <div>
      {/* Search Bar */}
      <form onSubmit={handleSearch} className="mb-6">
        <div className="relative">
          <Zap className="absolute left-3 top-3 w-5 h-5 text-lsc-rose" />
          <input
            type="text"
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            placeholder={t('components.knowledgeBase.quickAnswers.questionPlaceholder', 'Type your question... e.g. "How do I waive a fine?"')}
            aria-label={t('components.knowledgeBase.quickAnswers.searchForQuickAnswers')}
            className="w-full pl-10 pr-28 py-3 border border-lsc-border dark:border-earth-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-lsc-rose bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream text-lg"
          />
          <button
            type="submit"
            className="absolute right-2 top-1.5 px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-lg font-medium transition"
          >
            <Search className="w-4 h-4 inline mr-1" />
            {t('components.knowledgeBase.quickAnswers.findAnswer', 'Find Answer')}
          </button>
        </div>
      </form>

      {/* Common Questions Grid */}
      {!activeQuery && (
        <div>
          <h3 className="text-sm font-semibold text-earth-600 dark:text-earth-400 uppercase tracking-wide mb-3">
            {t('components.knowledgeBase.quickAnswers.commonQuestions', 'Common Questions')}
          </h3>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-2">
            {COMMON_QUESTIONS.map(q => (
              <button
                key={q.query}
                onClick={() => handleQuickQuestion(q.query)}
                className="text-left px-3 py-2 bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-lg text-sm text-earth-600 dark:text-earth-400 hover:bg-brand-50 hover:border-brand-300 dark:hover:bg-brand-900/20 dark:hover:border-brand-700 transition flex items-center gap-2"
              >
                <ChevronRight className="w-3 h-3 text-lsc-rose flex-shrink-0" />
                {q.label}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Search Results */}
      {activeQuery && (
        <div>
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-earth-600 dark:text-earth-400">
              {`${t('components.knowledgeBase.quickAnswers.resultsFor', 'Results for')} “${activeQuery}”`}
            </h3>
            <button
              onClick={() => { setActiveQuery(''); setSearchQuery(''); }}
              className="text-sm text-lsc-rose dark:text-lsc-rose-light hover:underline"
            >
              {t('components.knowledgeBase.quickAnswers.clear', 'Clear')}
            </button>
          </div>

          {isLoading && (
            <div className="text-center py-8" role="status">
              <div className="inline-block motion-safe:animate-spin rounded-full h-6 w-6 border-b-2 border-lsc-rose"></div>
              <p className="mt-2 text-earth-600 dark:text-earth-400 text-sm">{t('components.knowledgeBase.quickAnswers.searching', 'Searching...')}</p>
            </div>
          )}

          {results && results.length === 0 && (
            <div className="text-center py-8 bg-lsc-cream dark:bg-earth-900 rounded-lg border border-lsc-border dark:border-earth-700">
              <p className="text-earth-600 dark:text-earth-400">
                {t('components.knowledgeBase.quickAnswers.noQuickAnswersFound', 'No quick answers found. Try the Articles tab for a broader search, or ask a colleague in the Q&A tab.')}
              </p>
            </div>
          )}

          {results && results.length > 0 && (
            <div className="space-y-3">
              {results.map(result => (
                <button
                  key={result.id}
                  onClick={() => setSelectedId(result.id)}
                  className="w-full text-left bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-lg p-4 hover:shadow-md hover:border-brand-300 dark:hover:border-brand-700 transition"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="px-2 py-0.5 bg-brand-50 dark:bg-brand-900/30 text-brand-800 dark:text-brand-300 text-xs font-medium rounded">
                          {result.content_type.replace('_', ' ')}
                        </span>
                        <span className="text-xs text-earth-600 dark:text-earth-400">{result.category}</span>
                      </div>
                      <h4 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream truncate" title={result.title}>
                        {result.title}
                      </h4>
                      {result.description && (
                        <p className="text-sm text-earth-600 dark:text-earth-400 line-clamp-1 mt-1" title={result.description}>
                          {result.description}
                        </p>
                      )}
                    </div>
                    <ChevronRight className="w-5 h-5 text-earth-600 flex-shrink-0 mt-1" />
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
