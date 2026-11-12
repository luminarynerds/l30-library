/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Link } from 'react-router-dom'
import { ArrowLeft, CheckCircle, ChevronLeft, ChevronRight } from 'lucide-react'
import type { CourseLesson } from '../lesson-types'

interface Props {
  courseId: string | undefined
  prevLesson: CourseLesson | null
  nextLesson: CourseLesson | null
  currentIndex: number
  totalLessons: number
}

export function LessonNavigation({
  courseId,
  prevLesson,
  nextLesson,
  currentIndex,
  totalLessons,
}: Props) {
  return (
    <>
      <div className="mt-8 flex flex-col sm:flex-row justify-between gap-4">
        {prevLesson ? (
          <Link
            to={`/learn/course/${courseId}/lesson/${prevLesson.id}`}
            className="flex-1 flex items-center gap-3 p-4 bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 hover:border-lsc-rose dark:hover:border-lsc-rose transition-colors group"
          >
            <ChevronLeft aria-hidden="true" className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70 group-hover:text-lsc-rose" />
            <div className="flex-1 min-w-0">
              <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Previous</span>
              <p
                className="text-sm font-medium text-lsc-dark dark:text-lsc-cream truncate group-hover:text-lsc-rose"
                title={prevLesson.title}
              >
                {prevLesson.title}
              </p>
            </div>
          </Link>
        ) : (
          <Link
            to={`/learn/course/${courseId}`}
            className="flex-1 flex items-center gap-3 p-4 bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 hover:border-lsc-rose dark:hover:border-lsc-rose transition-colors group"
          >
            <ArrowLeft aria-hidden="true" className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70 group-hover:text-lsc-rose" />
            <div className="flex-1 min-w-0">
              <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Back to</span>
              <p className="text-sm font-medium text-lsc-dark dark:text-lsc-cream truncate group-hover:text-lsc-rose">
                Course Overview
              </p>
            </div>
          </Link>
        )}

        {nextLesson ? (
          <Link
            to={`/learn/course/${courseId}/lesson/${nextLesson.id}`}
            className="flex-1 flex items-center gap-3 p-4 bg-lsc-rose text-white rounded-xl hover:brightness-90 transition-all group"
          >
            <div className="flex-1 min-w-0 text-right">
              <span className="text-xs text-white/70">Next</span>
              <p className="text-sm font-medium truncate" title={nextLesson.title}>
                {nextLesson.title}
              </p>
            </div>
            <ChevronRight aria-hidden="true" className="w-5 h-5" />
          </Link>
        ) : (
          <Link
            to={`/learn/course/${courseId}`}
            className="flex-1 flex items-center gap-3 p-4 bg-status-success-600 text-white rounded-xl hover:bg-status-success-700 transition-colors group"
          >
            <div className="flex-1 min-w-0 text-right">
              <span className="text-xs text-white/70">Finished!</span>
              <p className="text-sm font-medium">Back to Course</p>
            </div>
            <CheckCircle aria-hidden="true" className="w-5 h-5" />
          </Link>
        )}
      </div>

      {totalLessons > 0 && (
        <div className="mt-4 text-center text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
          Lesson {currentIndex + 1} of {totalLessons}
        </div>
      )}
    </>
  )
}
