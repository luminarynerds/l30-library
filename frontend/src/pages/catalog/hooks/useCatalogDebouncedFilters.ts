/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useMemo } from 'react'
import { useDebounce } from '@/hooks/useDebounce'
import { FILTER_DEBOUNCE_DELAY } from '@/pages/catalog/utils/catalogPageConstants'
import type { CatalogFilters } from '@/pages/catalog/utils/catalogFilters'

export function useCatalogDebouncedFilters(searchQuery: string, submittedQuery: string, filters: CatalogFilters) {
  const debouncedSearchQuery = useDebounce(searchQuery, FILTER_DEBOUNCE_DELAY)
  const activeQuery = submittedQuery !== debouncedSearchQuery ? debouncedSearchQuery : submittedQuery

  const debouncedYearMin = useDebounce(filters.year_min, FILTER_DEBOUNCE_DELAY)
  const debouncedYearMax = useDebounce(filters.year_max, FILTER_DEBOUNCE_DELAY)
  const debouncedLocation = useDebounce(filters.location, FILTER_DEBOUNCE_DELAY)
  const debouncedPublisher = useDebounce(filters.publisher, FILTER_DEBOUNCE_DELAY)

  const debouncedFilters = useMemo(() => ({
    item_type: filters.item_type,
    available_only: filters.available_only,
    available_for_hold: filters.available_for_hold,
    year_min: debouncedYearMin,
    year_max: debouncedYearMax,
    location: debouncedLocation,
    publisher: debouncedPublisher,
    reading_time: filters.reading_time,
    access: filters.access,
    topic: filters.topic,
    language: filters.language,
    min_lexile: filters.min_lexile,
    max_lexile: filters.max_lexile,
    // Multi-select facets are pass-through (no debounce — chip clicks aren't
    // typing) but must be included so chip serialization and the queryKey
    // arrays in useCatalogSearch see them. Dropping them here silently
    // emptied the chip set / facet queryKey on every render.
    subject_facets: filters.subject_facets,
    author_facets: filters.author_facets,
    series_facets: filters.series_facets,
  }), [filters.item_type, filters.available_only, filters.available_for_hold, debouncedYearMin, debouncedYearMax, debouncedLocation, debouncedPublisher, filters.reading_time, filters.access, filters.topic, filters.language, filters.min_lexile, filters.max_lexile, filters.subject_facets, filters.author_facets, filters.series_facets])

  return { activeQuery, debouncedFilters, debouncedSearchQuery }
}
