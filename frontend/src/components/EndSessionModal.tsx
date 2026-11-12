/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { XCircle, Loader2 } from 'lucide-react'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'
import { t } from '@/i18n'

export type EndReasonCategory = 'time_up' | 'patron_left' | 'policy_violation' | 'technical_issue' | 'other'

const END_REASON_OPTIONS: { value: EndReasonCategory; label: string }[] = [
  { value: 'time_up', label: 'Time expired' },
  { value: 'patron_left', label: 'Patron left' },
  { value: 'policy_violation', label: 'Policy violation' },
  { value: 'technical_issue', label: 'Technical issue' },
  { value: 'other', label: 'Other' },
]

export interface EndSessionTarget {
  reservationId: number
  patronName: string | null
  minutesRemaining: number
}

interface EndReasonRadioGroupProps {
  name: string
  value: EndReasonCategory
  onChange: (val: EndReasonCategory) => void
}

export function EndReasonRadioGroup({ name, value, onChange }: EndReasonRadioGroupProps) {
  return (
    <div className="space-y-1.5">
      {END_REASON_OPTIONS.map(opt => (
        <label
          key={opt.value}
          className="flex items-center gap-2 px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-600 hover:bg-lsc-cream dark:hover:bg-earth-700 cursor-pointer text-sm text-lsc-dark dark:text-lsc-cream"
        >
          <input
            type="radio"
            name={name}
            value={opt.value}
            checked={value === opt.value}
            onChange={() => onChange(opt.value)}
            className="text-lsc-rose focus:ring-lsc-rose"
          />
          {opt.label}
        </label>
      ))}
    </div>
  )
}

interface EndSessionModalProps {
  endTarget: EndSessionTarget
  endReason: EndReasonCategory
  endNotes: string
  endingSession: boolean
  onClose: () => void
  onChangeReason: (reason: EndReasonCategory) => void
  onChangeNotes: (notes: string) => void
  onConfirm: () => void
}

const labelCls = "block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1"
const inputCls = "w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"

export function EndSessionModal({
  endTarget,
  endReason,
  endNotes,
  endingSession,
  onClose,
  onChangeReason,
  onChangeNotes,
  onConfirm,
}: EndSessionModalProps) {
  return (
    <ModalBackdrop onClose={onClose} title="End Session">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl max-w-md w-full">
        <div className="p-4 border-b border-lsc-border dark:border-earth-700 flex items-center justify-between">
          <h3 className="text-xl font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
            End Session
          </h3>
          <button onClick={onClose} disabled={endingSession} aria-label={t('aria.endSessionModal.closeModal', 'Close')}>
            <XCircle className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/60" />
          </button>
        </div>
        <div className="p-4 space-y-4">
          <div className="bg-lsc-cream dark:bg-earth-700/50 rounded-lg p-3 text-sm">
            <div className="text-lsc-dark dark:text-lsc-cream font-medium">
              {endTarget.patronName || 'Unknown patron'}
            </div>
            <div className="text-lsc-dark/70 dark:text-lsc-cream/70 text-xs mt-1">
              {endTarget.minutesRemaining > 0
                ? `${endTarget.minutesRemaining} min remaining in session`
                : 'Session is overtime'}
            </div>
          </div>

          <div>
            <label className={labelCls}>Reason</label>
            <EndReasonRadioGroup
              name="end-reason"
              value={endReason}
              onChange={onChangeReason}
            />
          </div>

          <div>
            <label className={labelCls}>
              Notes {endReason === 'other' && <span className="text-status-danger-600">*</span>}
            </label>
            <textarea
              value={endNotes}
              onChange={e => onChangeNotes(e.target.value)}
              rows={3}
              maxLength={500}
              placeholder="Optional context for the audit log"
              className={inputCls + ' resize-none'}
            />
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              disabled={endingSession}
              className="px-4 py-2 rounded-lg text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-earth-700"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={onConfirm}
              disabled={endingSession || (endReason === 'other' && !endNotes.trim())}
              className="px-4 py-2 rounded-lg bg-status-danger-600 text-white hover:bg-status-danger-700 disabled:opacity-50 flex items-center gap-2"
            >
              {endingSession ? (
                <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
              ) : (
                <XCircle className="w-4 h-4" />
              )}
              End Session
            </button>
          </div>
        </div>
      </div>
    </ModalBackdrop>
  )
}
