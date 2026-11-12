/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { CATALOG_COPY } from './catalogSearchConstants'

export function formatResultsCount(total: number): string {
  return `${total} ${total === 1 ? 'item' : 'items'} found`
}

export function getGentleResultsMessage(total: number, hasFilters: boolean): string {
  if (total === 0) {
    return hasFilters ? CATALOG_COPY.noFilterMatches : CATALOG_COPY.noSearchMatches
  }
  if (total === 1) {
    return CATALOG_COPY.singleResult
  }
  return `${formatResultsCount(total)}. ${CATALOG_COPY.multiResultNextStep}`
}

export function toTitleCaseLabel(value: string): string {
  return value
    .replace(/[_-]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .replace(/\b\w/g, (char) => char.toUpperCase())
}
