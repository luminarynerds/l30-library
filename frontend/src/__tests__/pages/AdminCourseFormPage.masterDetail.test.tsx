/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/// <reference types="vitest/globals" />
/// <reference types="@testing-library/jest-dom/vitest" />
import React from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { vi, describe, it, expect, beforeEach } from 'vitest'
import { axe } from 'jest-axe'

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

// ── Sentry ────────────────────────────────────────────────────────────────
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

// ── Course form sub-sections ───────────────────────────────────────────────
vi.mock('../../components/training/CourseDetailsSection', () => ({
  default: ({ formData, onUpdate }: { formData: { title: string }; onUpdate: (f: string, v: unknown) => void }) => (
    <div>
      <label htmlFor="title">Title</label>
      <input id="title" value={formData.title} onChange={(e) => onUpdate('title', e.target.value)} />
    </div>
  ),
}))
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

// ── toast ─────────────────────────────────────────────────────────────────
vi.mock('react-hot-toast', () => ({
  default: { success: vi.fn(), error: vi.fn() },
  toast: { success: vi.fn(), error: vi.fn() },
}))

// ── LessonEditorPanel: stub to avoid TipTap/media-upload machinery ─────────
vi.mock('@/components/LessonEditorPanel', () => ({
  default: ({ lessonId }: { lessonId: number }) => (
    <div data-testid="lesson-editor-panel" data-lesson-id={lessonId}>
      LESSON_PANEL lesson:{lessonId}
    </div>
  ),
}))
vi.mock('../../components/LessonEditorPanel', () => ({
  default: ({ lessonId }: { lessonId: number }) => (
    <div data-testid="lesson-editor-panel" data-lesson-id={lessonId}>
      LESSON_PANEL lesson:{lessonId}
    </div>
  ),
}))

// ── Import SUT after mocks ─────────────────────────────────────────────────
import AdminCourseFormPage from '@/pages/AdminCourseFormPage'

// ── Fixtures ───────────────────────────────────────────────────────────────
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

describe('AdminCourseFormPage master/detail', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    apiMock.get.mockImplementation((url: string) => {
      if (url.includes('/learning/courses/1')) return Promise.resolve(COURSE_FIXTURE)
      if (url.endsWith('/learning/courses')) return Promise.resolve({ items: [] })
      return Promise.resolve({})
    })
    apiMock.put.mockResolvedValue({})
  })

  it('renders the lesson panel inline when ?lesson= is present in the URL', async () => {
    renderWithRoute('/staff/admin/courses/1/edit?lesson=7')

    await waitFor(() =>
      expect(screen.getByRole('complementary', { name: /lesson editor/i })).toBeInTheDocument(),
    )

    // The stubbed panel surfaces the lesson id.
    await waitFor(() =>
      expect(screen.getByTestId('lesson-editor-panel')).toHaveAttribute(
        'data-lesson-id',
        '7',
      ),
    )
  })

  it('does not render the lesson panel when no ?lesson= param', async () => {
    renderWithRoute('/staff/admin/courses/1/edit')

    await waitFor(() =>
      expect(screen.getByTestId('course-outline-rail')).toBeInTheDocument(),
    )

    expect(screen.queryByRole('complementary', { name: /lesson editor/i })).not.toBeInTheDocument()
    expect(screen.queryByTestId('lesson-editor-panel')).not.toBeInTheDocument()
  })

  it('has no accessibility violations with lesson panel open', async () => {
    const { container } = renderWithRoute('/staff/admin/courses/1/edit?lesson=7')

    await waitFor(() =>
      expect(screen.getByTestId('lesson-editor-panel')).toBeInTheDocument(),
    )

    const results = await axe(container)
    expect(results).toHaveNoViolations()
  })
})
