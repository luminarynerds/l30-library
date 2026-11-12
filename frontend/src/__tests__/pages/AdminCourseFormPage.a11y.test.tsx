/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * A11y gate for the two-zone course editor.
 * Asserts axe cleanliness in both course-view and lesson-view.
 */
/// <reference types="@testing-library/jest-dom/vitest" />
import React from 'react'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { configureAxe } from 'jest-axe'

// ── Axe config: skip color-contrast (no real CSS in jsdom) ────────────────
const axeWithConfig = configureAxe({
  rules: {
    'color-contrast': { enabled: false },
  },
})

// ── Shell: renders h1 from title prop, mirrors real AdminShell ─────────────
vi.mock('@/components/shells', () => ({
  AdminShell: ({
    title,
    actions,
    loading,
    children,
  }: {
    title?: string
    actions?: React.ReactNode
    loading?: boolean
    children: React.ReactNode
  }) => (
    <div data-testid="admin-shell">
      {title ? <h1>{title}</h1> : null}
      {actions}
      {loading ? <div data-testid="admin-shell-loading">Loading...</div> : children}
    </div>
  ),
}))

vi.mock('@/lib/sentry-lazy', () => ({
  init: vi.fn(),
  captureException: vi.fn(),
  captureMessage: vi.fn(),
  addBreadcrumb: vi.fn(),
}))

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

vi.mock('../../components/ConfirmDialog', () => ({ default: () => null }))
vi.mock('@/components/ConfirmDialog', () => ({ default: () => null }))

// CourseDetailsSection: labelled section + h2 + labelled input (no axe violations)
vi.mock('../../components/training/CourseDetailsSection', () => ({
  default: ({ formData }: { formData: { title: string } }) => (
    <section aria-labelledby="cds-heading">
      <h2 id="cds-heading">Course Details</h2>
      <label htmlFor="course-title-input">Course title</label>
      <input id="course-title-input" type="text" defaultValue={formData.title} />
    </section>
  ),
}))

vi.mock('../../components/training/PrerequisitesSection', () => ({
  default: () => <div data-testid="prereq-section" />,
}))

// CourseOutlineRail: provides a nav with h2 and labelled buttons
vi.mock('../../components/training/CourseOutlineRail', () => ({
  default: ({
    courseTitle,
    onSelectCourse,
  }: {
    courseTitle: string
    onSelectCourse: () => void
  }) => (
    <nav aria-label="Course outline">
      <h2>Course outline</h2>
      <button type="button" onClick={onSelectCourse} aria-current="true">
        {courseTitle}
      </button>
    </nav>
  ),
}))

vi.mock('@/components/training/WhatsMissingPanel', () => ({
  default: () => <div data-testid="whats-missing-stub" />,
}))

vi.mock('../../components/training/CourseSaveStatusBar', () => ({
  default: () => (
    <div role="status" aria-live="polite">
      Saved
    </div>
  ),
}))

// LessonEditorPanel: labelled section + h2 + labelled input
vi.mock('@/components/LessonEditorPanel', () => ({
  default: ({ lessonId }: { lessonId: number }) => (
    <section aria-labelledby="lep-heading">
      <h2 id="lep-heading">Lesson editor</h2>
      <label htmlFor="lesson-title-input">Lesson title</label>
      <input
        id="lesson-title-input"
        type="text"
        data-lesson-id={lessonId}
        defaultValue="Intro"
      />
    </section>
  ),
}))
vi.mock('../../components/LessonEditorPanel', () => ({
  default: ({ lessonId }: { lessonId: number }) => (
    <section aria-labelledby="lep-heading">
      <h2 id="lep-heading">Lesson editor</h2>
      <label htmlFor="lesson-title-input">Lesson title</label>
      <input
        id="lesson-title-input"
        type="text"
        data-lesson-id={lessonId}
        defaultValue="Intro"
      />
    </section>
  ),
}))

vi.mock('@/api/domains/learning/courses-api', () => ({
  getCourseStageHistory: vi.fn().mockResolvedValue([]),
  createStubLesson: vi.fn(),
}))

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

vi.mock('react-hot-toast', () => ({
  default: { success: vi.fn(), error: vi.fn() },
  toast: { success: vi.fn(), error: vi.fn() },
}))

import AdminCourseFormPage from '@/pages/AdminCourseFormPage'

const COURSE_FIXTURE = {
  id: 1,
  title: 'Test Course',
  description: '',
  thumbnail_url: 'https://example.com/thumb.jpg',
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

describe('AdminCourseFormPage a11y', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    apiMock.get.mockImplementation((url: string) => {
      if (url.includes('/learning/courses/1')) return Promise.resolve(COURSE_FIXTURE)
      if (url.endsWith('/learning/courses')) return Promise.resolve({ items: [] })
      return Promise.resolve({})
    })
    apiMock.put.mockResolvedValue({})
  })

  it('(course-view) has no axe violations', async () => {
    const { container } = renderWithRoute('/staff/admin/courses/1/edit')
    await screen.findByText(/course details/i)
    const results = await axeWithConfig(container)
    expect(results).toHaveNoViolations()
  })

  it('(course-view) has exactly one h1', async () => {
    renderWithRoute('/staff/admin/courses/1/edit')
    await screen.findByText(/course details/i)
    const h1s = document.querySelectorAll('h1')
    expect(h1s).toHaveLength(1)
  })

  it('(lesson-view) has no axe violations', async () => {
    const { container } = renderWithRoute('/staff/admin/courses/1/edit?lesson=7')
    // Wait for the lesson panel to appear by looking for the labelled input
    await screen.findByLabelText(/lesson title/i)
    const results = await axeWithConfig(container)
    expect(results).toHaveNoViolations()
  })

  it('(lesson-view) has exactly one h1', async () => {
    renderWithRoute('/staff/admin/courses/1/edit?lesson=7')
    await screen.findByLabelText(/lesson title/i)
    const h1s = document.querySelectorAll('h1')
    expect(h1s).toHaveLength(1)
  })
})
