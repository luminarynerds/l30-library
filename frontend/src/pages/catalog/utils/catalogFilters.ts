/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { FORMAT_LABELS } from './catalogHelpers'
import { toTitleCaseLabel } from './catalogSearchCopy'

export interface CatalogFilters {
  item_type: string | null
  available_only: boolean
  available_for_hold: boolean
  year_min: string
  year_max: string
  location: string
  publisher: string
  reading_time: string
  access: string
  topic: string
  language: string
  min_lexile: number | null
  max_lexile: number | null
  subject_facets: string[]
  author_facets: string[]
  series_facets: string[]
}

export const EMPTY_FILTERS: CatalogFilters = {
  item_type: '',
  available_only: false,
  available_for_hold: false,
  year_min: '',
  year_max: '',
  location: '',
  publisher: '',
  reading_time: '',
  access: '',
  topic: '',
  language: '',
  min_lexile: null,
  max_lexile: null,
  subject_facets: [],
  author_facets: [],
  series_facets: [],
}

export function buildActiveFilterChips(
  filters: CatalogFilters,
  showNewArrivals: boolean,
  showLargePrintOnly: boolean,
): { key: string; label: string }[] {
  const chips: { key: string; label: string }[] = []
  if (filters.item_type) {
    chips.push({ key: 'item_type', label: `Format: ${FORMAT_LABELS[filters.item_type] || toTitleCaseLabel(filters.item_type)}` })
  }
  if (filters.available_only) {
    chips.push({ key: 'available_only', label: 'Availability: Available Now' })
  }
  if (filters.available_for_hold) {
    chips.push({ key: 'available_for_hold', label: 'Holdable: Yes' })
  }
  if (filters.year_min) {
    chips.push({ key: 'year_min', label: `Year From: ${filters.year_min}` })
  }
  if (filters.year_max) {
    chips.push({ key: 'year_max', label: `Year To: ${filters.year_max}` })
  }
  if (filters.location) {
    chips.push({ key: 'location', label: `Location: ${filters.location}` })
  }
  if (filters.publisher) {
    chips.push({ key: 'publisher', label: `Publisher: ${filters.publisher}` })
  }
  if (filters.reading_time) {
    chips.push({ key: 'reading_time', label: `Reading Time: ${toTitleCaseLabel(filters.reading_time)}` })
  }
  if (filters.access) {
    chips.push({ key: 'access', label: `Access: ${toTitleCaseLabel(filters.access)}` })
  }
  if (filters.topic) {
    chips.push({ key: 'topic', label: `Topic: ${toTitleCaseLabel(filters.topic)}` })
  }
  if (filters.language) {
    // We don't have access to the patron's UI locale here, so emit the
    // raw ISO 639-2/B code in the chip. The sidebar resolves it through
    // Intl.DisplayNames for the in-place label.
    chips.push({ key: 'language', label: `Language: ${filters.language}` })
  }
  if (filters.min_lexile !== null) {
    chips.push({ key: "min_lexile", label: `Lexile min: ${filters.min_lexile}` })
  }
  if (filters.max_lexile !== null) {
    chips.push({ key: "max_lexile", label: `Lexile max: ${filters.max_lexile}` })
  }
  if (showNewArrivals) {
    chips.push({ key: 'new', label: 'New Arrivals' })
  }
  if (showLargePrintOnly) {
    chips.push({ key: 'large_print', label: 'Large Print' })
  }
  for (const subject of filters.subject_facets ?? []) {
    chips.push({ key: `subject_facets:${subject}`, label: `Subject: ${subject}` })
  }
  for (const author of filters.author_facets ?? []) {
    chips.push({ key: `author_facets:${author}`, label: `Author: ${author}` })
  }
  for (const series of filters.series_facets ?? []) {
    chips.push({ key: `series_facets:${series}`, label: `Series: ${series}` })
  }
  return chips
}
