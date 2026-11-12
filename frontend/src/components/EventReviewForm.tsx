/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { CheckCircle, X } from 'lucide-react'
import FocusTrap from 'focus-trap-react'
import type { Event } from '@/api/api'
import { useTranslation } from '@/i18n/I18nContext'
import { useBranding } from '@/contexts/BrandingContext'
import { getCurrentLocale } from '@/i18n'

interface EventReviewFormProps {
  event: Event
  onClose: () => void
  onSuccess?: () => void
}

export default function EventReviewForm({ event, onClose, onSuccess: _onSuccess }: EventReviewFormProps): React.ReactElement {
  const branding = useBranding()
  const { t } = useTranslation()
  // Form is temporarily disabled to prevent spam
  return (
    <FocusTrap focusTrapOptions={{ allowOutsideClick: true }}>
      <div
        className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
        role="presentation"
        onClick={(e) => e.target === e.currentTarget && onClose()}
      >
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="review-modal-title"
          className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg max-w-md w-full"
        >
          <div className="flex items-center justify-between p-4 border-b border-lsc-border dark:border-earth-700">
            <h2
              id="review-modal-title"
              className="text-lg font-serif font-semibold text-lsc-dark dark:text-lsc-cream"
            >
              {t('events.detail.leaveReview')}
            </h2>
            <button
              onClick={onClose}
              className="p-1 hover:bg-lsc-cream dark:hover:bg-lsc-brown rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-lsc-rose"
              aria-label={t('common.close')}
            >
              <X aria-hidden="true" className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
            </button>
          </div>

          <div className="p-4">
            <div className="mb-4 p-3 bg-lsc-cream dark:bg-lsc-brown/30 rounded-xl">
              <h3 className="font-medium text-lsc-dark dark:text-lsc-cream">
                {event.title}
              </h3>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                {new Date(event.start_time).toLocaleDateString(getCurrentLocale(), {
                  weekday: 'long',
                  month: 'long',
                  day: 'numeric',
                  year: 'numeric',
                })}
              </p>
            </div>

            {/* Form temporarily disabled */}
            <div className="text-center py-6">
              <CheckCircle aria-hidden="true" className="w-16 h-16 text-earth-600 dark:text-earth-300 mx-auto mb-4" />
              <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-2">
                {t('events.review.thankYou')}
              </h3>
              <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
                {t('events.review.temporarilyUnavailable')}
              </p>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
                {t('events.review.feedbackPrefix')}{' '}
                <a href={`mailto:${branding.contact_email}`} className="text-lsc-rose hover:underline">
                  {branding.contact_email}
                </a>{' '}
                {t('events.review.feedbackSuffix')}
              </p>
              <button
                onClick={onClose}
                className="px-6 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-xl transition-colors"
              >
                {t('common.close')}
              </button>
            </div>
          </div>
        </div>
      </div>
    </FocusTrap>
  )
}
