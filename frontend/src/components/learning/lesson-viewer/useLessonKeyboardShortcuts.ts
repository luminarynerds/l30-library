/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect } from 'react'
import type { CourseLesson } from '../lesson-types'

interface Options {
  prevLesson: CourseLesson | null
  nextLesson: CourseLesson | null
  goToLesson: (lesson: CourseLesson | null) => void
  toggleBookmark?: () => void
  markComplete?: () => void
  completed: boolean
  toggleHelp: () => void
  closeOverlays: () => void
}

export function useLessonKeyboardShortcuts({
  prevLesson,
  nextLesson,
  goToLesson,
  toggleBookmark,
  markComplete,
  completed,
  toggleHelp,
  closeOverlays,
}: Options) {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return

      switch (e.key) {
        case 'ArrowLeft':
        case 'j':
          if (prevLesson) {
            e.preventDefault()
            goToLesson(prevLesson)
          }
          break
        case 'ArrowRight':
        case 'k':
          if (nextLesson) {
            e.preventDefault()
            goToLesson(nextLesson)
          }
          break
        case 'b':
          e.preventDefault()
          toggleBookmark?.()
          break
        case 'm':
          if (!completed) {
            e.preventDefault()
            markComplete?.()
          }
          break
        case '?':
          e.preventDefault()
          toggleHelp()
          break
        case 'Escape':
          closeOverlays()
          break
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [prevLesson, nextLesson, goToLesson, toggleBookmark, markComplete, completed, toggleHelp, closeOverlays])
}
