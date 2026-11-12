/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Link } from 'react-router-dom'
import {
  Bookmark,
  BookmarkCheck,
  CheckCircle,
  ChevronLeft,
  Keyboard,
} from 'lucide-react'
import { useTranslation } from '@/i18n'

interface Props {
  courseId: string | undefined
  isBookmarked: boolean
  completed: boolean
  onShowKeyboardHelp: () => void
  onToggleBookmark?: () => void
  onComplete?: () => void
  // Bookmark + complete need an account; hidden for anonymous preview readers.
  canTrackProgress?: boolean
}

export function LessonHeader({
  courseId,
  isBookmarked,
  completed,
  onShowKeyboardHelp,
  onToggleBookmark,
  onComplete,
  canTrackProgress = true,
}: Props) {
  const { t } = useTranslation()

  return (
    <div className="bg-lsc-white dark:bg-earth-800 border-b border-lsc-border dark:border-earth-700 sticky top-0 z-10">
      <div className="max-w-4xl mx-auto px-4 py-3 flex items-center justify-between">
        <Link
          to={`/learn/course/${courseId}`}
          className="inline-flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-rose dark:hover:text-lsc-rose"
        >
          <ChevronLeft aria-hidden="true" className="w-5 h-5" />
          Back to Course
        </Link>

        <div className="flex items-center gap-2">
          <button
            onClick={onShowKeyboardHelp}
            className="p-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream rounded-lg"
            aria-label={t('aria.lessonViewer.keyboardShortcuts')}
            title="Keyboard shortcuts (?)"
          >
            <Keyboard aria-hidden="true" className="w-5 h-5" />
          </button>

          {canTrackProgress && (
            <button
              onClick={onToggleBookmark}
              className={`p-2 rounded-lg transition-colors ${
                isBookmarked
                  ? 'text-lsc-rose'
                  : 'text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream'
              }`}
              aria-label={isBookmarked ? 'Remove bookmark' : 'Bookmark lesson'}
              title="Bookmark (B)"
            >
              {isBookmarked ? (
                <BookmarkCheck aria-hidden="true" className="w-5 h-5" />
              ) : (
                <Bookmark aria-hidden="true" className="w-5 h-5" />
              )}
            </button>
          )}

          {canTrackProgress && (completed ? (
            <span className="inline-flex items-center gap-2 text-status-success-600 dark:text-status-success-400 text-sm px-3 py-2">
              <CheckCircle aria-hidden="true" className="w-5 h-5" />
              Completed
            </span>
          ) : (
            <button
              onClick={onComplete}
              className="inline-flex items-center gap-2 bg-lsc-rose hover:brightness-90 text-white px-4 py-2 rounded-xl text-sm font-medium transition-colors"
              title="Mark complete (M)"
            >
              <CheckCircle aria-hidden="true" className="w-4 h-4" />
              Mark Complete
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
