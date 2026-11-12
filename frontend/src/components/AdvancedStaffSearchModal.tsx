/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
/**
 * Advanced Staff Search Modal
 *
 * A comprehensive search interface accessible via Ctrl+K that allows staff
 * to search across patrons, items, checkouts, and events simultaneously.
 *
 * Features:
 * - Real-time search across multiple entity types
 * - Recent searches with local persistence
 * - Fuzzy matching with "Did you mean?" suggestions
 * - Result filtering by type
 * - Voice search option for accessibility
 * - Sub-5-second search performance
 */

import { useEffect, useRef, useState, useCallback, useMemo } from 'react';
import { Search, Mic, X, Loader2, AlertCircle } from 'lucide-react'
import { staffSearchService } from '../services/staff-search-service';
import type { StaffSearchResponse, StaffSearchResult } from '../api/staff-search-api';
import { useTranslation} from '@/i18n'
import { clean } from '@/lib/utils'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

type EntityType = 'patron' | 'item' | 'checkout' | 'event' | 'all';

interface AdvancedStaffSearchModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function AdvancedStaffSearchModal({
  isOpen,
  onClose,
}: AdvancedStaffSearchModalProps) {
  const { t } = useTranslation()
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<StaffSearchResponse | null>(null);
  const [recentSearches, setRecentSearches] = useState<string[]>([]);
  const [selectedType, setSelectedType] = useState<EntityType>('all');
  const [isLoading, setIsLoading] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [_currentPage, setCurrentPage] = useState(1);
  const [selectedIndex, setSelectedIndex] = useState(-1);
  const searchInputRef = useRef<HTMLInputElement>(null);
  const modalRef = useRef<HTMLDivElement>(null);
  const recognitionRef = useRef<SpeechRecognition | null>(null);
  const resultsListRef = useRef<HTMLDivElement>(null);

  // Load recent searches on mount
  useEffect(() => {
    const loadRecent = async () => {
      const recent = await staffSearchService.getRecentSearches();
      setRecentSearches(recent);
    };
    loadRecent();
  }, []);

  // Focus input when modal opens
  useEffect(() => {
    if (isOpen && searchInputRef.current) {
      searchInputRef.current.focus();
    }
  }, [isOpen]);

  // Filter results by type (memoized, must be above keyboard handler that references it)
  const filteredResults = useMemo(() =>
    results
      ? {
          ...results,
          results:
            selectedType === 'all'
              ? results.results
              : results.results.filter(r => r.entity_type === selectedType),
        }
      : null,
    [results, selectedType]
  );

  // Reset selected index when results change
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- intentional reset of keyboard selection when result set / filter changes
    setSelectedIndex(-1);
  }, [results, selectedType]);

  // Scroll selected result into view
  useEffect(() => {
    if (selectedIndex >= 0 && resultsListRef.current) {
      const item = resultsListRef.current.querySelector(`[data-result-index="${selectedIndex}"]`);
      if (item) {
        item.scrollIntoView({ block: 'nearest' });
      }
    }
  }, [selectedIndex]);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Close on Escape
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }

      // Arrow keys for navigation
      if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
        if (!filteredResults || filteredResults.results.length === 0) return;
        e.preventDefault();
        const count = filteredResults.results.length;
        setSelectedIndex(prev => {
          if (e.key === 'ArrowDown') {
            return prev < count - 1 ? prev + 1 : 0;
          } else {
            return prev > 0 ? prev - 1 : count - 1;
          }
        });
      }

      // Enter to select
      if (e.key === 'Enter') {
        const selected = filteredResults?.results[selectedIndex];
        if (selected?.url) {
          e.preventDefault();
          window.location.href = selected.url;
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose, filteredResults, selectedIndex]);

  // Close when clicking outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (modalRef.current && !modalRef.current.contains(e.target as Node)) {
        onClose();
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [isOpen, onClose]);

  // Perform search
  const handleSearch = useCallback(
    async (searchQuery: string) => {
      if (!searchQuery.trim()) {
        setResults(null);
        return;
      }

      setIsLoading(true);
      setCurrentPage(1);

      const types =
        selectedType === 'all'
          ? undefined
          : [selectedType];

      const response = await staffSearchService.search(searchQuery, clean({
        page: 1,
        per_page: 20,
        types: types as string[] | undefined,
        useCache: true,
      }));

      if (response) {
        setResults(response);
      }
      setIsLoading(false);
    },
    [selectedType]
  );

  // Debounced search
  useEffect(() => {
    const timer = setTimeout(() => {
      if (query.trim().length > 0) {
        handleSearch(query);
      } else {
        setResults(null);
      }
    }, 300);

    return () => clearTimeout(timer);
  }, [query, handleSearch]);

  // Start voice search
  const startVoiceSearch = useCallback(() => {
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
      alert('Voice search is not supported in your browser.');
      return;
    }

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    const recognition = new SpeechRecognition();

    recognition.onstart = () => {
      setIsListening(true);
    };

    recognition.onresult = (event: SpeechRecognitionEvent) => {
      const transcript = Array.from(event.results)
        .map((result: SpeechRecognitionResult) => result[0]?.transcript)
        .join('');
      setQuery(transcript);
    };

    recognition.onerror = (event: Event & { error?: string }) => {
      Sentry.captureMessage('Speech recognition error: ' + String(event.error), 'warning');
      setIsListening(false);
    };

    recognition.onend = () => {
      setIsListening(false);
    };

    recognition.start();
    recognitionRef.current = recognition;
  }, []);

  const stopVoiceSearch = useCallback(() => {
    if (recognitionRef.current) {
      recognitionRef.current.abort();
      setIsListening(false);
    }
  }, []);

  // Handle recent search click
  const handleRecentSearchClick = (search: string) => {
    setQuery(search);
  };

  if (!isOpen) {
    return null;
  }

  return (
    <ModalBackdrop onClose={() => setQuery('')} title="Recent Searches">
      <div
        ref={modalRef}
        className="w-full max-w-2xl rounded-lg bg-lsc-white dark:bg-earth-800 shadow-lg"
      >
        {/* Search Input */}
        <div className="border-b border-lsc-border dark:border-earth-700 p-4">
          <div className="flex items-center gap-2">
            {isLoading ? (
              <Loader2 className="h-5 w-5 motion-safe:animate-spin text-lsc-dark/70 dark:text-lsc-cream/70" />
            ) : (
              <Search className="h-5 w-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
            )}
            <input
              ref={searchInputRef}
              type="text"
              placeholder={t('components.advancedStaffSearch.searchPatronsItemsCheckoutsEvents')}
              aria-label={t('components.advancedStaffSearch.searchPatronsItemsCheckoutsEvents2')}
              aria-controls="search-results-listbox"
              aria-activedescendant={selectedIndex >= 0 ? `search-result-${selectedIndex}` : undefined}
              value={query}
              onChange={e => setQuery(e.target.value)}
              className="flex-1 bg-transparent outline-none text-lg dark:text-earth-50"
            />
            {query && (
              <button
                onClick={() => setQuery('')}
                className="p-1 hover:bg-earth-100 dark:bg-earth-700 dark:hover:bg-earth-700 rounded"
                aria-label={t('aria.advancedStaffSearchModal.clearSearch')}
              >
                <X className="h-5 w-5 text-lsc-dark/70 dark:text-lsc-cream/70" aria-hidden="true" />
              </button>
            )}
            {isListening ? (
              <button
                onClick={stopVoiceSearch}
                className="p-2 bg-status-danger-100 dark:bg-status-danger-900/30 hover:bg-status-danger-200 rounded-lg"
              >
                <Mic className="h-5 w-5 text-status-danger-600" />
              </button>
            ) : (
              <button
                onClick={startVoiceSearch}
                className="p-2 hover:bg-earth-100 dark:bg-earth-700 dark:hover:bg-earth-700 rounded-lg"
                title="Voice search (Accessibility)"
              >
                <Mic className="h-5 w-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
              </button>
            )}
          </div>

          {/* Filter Pills */}
          <div className="flex gap-2 mt-3 flex-wrap">
            {(['all', 'patron', 'item', 'checkout', 'event'] as const).map(type => (
              <button
                key={type}
                onClick={() => setSelectedType(type)}
                className={`px-3 py-1 rounded-full text-sm font-medium transition-colors ${
                  selectedType === type
                    ? 'bg-earth-500 text-white'
                    : 'bg-earth-100 dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-earth-200 dark:hover:bg-earth-600'
                }`}
              >
                {type === 'all' ? 'All' : type.charAt(0).toUpperCase() + type.slice(1)}
              </button>
            ))}
          </div>
        </div>

        {/* Results or Recent Searches */}
        <div className="max-h-96 overflow-y-auto">
          {filteredResults && filteredResults.results.length > 0 ? (
            <div ref={resultsListRef} className="divide-y divide-lsc-border" role="listbox" id="search-results-listbox">
              {/* Suggestions */}
              {filteredResults.suggestions && filteredResults.suggestions.length > 0 && (
                <div className="p-4 bg-status-warning-50 dark:bg-status-warning-900/20 border-b border-status-warning-200 dark:border-status-warning-800">
                  <div className="flex items-start gap-2">
                    <AlertCircle className="h-4 w-4 text-status-warning-600 mt-0.5" />
                    <div>
                      <p className="text-sm font-medium text-status-warning-900 dark:text-status-warning-200">Did you mean?</p>
                      <div className="flex gap-2 mt-1 flex-wrap">
                        {filteredResults.suggestions.map((suggestion, idx) => (
                          <button
                            key={idx}
                            onClick={() => setQuery(suggestion)}
                            className="text-sm text-status-warning-700 dark:text-status-warning-300 underline hover:no-underline"
                          >
                            {suggestion}
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Results */}
              {filteredResults.results.map((result, idx) => (
                <SearchResultItem key={idx} result={result} index={idx} isSelected={idx === selectedIndex} />
              ))}

              {/* Pagination */}
              {filteredResults.has_more && (
                <div className="p-4 text-center border-t border-lsc-border dark:border-earth-700">
                  <button className="text-lsc-rose dark:text-lsc-rose-light hover:text-lsc-rose dark:text-lsc-rose-light text-sm font-medium">
                    Load more results
                  </button>
                </div>
              )}

              {/* Result count */}
              <div className="p-2 text-xs text-lsc-dark/70 dark:text-lsc-cream/70 text-center border-t border-lsc-border dark:border-earth-700">
                {filteredResults.total_results} result
                {filteredResults.total_results !== 1 ? 's' : ''} found in{' '}
                <span className="font-medium">search</span>
              </div>
            </div>
          ) : query.trim() ? (
            <div className="p-8 text-center text-lsc-dark/70 dark:text-lsc-cream/70">
              <p>No results found for "{query}"</p>
              <p className="text-sm mt-1">{t('components.advancedStaffSearch.trySearchingByPatronName')}</p>
            </div>
          ) : recentSearches.length > 0 ? (
            <div className="p-4">
              <h3 className="text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 uppercase mb-3">
                Recent Searches
              </h3>
              <div className="space-y-2">
                {recentSearches.map((search, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleRecentSearchClick(search)}
                    className="w-full text-left px-3 py-2 rounded hover:bg-earth-100 dark:bg-earth-700 dark:hover:bg-earth-700 transition-colors text-sm text-lsc-dark/70 dark:text-lsc-cream/70"
                  >
                    <div className="flex items-center gap-2">
                      <Search className="h-4 w-4 text-lsc-dark/70 dark:text-lsc-cream/70" />
                      {search}
                    </div>
                  </button>
                ))}
              </div>

              {recentSearches.length > 0 && (
                <button
                  onClick={() => {
                    staffSearchService.clearRecentSearches();
                    setRecentSearches([]);
                  }}
                  className="w-full mt-3 text-xs text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-earth-700 dark:hover:text-earth-200"
                >
                  Clear recent searches
                </button>
              )}
            </div>
          ) : null}
        </div>

        {/* Footer */}
        <div className="border-t border-lsc-border dark:border-earth-700 bg-earth-50 dark:bg-earth-900 px-4 py-3 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
          <div className="flex justify-between items-center">
            <span>Press <kbd className="px-2 py-1 bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded font-mono text-xs">ESC</kbd> to close</span>
            <span>{t('components.advancedStaffSearch.voiceSearchAvailableForAccessibility')}</span>
          </div>
        </div>
      </div>
    </ModalBackdrop>
  );
}

interface SearchResultItemProps {
  result: StaffSearchResult;
  index: number;
  isSelected: boolean;
}

function SearchResultItem({ result, index, isSelected }: SearchResultItemProps) {
  const getIcon = (type: string) => {
    switch (type) {
      case 'patron':
        return '👤';
      case 'item':
        return '📚';
      case 'checkout':
        return '📋';
      case 'event':
        return '📅';
      default:
        return '📎';
    }
  };

  return (
    <a
      id={`search-result-${index}`}
      data-result-index={index}
      href={result.url || '#'}
      role="option"
      aria-selected={isSelected}
      className={`flex items-start gap-3 px-4 py-3 transition-colors cursor-pointer ${
        isSelected
          ? 'bg-earth-100 dark:bg-earth-700'
          : 'hover:bg-earth-50 dark:bg-earth-900 dark:hover:bg-earth-800'
      }`}
    >
      <span className="text-lg">{getIcon(result.entity_type)}</span>
      <div className="flex-1 min-w-0">
        <p className="font-medium text-lsc-dark dark:text-lsc-cream">{result.title}</p>
        {result.subtitle && (
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 truncate" title={result.subtitle}>{result.subtitle}</p>
        )}
        {result.snippet && (
          <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 truncate mt-0.5" title={result.snippet}>{result.snippet}</p>
        )}
      </div>
      <span className="text-xs px-2 py-1 bg-earth-100 dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70 rounded">
        {result.entity_type}
      </span>
    </a>
  );
}
