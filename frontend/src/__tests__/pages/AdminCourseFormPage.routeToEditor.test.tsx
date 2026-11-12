/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/// <reference types="vitest/globals" />
/// <reference types="@testing-library/jest-dom/vitest" />
import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { vi, describe, it, expect, beforeEach } from 'vitest'

// AdminShell pulls in AuthContext + Preferences + sidebar config.
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

// Stable i18n -- string `t` so any t(...) call returns its first arg.
const { stableI18n } = vi.hoisted(() => {
  const t = (key: string, fallback?: string | Record<string, unknown>) =>
    typeof fallback === 'string' ? fallback : key
  const setLanguage = () => {}
  return {
    stableI18n: { t, language: 'en', setLanguage, isRTL: false },
  }
})
vi.mock('@/i18n', () => ({
  useTranslation: () => stableI18n,
}))

vi.mock('../../components/ConfirmDialog', () => ({
  default: () => null,
}))
vi.mock('@/components/ConfirmDialog', () => ({
  default: () => null,
}))

// Heavy section components — stub minimally. CourseOutlineRail surfaces
// onAddLesson and onSelectLesson so we can click Add/Edit buttons.
vi.mock('../../components/training/CourseDetailsSection', () => ({
  default: ({
    formData,
    onUpdate,
  }: {
    formData: { title: string }
    onUpdate: (field: string, value: unknown) => void
  }) => (
    <div>
      <label htmlFor="title">Title</label>
      <input
        id="title"
        value={formData.title}
        onChange={(e) => onUpdate('title', e.target.value)}
      />
    </div>
  ),
}))
vi.mock('../../components/training/PrerequisitesSection', () => ({
  default: () => <div data-testid="prereq-section" />,
}))
vi.mock('../../components/training/CourseOutlineRail', () => ({
  default: ({
    modules,
    onAddLesson,
    onSelectLesson,
  }: {
    modules: Array<{
      id?: number
      title: string
      lessons: Array<{ id?: number; title: string }>
    }>
    onAddLesson: (moduleId: number) => void
    onSelectLesson: (lessonId: number) => void
  }) => (
    <div data-testid="course-outline-rail">
      {modules.map((m, mIdx) => (
        <div key={m.id ?? `m-${mIdx}`}>
          {m.lessons.map((l, lIdx) => (
            <button
              key={l.id ?? `l-${lIdx}`}
              type="button"
              onClick={() => l.id !== undefined && onSelectLesson(l.id)}
              aria-label={`Edit lesson: ${l.title}`}
            >
              Edit lesson {l.title}
            </button>
          ))}
          <button
            type="button"
            onClick={() => m.id !== undefined && onAddLesson(m.id)}
          >
            Add lesson
          </button>
        </div>
      ))}
    </div>
  ),
}))

// WhatsMissingPanel
vi.mock('@/components/training/WhatsMissingPanel', () => ({
  default: () => <div data-testid="whats-missing-stub" />,
}))

// Stub the autosave bar so we don't have to care about its inner state.
vi.mock('../../components/training/CourseSaveStatusBar', () => ({
  default: () => null,
}))

// LessonEditorPanel is now rendered inline; stub it so we can assert its
// presence without needing TipTap or media upload machinery.
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

// Mock courses-api: keep real exports, override createStubLesson +
// getCourseStageHistory (the latter fires unconditionally on edit mount).
vi.mock('@/api/domains/learning/courses-api', async () => {
  const actual = await vi.importActual<
    typeof import('@/api/domains/learning/courses-api')
  >('@/api/domains/learning/courses-api')
  return {
    ...actual,
    createStubLesson: vi.fn(),
    getCourseStageHistory: vi.fn().mockResolvedValue([]),
  }
})

// Mock api (used by AdminCourseFormPage to load the course + courses list).
const { apiMock } = vi.hoisted(() => ({
  apiMock: {
    get: vi.fn(),
    put: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}))
vi.mock('@/api/api', () => ({
  default: apiMock,
  api: apiMock,
}))
vi.mock('../../api/api', () => ({
  default: apiMock,
  api: apiMock,
}))

vi.mock('react-hot-toast', () => ({
  default: { success: vi.fn(), error: vi.fn() },
  toast: { success: vi.fn(), error: vi.fn() },
}))

import AdminCourseFormPage from '@/pages/AdminCourseFormPage'
import * as coursesApi from '@/api/domains/learning/courses-api'

// Seeded course: one saved module (id 7) holding one saved lesson (id 200).
const COURSE_FIXTURE = {
  id: 42,
  title: 'Genealogy 101',
  description: 'Tracing your roots',
  thumbnail_url: '',
  access_level: 'patron',
  difficulty: 'beginner',
  estimated_minutes: 60,
  sensory_warning: '',
  quiz_passing_threshold: 70,
  prerequisite_course_ids: [],
  modules: [
    {
      id: 7,
      title: 'Sources',
      description: '',
      sort_order: 0,
      lessons: [
        {
          id: 200,
          title: 'Census records',
          lesson_type: 'article',
          content: { body: '' },
          sort_order: 0,
        },
      ],
    },
  ],
}

function setupGetMocks() {
  apiMock.get.mockImplementation((url: string) => {
    if (url.includes('/learning/courses/42')) return Promise.resolve(COURSE_FIXTURE)
    if (url.endsWith('/learning/courses')) return Promise.resolve({ items: [] })
    return Promise.resolve({})
  })
}

const renderEdit = (id = '42') => render(
  <MemoryRouter initialEntries={[`/staff/admin/courses/${id}/edit`]}>
    <Routes>
      <Route path="/staff/admin/courses/:id/edit" element={<AdminCourseFormPage />} />
    </Routes>
  </MemoryRouter>,
)

describe('AdminCourseFormPage route-to-editor (W2-A)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    apiMock.get.mockReset()
    apiMock.put.mockReset()
    apiMock.post.mockReset()
    vi.mocked(coursesApi.createStubLesson).mockReset()
    setupGetMocks()
    apiMock.put.mockResolvedValue({})
  })

  it('"+ Add lesson" creates a stub and opens the inline lesson panel', async () => {
    vi.mocked(coursesApi.createStubLesson).mockResolvedValue({
      id: 999,
      module_id: 7,
      title: '',
      lesson_type: 'article',
      content: { body: '' },
      sort_order: 3,
    } as never)
    renderEdit()
    const addBtn = await screen.findByRole('button', { name: /Add lesson/i })
    fireEvent.click(addBtn)
    // Add lesson now opens the lesson-template picker (E2) before creating
    // a stub — see AdminCourseFormPage.tsx's templatePickerModuleId/
    // LessonTemplatePicker. Pick "Blank" to proceed with the old stub flow.
    const blankTemplateBtn = await screen.findByRole('button', { name: /^Blank$/i })
    fireEvent.click(blankTemplateBtn)
    await waitFor(() =>
      expect(coursesApi.createStubLesson).toHaveBeenCalledWith(7),
    )
    // The inline panel should appear with the stub's lesson id.
    await waitFor(() =>
      expect(screen.getByTestId('lesson-editor-panel')).toHaveAttribute(
        'data-lesson-id',
        '999',
      ),
    )
  })

  it('does NOT render the old LessonFormModal', async () => {
    renderEdit()
    // Wait for the page to finish loading the course fixture.
    await screen.findByRole('button', { name: /Add lesson/i })
    expect(screen.queryByTestId('lesson-form-modal')).toBeNull()
    // The old modal title hook was the H3 "Add Lesson" / "Edit Lesson"
    // header inside a role=dialog. Make sure no dialog is rendered.
    expect(screen.queryByRole('dialog')).toBeNull()
  })

  it('clicking an existing lesson Edit opens the inline panel with that lesson id', async () => {
    renderEdit()
    const editBtn = await screen.findByRole('button', {
      name: /Edit lesson: Census records/i,
    })
    fireEvent.click(editBtn)
    // Existing lesson id is 200 in the fixture.
    await waitFor(() =>
      expect(screen.getByTestId('lesson-editor-panel')).toHaveAttribute(
        'data-lesson-id',
        '200',
      ),
    )
    // No stub should have been created — Edit on a saved lesson is a
    // pure selection, not a stub creation.
    expect(coursesApi.createStubLesson).not.toHaveBeenCalled()
  })

  it('on stub creation failure, surfaces error inline (not a toast)', async () => {
    vi.mocked(coursesApi.createStubLesson).mockRejectedValue(
      new Error('Network error'),
    )
    renderEdit()
    const addBtn = await screen.findByRole('button', { name: /Add lesson/i })
    fireEvent.click(addBtn)
    const blankTemplateBtn = await screen.findByRole('button', { name: /^Blank$/i })
    fireEvent.click(blankTemplateBtn)
    await waitFor(() => {
      expect(screen.getByText(/Could not create lesson/i)).toBeInTheDocument()
    })
    // And no error toast was raised.
    const toastModule = await import('react-hot-toast')
    expect(
      (toastModule.default as unknown as { error: ReturnType<typeof vi.fn> }).error,
    ).not.toHaveBeenCalled()
  })
})
