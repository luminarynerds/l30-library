/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/// <reference types="@testing-library/jest-dom/vitest" />
import React from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, it, expect, vi, beforeEach } from 'vitest'

// ── Shell ──────────────────────────────────────────────────────────────────
vi.mock('@/components/shells', () => ({
  AdminShell: ({
    title,
    loading,
    children,
  }: {
    title?: string
    loading?: boolean
    children: React.ReactNode
  }) => (
    <div data-testid="admin-shell">
      {title ? <h1>{title}</h1> : null}
      {loading ? <div data-testid="admin-shell-loading">Loading...</div> : children}
    </div>
  ),
}))

// ── Sentry ─────────────────────────────────────────────────────────────────
vi.mock('@/lib/sentry-lazy', () => ({
  init: vi.fn(),
  captureException: vi.fn(),
  captureMessage: vi.fn(),
  addBreadcrumb: vi.fn(),
}))

// ── i18n (stable refs so useEffect dep arrays don't loop) ─────────────────
const { stableI18n } = vi.hoisted(() => {
  const t = (key: string, fallback?: string | Record<string, unknown>) =>
    typeof fallback === 'string' ? fallback : key
  return {
    stableI18n: { t, language: 'en', setLanguage: () => {}, isRTL: false },
  }
})
vi.mock('@/i18n', () => ({
  useTranslation: () => stableI18n,
}))

// ── Dialogs ───────────────────────────────────────────────────────────────
vi.mock('../../components/ConfirmDialog', () => ({ default: () => null }))
vi.mock('@/components/ConfirmDialog', () => ({ default: () => null }))

// ── CourseDetailsSection: stub that includes recognizable heading text ──────
vi.mock('../../components/training/CourseDetailsSection', () => ({
  default: ({ formData }: { formData: { title: string } }) => (
    <div data-testid="course-details-section">
      <h2>Course Details</h2>
      <span>{formData.title}</span>
    </div>
  ),
}))

// ── Other course form sub-sections ─────────────────────────────────────────
vi.mock('../../components/training/PrerequisitesSection', () => ({
  default: () => <div data-testid="prereq-section" />,
}))
vi.mock('../../components/training/CourseOutlineRail', () => ({
  default: () => <div data-testid="course-outline-rail" />,
}))
vi.mock('@/components/training/WhatsMissingPanel', () => ({
  default: () => <div data-testid="whats-missing-stub" />,
}))
vi.mock('../../components/training/CourseSaveStatusBar', () => ({
  default: () => null,
}))

// ── LessonEditorPanel: stub that includes recognisable text ────────────────
vi.mock('@/components/LessonEditorPanel', () => ({
  default: ({ lessonId }: { lessonId: number }) => (
    <div data-testid="lesson-editor-panel" data-lesson-id={lessonId}>
      <h2>Edit lesson</h2>
      <input aria-label="Lesson title" defaultValue="Intro" />
    </div>
  ),
}))
vi.mock('../../components/LessonEditorPanel', () => ({
  default: ({ lessonId }: { lessonId: number }) => (
    <div data-testid="lesson-editor-panel" data-lesson-id={lessonId}>
      <h2>Edit lesson</h2>
      <input aria-label="Lesson title" defaultValue="Intro" />
    </div>
  ),
}))

// ── courses-api ────────────────────────────────────────────────────────────
vi.mock('@/api/domains/learning/courses-api', () => ({
  getCourseStageHistory: vi.fn().mockResolvedValue([]),
  createStubLesson: vi.fn(),
}))

// ── api mock ───────────────────────────────────────────────────────────────
const { apiMock } = vi.hoisted(() => ({
  apiMock: {
    get: vi.fn(),
    put: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}))
vi.mock('@/api/api', () => ({ default: apiMock, api: apiMock }))
vi.mock('../../api/api', () => ({ default: apiMock, api: apiMock }))
vi.mock('../../api/api', () => ({ default: apiMock, api: apiMock }))

// ── toast ──────────────────────────────────────────────────────────────────
vi.mock('react-hot-toast', () => ({
  default: { success: vi.fn(), error: vi.fn() },
  toast: { success: vi.fn(), error: vi.fn() },
}))

// ── Import SUT after mocks ─────────────────────────────────────────────────
import AdminCourseFormPage from '@/pages/AdminCourseFormPage'

// ── Fixture ────────────────────────────────────────────────────────────────
const COURSE_FIXTURE = {
  id: 1,
  title: 'Test Course',
  description: '',
  thumbnail_url: '',
  access_level: 'patron',
  difficulty: 'beginner',
  estimated_minutes: null,
  sensory_warning: '',
  quiz_passing_threshold: 70,
  prerequisite_course_ids: [],
  xp_reward: 100,
  duration_days: null,
  modules: [],
}

function renderWithRoute(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/staff/admin/courses/:id/edit" element={<AdminCourseFormPage />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('AdminCourseFormPage two-zone', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    apiMock.get.mockImplementation((url: string) => {
      if (url.includes('/learning/courses/1')) return Promise.resolve(COURSE_FIXTURE)
      if (url.endsWith('/learning/courses')) return Promise.resolve({ items: [] })
      return Promise.resolve({})
    })
    apiMock.put.mockResolvedValue({})
  })

  it('shows course settings (not a lesson) when no lesson is selected', async () => {
    renderWithRoute('/staff/admin/courses/1/edit')
    expect(await screen.findByText(/course details/i)).toBeInTheDocument()
    expect(screen.queryByTestId('lesson-editor-panel')).not.toBeInTheDocument()
  })

  it('shows the lesson (not the course details form) when a lesson is selected', async () => {
    renderWithRoute('/staff/admin/courses/1/edit?lesson=7')
    await waitFor(() =>
      expect(screen.getByTestId('lesson-editor-panel')).toBeInTheDocument(),
    )
    expect(screen.queryByTestId('course-details-section')).not.toBeInTheDocument()
  })

  it('WhatsMissingPanel is not rendered as a column in the main layout', async () => {
    renderWithRoute('/staff/admin/courses/1/edit')
    // Wait for page to load
    await screen.findByText(/course details/i)
    // WhatsMissingPanel stub must not be present in the layout
    expect(screen.queryByTestId('whats-missing-stub')).not.toBeInTheDocument()
  })

  it('no <form> is nested inside another <form> when a lesson is selected', async () => {
    renderWithRoute('/staff/admin/courses/1/edit?lesson=7')
    await waitFor(() =>
      expect(screen.getByTestId('lesson-editor-panel')).toBeInTheDocument(),
    )
    // Every <form> in the document must not have a <form> ancestor.
    const forms = document.querySelectorAll('form')
    forms.forEach((form) => {
      expect(form.parentElement?.closest('form')).toBeNull()
    })
  })
})
