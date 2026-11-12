/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import { useState, useEffect } from 'react'
import { Book, Clock, Users, ChevronDown, ChevronUp, CheckCircle2, AlertCircle, Loader } from 'lucide-react'
import toast from 'react-hot-toast'
import { clsx } from '@/utils/helpers'
import { useAuth } from '@/contexts/AuthContext'
import { genealogyEnrollmentApi } from '@/api/genealogy-api'
import { fetchApi } from '@/api/fetchApi'
import { useTranslation } from '@/i18n'

interface Course {
  id: number
  title: string
  description: string
  duration_minutes: number
  difficulty_level: 'beginner' | 'intermediate' | 'advanced'
  next_session_day?: string
  next_session_time?: string
  modules?: string
  prerequisites?: string
  is_active: boolean
  created_at: string
  updated_at: string
}

function CourseCard({
  course,
  isExpanded,
  onToggle,
  onEnroll,
  isEnrolling
}: {
  course: Course
  isExpanded: boolean
  onToggle: () => void
  onEnroll: (courseId: number) => void
  isEnrolling: boolean
}) {
  const difficultyColors = {
    beginner: 'text-status-success-600 dark:text-status-success-400 bg-status-success-50 dark:bg-status-success-900/20',
    intermediate: 'text-status-warning-600 dark:text-status-warning-400 bg-status-warning-50 dark:bg-status-warning-900/20',
    advanced: 'text-status-danger-600 dark:text-status-danger-400 bg-status-danger-50 dark:bg-status-danger-900/20',
  }

  const difficultyLabel = {
    beginner: 'Good starting point',
    intermediate: 'Build on basics',
    advanced: 'For experienced researchers',
  }

  // Parse modules if it's a JSON string
  let parsedModules: Array<{ title: string; duration: string; description: string; key_topics?: string[] }> = []
  if (course.modules) {
    try {
      parsedModules = JSON.parse(course.modules)
    } catch (_e) {
      parsedModules = []
    }
  }

  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm hover:shadow-md transition-shadow border border-lsc-border dark:border-earth-700">
      <button
        onClick={onToggle}
        className="w-full p-5 flex items-start gap-4 text-left hover:bg-lsc-cream/50 dark:hover:bg-earth-700/50 transition-colors"
        aria-expanded={isExpanded}
        aria-controls={`course-${course.id}`}
      >
        <div className="w-12 h-12 rounded-lg bg-lsc-rose/10 flex items-center justify-center flex-shrink-0">
          <Book className="w-6 h-6 text-lsc-rose dark:text-lsc-rose-light" aria-hidden="true" />
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream text-lg">
            {course.title}
          </h3>
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
            {course.description}
          </p>
          <div className="flex flex-wrap items-center gap-3 mt-3">
            <span className={clsx('text-xs font-medium px-2.5 py-1 rounded-full', difficultyColors[course.difficulty_level])}>
              {difficultyLabel[course.difficulty_level]}
            </span>
            <div className="flex items-center gap-1 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
              <Clock className="w-4 h-4" aria-hidden="true" />
              <span>{course.duration_minutes} minutes</span>
            </div>
            {course.next_session_day && (
              <div className="flex items-center gap-1 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                <Users className="w-4 h-4" aria-hidden="true" />
                <span>{course.next_session_day} {course.next_session_time ? `@ ${course.next_session_time}` : ''}</span>
              </div>
            )}
          </div>
        </div>
        <div className="flex-shrink-0 text-lsc-dark/70 dark:text-lsc-cream/70">
          {isExpanded ? (
            <ChevronUp className="w-5 h-5" aria-hidden="true" />
          ) : (
            <ChevronDown className="w-5 h-5" aria-hidden="true" />
          )}
        </div>
      </button>

      {isExpanded && (
        <div id={`course-${course.id}`} className="px-5 pb-5 border-t border-lsc-border dark:border-earth-700 space-y-4">
          <div>
            <h4 className="font-semibold text-lsc-dark dark:text-lsc-cream text-sm mb-3">
              What You'll Learn
            </h4>
            {parsedModules.length > 0 ? (
              <div className="space-y-3">
                {parsedModules.map((module: { title: string; duration: string; description: string; key_topics?: string[] }, idx: number) => (
                  <div key={idx} className="p-3 bg-lsc-cream/50 dark:bg-earth-700/50 rounded-lg">
                    <div className="flex items-start gap-3">
                      <CheckCircle2 className="w-5 h-5 text-status-success-600 dark:text-status-success-400 flex-shrink-0 mt-0.5" aria-hidden="true" />
                      <div className="flex-1">
                        <h5 className="font-medium text-lsc-dark dark:text-lsc-cream">
                          {module.title}
                        </h5>
                        <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                          {module.duration}
                        </p>
                        <p className="text-sm text-lsc-dark/80 dark:text-lsc-cream/80 mt-2">
                          {module.description}
                        </p>
                        {module.key_topics && module.key_topics.length > 0 && (
                          <div className="mt-2 flex flex-wrap gap-1">
                            {module.key_topics.map((topic: string, topicIdx: number) => (
                              <span
                                key={topicIdx}
                                className="text-xs bg-lsc-rose/10 text-lsc-rose dark:text-lsc-rose-light px-2 py-1 rounded"
                              >
                                {topic}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                No modules available at this time.
              </p>
            )}
          </div>

          <div className="pt-2 border-t border-lsc-border dark:border-earth-700">
            <button
              onClick={() => onEnroll(course.id)}
              disabled={isEnrolling}
              className={clsx(
                'inline-flex items-center justify-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-lsc-rose focus:ring-offset-2 dark:focus:ring-offset-earth-800',
                isEnrolling
                  ? 'bg-lsc-rose/50 text-white cursor-not-allowed'
                  : 'bg-lsc-rose hover:bg-lsc-rose/90 text-white'
              )}
              aria-busy={isEnrolling}
            >
              {isEnrolling && <Loader className="w-4 h-4 motion-safe:animate-spin" aria-hidden="true" />}
              {isEnrolling ? 'Enrolling...' : 'Enroll in Course'}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

export default function GenealogyTrainingPage(): React.ReactElement {
  const { t } = useTranslation()
  const [courses, setCourses] = useState<Course[]>([])
  const [expandedCourse, setExpandedCourse] = useState<number | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [enrollingCourse, setEnrollingCourse] = useState<number | null>(null)
  const { isAuthenticated } = useAuth()

  useEffect(() => {
    const loadCourses = async () => {
      try {
        const data = await fetchApi('/genealogy/courses')
        setCourses(data)
      } catch (error: unknown) {
        Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
        toast.error(t('genealogyTraining.failedToLoadCourses'))
        setCourses([])
      } finally {
        setIsLoading(false)
      }
    }

    loadCourses()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const handleEnroll = async (courseId: number) => {
    if (!isAuthenticated) {
      toast.error(t('genealogyTraining.pleaseLogInToEnroll'))
      return
    }

    setEnrollingCourse(courseId)
    try {
      await genealogyEnrollmentApi.enroll(courseId)

      toast.success(t('genealogyTraining.successfullyEnrolledInCourse'))
    } catch (error: unknown) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
      const message = error instanceof Error
        ? error.message
        : (error && typeof error === 'object' && 'message' in error)
          ? String((error as Record<string, unknown>).message)
          : 'Failed to enroll in course'
      toast.error(message)
    } finally {
      setEnrollingCourse(null)
    }
  }

  return (
    <div className="space-y-8 max-w-4xl mx-auto">
      {/* Header */}
      <div className="text-center space-y-3">
        <h1 className="text-3xl md:text-4xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
          Genealogy Research Training
        </h1>
        <p className="text-lg text-lsc-dark/70 dark:text-lsc-cream/70">
          Learn the fundamentals of family history research through our structured courses.
        </p>
      </div>

      {/* Key Information */}
      <div className="bg-earth-50 dark:bg-earth-800/20 border border-lsc-border dark:border-earth-700 rounded-xl p-5 flex gap-4">
        <AlertCircle className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light flex-shrink-0 mt-0.5" aria-hidden="true" />
        <div className="text-sm">
          <p className="font-medium text-earth-900 dark:text-earth-200 mb-2">
            Getting Started
          </p>
          <ul className="space-y-1 text-earth-800 dark:text-lsc-rose-light/80 list-disc list-inside">
            <li>
              All courses are <strong>free</strong> for library cardholders
            </li>
            <li>
              Start with <strong>{t('genealogyTraining.gettingStartedWithGenealogy')}</strong> if you're new
            </li>
            <li>
              No computer experience needed-we'll show you everything
            </li>
            <li>
              Questions during class? Ask anytime-no such thing as a silly question
            </li>
          </ul>
        </div>
      </div>

      {/* Course List */}
      <div>
        <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-4">
          Available Courses
        </h2>

        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader className="w-6 h-6 motion-safe:animate-spin text-lsc-rose" aria-hidden="true" />
            <span className="ml-3 text-lsc-dark/70 dark:text-lsc-cream/70">Loading courses...</span>
          </div>
        ) : courses.length > 0 ? (
          <div className="space-y-3">
            {courses.map(course => (
              <CourseCard
                key={course.id}
                course={course}
                isExpanded={expandedCourse === course.id}
                onToggle={() => setExpandedCourse(expandedCourse === course.id ? null : course.id)}
                onEnroll={handleEnroll}
                isEnrolling={enrollingCourse === course.id}
              />
            ))}
          </div>
        ) : (
          <div className="text-center py-8 text-lsc-dark/70 dark:text-lsc-cream/70">
            <p>{t('genealogyTraining.noCoursesAvailableYetCheck')}</p>
          </div>
        )}
      </div>

      {/* Registration Info */}
      <div className="bg-lsc-cream dark:bg-lsc-brown/30 rounded-xl p-6 border border-lsc-border dark:border-earth-700">
        <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream text-lg mb-3">
          How to Register
        </h3>
        <ol className="space-y-3 text-lsc-dark/80 dark:text-lsc-cream/80 list-decimal list-inside">
          <li>{t('genealogyTraining.chooseACourseThatInterests')}</li>
          <li>{t('genealogyTraining.clickEnrollInCourse')}</li>
          <li>{t('genealogyTraining.contactPatriciaWilliamsOurGenealogy')}</li>
          <li>{t('genealogyTraining.attendDuringTheScheduledTime')}</li>
          <li>{t('genealogyTraining.bringQuestionsAndNotebookComputer')}</li>
        </ol>
      </div>

      {/* Contact Genealogist */}
      <div className="bg-lsc-rose/5 border border-lsc-rose/30 rounded-xl p-6 text-center">
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
          Have questions before registering? Need a different time?
        </p>
        <a
          href="/genealogy/ask-genealogist"
          className="inline-flex items-center gap-2 px-6 py-3 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-lg font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-lsc-rose focus:ring-offset-2 dark:focus:ring-offset-earth-800"
        >
          Ask a Genealogist
        </a>
      </div>
    </div>
  )
}
