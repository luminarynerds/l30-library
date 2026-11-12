/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/// <reference types="vitest/globals" />
/// <reference types="@testing-library/jest-dom/vitest" />
import React from 'react'
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { expect } from 'vitest'

// AdminShell pulls in AuthContext + Preferences + sidebar config.
// Pass-through so the test focuses on the autosave bar.
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

// `t` and the returned translation object must be stable references — any
// useEffect with `t` in its deps array will loop forever otherwise.
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

// ConfirmDialog pulls in UnifiedAccessibilityProvider; stub it out.
vi.mock('../../components/ConfirmDialog', () => ({
  default: () => null,
}))
vi.mock('@/components/ConfirmDialog', () => ({
  default: () => null,
}))

// Heavy section components are not the SUT; stub to keep test focused on autosave.
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
  default: () => <div data-testid="course-outline-rail" />,
}))

// Stage history panel does its own GET on mount; stub it.
vi.mock('@/api/domains/learning/courses-api', () => ({
  getCourseStageHistory: vi.fn().mockResolvedValue([]),
}))

// Mock api with overridable get/put/post.
// Must use vi.hoisted because vi.mock factories are hoisted above imports.
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

// react-hot-toast — silence error toasts in tests; we assert inline state, not toasts.
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

function setupGetMocks() {
  apiMock.get.mockImplementation((url: string) => {
    if (url.includes('/learning/courses/42')) return Promise.resolve(COURSE_FIXTURE)
    if (url.endsWith('/learning/courses')) return Promise.resolve({ items: [] })
    return Promise.resolve({})
  })
}

// Render + wait for course data to be loaded (uses real timers for the wait,
// then the caller switches to fake timers).
async function setupLoaded() {
  setupGetMocks()
  apiMock.put.mockResolvedValue({})
  renderEditPage()
  await waitFor(() => {
    expect(screen.getByDisplayValue('Genealogy 101')).toBeInTheDocument()
  })
}

describe('AdminCourseFormPage autosave', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    apiMock.get.mockReset()
    apiMock.put.mockReset()
    apiMock.post.mockReset()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('shows "Writing..." during debounce then "Saved <time>" after success', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    await setupLoaded()

    const titleInput = screen.getByDisplayValue('Genealogy 101')
    fireEvent.change(titleInput, { target: { value: 'Genealogy 101 (revised)' } })

    // Writing state appears immediately on change.
    await waitFor(() => {
      expect(screen.getByTestId('course-save-status')).toHaveTextContent(/Writing/i)
    })

    // Advance past 2s debounce -> save fires.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(2100)
    })

    await waitFor(() => {
      expect(apiMock.put).toHaveBeenCalledWith(
        expect.stringContaining('/learning/courses/42'),
        expect.objectContaining({ title: 'Genealogy 101 (revised)' }),
      )
    })

    await waitFor(() => {
      expect(screen.getByTestId('course-save-status')).toHaveTextContent(/Saved/i)
    })
  })

  it('ticks the relative timestamp every 30s', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    await setupLoaded()

    const titleInput = screen.getByDisplayValue('Genealogy 101')
    fireEvent.change(titleInput, { target: { value: 'Edited' } })
    await act(async () => {
      await vi.advanceTimersByTimeAsync(2100)
    })

    await waitFor(() => {
      expect(screen.getByTestId('course-save-status')).toHaveTextContent(/Saved/i)
    })

    // Initially "just now" / "0..9 seconds".
    expect(screen.getByTestId('course-save-status')).toHaveTextContent(/just now|seconds ago/i)

    // Advance 31s — relative label should reflect ~30s, not stay at "just now".
    await act(async () => {
      await vi.advanceTimersByTimeAsync(31_000)
    })

    expect(screen.getByTestId('course-save-status')).toHaveTextContent(/30 seconds ago|31 seconds ago|seconds ago/i)
  })

  it('shows the absolute clock time for clock-blindness mitigation', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    // Pin "now" to a known clock time so we can assert the rendered timestamp.
    vi.setSystemTime(new Date('2026-05-24T14:14:00'))

    await setupLoaded()

    const titleInput = screen.getByDisplayValue('Genealogy 101')
    fireEvent.change(titleInput, { target: { value: 'Pinned-time edit' } })
    await act(async () => {
      await vi.advanceTimersByTimeAsync(2100)
    })

    await waitFor(() => {
      expect(screen.getByTestId('course-save-status')).toHaveTextContent(/Saved/i)
    })

    // Absolute clock time of the save instant must appear (~2:14 PM,
    // accept any locale variant of 2:14).
    expect(screen.getByTestId('course-save-status')).toHaveTextContent(/2:14/)
  })

  it('Cmd-S triggers an immediate save', async () => {
    await setupLoaded()

    // Cmd-S (mac) — should fire a save even without debounce / before changes.
    const evt = new KeyboardEvent('keydown', {
      key: 's',
      metaKey: true,
      bubbles: true,
      cancelable: true,
    })
    await act(async () => {
      window.dispatchEvent(evt)
    })

    await waitFor(() => {
      expect(apiMock.put).toHaveBeenCalled()
    })
    expect(evt.defaultPrevented).toBe(true)
  })

  it('on 4xx, surfaces validation error inline and stops autosave until field changes', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    apiMock.get.mockImplementation((url: string) => {
      if (url.includes('/learning/courses/42')) return Promise.resolve(COURSE_FIXTURE)
      if (url.endsWith('/learning/courses')) return Promise.resolve({ items: [] })
      return Promise.resolve({})
    })
    // First put -> 422 with detail.
    const apiError = Object.assign(new Error('Validation failed'), {
      status: 422,
      detail: 'Title too short',
      body: { detail: 'Title too short' },
    })
    apiMock.put.mockRejectedValueOnce(apiError).mockResolvedValue({})
    renderEditPage()
    await waitFor(() => expect(screen.getByDisplayValue('Genealogy 101')).toBeInTheDocument())

    const titleInput = screen.getByDisplayValue('Genealogy 101')
    fireEvent.change(titleInput, { target: { value: 'X' } })
    await act(async () => {
      await vi.advanceTimersByTimeAsync(2100)
    })

    await waitFor(() => {
      expect(screen.getByTestId('course-save-status')).toHaveTextContent(/Title too short|Validation error/i)
    })

    const callsAfterError = apiMock.put.mock.calls.length

    // Wait another full debounce without changing the field — autosave must NOT fire again.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(5_000)
    })
    expect(apiMock.put).toHaveBeenCalledTimes(callsAfterError)

    // Now mutate the field — autosave should resume.
    fireEvent.change(titleInput, { target: { value: 'Genealogy 102' } })
    await act(async () => {
      await vi.advanceTimersByTimeAsync(2100)
    })
    await waitFor(() => {
      expect(apiMock.put.mock.calls.length).toBeGreaterThan(callsAfterError)
    })
  })

  it('on 5xx, shows "Last save failed - retrying" (not a toast)', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    apiMock.get.mockImplementation((url: string) => {
      if (url.includes('/learning/courses/42')) return Promise.resolve(COURSE_FIXTURE)
      if (url.endsWith('/learning/courses')) return Promise.resolve({ items: [] })
      return Promise.resolve({})
    })
    const apiError = Object.assign(new Error('Server crash'), {
      status: 500,
      detail: 'Server crash',
    })
    apiMock.put.mockRejectedValue(apiError)
    renderEditPage()
    await waitFor(() => expect(screen.getByDisplayValue('Genealogy 101')).toBeInTheDocument())

    const titleInput = screen.getByDisplayValue('Genealogy 101')
    fireEvent.change(titleInput, { target: { value: 'Edited' } })
    await act(async () => {
      await vi.advanceTimersByTimeAsync(2100)
    })

    await waitFor(() => {
      expect(screen.getByTestId('course-save-status')).toHaveTextContent(/Last save failed.*retrying/i)
    })

    // The toast.error import was mocked; confirm no error toast was raised
    // for autosave 5xx (the bar carries the message, not a toast).
    const toastModule = await import('react-hot-toast')
    expect(
      (toastModule.default as unknown as { error: ReturnType<typeof vi.fn> }).error,
    ).not.toHaveBeenCalled()
  })

  it('Pause autosave toggle prevents new saves until resumed', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    await setupLoaded()

    // Pause.
    fireEvent.click(screen.getByRole('button', { name: /pause autosave/i }))

    const titleInput = screen.getByDisplayValue('Genealogy 101')
    fireEvent.change(titleInput, { target: { value: 'Paused edit' } })
    await act(async () => {
      await vi.advanceTimersByTimeAsync(2500)
    })
    expect(apiMock.put).not.toHaveBeenCalled()

    // Resume.
    fireEvent.click(screen.getByRole('button', { name: /resume autosave/i }))
    fireEvent.change(titleInput, { target: { value: 'Resumed edit' } })
    await act(async () => {
      await vi.advanceTimersByTimeAsync(2100)
    })
    await waitFor(() => {
      expect(apiMock.put).toHaveBeenCalled()
    })
  })

  it('attaches a beforeunload guard while writing/saving is in flight', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    // Hold the put open so we observe in-flight 'saving' state.
    let resolvePut: (v: unknown) => void = () => {}
    apiMock.get.mockImplementation((url: string) => {
      if (url.includes('/learning/courses/42')) return Promise.resolve(COURSE_FIXTURE)
      if (url.endsWith('/learning/courses')) return Promise.resolve({ items: [] })
      return Promise.resolve({})
    })
    apiMock.put.mockImplementation(
      () => new Promise((resolve) => { resolvePut = resolve }),
    )
    renderEditPage()
    await waitFor(() => expect(screen.getByDisplayValue('Genealogy 101')).toBeInTheDocument())

    const titleInput = screen.getByDisplayValue('Genealogy 101')
    fireEvent.change(titleInput, { target: { value: 'In-flight' } })

    // Writing immediately (during debounce) should already arm the guard.
    const writingEvent = new Event('beforeunload', { cancelable: true }) as BeforeUnloadEvent
    await act(async () => {
      window.dispatchEvent(writingEvent)
    })
    expect(writingEvent.defaultPrevented).toBe(true)

    // Resolve the in-flight save -> status returns to saved, guard releases.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(2100)
    })
    await act(async () => {
      resolvePut({})
      await Promise.resolve()
    })

    await waitFor(() => {
      expect(screen.getByTestId('course-save-status')).toHaveTextContent(/Saved/i)
    })

    const idleEvent = new Event('beforeunload', { cancelable: true }) as BeforeUnloadEvent
    await act(async () => {
      window.dispatchEvent(idleEvent)
    })
    expect(idleEvent.defaultPrevented).toBe(false)
  })

  it('renders save status in a role="status" aria-live region with no standalone Save button at idle', async () => {
    await setupLoaded()

    // The status element must carry the live region role so screen readers
    // announce state changes without focus movement.
    const statusEl = screen.getByTestId('course-save-status')
    expect(statusEl).toHaveAttribute('role', 'status')
    expect(statusEl).toHaveAttribute('aria-live', 'polite')

    // After the ambient redesign the prominent "Save" button is removed from
    // the status bar entirely — only a Retry affordance appears on failure.
    // A standalone "Save now" button must NOT be present at idle state.
    expect(screen.queryByRole('button', { name: /save now/i })).not.toBeInTheDocument()
  })

  it('exposes a Retry button (not just toast) when save status is failed-retry', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    apiMock.get.mockImplementation((url: string) => {
      if (url.includes('/learning/courses/42')) return Promise.resolve(COURSE_FIXTURE)
      if (url.endsWith('/learning/courses')) return Promise.resolve({ items: [] })
      return Promise.resolve({})
    })
    const apiError = Object.assign(new Error('Server crash'), {
      status: 500,
      detail: 'Server crash',
    })
    apiMock.put.mockRejectedValue(apiError)
    renderEditPage()
    await waitFor(() => expect(screen.getByDisplayValue('Genealogy 101')).toBeInTheDocument())

    const titleInput = screen.getByDisplayValue('Genealogy 101')
    fireEvent.change(titleInput, { target: { value: 'Edited for retry test' } })
    await act(async () => {
      await vi.advanceTimersByTimeAsync(2100)
    })

    await waitFor(() => {
      expect(screen.getByTestId('course-save-status')).toHaveTextContent(/Last save failed.*retrying/i)
    })

    // An inline Retry button must be reachable by keyboard users — not hidden
    // behind a toast or requiring a page reload.
    expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument()
  })
})
