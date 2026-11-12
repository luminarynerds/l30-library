/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { BookOpen, Library } from 'lucide-react'
import type { SearchMode } from './types'

export const SOURCE_CONFIG: Record<string, { label: string; color: string }> = {
  local: { label: 'Catalog', color: 'bg-status-success-100 text-status-success-700 dark:bg-status-success-900/30 dark:text-status-success-300' },
  gutenberg: { label: 'Gutenberg', color: 'bg-status-warning-100 text-status-warning-700 dark:bg-status-warning-900/30 dark:text-status-warning-300' },
  palace: { label: 'Palace', color: 'bg-status-success-100 text-status-success-700 dark:bg-status-success-900/30 dark:text-status-success-300' },
}

export const EXAMPLE_QUERIES: Record<SearchMode, string[]> = {
  hybrid: [
    'mystery novels set in Japan',
    'Stephen King horror',
    'books about climate change',
  ],
  semantic: [
    'books about finding purpose in life',
    'cozy mysteries with strong female leads',
    'coming of age during wartime',
    'novels that explore memory and grief',
  ],
  'cross-collection': [
    'classic science fiction space opera',
    'Victorian detective fiction',
    'ancient Greek philosophy',
  ],
  'hidden-gems': ['science fiction', 'historical fiction', 'poetry', 'nature writing'],
  'similar-authors': ['Isaac Asimov', 'Ursula K. Le Guin', 'Terry Pratchett', 'Agatha Christie'],
}

export const COLLECTION_OPTIONS = [
  { id: 'local', label: 'Library Catalog', icon: Library },
  { id: 'gutenberg', label: 'Gutenberg', icon: BookOpen },
]
