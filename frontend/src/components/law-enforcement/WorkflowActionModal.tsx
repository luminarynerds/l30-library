/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { X, Gavel, Send } from 'lucide-react'
import { useTranslation } from '@/i18n'
import type { WorkflowActionType } from './types'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

interface WorkflowActionState {
  action: WorkflowActionType
  data: Record<string, unknown>
}

interface WorkflowActionModalProps {
  show: boolean
  workflowAction: WorkflowActionState | null
  noteText: string
  onNoteChange: (text: string) => void
  onActionChange: (action: WorkflowActionState) => void
  onClose: () => void
  onConfirm: () => void
}

export function WorkflowActionModal({
  show,
  workflowAction,
  noteText,
  onNoteChange,
  onActionChange,
  onClose,
  onConfirm,
}: WorkflowActionModalProps): React.ReactElement | null {
  const { t } = useTranslation()

  if (!show || !workflowAction) return null

  const isLegalReview = workflowAction.action === 'legal_review'
  const isStatusChange = workflowAction.action === 'workflow_status'
  const isResponse = workflowAction.action === 'response'
  const isNotification = workflowAction.action === 'patron_notification'

  const titleText = isLegalReview ? 'Legal Review'
    : isStatusChange ? 'Change Status'
    : isResponse ? 'Record Response'
    : isNotification ? 'Send Notification'
    : 'Workflow Action'

  return (
    <ModalBackdrop onClose={onClose} title={titleText}>
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg max-w-lg w-full">
        <div className="p-4 border-b border-lsc-border dark:border-earth-700 flex items-center justify-between">
          <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream flex items-center gap-2">
            <Gavel className="w-5 h-5" />
            {isLegalReview && 'Legal Review'}
            {isStatusChange && 'Change Status'}
            {isResponse && 'Record Response'}
            {isNotification && 'Send Notification'}
          </h3>
          <button
            onClick={onClose}
            className="p-1 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        <div className="p-4 space-y-4">
          {isLegalReview && (
            <>
              <div>
                <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
                  Legal Review Status
                </label>
                <select
                  value={(workflowAction.data?.status as string) || ''}
                  onChange={(e) =>
                    onActionChange({
                      ...workflowAction,
                      data: { ...workflowAction.data, status: e.target.value },
                    })
                  }
                  className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
                >
                  <option value="">Select status</option>
                  <option value="pending">Pending Review</option>
                  <option value="approved">Approved</option>
                  <option value="denied">Denied</option>
                  <option value="partial">Partial Disclosure</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
                  Notes
                </label>
                <textarea
                  value={noteText}
                  onChange={(e) => onNoteChange(e.target.value)}
                  rows={3}
                  placeholder={t('placeholder.adminLawEnforcement.legalReviewNotes')}
                  className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
                />
              </div>
            </>
          )}

          {isStatusChange && (
            <div>
              <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
                New Status
              </label>
              <select
                value={(workflowAction.data?.status as string) || ''}
                onChange={(e) =>
                  onActionChange({
                    ...workflowAction,
                    data: { ...workflowAction.data, status: e.target.value },
                  })
                }
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
              >
                <option value="">Select status</option>
                <option value="received">Received</option>
                <option value="validating">Validating</option>
                <option value="legal_review">Legal Review</option>
                <option value="preparing_response">Preparing Response</option>
                <option value="completed">Completed</option>
                <option value="rejected">Rejected</option>
              </select>
            </div>
          )}

          {isResponse && (
            <>
              <div>
                <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
                  Response Date
                </label>
                <input
                  type="date"
                  value={(workflowAction.data?.response_date as string) || ''}
                  onChange={(e) =>
                    onActionChange({
                      ...workflowAction,
                      data: { ...workflowAction.data, response_date: e.target.value },
                    })
                  }
                  className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
                  Response Summary
                </label>
                <textarea
                  value={noteText}
                  onChange={(e) => onNoteChange(e.target.value)}
                  rows={3}
                  placeholder={t('placeholder.adminLawEnforcement.summaryOfResponse')}
                  className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
                />
              </div>
            </>
          )}

          {isNotification && (
            <div>
              <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
                Notification Date
              </label>
              <input
                type="date"
                value={(workflowAction.data?.notification_date as string) || ''}
                onChange={(e) =>
                  onActionChange({
                    ...workflowAction,
                    data: { ...workflowAction.data, notification_date: e.target.value },
                  })
                }
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
              />
            </div>
          )}
        </div>
        <div className="p-4 border-t border-lsc-border dark:border-earth-700 flex justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-lsc-brown/30 rounded-lg"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            className="flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90"
          >
            <Send className="w-4 h-4" />
            Confirm
          </button>
        </div>
      </div>
    </ModalBackdrop>
  )
}
