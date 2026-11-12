/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { CircleCheck, Clock } from 'lucide-react'
import { clsx } from '@/utils/helpers'
import type { CatalogItem } from '@/api/domains/catalog/catalog-api'

interface WantToReadActionsProps {
  item: CatalogItem
  onPlaceHold: (itemId: number) => void
}

export default function WantToReadActions({ item, onPlaceHold }: WantToReadActionsProps) {
  const isAvailable = item.status === 'available'

  return (
    <div className="flex items-center gap-2 mt-1">
      {/* Availability badge */}
      <span
        className={clsx(
          'inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full',
          isAvailable
            ? 'bg-status-success-100 text-status-success-700 dark:bg-status-success-900/30 dark:text-status-success-300'
            : 'bg-status-warning-100 text-status-warning-700 dark:bg-status-warning-900/30 dark:text-status-warning-300',
        )}
      >
        {isAvailable ? (
          <CircleCheck className="w-3 h-3" aria-hidden="true" />
        ) : (
          <Clock className="w-3 h-3" aria-hidden="true" />
        )}
        {isAvailable ? 'Available' : 'Checked Out'}
      </span>

      {/* Action button */}
      <button
        onClick={(e) => { e.preventDefault(); e.stopPropagation(); onPlaceHold(item.id) }}
        className={clsx(
          'text-xs font-semibold px-2.5 py-1 rounded-lg transition-colors',
          isAvailable
            ? 'bg-lsc-rose/10 text-lsc-rose hover:bg-lsc-rose/20'
            : 'bg-earth-100 dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-earth-200 dark:hover:bg-earth-600',
        )}
      >
        {isAvailable ? 'Place Hold' : 'Join Waitlist'}
      </button>
    </div>
  )
}
