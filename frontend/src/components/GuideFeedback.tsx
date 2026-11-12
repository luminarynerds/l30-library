/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import { useState } from 'react'
import { ThumbsUp, ThumbsDown } from 'lucide-react'
import toast from 'react-hot-toast'
import { submitGuideFeedback } from '@/api/guide-feedback-api'
import { isApiError } from '@/lib/api-client'
import { useTranslation} from '@/i18n'

interface GuideFeedbackProps {
  guideId: string
  guideTitle: string
  onSubmitFeedback?: (feedback: {
    guideId: string
    helpful: boolean
    comment?: string
  }) => void
}

export default function GuideFeedback({
  guideId,
  guideTitle: _guideTitle,
  onSubmitFeedback,
}: GuideFeedbackProps): React.ReactElement {
  const { t } = useTranslation()
  const [helpful, setHelpful] = useState<boolean | null>(null)
  const [showComment, setShowComment] = useState(false)
  const [comment, setComment] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [submitted, setSubmitted] = useState(false)

  const handleSubmit = async () => {
    setIsSubmitting(true)
    try {
      // Convert guideId from string to number
      const guideIdNum = parseInt(guideId, 10)
      if (isNaN(guideIdNum)) {
        toast.error(t('toast.guideFeedback.invalidGuideId'))
        setIsSubmitting(false)
        return
      }

      // Submit feedback to backend API
      await submitGuideFeedback(
        guideIdNum,
        helpful ?? false,
        comment || undefined
      )

      // Call optional callback with feedback data
      const feedbackData = {
        guideId,
        helpful: helpful ?? false,
        ...(comment ? { comment } : {}),
      }
      onSubmitFeedback?.(feedbackData)

      setSubmitted(true)
      toast.success(t('components.guideFeedback.thankYouForYourFeedback'))

      // Reset after 3 seconds
      setTimeout(() => {
        setHelpful(null)
        setComment('')
        setShowComment(false)
        setSubmitted(false)
      }, 3000)
    } catch (error: unknown) {
      // Provide user-friendly error message
      let errorMessage = 'Failed to submit feedback'
      if (isApiError(error)) {
        errorMessage = error.detail || error.message || 'Failed to submit feedback'
      } else if (error instanceof Error) {
        errorMessage = error.message
      }
      toast.error(errorMessage)
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
    } finally {
      setIsSubmitting(false)
    }
  }

  if (submitted) {
    return (
      <div className="bg-status-success-50 dark:bg-status-success-900/20 border border-status-success-200 dark:border-status-success-900/50 rounded-xl p-4 text-center">
        <p className="text-status-success-800 dark:text-status-success-200 font-medium">✓ Feedback received!</p>
        <p className="text-sm text-status-success-700 dark:text-status-success-300 mt-1">
          We'll use this to improve our guides.
        </p>
      </div>
    )
  }

  return (
    <div className="bg-lsc-cream dark:bg-lsc-brown/20 rounded-xl p-4 border border-lsc-border dark:border-earth-700">
      <p className="text-sm font-medium text-lsc-dark dark:text-earth-50 mb-3">
        Was this guide helpful?
      </p>

      <div className="flex items-center gap-2 mb-3">
        <button
          onClick={() => {
            setHelpful(true)
            setShowComment(false)
          }}
          aria-pressed={helpful === true}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg motion-safe:transition-colors ${
            helpful === true
              ? 'bg-status-success-100 dark:bg-status-success-900/30 text-status-success-700 dark:text-status-success-400'
              : 'bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream hover:bg-status-success-50 dark:hover:bg-status-success-900/20'
          }`}
        >
          <ThumbsUp aria-hidden="true" className="w-4 h-4" />
          <span className="text-sm">Yes, helpful</span>
        </button>

        <button
          onClick={() => {
            setHelpful(false)
            setShowComment(true)
          }}
          aria-pressed={helpful === false}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg motion-safe:transition-colors ${
            helpful === false
              ? 'bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-700 dark:text-status-warning-400'
              : 'bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream hover:bg-status-warning-50 dark:hover:bg-status-warning-900/20'
          }`}
        >
          <ThumbsDown aria-hidden="true" className="w-4 h-4" />
          <span className="text-sm">Not helpful</span>
        </button>
      </div>

      {showComment && helpful === false && (
        <div className="space-y-2 mb-3 p-3 bg-lsc-white dark:bg-earth-800 rounded-lg">
          <label className="text-xs font-medium text-lsc-dark dark:text-earth-50">
            What didn't work?
          </label>
          <textarea
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            placeholder={t('components.guideFeedback.letUsKnowWhatWe')}
            className="w-full px-3 py-2 text-sm rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-earth-50 placeholder-earth-500 dark:placeholder-earth-500 focus:ring-2 focus:ring-lsc-rose focus:border-transparent resize-none"
            rows={3}
          />
        </div>
      )}

      {helpful !== null && (
        <button
          onClick={handleSubmit}
          disabled={isSubmitting}
          className="w-full px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-lg text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed motion-safe:transition-colors"
        >
          {isSubmitting ? 'Submitting...' : 'Submit Feedback'}
        </button>
      )}

      {helpful === null && (
        <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 text-center">
          Your feedback helps us improve
        </p>
      )}
    </div>
  )
}
