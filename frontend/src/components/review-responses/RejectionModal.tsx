/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { XCircle, Loader2 } from 'lucide-react'
import { useTranslation } from '@/i18n'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

export function RejectionModal({
  onClose,
  onSubmit,
  isSubmitting,
  count,
}: {
  onClose: () => void
  onSubmit: (reason: string) => void
  isSubmitting: boolean
  count: number
}): React.ReactElement {
  const { t } = useTranslation()
  const [reason, setReason] = useState('')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (reason.trim()) {
      onSubmit(reason.trim())
    }
  }

  return (
    <ModalBackdrop onClose={onClose} title="Reject Response">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl max-w-md w-full">
        <div className="p-4 border-b border-lsc-border dark:border-earth-700">
          <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream flex items-center gap-2">
            <XCircle className="w-5 h-5 text-status-danger-500" />
            Reject Response{count > 1 ? 's' : ''}
          </h2>
        </div>
        <form onSubmit={handleSubmit} className="p-4 space-y-4">
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
            Please provide a reason for rejecting {count > 1 ? `these ${count} responses` : 'this response'}.
          </p>
          <div>
            <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
              Reason <span className="text-status-danger-500">*</span>
            </label>
            <textarea
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              rows={3}
              required
              placeholder={t('staffReviewResponses.explainWhyThisResponseIs')}
              className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose resize-none"
            />
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-earth-700 rounded-lg"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!reason.trim() || isSubmitting}
              className="flex items-center gap-2 px-4 py-2 bg-status-danger-600 text-white rounded-lg hover:bg-status-danger-700 disabled:opacity-50"
            >
              {isSubmitting && <Loader2 className="w-4 h-4 motion-safe:animate-spin" />}
              Reject
            </button>
          </div>
        </form>
      </div>
    </ModalBackdrop>
  )
}
