/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React, { useState } from "react"
import { Loader2, X, CheckCircle } from "lucide-react"
import { CheckInException, getExceptionTypeLabel } from "@/api/book-drop-api"
import { useTranslation } from '@/i18n'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

interface ResolveExceptionModalProps {
  exception: CheckInException
  isSaving: boolean
  onSubmit: (action: string) => void
  onCancel: () => void
}

export const ResolveExceptionModal: React.FC<ResolveExceptionModalProps> = ({
  exception,
  isSaving,
  onSubmit,
  onCancel,
}) => {
  const { t } = useTranslation()
  const [resolveAction, setResolveAction] = useState("")

  return (
    <ModalBackdrop onClose={onCancel} title="Resolve Exception">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg max-w-md w-full">
        <div className="p-4 border-b border-lsc-border dark:border-earth-700 flex items-center justify-between">
          <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
            Resolve Exception
          </h3>
          <button
            onClick={onCancel}
            aria-label={t('aria.resolveException.close', 'Close')}
            className="p-1 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        <div className="p-4 space-y-4">
          <div className="bg-status-danger-50 dark:bg-status-danger-900/20 rounded-lg p-3">
            <p className="font-medium text-status-danger-700 dark:text-status-danger-400">
              {getExceptionTypeLabel(exception.exception_type)}
            </p>
            <p className="text-sm text-status-danger-600 dark:text-status-danger-300">
              Barcode: {exception.barcode}
            </p>
            <p className="text-sm text-status-danger-600/80 dark:text-status-danger-300/80 mt-1">
              {exception.message}
            </p>
          </div>

          <div>
            <label htmlFor="resolve-exception-action" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
              Action Taken <span className="text-status-danger-600">*</span>
            </label>
            <textarea
              id="resolve-exception-action"
              value={resolveAction}
              onChange={(e) => setResolveAction(e.target.value)}
              placeholder={t('resolveException.describeHowThisExceptionWas')}
              rows={3}
              required
              aria-required="true"
              className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent resize-none"
            />
          </div>
        </div>
        <div className="p-4 border-t border-lsc-border dark:border-earth-700 flex justify-end gap-3">
          <button
            onClick={onCancel}
            className="px-4 py-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-lsc-brown/30 rounded-lg transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={() => onSubmit(resolveAction)}
            disabled={isSaving || !resolveAction.trim()}
            className="flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 transition-colors disabled:opacity-50"
          >
            {isSaving && <Loader2 className="w-4 h-4 motion-safe:animate-spin" />}
            <CheckCircle className="w-4 h-4" />
            Resolve
          </button>
        </div>
      </div>
    </ModalBackdrop>
  )
}
