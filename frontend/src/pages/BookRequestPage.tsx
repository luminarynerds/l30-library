/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import { BookOpen, Search, CheckCircle, Plus } from 'lucide-react';
import { patronRequestsApi, LibrarySearchResult } from '../api/domains/patron-requests-api';
import { clean } from '@/lib/utils';
import { t } from '@/i18n'

export default function BookRequestPage() {
  const { ebookId } = useParams<{ ebookId: string }>();
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<LibrarySearchResult[]>([]);
  const [selected, setSelected] = useState<LibrarySearchResult | null>(null);
  const [email, setEmail] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const [response, setResponse] = useState<{ message: string; is_connected: boolean } | null>(null);
  const [loading, setLoading] = useState(false);
  const [searching, setSearching] = useState(false);
  const [showAddForm, setShowAddForm] = useState(false);
  const [newLibName, setNewLibName] = useState('');
  const [newLibCity, setNewLibCity] = useState('');
  const [newLibState, setNewLibState] = useState('');
  const [addingLib, setAddingLib] = useState(false);
  const [addError, setAddError] = useState('');

  useEffect(() => {
    if (query.length < 2) {
      setResults([]);
      return;
    }
    const timer = setTimeout(async () => {
      setSearching(true);
      try {
        const libs = await patronRequestsApi.searchLibraries(query);
        setResults(libs);
      } catch {
        setResults([]);
      } finally {
        setSearching(false);
      }
    }, 300);
    return () => clearTimeout(timer);
  }, [query]);

  const handleSubmit = useCallback(async () => {
    if (!selected || !ebookId) return;
    setLoading(true);
    try {
      const res = await patronRequestsApi.submitRequest(clean({
        ebook_id: parseInt(ebookId),
        library_directory_id: selected.id,
        patron_email: email || undefined,
        source: 'booktok',
      }));
      setResponse({ message: res.message, is_connected: res.is_connected });
      setSubmitted(true);
    } catch {
      setResponse({ message: "We couldn't submit your request just yet. Please try again.", is_connected: false });
    } finally {
      setLoading(false);
    }
  }, [selected, ebookId, email]);

  const handleAddLibrary = useCallback(async () => {
    if (!newLibName.trim()) return;
    setAddingLib(true);
    setAddError('');
    try {
      const res = await patronRequestsApi.addLibrary(clean({
        name: newLibName.trim(),
        city: newLibCity.trim() || undefined,
        state: newLibState.trim() || undefined,
      }));
      setSelected({ id: res.id, name: res.name, city: newLibCity.trim() || null, state: newLibState.trim() || null, is_connected: false });
      setShowAddForm(false);
      setNewLibName('');
      setNewLibCity('');
      setNewLibState('');
    } catch (e: unknown) {
      setAddError(e instanceof Error ? e.message : 'Could not add library');
    } finally {
      setAddingLib(false);
    }
  }, [newLibName, newLibCity, newLibState]);

  if (submitted && response) {
    return (
      <div className="min-h-screen bg-cream-50 dark:bg-earth-950 flex items-center justify-center p-4">
        <div className="max-w-md w-full bg-lsc-white dark:bg-earth-900 rounded-xl shadow-soft-md p-8 text-center">
          <CheckCircle className="w-16 h-16 mx-auto mb-4 text-sage-600" />
          <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-3">
            {response.is_connected ? 'Available Now!' : 'Request Sent!'}
          </h2>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70 leading-relaxed">
            {response.message}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-cream-50 dark:bg-earth-950 flex items-center justify-center p-4">
      <div className="max-w-md w-full bg-lsc-white dark:bg-earth-900 rounded-xl shadow-soft-md p-8">
        <div className="text-center mb-8">
          <BookOpen className="w-12 h-12 mx-auto mb-3 text-status-warning-600" />
          <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-2">
            Request This Book at Your Library
          </h1>
          <p className="text-earth-600 dark:text-earth-400 text-sm">
            Find your library and let them know you want this title.
          </p>
        </div>

        <div className="mb-6">
          <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">
            Your Library
          </label>
          <div className="relative">
            <Search className="absolute left-3 top-3 w-4 h-4 text-earth-600" />
            <input
              type="text"
              value={selected ? selected.name : query}
              onChange={(e) => {
                setQuery(e.target.value);
                setSelected(null);
              }}
              placeholder={t('placeholder.bookRequest.searchByLibraryName')}
              className="w-full pl-10 pr-4 py-2.5 border border-lsc-border dark:border-earth-700 rounded-lg
                bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream
                focus:ring-2 focus:ring-status-warning-500 focus:border-transparent outline-none"
            />
          </div>

          {results.length > 0 && !selected && (
            <ul className="mt-1 border border-lsc-border dark:border-earth-700 rounded-lg
              bg-lsc-white dark:bg-earth-800 max-h-48 overflow-y-auto">
              {results.map((lib) => (
                <li key={lib.id}>
                  <button
                    onClick={() => {
                      setSelected(lib);
                      setResults([]);
                    }}
                    className="w-full text-left px-4 py-3 hover:bg-cream-50 dark:hover:bg-earth-700
                      flex items-center justify-between"
                  >
                    <div>
                      <span className="text-lsc-dark dark:text-lsc-cream font-medium">{lib.name}</span>
                      {lib.city && lib.state && (
                        <span className="text-earth-600 dark:text-earth-400 text-sm ml-2">
                          {lib.city}, {lib.state}
                        </span>
                      )}
                    </div>
                    {lib.is_connected && (
                      <span className="text-xs bg-sage-100 dark:bg-sage-900 text-sage-700 dark:text-sage-300
                        px-2 py-0.5 rounded-full">
                        Available
                      </span>
                    )}
                  </button>
                </li>
              ))}
            </ul>
          )}

          {searching && (
            <p className="mt-2 text-sm text-earth-600 dark:text-earth-400">Searching...</p>
          )}
        </div>

        <div className="mb-6">
          <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">
            Your Email <span className="text-earth-600 font-normal">(optional)</span>
          </label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder={t('placeholder.bookRequest.getNotifiedWhenAvailable')}
            className="w-full px-4 py-2.5 border border-lsc-border dark:border-earth-700 rounded-lg
              bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream
              focus:ring-2 focus:ring-status-warning-500 focus:border-transparent outline-none"
          />
        </div>

        <button
          onClick={handleSubmit}
          disabled={!selected || loading}
          className="w-full py-3 bg-status-warning-700 hover:bg-status-warning-800 disabled:bg-earth-300
            dark:disabled:bg-earth-700 text-white font-medium rounded-lg
            motion-safe:transition-colors disabled:cursor-not-allowed"
        >
          {loading ? 'Sending...' : 'Request This Book'}
        </button>

        {!showAddForm ? (
          <button
            onClick={() => setShowAddForm(true)}
            className="mt-4 w-full text-xs text-status-warning-600 dark:text-status-warning-400 hover:underline
              flex items-center justify-center gap-1"
          >
            <Plus className="w-3 h-3" />
            Don't see your library? Add it here.
          </button>
        ) : (
          <div className="mt-4 p-4 border border-lsc-border dark:border-earth-700 rounded-lg bg-cream-50 dark:bg-earth-800">
            <p className="text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-3">
              Add Your Library
            </p>
            <div className="space-y-2">
              <input
                type="text"
                value={newLibName}
                onChange={(e) => setNewLibName(e.target.value)}
                placeholder={t('placeholder.bookRequest.libraryName')}
                className="w-full px-3 py-2 text-sm border border-lsc-border dark:border-earth-700 rounded-lg
                  bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream
                  focus:ring-2 focus:ring-status-warning-500 focus:border-transparent outline-none"
              />
              <div className="flex gap-2">
                <input
                  type="text"
                  value={newLibCity}
                  onChange={(e) => setNewLibCity(e.target.value)}
                  placeholder={t('placeholder.bookRequest.city')}
                  className="w-1/2 px-3 py-2 text-sm border border-lsc-border dark:border-earth-700 rounded-lg
                    bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream
                    focus:ring-2 focus:ring-status-warning-500 focus:border-transparent outline-none"
                />
                <input
                  type="text"
                  value={newLibState}
                  onChange={(e) => setNewLibState(e.target.value)}
                  placeholder={t('placeholder.bookRequest.state')}
                  className="w-1/2 px-3 py-2 text-sm border border-lsc-border dark:border-earth-700 rounded-lg
                    bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream
                    focus:ring-2 focus:ring-status-warning-500 focus:border-transparent outline-none"
                />
              </div>
              {addError && (
                <p className="text-xs text-status-danger-700">{addError}</p>
              )}
              <div className="flex gap-2">
                <button
                  onClick={handleAddLibrary}
                  disabled={!newLibName.trim() || addingLib}
                  className="flex-1 py-2 text-sm bg-status-warning-700 hover:bg-status-warning-800 disabled:bg-earth-300
                    dark:disabled:bg-earth-700 text-white rounded-lg motion-safe:transition-colors
                    disabled:cursor-not-allowed"
                >
                  {addingLib ? 'Adding...' : 'Add Library'}
                </button>
                <button
                  onClick={() => setShowAddForm(false)}
                  className="px-3 py-2 text-sm text-earth-600 hover:text-earth-700 dark:text-earth-400
                    dark:hover:text-earth-200"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
