/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import type { ItemAvailabilityInfo } from '@/hooks/useAvailabilityMap'
import { statusColor, statusLabel, type StatusColorName } from '@/pages/catalog/utils/catalogHelpers'

// ---------------------------------------------------------------------------
// availabilityChip
//
// ONE chip, ONE grammar, used identically by the grid and list cards. Fixes
// the self-contradicting "Checked Out · 1 of 2 available" by deciding the
// label from copy counts FIRST: if any copy is on the shelf the chip is green
// and says "N of M available"; only when zero copies are available does it go
// amber and say "All copies out · place hold". A red/amber "checked out" chip
// is never paired with the word "available".
//
// Returns a single resolved label + a three-state tone that maps to the same
// green/amber/blue tokens the cards already use, so callers don't branch on
// status themselves.
// ---------------------------------------------------------------------------

export interface AvailabilityChip {
  label: string
  tone: StatusColorName
}

/**
 * @param status   item.status enum (available / checked_out / on_hold / ...)
 * @param copy     batched copy-level availability for the item, if known
 * @param t        i18n translate fn (key, fallback) -> string
 */
export function resolveAvailabilityChip(
  status: string,
  copy: ItemAvailabilityInfo | undefined,
  t: (key: string, fallback: string) => string,
): AvailabilityChip {
  // Special non-circulating / transit statuses keep their own wording and
  // color; copy counts are not meaningful for them.
  if (status === 'in_transit' || status === 'on_order' || status === 'in_processing') {
    return { label: statusLabel(status), tone: statusColor(status) }
  }

  // Copy-count path: authoritative when we have it. Decide by available_copies,
  // not the title-level status, so "some copies out, some in" reads as green.
  if (copy && copy.total_copies > 1) {
    if (copy.available_copies > 0) {
      return {
        label: t('catalog.chip.nOfMAvailable', '{available} of {total} available')
          .replace('{available}', String(copy.available_copies))
          .replace('{total}', String(copy.total_copies)),
        tone: 'green',
      }
    }
    return {
      label: t('catalog.chip.allCopiesOut', 'All copies out · place hold'),
      tone: 'amber',
    }
  }

  // Single-copy (or unknown copy data): fall back to the title-level status.
  if (status === 'available') {
    return { label: t('catalog.chip.available', 'Available'), tone: 'green' }
  }
  if (status === 'checked_out') {
    return { label: t('catalog.chip.checkedOut', 'Checked out · place hold'), tone: 'amber' }
  }
  // Any other status (on_hold, lost, withdrawn, reference, ...) -> its label.
  return { label: statusLabel(status), tone: statusColor(status) }
}
