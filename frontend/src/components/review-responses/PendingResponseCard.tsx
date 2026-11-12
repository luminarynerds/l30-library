/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { MessageSquare, CheckCircle, XCircle, Eye } from 'lucide-react'
import { clsx, formatDate } from '@/utils/helpers'
import type { PendingResponseItem } from '@/api/review-response-api'
import { REVIEW_TYPE_ICONS, REVIEW_TYPE_LABELS, STATUS_COLORS, StarRating } from './ReviewResponsesShared'

export function PendingResponseCard({
  response,
  onApprove,
  onReject,
  onView,
  isSelected,
  onSelect,
}: {
  response: PendingResponseItem
  onApprove: () => void
  onReject: () => void
  onView: () => void
  isSelected: boolean
  onSelect: (selected: boolean) => void
}): React.ReactElement {
  return (
    <div className={clsx(
      'bg-lsc-white dark:bg-earth-800 rounded-xl border overflow-hidden transition-colors',
      isSelected
        ? 'border-lsc-rose dark:border-lsc-rose'
        : 'border-lsc-border dark:border-earth-700'
    )}>
      <div className="p-4">
        <div className="flex items-start gap-3 mb-3">
          <input
            type="checkbox"
            checked={isSelected}
            onChange={(e) => onSelect(e.target.checked)}
            className="mt-1 rounded border-lsc-border"
          />
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-xs px-2 py-0.5 rounded-full bg-lsc-cream dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream flex items-center gap-1">
                {REVIEW_TYPE_ICONS[response.review_type]}
                {REVIEW_TYPE_LABELS[response.review_type]}
              </span>
              <span className={clsx('text-xs px-2 py-0.5 rounded-full', STATUS_COLORS[response.moderation_status])}>
                {response.moderation_status}
              </span>
              {response.is_staff_response && (
                <span className="text-xs px-2 py-0.5 rounded-full bg-earth-100 text-earth-800 dark:bg-earth-800/30 dark:text-lsc-rose-light">
                  Staff Response
                </span>
              )}
            </div>
            <h3 className="font-medium text-lsc-dark dark:text-lsc-cream mt-1 truncate" title={response.item_title}>
              {response.item_title}
            </h3>
          </div>
          <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 whitespace-nowrap">
            {formatDate(response.created_at)}
          </span>
        </div>

        <div className="bg-lsc-cream/50 dark:bg-earth-700/50 rounded-lg p-3 mb-3">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70">
              Original Review by {response.reviewer_name || 'Anonymous'}
            </span>
            <StarRating rating={response.review_rating} />
          </div>
          <p className="text-sm text-lsc-dark/80 dark:text-lsc-cream/80 line-clamp-2" title={response.review_content}>
            {response.review_content}
          </p>
        </div>

        <div className="mb-3">
          <div className="flex items-center gap-2 mb-1">
            <MessageSquare className="w-4 h-4 text-lsc-rose" />
            <span className="text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70">
              Response by {response.author_name || response.author_email || 'Unknown'}
            </span>
          </div>
          <p className="text-sm text-lsc-dark dark:text-lsc-cream">
            {response.content}
          </p>
        </div>

        <div className="flex items-center gap-2 pt-3 border-t border-lsc-border dark:border-earth-700">
          <button
            onClick={onView}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-earth-700 rounded-lg transition-colors"
          >
            <Eye className="w-4 h-4" />
            View
          </button>
          <div className="flex-1" />
          <button
            onClick={onReject}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-status-danger-600 dark:text-status-danger-400 hover:bg-status-danger-50 dark:bg-status-danger-900/20 dark:hover:bg-status-danger-900/20 rounded-lg transition-colors"
          >
            <XCircle className="w-4 h-4" />
            Reject
          </button>
          <button
            onClick={onApprove}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-status-success-600 text-white rounded-lg hover:bg-status-success-700 transition-colors"
          >
            <CheckCircle className="w-4 h-4" />
            Approve
          </button>
        </div>
      </div>
    </div>
  )
}
