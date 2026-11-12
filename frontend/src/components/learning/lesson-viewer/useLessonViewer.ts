/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import { useCallback, useEffect, useState } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import toast from 'react-hot-toast'
import api from '../../../api/api'
import { isApiError } from '@/lib/api-client'
import { API_BASE } from '@/api/types'
import { useAuth } from '../../../contexts/AuthContext'
import { usePreferences } from '../../../contexts/PreferencesContext'
import { useTranslation } from '@/i18n'
import { addToRecentlyViewed, setLastLesson } from '../../../services/learning-storage'
import { getBookmarks, toggleBookmark } from '../lesson-bookmarks'
import type {
  ArticleContent,
  CourseLesson,
  CourseStructure,
  Lesson,
  QuizResult,
  SandboxContent,
  VideoContent,
} from '../lesson-types'

export type FeedbackType =
  | 'helpful'
  | 'not_helpful'
  | 'content_error'
  | 'broken_link'
  | 'accessibility'
  | 'other'

export function useLessonViewer() {
  const { t } = useTranslation()
  const { id: courseId, lessonId } = useParams<{ id: string; lessonId: string }>()
  const [searchParams] = useSearchParams()
  const isStaffPreview = searchParams.get('preview') === 'true'
  const navigate = useNavigate()
  const { isAuthenticated, user } = useAuth()
  const { preferences } = usePreferences()

  const [lesson, setLesson] = useState<Lesson | null>(null)
  const [courseStructure, setCourseStructure] = useState<CourseStructure | null>(null)
  const [lessonLoading, setLessonLoading] = useState(true)
  const [courseLoading, setCourseLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [notFound, setNotFound] = useState(false)
  const [completed, setCompleted] = useState(false)
  const loading = lessonLoading || courseLoading
  const [activeVariant, setActiveVariant] = useState<string>('default')
  const [isBookmarked, setIsBookmarked] = useState(false)
  const [feedbackSubmitted, setFeedbackSubmitted] = useState(false)

  const [quizAnswers, setQuizAnswers] = useState<Record<number, number>>({})
  const [quizSubmitted, setQuizSubmitted] = useState(false)
  const [quizResult, setQuizResult] = useState<QuizResult | null>(null)

  const allLessons = courseStructure?.modules.flatMap(m => m.lessons) || []
  const currentIndex = allLessons.findIndex(l => l.id === Number(lessonId))
  const prevLesson = currentIndex > 0 ? allLessons[currentIndex - 1] ?? null : null
  const nextLesson =
    currentIndex < allLessons.length - 1 ? allLessons[currentIndex + 1] ?? null : null
  const isFinalLesson =
    allLessons.length > 0 && currentIndex === allLessons.length - 1

  const goToLesson = useCallback(
    (target: CourseLesson | null) => {
      if (target && courseId) {
        navigate(`/learn/course/${courseId}/lesson/${target.id}`)
      }
    },
    [courseId, navigate],
  )

  useEffect(() => {
    if (!lessonId) return
    let cancelled = false
    setLessonLoading(true)
    setLesson(null)
    setError(null)
    setNotFound(false)
    setCompleted(false)
    setActiveVariant('default')
    setQuizAnswers({})
    setQuizSubmitted(false)
    setQuizResult(null)
    setFeedbackSubmitted(false)
    ;(async () => {
      try {
        const lessonUrl = isStaffPreview
          ? `${API_BASE}/learning/lessons/${lessonId}?preview=true`
          : `${API_BASE}/learning/lessons/${lessonId}`
        const data = await api.get(lessonUrl)
        if (cancelled) return
        setLesson(data)
        const savedPosition = data.progress?.scroll_position
        if (typeof savedPosition === 'number' && savedPosition > 0) {
          setTimeout(() => {
            window.scrollTo({ top: savedPosition, behavior: 'instant' })
          }, 0)
        }
        if (
          preferences?.preferred_content_variant &&
          data.variants.some(
            (v: { variant_type: string }) =>
              v.variant_type === preferences.preferred_content_variant,
          )
        ) {
          setActiveVariant(preferences.preferred_content_variant)
        }
      } catch (err: unknown) {
        if (cancelled) return
        if (isApiError(err) && err.status === 404) {
          setNotFound(true)
          Sentry.captureMessage(
            `Lesson not found: course=${courseId} lesson=${lessonId}`,
            'warning',
          )
        } else {
          setError(err instanceof Error ? err.message : 'Unable to load lesson')
        }
      } finally {
        if (!cancelled) setLessonLoading(false)
      }
    })()
    getBookmarks().then(bm => {
      if (!cancelled) setIsBookmarked(bm.includes(Number(lessonId)))
    })
    return () => {
      cancelled = true
    }
  }, [lessonId, courseId, isStaffPreview, preferences?.preferred_content_variant])

  useEffect(() => {
    if (!courseId) return
    let cancelled = false
    setCourseLoading(true)
    api
      .get(`${API_BASE}/learning/courses/${courseId}`)
      .then(data => {
        if (cancelled) return
        setCourseStructure(data)
        if (isAuthenticated) addToRecentlyViewed({ id: data.id, title: data.title })
      })
      .catch(err => {
        if (cancelled) return
        if (isApiError(err) && err.status === 404) {
          setNotFound(true)
          Sentry.captureMessage(`Course not found: course=${courseId}`, 'warning')
          return
        }
        Sentry.captureException(err instanceof Error ? err : new Error(String(err)))
        setError('Unable to load course structure')
      })
      .finally(() => {
        if (!cancelled) setCourseLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [courseId, isAuthenticated])

  useEffect(() => {
    if (lesson && courseStructure) {
      setLastLesson({
        lessonId: lesson.id,
        lessonTitle: lesson.title,
        courseId: courseStructure.id,
        courseTitle: courseStructure.title,
        viewedAt: new Date().toISOString(),
      })
    }
  }, [lesson, courseStructure])

  const handleComplete = useCallback(async () => {
    try {
      await api.post(`${API_BASE}/learning/lessons/${lessonId}/complete`)
      setCompleted(true)
      toast.success(t('lessonViewer.lessonMarkedAsComplete'))
    } catch (err) {
      Sentry.captureException(err)
    }
  }, [lessonId, t])

  const handleToggleBookmark = useCallback(async () => {
    if (!lessonId) return
    const added = await toggleBookmark(Number(lessonId))
    setIsBookmarked(added)
    toast.success(added ? 'Lesson bookmarked!' : 'Bookmark removed')
  }, [lessonId])

  const handleFeedback = useCallback(
    async (type: FeedbackType) => {
      if (!courseId) return
      try {
        await api.post(`${API_BASE}/learning/feedback`, {
          course_id: Number(courseId),
          lesson_id: lessonId ? Number(lessonId) : undefined,
          feedback_type: type,
        })
        setFeedbackSubmitted(true)
        const isReport = !['helpful', 'not_helpful'].includes(type)
        toast.success(
          isReport
            ? t('toast.lessonViewer.issueReportedThankYou')
            : t('toast.lessonViewer.thanksForYourFeedback'),
        )
      } catch (err) {
        Sentry.captureException(err)
        toast.error(t('lessonViewer.unableToSubmitFeedbackPlease'))
      }
    },
    [courseId, lessonId, t],
  )

  const setQuizAnswer = useCallback(
    (questionId: number, optionIndex: number) => {
      if (quizSubmitted) return
      setQuizAnswers(prev => ({ ...prev, [questionId]: optionIndex }))
    },
    [quizSubmitted],
  )

  const handleQuizSubmit = useCallback(async () => {
    if (!lesson) return
    const answers = Object.entries(quizAnswers).map(([qId, optIdx]) => ({
      question_id: Number(qId),
      selected_option_index: optIdx,
    }))
    try {
      const result = await api.post<QuizResult>(
        `${API_BASE}/learning/lessons/${lessonId}/quiz/submit`,
        { answers },
      )
      setQuizResult(result)
      setQuizSubmitted(true)
      if (result.passed) setCompleted(true)
    } catch (err) {
      Sentry.captureException(err)
      toast.error(t('lessonViewer.unableToSubmitQuizPlease'))
    }
  }, [lesson, lessonId, quizAnswers, t])

  const resetQuiz = useCallback(() => {
    setQuizSubmitted(false)
    setQuizResult(null)
    setQuizAnswers({})
  }, [])

  const getActiveContent = useCallback((): ArticleContent | VideoContent | SandboxContent | null => {
    if (!lesson) return null
    if (activeVariant === 'default') {
      return lesson.content as ArticleContent | VideoContent | SandboxContent | null
    }
    const variant = lesson.variants.find(v => v.variant_type === activeVariant)
    return (variant?.content || lesson.content) as
      | ArticleContent
      | VideoContent
      | SandboxContent
      | null
  }, [lesson, activeVariant])

  return {
    courseId,
    lessonId,
    isAuthenticated,
    isStaffPreview,
    user,
    lesson,
    courseStructure,
    loading,
    error,
    notFound,
    completed,
    activeVariant,
    setActiveVariant,
    isBookmarked,
    feedbackSubmitted,
    quizAnswers,
    quizSubmitted,
    quizResult,
    allLessons,
    currentIndex,
    prevLesson,
    nextLesson,
    isFinalLesson,
    goToLesson,
    handleComplete,
    handleToggleBookmark,
    handleFeedback,
    setQuizAnswer,
    handleQuizSubmit,
    resetQuiz,
    getActiveContent,
  }
}
