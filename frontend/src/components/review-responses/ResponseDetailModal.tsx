/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { X, Edit, Trash2, XCircle, CheckCircle, Loader2 } from 'lucide-react'
import { clsx, formatDate } from '@/utils/helpers'
import type { PendingResponseItem } from '@/api/review-response-api'
import { REVIEW_TYPE_ICONS, REVIEW_TYPE_LABELS, STATUS_COLORS, StarRating } from './ReviewResponsesShared'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

export function ResponseDetailModal({
  response,
  onClose,
  onApprove,
  onReject,
  onEdit,
  onDelete,
  isProcessing,
}: {
  response: PendingResponseItem
  onClose: () => void
  onApprove: () => void
  onReject: () => void
  onEdit: () => void
  onDelete: () => void
  isProcessing: boolean
}): React.ReactElement {
  return (
    <ModalBackdrop onClose={onClose} title="Response Details">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-4 border-b border-lsc-border dark:border-earth-700">
          <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
            Response Details
          </h2>
          <button
            onClick={onClose}
            className="p-2 hover:bg-lsc-cream dark:hover:bg-earth-700 rounded-lg"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6 space-y-6">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs px-2 py-1 rounded-full bg-lsc-cream dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream flex items-center gap-1">
              {REVIEW_TYPE_ICONS[response.review_type]}
              {REVIEW_TYPE_LABELS[response.review_type]}
            </span>
            <span className={clsx('text-xs px-2 py-1 rounded-full font-medium', STATUS_COLORS[response.moderation_status])}>
              {response.moderation_status}
            </span>
            {response.is_staff_response && (
              <span className="text-xs px-2 py-1 rounded-full bg-earth-100 text-earth-800 dark:bg-earth-800/30 dark:text-lsc-rose-light">
                Staff Response
              </span>
            )}
          </div>

          <div>
            <h3 className="text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
              Item
            </h3>
            <p className="font-medium text-lsc-dark dark:text-lsc-cream">
              {response.item_title}
            </p>
          </div>

          <div>
            <h3 className="text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">
              Original Review
            </h3>
            <div className="bg-lsc-cream/50 dark:bg-earth-700/50 rounded-lg p-4">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                  by {response.reviewer_name || 'Anonymous'}
                </span>
                <StarRating rating={response.review_rating} />
              </div>
              <p className="text-sm text-lsc-dark dark:text-lsc-cream">
                {response.review_content}
              </p>
            </div>
          </div>

          <div>
            <h3 className="text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">
              Response
            </h3>
            <div className="bg-lsc-white dark:bg-earth-900 rounded-lg p-4 border border-lsc-border dark:border-earth-700">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                  by {response.author_name || response.author_email || 'Unknown'}
                </span>
                <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                  {formatDate(response.created_at)}
                </span>
              </div>
              <p className="text-sm text-lsc-dark dark:text-lsc-cream whitespace-pre-wrap">
                {response.content}
              </p>
            </div>
          </div>
        </div>

        <div className="p-4 border-t border-lsc-border dark:border-earth-700 flex flex-wrap items-center gap-3">
          <button
            onClick={onEdit}
            className="flex items-center gap-1.5 px-3 py-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-earth-700 rounded-lg"
          >
            <Edit className="w-4 h-4" />
            Edit
          </button>
          <button
            onClick={onDelete}
            className="flex items-center gap-1.5 px-3 py-2 text-sm text-status-danger-600 dark:text-status-danger-400 hover:bg-status-danger-50 dark:bg-status-danger-900/20 dark:hover:bg-status-danger-900/20 rounded-lg"
          >
            <Trash2 className="w-4 h-4" />
            Delete
          </button>
          <div className="flex-1" />
          {response.moderation_status === 'pending' && (
            <>
              <button
                onClick={onReject}
                disabled={isProcessing}
                className="flex items-center gap-1.5 px-4 py-2 text-sm border border-status-danger-300 text-status-danger-600 dark:border-status-danger-800 dark:text-status-danger-400 rounded-lg hover:bg-status-danger-50 dark:bg-status-danger-900/20 dark:hover:bg-status-danger-900/20 disabled:opacity-50"
              >
                <XCircle className="w-4 h-4" />
                Reject
              </button>
              <button
                onClick={onApprove}
                disabled={isProcessing}
                className="flex items-center gap-1.5 px-4 py-2 text-sm bg-status-success-600 text-white rounded-lg hover:bg-status-success-700 disabled:opacity-50"
              >
                {isProcessing ? (
                  <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
                ) : (
                  <CheckCircle className="w-4 h-4" />
                )}
                Approve
              </button>
            </>
          )}
          {response.moderation_status !== 'pending' && (
            <button
              onClick={onClose}
              className="px-4 py-2 text-sm bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90"
            >
              Close
            </button>
          )}
        </div>
      </div>
    </ModalBackdrop>
  )
}
