/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useCallback, useState } from 'react'
import { CourseCompletionModal } from '../components/learning/lesson-viewer/CourseCompletionModal'
import { FacilitatorNotes } from '../components/learning/lesson-viewer/FacilitatorNotes'
import { KeyboardShortcutsModal } from '../components/learning/lesson-viewer/KeyboardShortcutsModal'
import { LessonBody } from '../components/learning/lesson-viewer/LessonBody'
import { LessonFeedback } from '../components/learning/lesson-viewer/LessonFeedback'
import { LessonHeader } from '../components/learning/lesson-viewer/LessonHeader'
import { LessonHero } from '../components/learning/lesson-viewer/LessonHero'
import { LessonNavigation } from '../components/learning/lesson-viewer/LessonNavigation'
import {
  ErrorState,
  LoadingState,
  NotFoundState,
  UnauthenticatedState,
} from '../components/learning/lesson-viewer/LessonStates'
import { PlacementRecommendation } from '../components/learning/lesson-viewer/PlacementRecommendation'
import { VariantSelector } from '../components/learning/lesson-viewer/VariantSelector'
import { useLessonKeyboardShortcuts } from '../components/learning/lesson-viewer/useLessonKeyboardShortcuts'
import { useLessonViewer } from '../components/learning/lesson-viewer/useLessonViewer'
import PageContainer from '@/components/layout/PageContainer'

export default function LessonViewerPage() {
  const v = useLessonViewer()
  const [showKeyboardHelp, setShowKeyboardHelp] = useState(false)
  const [completionDismissed, setCompletionDismissed] = useState(false)
  const showCompletionModal = v.completed && v.isFinalLesson && !completionDismissed

  const closeOverlays = useCallback(() => {
    setShowKeyboardHelp(false)
    setCompletionDismissed(true)
  }, [])
  const toggleHelp = useCallback(() => setShowKeyboardHelp(prev => !prev), [])

  useLessonKeyboardShortcuts({
    prevLesson: v.prevLesson,
    nextLesson: v.nextLesson,
    goToLesson: v.goToLesson,
    toggleBookmark: v.isAuthenticated ? v.handleToggleBookmark : undefined,
    markComplete: v.isAuthenticated ? v.handleComplete : undefined,
    completed: v.completed,
    toggleHelp,
    closeOverlays,
  })

  if (v.loading) return <LoadingState />
  if (v.notFound) return <NotFoundState courseId={v.courseId} />
  if (v.error) {
    // Anon hitting a locked (non-preview) lesson gets a friendlier sign-in prompt
    // rather than a raw error message.
    if (!v.isAuthenticated) return <UnauthenticatedState />
    return <ErrorState message={v.error} />
  }
  if (!v.lesson) return <NotFoundState courseId={v.courseId} />

  const lesson = v.lesson
  const content = v.getActiveContent()
  const canTrackProgress = v.isAuthenticated

  return (
    <div className="min-h-screen bg-lsc-cream dark:bg-lsc-dark">
      <LessonHeader
        courseId={v.courseId}
        isBookmarked={v.isBookmarked}
        completed={v.completed}
        onShowKeyboardHelp={() => setShowKeyboardHelp(true)}
        onToggleBookmark={canTrackProgress ? v.handleToggleBookmark : undefined}
        onComplete={canTrackProgress ? v.handleComplete : undefined}
        canTrackProgress={canTrackProgress}
      />

      <KeyboardShortcutsModal open={showKeyboardHelp} onClose={() => setShowKeyboardHelp(false)} />

      <CourseCompletionModal
        isOpen={showCompletionModal}
        onClose={() => setCompletionDismissed(true)}
        courseId={v.courseId}
        courseTitle={v.courseStructure?.title || ''}
      />

      <PageContainer className="py-8">
        {!canTrackProgress && (
          <div className="mb-6 flex items-center justify-between gap-4 bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-xl px-4 py-3 text-sm text-lsc-dark/80 dark:text-lsc-cream/80">
            <span>You're reading a preview. Sign in to enroll and track your progress.</span>
            <a href="/account" className="shrink-0 text-lsc-rose dark:text-lsc-rose-light hover:underline font-medium">Sign in</a>
          </div>
        )}

        <LessonHero
          title={lesson.title}
          estimatedMinutes={lesson.estimated_minutes}
          sensoryNotes={lesson.sensory_notes}
        />

        <VariantSelector
          variants={lesson.variants}
          activeVariant={v.activeVariant}
          onChange={v.setActiveVariant}
        />

        <LessonBody
          lesson={lesson}
          content={content}
          quizAnswers={v.quizAnswers}
          quizSubmitted={v.quizSubmitted}
          quizResult={v.quizResult}
          onAnswer={v.setQuizAnswer}
          onQuizSubmit={canTrackProgress ? v.handleQuizSubmit : () => {}}
          onQuizRetry={v.resetQuiz}
          onComplete={canTrackProgress ? v.handleComplete : () => {}}
        />

        <FacilitatorNotes notes={lesson.facilitator_notes} userRole={v.user?.role} />

        <PlacementRecommendation quizResult={v.quizResult} visible={v.quizSubmitted} />

        {canTrackProgress && (
          <LessonFeedback submitted={v.feedbackSubmitted} onSubmit={v.handleFeedback} />
        )}

        <LessonNavigation
          courseId={v.courseId}
          prevLesson={v.prevLesson}
          nextLesson={v.nextLesson}
          currentIndex={v.currentIndex}
          totalLessons={v.allLessons.length}
        />
      </PageContainer>
    </div>
  )
}
