/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { Flag, ThumbsDown, ThumbsUp } from 'lucide-react'
import { useTranslation } from '@/i18n'
import type { FeedbackType } from './useLessonViewer'

interface Props {
  submitted: boolean
  onSubmit: (type: FeedbackType) => void
}

const REPORT_OPTIONS: { type: FeedbackType; label: string }[] = [
  { type: 'content_error', label: 'Content error' },
  { type: 'broken_link', label: 'Broken link/media' },
  { type: 'accessibility', label: 'Accessibility issue' },
  { type: 'other', label: 'Other' },
]

export function LessonFeedback({ submitted, onSubmit }: Props) {
  const { t } = useTranslation()
  const [showReport, setShowReport] = useState(false)

  if (submitted) return null

  const handleReport = (type: FeedbackType) => {
    onSubmit(type)
    setShowReport(false)
  }

  return (
    <div className="mt-8 bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm border border-lsc-border dark:border-earth-700">
      {!showReport ? (
        <div className="flex items-center justify-between">
          <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
            {t('lessonViewer.wasThisLessonHelpful')}
          </span>
          <div className="flex gap-2">
            <button
              onClick={() => onSubmit('helpful')}
              className="inline-flex items-center gap-1 px-3 py-1.5 text-sm bg-status-success-100 dark:bg-status-success-900/30 text-status-success-700 dark:text-status-success-300 rounded-lg hover:bg-status-success-200 dark:hover:bg-status-success-900/50 transition-colors"
            >
              <ThumbsUp className="w-4 h-4" />
              Yes
            </button>
            <button
              onClick={() => onSubmit('not_helpful')}
              className="inline-flex items-center gap-1 px-3 py-1.5 text-sm bg-lsc-cream dark:bg-lsc-brown text-lsc-dark/70 dark:text-lsc-cream/70 rounded-lg hover:bg-lsc-cream/80 dark:hover:bg-lsc-brown/80 transition-colors"
            >
              <ThumbsDown className="w-4 h-4" />
              No
            </button>
            <button
              onClick={() => setShowReport(true)}
              className="inline-flex items-center gap-1 px-3 py-1.5 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-rose transition-colors"
              title="Report an issue"
            >
              <Flag className="w-4 h-4" />
            </button>
          </div>
        </div>
      ) : (
        <div>
          <div className="flex items-center justify-between mb-3">
            <span className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
              Report an issue
            </span>
            <button
              onClick={() => setShowReport(false)}
              className="text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream"
            >
              ×
            </button>
          </div>
          <div className="flex flex-wrap gap-2">
            {REPORT_OPTIONS.map(opt => (
              <button
                key={opt.type}
                onClick={() => handleReport(opt.type)}
                className="px-3 py-1.5 text-sm bg-lsc-cream dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream rounded-lg hover:bg-lsc-cream/80"
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
