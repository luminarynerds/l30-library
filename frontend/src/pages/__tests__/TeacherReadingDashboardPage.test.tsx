/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'

// i18n mock: return the key (or interpolate {{title}} naively) so we can assert.
vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string, vars?: Record<string, unknown>) => {
      if (!vars) return key
      return Object.entries(vars).reduce<string>(
        (acc, [k, v]) => acc.replace(`{{${k}}}`, String(v)),
        key,
      )
    },
  }),
}))

vi.mock('react-hot-toast', () => ({
  default: {
    success: vi.fn(),
    error: vi.fn(),
  },
}))

vi.mock('@/lib/sentry-lazy', () => ({
  captureException: vi.fn(),
}))

// Per-file override of the global AuthContext mock (setup.ts mocks user=null).
// Dashboard gates render on user + token, so without this it shows the auth
// gate instead of any data path.
const TEACHER_AUTH = {
  user: { id: 7, role: 'teacher', school_id: 1 },
  token: 'test-token',
}
type MockAuth = { user: { id: number; role: string; school_id?: number }; token: string }
let mockAuth: MockAuth = TEACHER_AUTH
vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => mockAuth,
}))

const mockFetchApi = vi.fn()
vi.mock('@/api/fetchApi', () => ({
  fetchApi: (path: string) => mockFetchApi(path),
}))

// Import after mocks
import TeacherReadingDashboardPage from '../TeacherReadingDashboardPage'

const DASHBOARD = {
  school_id: 1,
  school_name: 'Maple Elementary',
  active_programs_count: 3,
  student_registration_count: 42,
  total_reading_activity: 100,
  total_minutes_read: 1200,
  total_books_read: 88,
  school_badges: [],
  recent_activity_count: 5,
}

const PROGRAM_ACTIVE = {
  id: 11,
  name: 'Spring Reading Sprint',
  description: 'Curated for spring unit',
  program_type: 'reading',
  curriculum_alignment: 'Language Arts',
  grade_levels: ['3rd', '4th'],
  reading_levels: ['AR 3.0-4.0'],
  start_date: '2026-03-01',
  end_date: '2026-06-01',
  is_active: true,
}

const PROGRAM_COMPLETED = {
  id: 12,
  name: 'Winter Wonders',
  description: 'Winter-themed reading',
  program_type: 'reading',
  curriculum_alignment: 'SEL',
  grade_levels: ['2nd'],
  reading_levels: ['AR 2.0-3.0'],
  start_date: '2025-12-01',
  end_date: '2026-02-28',
  is_active: false,
}

const BADGE = {
  id: 1,
  badge_name: 'Reading Champion',
  badge_description: 'Read 30 minutes daily',
  threshold_type: 'minutes',
  threshold_value: 30,
  is_active: true,
  created_at: '2026-01-01T00:00:00Z',
}

function renderPage(initialEntries: string[] = ['/']) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <MemoryRouter initialEntries={initialEntries}>
      <QueryClientProvider client={qc}>
        <TeacherReadingDashboardPage />
      </QueryClientProvider>
    </MemoryRouter>,
  )
}

describe('TeacherReadingDashboardPage', () => {
  beforeEach(() => {
    mockFetchApi.mockReset()
    mockAuth = TEACHER_AUTH
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('renders a loading state before the dashboard query resolves', () => {
    // Never-resolving promise: keeps both queries in loading state.
    mockFetchApi.mockImplementation(() => new Promise(() => {}))

    renderPage()

    expect(screen.getByText(/Loading dashboard/i)).toBeInTheDocument()
  })

  it('renders the friendly 403 notice when the dashboard endpoint forbids access', async () => {
    mockFetchApi.mockImplementation((path: string) => {
      if (path.includes('/teacher-dashboard/')) {
        return Promise.reject({ status: 403, message: 'forbidden' })
      }
      // Programs/badges resolve so we land on the 403 branch rather than loading.
      return Promise.resolve([])
    })

    renderPage()

    await waitFor(() => {
      expect(screen.getByText(/Dashboard not available/i)).toBeInTheDocument()
    })
    expect(
      screen.getByText(/This dashboard is for a school you/i),
    ).toBeInTheDocument()
  })

  it('renders empty-state copy when programs and badges are empty', async () => {
    mockFetchApi.mockImplementation((path: string) => {
      if (path.includes('/teacher-dashboard/')) return Promise.resolve(DASHBOARD)
      if (path.endsWith('/programs')) return Promise.resolve([])
      if (path.endsWith('/badges')) return Promise.resolve([])
      return Promise.resolve({})
    })

    renderPage()

    await waitFor(() => {
      expect(screen.getByText('Maple Elementary')).toBeInTheDocument()
    })

    // Programs empty-state (translation key surfaces because we mock t to identity)
    expect(
      screen.getByText('teacherReadingDashboard.noReadingProgramsFoundCreate'),
    ).toBeInTheDocument()

    // Badges empty-state copy
    expect(
      screen.getByText(/No badges created yet/i),
    ).toBeInTheDocument()
  })

  it('renders dashboard metrics, programs, and badges from the API', async () => {
    mockFetchApi.mockImplementation((path: string) => {
      if (path.includes('/teacher-dashboard/')) return Promise.resolve(DASHBOARD)
      if (path.endsWith('/programs')) {
        return Promise.resolve([PROGRAM_ACTIVE, PROGRAM_COMPLETED])
      }
      if (path.endsWith('/badges')) return Promise.resolve([BADGE])
      return Promise.resolve({})
    })

    renderPage()

    // Both programs render
    await waitFor(() => {
      expect(screen.getByText('Spring Reading Sprint')).toBeInTheDocument()
    })
    expect(screen.getByText('Winter Wonders')).toBeInTheDocument()

    // School name in header
    expect(screen.getByText('Maple Elementary')).toBeInTheDocument()

    // Metric labels + a few key numbers
    expect(screen.getByText('Active Programs')).toBeInTheDocument()
    expect(screen.getByText('Students Registered')).toBeInTheDocument()
    expect(screen.getByText('42')).toBeInTheDocument() // student_registration_count
    expect(screen.getByText('1200')).toBeInTheDocument() // total_minutes_read

    // Badge name from sidebar
    expect(screen.getByText('Reading Champion')).toBeInTheDocument()

    // All three expected endpoints were hit (teacher dashboard, programs, badges)
    const calls = mockFetchApi.mock.calls.map((c) => c[0] as string)
    expect(calls.some((u) => u.includes('/teacher-dashboard/1'))).toBe(true)
    expect(calls.some((u) => u.endsWith('/schools/1/programs'))).toBe(true)
    expect(calls.some((u) => u.endsWith('/schools/1/badges'))).toBe(true)
  })

  it('filters programs to active-only when the "Active" filter is clicked', async () => {
    mockFetchApi.mockImplementation((path: string) => {
      if (path.includes('/teacher-dashboard/')) return Promise.resolve(DASHBOARD)
      if (path.endsWith('/programs')) {
        return Promise.resolve([PROGRAM_ACTIVE, PROGRAM_COMPLETED])
      }
      if (path.endsWith('/badges')) return Promise.resolve([])
      return Promise.resolve({})
    })

    renderPage()

    // Wait for both programs to render under the default "all" filter
    await waitFor(() => {
      expect(screen.getByText('Spring Reading Sprint')).toBeInTheDocument()
    })
    expect(screen.getByText('Winter Wonders')).toBeInTheDocument()

    // Click the "Active" filter pill
    fireEvent.click(screen.getByRole('button', { name: /^Active$/i }))

    // Completed program is hidden; active one stays
    await waitFor(() => {
      expect(screen.queryByText('Winter Wonders')).not.toBeInTheDocument()
    })
    expect(screen.getByText('Spring Reading Sprint')).toBeInTheDocument()
  })

  it('renders a school picker for staff and defaults to the first school (no || 1 fallback)', async () => {
    mockAuth = { user: { id: 99, role: 'staff' }, token: 'test-token' }

    const SCHOOLS = [
      { id: 7, name: 'Maple Elementary' },
      { id: 9, name: 'Oak Middle School' },
    ]

    mockFetchApi.mockImplementation((path: string) => {
      if (path.endsWith('/school-partnerships/schools')) {
        return Promise.resolve(SCHOOLS)
      }
      if (path.includes('/teacher-dashboard/')) return Promise.resolve(DASHBOARD)
      if (path.endsWith('/programs')) return Promise.resolve([PROGRAM_ACTIVE])
      if (path.endsWith('/badges')) return Promise.resolve([])
      return Promise.resolve({})
    })

    renderPage()

    // Picker shows up labelled "School:" with both options
    await waitFor(() => {
      expect(screen.getByLabelText(/School:/i)).toBeInTheDocument()
    })
    const picker = screen.getByLabelText(/School:/i) as HTMLSelectElement
    expect(picker.value).toBe('7') // first school in list, NOT a hardcoded || 1

    // Both schools are options
    expect(screen.getByRole('option', { name: 'Maple Elementary' })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: 'Oak Middle School' })).toBeInTheDocument()

    // Downstream queries used the picked school id (7), not 1.
    await waitFor(() => {
      const calls = mockFetchApi.mock.calls.map((c) => c[0] as string)
      expect(calls.some((u) => u.includes('/teacher-dashboard/7'))).toBe(true)
      expect(calls.some((u) => u.endsWith('/schools/7/programs'))).toBe(true)
    })
    const calls = mockFetchApi.mock.calls.map((c) => c[0] as string)
    expect(calls.every((u) => !u.includes('/teacher-dashboard/1'))).toBe(true)
  })

  it('reads ?school_id= from the URL for staff/admin instead of defaulting to first', async () => {
    mockAuth = { user: { id: 99, role: 'admin' }, token: 'test-token' }
    const SCHOOLS = [
      { id: 7, name: 'Maple Elementary' },
      { id: 9, name: 'Oak Middle School' },
    ]
    mockFetchApi.mockImplementation((path: string) => {
      if (path.endsWith('/school-partnerships/schools')) return Promise.resolve(SCHOOLS)
      if (path.includes('/teacher-dashboard/')) return Promise.resolve(DASHBOARD)
      if (path.endsWith('/programs')) return Promise.resolve([])
      if (path.endsWith('/badges')) return Promise.resolve([])
      return Promise.resolve({})
    })

    renderPage(['/?school_id=9'])

    await waitFor(() => {
      const picker = screen.getByLabelText(/School:/i) as HTMLSelectElement
      expect(picker.value).toBe('9')
    })
    await waitFor(() => {
      const calls = mockFetchApi.mock.calls.map((c) => c[0] as string)
      expect(calls.some((u) => u.includes('/teacher-dashboard/9'))).toBe(true)
    })
  })

  it('does NOT render the school picker for teachers (pinned to user.school_id)', async () => {
    // mockAuth defaults to TEACHER_AUTH (role: 'teacher', school_id: 1)
    mockFetchApi.mockImplementation((path: string) => {
      if (path.includes('/teacher-dashboard/')) return Promise.resolve(DASHBOARD)
      if (path.endsWith('/programs')) return Promise.resolve([])
      if (path.endsWith('/badges')) return Promise.resolve([])
      return Promise.resolve({})
    })

    renderPage()

    await waitFor(() => {
      expect(screen.getByText('Maple Elementary')).toBeInTheDocument()
    })

    expect(screen.queryByLabelText(/School:/i)).not.toBeInTheDocument()
    // Schools list endpoint should not have been called for teachers.
    const calls = mockFetchApi.mock.calls.map((c) => c[0] as string)
    expect(calls.every((u) => !u.endsWith('/school-partnerships/schools'))).toBe(true)
  })
})
