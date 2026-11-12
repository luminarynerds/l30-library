/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Send } from 'lucide-react'
import { formatDate } from '@/utils/helpers'
import type { PendingReviewItem } from '@/api/review-response-api'
import { REVIEW_TYPE_ICONS, REVIEW_TYPE_LABELS, StarRating } from './ReviewResponsesShared'

export function ReviewNeedingResponseCard({
  review,
  onCompose,
}: {
  review: PendingReviewItem
  onCompose: () => void
}): React.ReactElement {
  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 overflow-hidden">
      <div className="p-4">
        <div className="flex items-start justify-between mb-3">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xs px-2 py-0.5 rounded-full bg-lsc-cream dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream flex items-center gap-1">
                {REVIEW_TYPE_ICONS[review.review_type]}
                {REVIEW_TYPE_LABELS[review.review_type]}
              </span>
              {review.response_count > 0 && (
                <span className="text-xs px-2 py-0.5 rounded-full bg-earth-100 text-earth-800 dark:bg-earth-800/30 dark:text-lsc-rose-light">
                  {review.response_count} response{review.response_count !== 1 ? 's' : ''}
                </span>
              )}
              {!review.has_staff_response && (
                <span className="text-xs px-2 py-0.5 rounded-full bg-status-warning-100 text-status-warning-800 dark:bg-status-warning-900/30 dark:text-status-warning-300">
                  Needs Staff Response
                </span>
              )}
            </div>
            <h3 className="font-medium text-lsc-dark dark:text-lsc-cream">
              {review.item_title}
            </h3>
          </div>
          <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
            {formatDate(review.review_created_at)}
          </span>
        </div>

        <div className="mb-3">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
              by {review.reviewer_name || 'Anonymous'}
            </span>
            <StarRating rating={review.review_rating} />
          </div>
          <p className="text-sm text-lsc-dark dark:text-lsc-cream">
            {review.review_content}
          </p>
        </div>

        <div className="flex items-center gap-2 pt-3 border-t border-lsc-border dark:border-earth-700">
          <div className="flex-1" />
          <button
            onClick={onCompose}
            className="flex items-center gap-1.5 px-4 py-2 text-sm bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 transition-colors"
          >
            <Send className="w-4 h-4" />
            Compose Response
          </button>
        </div>
      </div>
    </div>
  )
}
