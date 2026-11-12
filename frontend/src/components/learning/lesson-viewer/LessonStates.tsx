/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Link } from 'react-router-dom'
import { BookOpen, SearchX } from 'lucide-react'
import { useTranslation } from '@/i18n'

const SHELL = 'min-h-screen bg-lsc-cream dark:bg-lsc-dark py-8 px-4'

export function UnauthenticatedState() {
  const { t } = useTranslation()
  return (
    <div className={SHELL}>
      <div className="max-w-4xl mx-auto text-center">
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-3">
          {t('lessonViewer.pleaseSignInToView', 'Sign in and enroll to read this lesson.')}
        </p>
        <Link to="/account" className="text-lsc-rose dark:text-lsc-rose-light hover:underline">
          {t('lessonViewer.signIn', 'Sign in')}
        </Link>
      </div>
    </div>
  )
}

export function LoadingState() {
  return (
    <div className={SHELL}>
      <div className="max-w-4xl mx-auto motion-safe:animate-pulse">
        <div className="h-8 bg-lsc-cream dark:bg-lsc-brown rounded w-48 mb-6"></div>
        <div className="h-96 bg-lsc-cream dark:bg-lsc-brown rounded-xl"></div>
      </div>
    </div>
  )
}

export function NotFoundState({ courseId }: { courseId?: string }) {
  return (
    <div className={SHELL}>
      <div className="max-w-2xl mx-auto text-center py-16">
        <SearchX
          aria-hidden="true"
          className="w-12 h-12 mx-auto mb-4 text-lsc-dark/50 dark:text-lsc-cream/50 opacity-50"
        />
        <h1 className="font-serif text-2xl font-bold text-lsc-dark dark:text-lsc-cream mb-2">
          Lesson not found
        </h1>
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-6">
          This lesson doesn't exist or may have been removed. The link you followed might be out of
          date.
        </p>
        <div className="flex items-center justify-center gap-3">
          {courseId && (
            <Link
              to={`/learn/course/${courseId}`}
              className="inline-flex items-center gap-2 bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-earth-700 px-4 py-2 rounded-lg font-medium"
            >
              Back to course
            </Link>
          )}
          <Link
            to="/learn/catalog"
            className="inline-flex items-center gap-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white px-4 py-2 rounded-lg font-medium"
          >
            <BookOpen aria-hidden="true" className="w-4 h-4" />
            Browse courses
          </Link>
        </div>
      </div>
    </div>
  )
}

export function ErrorState({ message }: { message: string }) {
  return (
    <div className={SHELL}>
      <div className="max-w-4xl mx-auto">
        <div className="bg-status-danger-50 dark:bg-status-danger-900/20 text-status-danger-700 dark:text-status-danger-300 px-4 py-3 rounded-xl mb-4">
          {message}
        </div>
        <Link
          to="/learn/catalog"
          className="inline-flex items-center gap-2 text-lsc-rose dark:text-lsc-rose-light hover:underline"
        >
          <BookOpen aria-hidden="true" className="w-4 h-4" />
          Browse courses
        </Link>
      </div>
    </div>
  )
}
