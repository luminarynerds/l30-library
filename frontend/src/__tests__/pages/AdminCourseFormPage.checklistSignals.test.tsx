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

// ── CourseDetailsSection stub ──────────────────────────────────────────────
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
vi.mock('../../components/training/CourseSaveStatusBar', () => ({
  default: () => null,
}))

// ── LessonEditorPanel stub ────────────────────────────────────────────────
vi.mock('@/components/LessonEditorPanel', () => ({
  default: ({ lessonId }: { lessonId: number }) => (
    <div data-testid="lesson-editor-panel" data-lesson-id={lessonId}>
      <h2>Edit lesson</h2>
    </div>
  ),
}))
vi.mock('../../components/LessonEditorPanel', () => ({
  default: ({ lessonId }: { lessonId: number }) => (
    <div data-testid="lesson-editor-panel" data-lesson-id={lessonId}>
      <h2>Edit lesson</h2>
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

import AdminCourseFormPage from '@/pages/AdminCourseFormPage'

// ── Fixture: course with a video lesson missing video_url ─────────────────
const COURSE_FIXTURE = {
  id: 5,
  title: 'AI in Libraries',
  description: '',
  thumbnail_url: '',  // missing thumbnail -> 1 course issue
  access_level: 'patron',
  difficulty: 'beginner',
  estimated_minutes: null,
  sensory_warning: '',
  quiz_passing_threshold: 70,
  prerequisite_course_ids: [],
  xp_reward: 100,
  duration_days: null,
  modules: [
    {
      id: 10,
      title: 'Module 1',
      sort_order: 0,
      lessons: [
        {
          id: 20,
          title: 'AI in Libraries',
          lesson_type: 'video',
          sort_order: 0,
          content: { video_url: '', transcript: '' },  // missing video_url + transcript -> 2 lesson issues
          estimated_minutes: null,
          sensory_notes: '',
        },
      ],
    },
  ],
}

function renderEditPage() {
  return render(
    <MemoryRouter initialEntries={['/staff/admin/courses/5/edit']}>
      <Routes>
        <Route path="/staff/admin/courses/:id/edit" element={<AdminCourseFormPage />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('AdminCourseFormPage checklist signals', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
    apiMock.get.mockImplementation((url: string) => {
      if (url.includes('/learning/courses/5')) return Promise.resolve(COURSE_FIXTURE)
      if (url.endsWith('/learning/courses')) return Promise.resolve({ items: [] })
      return Promise.resolve({})
    })
    apiMock.put.mockResolvedValue({})
  })

  it('renders a header badge button showing "N to finish" when issues exist', async () => {
    renderEditPage()
    // Wait for the course to load
    await screen.findByTestId('course-details-section')
    // Total issues: 1 thumbnail + 1 video_url + 1 transcript = 3
    // Badge should show total count
    const badge = await screen.findByRole('button', { name: /\d+ to finish/i })
    expect(badge).toBeInTheDocument()
  })

  it('badge count reflects total open issues', async () => {
    renderEditPage()
    await screen.findByTestId('course-details-section')
    const badge = await screen.findByRole('button', { name: /to finish/i })
    // 3 issues: missing thumbnail, missing video_url, missing transcript
    expect(badge).toHaveAccessibleName(expect.stringMatching(/3 to finish/i))
  })

  it('WhatsMissingPanel is not visible by default (it opens on badge click)', async () => {
    renderEditPage()
    await screen.findByTestId('course-details-section')
    // The panel content heading should not be visible until badge is clicked
    // We look for the distinctive "things to finish" heading inside the panel
    await waitFor(() => {
      expect(screen.queryByText(/3 thing/i)).not.toBeInTheDocument()
    })
  })

  it("badge count drops when a dismissed issue key is pre-seeded in localStorage", async () => {
    // localStorage is a vi.fn() mock (see src/__tests__/setup.ts).
    // Configure getItem to return the dismissed map for courseId 5 so
    // getDismissedIssueKeys picks it up when the component mounts.
    const dismissedJson = JSON.stringify({ course_missing_thumbnail: true })
    vi.spyOn(localStorage, "getItem").mockImplementation((key: string) =>
      key === "lsc_authoring_dismissed_5" ? dismissedJson : null,
    )

    renderEditPage()
    await screen.findByTestId("course-details-section")

    // With one dismissed, only 2 remain -> badge reads "2 to finish"
    const badge = await screen.findByRole("button", { name: /to finish/i })
    expect(badge).toHaveAccessibleName(expect.stringMatching(/2 to finish/i))
  })
})
