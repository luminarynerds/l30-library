/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/// <reference types="vitest/globals" />
import React from 'react'
import { render, screen, waitFor, fireEvent, act } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'

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
  xp_reward: 100,
  duration_days: 30,
  prerequisite_course_ids: [],
  modules: [],
}

function renderEditPage() {
  return render(
    <MemoryRouter initialEntries={['/staff/admin/courses/42/edit']}>
      <Routes>
        <Route path="/staff/admin/courses/:id/edit" element={<AdminCourseFormPage />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('AdminCourseFormPage fields', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    apiMock.get.mockImplementation((url: string) => {
      if (url.includes('/learning/courses/42')) return Promise.resolve(COURSE_FIXTURE)
      if (url.endsWith('/learning/courses')) return Promise.resolve({ items: [] })
      return Promise.resolve({})
    })
    apiMock.put.mockResolvedValue({})
  })

  it('renders the XP reward input', async () => {
    renderEditPage()
    await waitFor(() => {
      // Throws if not found — that IS the assertion.
      screen.getByDisplayValue('Genealogy 101')
    })
    expect(screen.getByRole('spinbutton', { name: /xp reward/i })).toBeDefined()
  })

  it('renders the Duration (days) input', async () => {
    renderEditPage()
    await waitFor(() => {
      screen.getByDisplayValue('Genealogy 101')
    })
    expect(screen.getByRole('spinbutton', { name: /duration.*days/i })).toBeDefined()
  })

})

function renderNewPage() {
  return render(
    <MemoryRouter initialEntries={['/staff/admin/courses/new']}>
      <Routes>
        <Route path="/staff/admin/courses/:id" element={<AdminCourseFormPage />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('AdminCourseFormPage xp_reward fallback', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    apiMock.get.mockResolvedValue({ items: [] })
    apiMock.post.mockResolvedValue({})
  })

  it('sends xp_reward: 100 when XP field is cleared before submit', async () => {
    renderNewPage()

    // Wait for the form to settle (available-courses GET resolves).
    await waitFor(() => {
      expect(screen.getByRole('spinbutton', { name: /xp reward/i })).toBeDefined()
    })

    // Fill required title field.
    const titleInput = screen.getByLabelText(/course title/i)
    fireEvent.change(titleInput, { target: { value: 'Test Course' } })

    // Clear XP reward — simulates user deleting the default value.
    const xpInput = screen.getByRole('spinbutton', { name: /xp reward/i })
    fireEvent.change(xpInput, { target: { value: '' } })

    // Submit the form.
    await act(async () => {
      fireEvent.submit(screen.getByRole('button', { name: /create course/i }).closest('form')!)
    })

    await waitFor(() => {
      expect(apiMock.post).toHaveBeenCalled()
    })

    const [, payload] = apiMock.post.mock.calls[0] as [string, Record<string, unknown>]
    expect(payload.xp_reward).toBe(100)
  })
})
