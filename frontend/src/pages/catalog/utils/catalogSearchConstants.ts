/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { type CatalogSortBy, type CatalogSortDirection } from '@/api/api'

export const QUIET_BANNER_KEY = 'lsc-quiet-mode-banner-dismissed'

/** Sort values accepted from the URL and persisted prefs (validation allowlist). */
export const CATALOG_SORT_VALUES: readonly string[] = [
  'relevance', 'title', 'author', 'year', 'popularity', 'recently_added',
]

export const SORT_OPTIONS: { value: string; labelKey: string; sortBy: CatalogSortBy; sortDirection: CatalogSortDirection }[] = [
  { value: 'relevance', labelKey: 'catalog.sort.relevance', sortBy: 'relevance', sortDirection: 'desc' },
  { value: 'popularity', labelKey: 'catalog.sort.popularity', sortBy: 'popularity', sortDirection: 'desc' },
  { value: 'recently-added', labelKey: 'catalog.sort.recentlyAdded', sortBy: 'recently_added', sortDirection: 'desc' },
  { value: 'title-asc', labelKey: 'catalog.sort.titleAZ', sortBy: 'title', sortDirection: 'asc' },
  { value: 'title-desc', labelKey: 'catalog.sort.titleZA', sortBy: 'title', sortDirection: 'desc' },
  { value: 'author-asc', labelKey: 'catalog.sort.authorAZ', sortBy: 'author', sortDirection: 'asc' },
  { value: 'author-desc', labelKey: 'catalog.sort.authorZA', sortBy: 'author', sortDirection: 'desc' },
  { value: 'year-desc', labelKey: 'catalog.sort.yearNewest', sortBy: 'year', sortDirection: 'desc' },
  { value: 'year-asc', labelKey: 'catalog.sort.yearOldest', sortBy: 'year', sortDirection: 'asc' },
]

/** Human-friendly labels for facet groups (used in screen reader announcements) */
export const FACET_GROUP_LABELS: Record<string, string> = {
  item_type: 'Format',
  status: 'Availability',
  location: 'Branch',
  publisher: 'Publisher',
}

export const CATALOG_COPY = {
  loadingResults: 'Loading results...',
  clearFiltersCta: 'Clear filters',
  noFilterMatches: 'No matches for your current filters. Clear one filter or try a broader keyword.',
  noSearchMatches: 'No matches for your search. Try a broader keyword.',
  singleResult: '1 item found. Open it to view availability and details.',
  multiResultNextStep: 'Use filters or open an item for details.',
} as const
