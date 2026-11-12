/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { t } from '@/i18n'

// ---------------------------------------------------------------------------
// Status helpers
// ---------------------------------------------------------------------------

export type StatusColorName = 'green' | 'amber' | 'blue'

export function statusColor(status: string): StatusColorName {
  switch (status) {
    case 'available':
      return 'green'
    case 'in_transit':
    case 'on_order':
    case 'in_processing':
      return 'blue'
    default:
      return 'amber'
  }
}

export function statusIcon(status: string): string {
  switch (status) {
    case 'available':
      return 'CircleCheck'
    case 'on_hold':
      return 'Users'
    case 'in_transit':
      return 'Truck'
    case 'on_order':
    case 'in_processing':
      return 'PackageSearch'
    default:
      return 'Clock'
  }
}

export function statusLabel(status: string): string {
  const labels: Record<string, string> = {
    available: 'Available',
    checked_out: 'Checked Out',
    on_hold: 'On Hold',
    in_transit: 'In Transit',
    on_order: 'On Order',
    in_processing: 'In Processing',
    missing: 'Missing',
    lost: 'Lost',
    damaged: 'Damaged',
    withdrawn: 'Withdrawn',
    reference: 'Reference Only',
    restricted: 'Restricted',
  }
  return labels[status] || status.replace(/_/g, ' ')
}

/**
 * Locale-aware status label. Looks up catalog.statusLabels.<enum> and falls
 * back to the English statusLabel() mapping for unknown values.
 */
export function statusLabelI18n(status: string): string {
  return t(`catalog.statusLabels.${status}`, statusLabel(status))
}

/**
 * Normalized availability chip for catalog cards. One scheme:
 *   all copies available -> "Available" (green)
 *   some available       -> "X of Y available" (green)
 *   none available       -> "All copies out" (amber, still holdable)
 * Never pairs "Checked Out" with an "available" count in one chip.
 * Non-circulating statuses (in transit, on order, lost...) keep their
 * status label. Color is always paired with text (WCAG 1.4.1).
 */
export function availabilityChip(
  status: string,
  copyAvailability?: { available_copies: number; total_copies: number } | null,
): { label: string; color: StatusColorName } {
  const circulating = status === 'available' || status === 'checked_out'
  if (circulating && copyAvailability && copyAvailability.total_copies > 0) {
    const { available_copies: avail, total_copies: total } = copyAvailability
    if (avail >= total) return { label: statusLabelI18n('available'), color: 'green' }
    if (avail > 0) {
      return {
        label: t('catalog.availableCopies', { available: avail, total }),
        color: 'green',
      }
    }
    return { label: t('catalog.allCopiesOut', 'All copies out'), color: 'amber' }
  }
  if (status === 'checked_out') {
    return { label: t('catalog.allCopiesOut', 'All copies out'), color: 'amber' }
  }
  return { label: statusLabelI18n(status), color: statusColor(status) }
}

/** Badge copy mapped from the three-state status color. */
export const STATUS_BADGE_LABELS: Record<string, string> = {
  green: 'Available',
  amber: 'Checked Out',
  blue: 'In Transit',
}

// ---------------------------------------------------------------------------
// Format / item-type metadata
// ---------------------------------------------------------------------------

export const FORMAT_LABELS: Record<string, string> = {
  book: 'Book',
  audiobook: 'Audiobook',
  ebook: 'E-Book',
  dvd: 'DVD',
  bluray: 'Blu-ray',
  cd: 'CD',
  vinyl: 'Vinyl',
  magazine: 'Magazine',
  game: 'Game',
  equipment: 'Equipment',
  kit: 'Kit',
  other: 'Other',
}

export function coverProxyUrl(itemId: number): string {
  return `/api/v1/catalog/covers/${itemId}`
}

export function buildCoverAlt(title: string, author?: string | null, itemType?: string | null): string {
  const formatLabel = itemType ? FORMAT_LABELS[itemType] || itemType : null
  const parts = [title]
  if (author) parts.push(`by ${author}`)
  if (formatLabel) parts.push(`${formatLabel} cover`)
  else parts.push('cover')
  return parts.join(', ')
}

/** Tailwind background classes for fallback cover placeholders. */
export const ITEM_TYPE_COLORS: Record<string, string> = {
  book: 'bg-lsc-rose/90',
  audiobook: 'bg-category-700',
  ebook: 'bg-earth-800',
  dvd: 'bg-lsc-rose',
  bluray: 'bg-earth-800',
  cd: 'bg-category-800',
  vinyl: 'bg-earth-900',
  magazine: 'bg-earth-500',
  game: 'bg-status-success-700',
  equipment: 'bg-emerald-700',
  kit: 'bg-status-warning-800',
  other: 'bg-earth-600',
}

/** Status dot colors (light + dark mode). */
export const DOT_COLORS = {
  green: 'bg-status-success-600 dark:bg-status-success-400',
  amber: 'bg-status-warning-500 dark:bg-status-warning-400',
  blue: 'bg-status-info-500 dark:bg-status-info-400',
} as const

// ---------------------------------------------------------------------------
// Routing helpers
// ---------------------------------------------------------------------------

export function catalogItemLink(id: number, title: string, source?: string): string {
  if (source === 'indie') {
    const slug = title.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '')
    return `/indie/book/${slug}-${id}`
  }
  return `/catalog/${id}`
}

/**
 * Sign-in-and-return navigation target for catalog actions. LoginPage honors
 * `state.from`; `?action=hold` re-opens the place-hold modal after auth.
 * Usage: `const { pathname, state } = catalogSignInPath(id, { action: 'hold', title }); navigate(pathname, { state })`
 */
export function catalogSignInPath(
  itemId: number | string,
  opts?: { action?: 'hold'; title?: string },
): { pathname: string; state: { from: string; holdTitle?: string } } {
  return {
    pathname: '/login',
    state: {
      from: `/catalog/${itemId}${opts?.action ? `?action=${opts.action}` : ''}`,
      ...(opts?.title ? { holdTitle: opts.title } : {}),
    },
  }
}
