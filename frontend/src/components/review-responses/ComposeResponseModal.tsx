/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { MessageSquare, X, Send, Loader2, AlertCircle } from 'lucide-react'
import { clsx } from '@/utils/helpers'
import { useTranslation } from '@/i18n'
import type { PendingReviewItem } from '@/api/review-response-api'
import { REVIEW_TYPE_ICONS, StarRating } from './ReviewResponsesShared'
import { formatDate } from '@/utils/helpers'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

export function ComposeResponseModal({
  review,
  onClose,
  onSubmit,
  isSubmitting,
}: {
  review: PendingReviewItem
  onClose: () => void
  onSubmit: (content: string) => void
  isSubmitting: boolean
}): React.ReactElement {
  const { t } = useTranslation()
  const [content, setContent] = useState('')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (content.trim().length >= 10) {
      onSubmit(content.trim())
    }
  }

  return (
    <ModalBackdrop onClose={onClose} title="Compose Response">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-4 border-b border-lsc-border dark:border-earth-700">
          <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream flex items-center gap-2">
            <MessageSquare className="w-5 h-5 text-lsc-rose" />
            Compose Response
          </h2>
          <button
            onClick={onClose}
            className="p-2 hover:bg-lsc-cream dark:hover:bg-earth-700 rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          <div>
            <h3 className="text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
              Original Review
            </h3>
            <div className="bg-lsc-cream/50 dark:bg-earth-700/50 rounded-lg p-4">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-xs px-2 py-0.5 rounded-full bg-lsc-cream dark:bg-earth-600 flex items-center gap-1">
                  {REVIEW_TYPE_ICONS[review.review_type]}
                  {review.item_title}
                </span>
              </div>
              <div className="flex items-center gap-2 mb-2">
                <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                  by {review.reviewer_name || 'Anonymous'}
                </span>
                <StarRating rating={review.review_rating} />
                <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                  {formatDate(review.review_created_at)}
                </span>
              </div>
              <p className="text-sm text-lsc-dark dark:text-lsc-cream">
                {review.review_content}
              </p>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
              Your Response <span className="text-status-danger-500">*</span>
            </label>
            <textarea
              value={content}
              onChange={(e) => setContent(e.target.value)}
              rows={5}
              minLength={10}
              maxLength={2000}
              required
              placeholder={t('staffReviewResponses.writeAThoughtfulResponseTo')}
              className="w-full px-4 py-3 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent resize-none"
            />
            <div className="flex justify-between mt-1">
              <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                Be professional and helpful in your response
              </span>
              <span className={clsx(
                'text-xs',
                content.length < 10 ? 'text-status-danger-500' : 'text-lsc-dark/70 dark:text-lsc-cream/70'
              )}>
                {content.length}/2000
              </span>
            </div>
          </div>

          <div className="bg-earth-50 dark:bg-earth-800/20 rounded-lg p-4 flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-earth-600 flex-shrink-0 mt-0.5" />
            <div className="text-sm text-lsc-rose dark:text-lsc-rose-light">
              <p className="font-medium mb-1">Staff Response Guidelines</p>
              <ul className="list-disc list-inside text-xs space-y-1 text-lsc-rose dark:text-lsc-rose-light">
                <li>{t('staffReviewResponses.beProfessionalAndCourteous')}</li>
                <li>{t('staffReviewResponses.addressSpecificConcernsRaisedIn')}</li>
                <li>{t('staffReviewResponses.provideHelpfulInformationWhenPossible')}</li>
                <li>{t('staffReviewResponses.staffResponsesAreAutomaticallyApproved')}</li>
              </ul>
            </div>
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t border-lsc-border dark:border-earth-700">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-earth-700 rounded-lg transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={content.trim().length < 10 || isSubmitting}
              className="flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 disabled:opacity-50 transition-colors"
            >
              {isSubmitting ? (
                <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
              ) : (
                <Send className="w-4 h-4" />
              )}
              Submit Response
            </button>
          </div>
        </form>
      </div>
    </ModalBackdrop>
  )
}
