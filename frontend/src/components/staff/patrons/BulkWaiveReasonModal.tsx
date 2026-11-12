/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useState } from 'react'
import { X } from 'lucide-react'
import FocusTrap from 'focus-trap-react'

interface BulkWaiveReasonModalProps {
  isOpen: boolean
  patronCount: number
  onCancel: () => void
  onSubmit: (reason: string) => void
}

const MIN_REASON_LENGTH = 5

export function BulkWaiveReasonModal({
  isOpen,
  patronCount,
  onCancel,
  onSubmit,
}: BulkWaiveReasonModalProps) {
  const [reason, setReason] = useState('')

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- intentional reset on open
    if (isOpen) setReason('')
  }, [isOpen])

  if (!isOpen) return null

  const trimmed = reason.trim()
  const isValid = trimmed.length >= MIN_REASON_LENGTH

  return (
    <FocusTrap
      focusTrapOptions={{
        initialFocus: 'body',
        allowOutsideClick: true,
        escapeDeactivates: false,
        fallbackFocus: () => document.body,
        returnFocusOnDeactivate: true,
      }}
    >
      <div
        className="fixed inset-0 motion-safe:backdrop-blur-md bg-black/50 flex items-center justify-center z-50 p-4"
        role="presentation"
      >
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="bulk-waive-reason-title"
          className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg max-w-md w-full"
        >
          <div className="flex items-center justify-between p-4 border-b border-lsc-border dark:border-earth-700">
            <h2
              id="bulk-waive-reason-title"
              className="text-lg font-serif font-semibold text-lsc-dark dark:text-lsc-cream"
            >
              Reason for bulk waive
            </h2>
            <button
              onClick={onCancel}
              className="p-1 hover:bg-lsc-cream dark:hover:bg-lsc-brown rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-lsc-rose"
              aria-label="Close"
            >
              <X className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
            </button>
          </div>
          <form
            className="p-4 space-y-4"
            onSubmit={(e) => {
              e.preventDefault()
              if (isValid) onSubmit(trimmed)
            }}
          >
            <p className="text-sm text-lsc-dark/80 dark:text-lsc-cream/80">
              Waiving all outstanding fines for {patronCount}{' '}
              {patronCount === 1 ? 'patron' : 'patrons'}. The same reason is
              applied to every waiver in this operation.
            </p>
            <div>
              <label
                htmlFor="bulk-waive-reason"
                className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-2"
              >
                Reason <span className="text-status-danger-600">*</span>
              </label>
              <textarea
                id="bulk-waive-reason"
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                rows={4}
                minLength={MIN_REASON_LENGTH}
                required
                aria-required="true"
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent resize-none"
                placeholder="e.g. Amnesty day 2026"
              />
              <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                Minimum {MIN_REASON_LENGTH} characters. Recorded in the audit log.
              </p>
            </div>
            <div className="flex gap-3 pt-2">
              <button
                type="button"
                onClick={onCancel}
                className="flex-1 px-4 py-2 border border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream/80 rounded-xl hover:bg-lsc-cream dark:hover:bg-lsc-brown transition-colors"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={!isValid}
                className="flex-1 px-4 py-2 bg-status-warning-600 hover:bg-status-warning-700 disabled:bg-status-warning-600/50 text-white rounded-xl transition-colors font-medium"
              >
                Waive Fines
              </button>
            </div>
          </form>
        </div>
      </div>
    </FocusTrap>
  )
}
