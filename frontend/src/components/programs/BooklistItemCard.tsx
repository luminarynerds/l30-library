/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { BookOpen, Loader2 } from 'lucide-react'
import toast from 'react-hot-toast'

import { t } from '@/i18n'
import { useAuth } from '@/contexts/AuthContext'
import { placeHold } from '@/api/domains/circulation/circulation-api'
import type { ProgramBooklistItem } from '@/api/domains/content/reading-programs-api'

interface BooklistItemCardProps {
  item: ProgramBooklistItem
}

export default function BooklistItemCard({ item }: BooklistItemCardProps): React.ReactElement {
  const { token } = useAuth()
  const [submitting, setSubmitting] = useState(false)
  const [held, setHeld] = useState(false)

  const ci = item.catalog_item
  const checkedOut = !ci.available_for_hold && ci.status !== 'available'

  const onPlaceHold = async () => {
    if (!token) {
      toast.error(t('aria.authModals.signInRequired') || 'Please sign in to place a hold.')
      return
    }
    setSubmitting(true)
    try {
      await placeHold(token, ci.id)
      setHeld(true)
      toast.success(t('programs.booklist.holdPlaced') || 'Hold placed')
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to place hold')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="flex gap-4 p-3 bg-lsc-cream/40 dark:bg-lsc-brown/20 rounded-xl">
      <div className="shrink-0 w-16 h-24 bg-lsc-cream dark:bg-lsc-brown/40 rounded-lg overflow-hidden flex items-center justify-center">
        {ci.cover_url ? (
          <img
            src={ci.cover_url}
            alt={`Cover of ${ci.title}`}
            className="w-full h-full object-cover"
            loading="lazy"
          />
        ) : (
          <BookOpen
            data-testid="booklist-cover-fallback"
            className="w-8 h-8 text-lsc-dark/50 dark:text-lsc-cream/50"
            aria-hidden="true"
          />
        )}
      </div>
      <div className="flex-1 min-w-0">
        <div className="font-medium text-lsc-dark dark:text-lsc-cream truncate">{ci.title}</div>
        {ci.author && (
          <div className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 truncate">{ci.author}</div>
        )}
        {item.note && (
          <p className="text-sm italic text-lsc-dark/80 dark:text-lsc-cream/80 mt-1">
            {item.note}
          </p>
        )}
        <div className="mt-2 flex items-center gap-2">
          <span
            className={`text-xs px-2 py-0.5 rounded-full ${
              ci.available_for_hold
                ? 'bg-status-success-100 dark:bg-status-success-900/30 text-status-success-700 dark:text-status-success-300'
                : 'bg-lsc-cream dark:bg-lsc-brown/40 text-lsc-dark/70 dark:text-lsc-cream/70'
            }`}
          >
            {ci.status === 'available'
              ? t('programs.booklist.available') || 'Available'
              : checkedOut
                ? t('programs.booklist.checkedOut') || 'Checked out'
                : ci.status}
          </span>
          <button
            type="button"
            onClick={onPlaceHold}
            disabled={submitting || held || !ci.available_for_hold}
            className="text-sm px-3 py-1.5 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-lg shadow-sm disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {submitting && <Loader2 className="inline w-3 h-3 animate-spin mr-1" aria-hidden="true" />}
            {held
              ? t('programs.booklist.holdPlaced') || 'On hold'
              : t('programs.booklist.placeHold') || 'Place hold'}
          </button>
        </div>
      </div>
    </div>
  )
}
