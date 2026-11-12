/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'

// i18n mock: return the key (or interpolate {{title}} naively) so we can assert on strings.
vi.mock('../../i18n/I18nContext', () => ({
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

vi.mock('@sentry/browser', () => ({
  captureException: vi.fn(),
}))

// sentry-lazy is a dynamic wrapper around @sentry/browser; the wrapper file
// is referenced by 192 imports but isn't checked in (see commit c0407f808).
// Stub it so test transforms can resolve the import.
vi.mock('@/lib/sentry-lazy', () => ({
  captureException: vi.fn(),
}))

vi.mock('@/components/ui/ModalBackdrop', () => ({
  ModalBackdrop: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}))

import ProfessionalDevelopmentPage from '../ProfessionalDevelopmentPage'

const SCHOOL = { id: 1, name: 'Maple Elementary' }
// Real backend wire shape (snake_case, see backend/app/schemas/reading.py
// TeacherTrainingModuleResponse). fetchApi does NOT camelCase responses.
const MODULE = {
  id: 1,
  partner_id: 1,
  title: 'Phonics Foundations',
  description: 'Intro phonics module',
  content_url: null,
  duration_minutes: 30,
  category: 'reading-strategies',
  level: 'beginner',
  is_active: true,
}
// Real completions shape: GET /training-modules/{id}/completions -> {completions:[...]}
const COMPLETION = {
  module_id: 1,
  module_title: 'Phonics Foundations',
  status: 'completed',
  started_at: '2025-09-10T00:00:00Z',
  completed_at: '2025-09-15T00:00:00Z',
  quiz_score: 83,
  passed_assessment: true,
}

// modulesBody lets a test choose the real bare-array shape vs a wrapped one.
// The live endpoint returns a bare List[TeacherTrainingModuleResponse].
function mockFetchByUrl(
  schoolsBody: unknown,
  opts: { modulesBody?: unknown; completions?: unknown[] } = {},
) {
  const modulesBody = opts.modulesBody ?? [MODULE]
  const completions = opts.completions ?? []
  return vi.spyOn(global, 'fetch').mockImplementation(async (input: RequestInfo | URL) => {
    const url = typeof input === 'string' ? input : (input as URL).toString()
    if (url.endsWith('/school-partnerships/schools')) {
      return new Response(JSON.stringify(schoolsBody), { status: 200 })
    }
    if (url.endsWith(`/school-partnerships/training-modules/${SCHOOL.id}`)) {
      return new Response(JSON.stringify(modulesBody), { status: 200 })
    }
    if (url.endsWith(`/school-partnerships/training-modules/${SCHOOL.id}/completions`)) {
      return new Response(JSON.stringify({ completions }), { status: 200 })
    }
    if (url.endsWith(`/school-partnerships/training-modules/${SCHOOL.id}/certificates`)) {
      return new Response(JSON.stringify({ certificates: [] }), { status: 200 })
    }
    return new Response(JSON.stringify({}), { status: 404 })
  })
}

describe('ProfessionalDevelopmentPage', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('loads schools + modules + completions + certificates and renders the module with an enabled Start button', async () => {
    mockFetchByUrl({ schools: [SCHOOL] })
    render(<ProfessionalDevelopmentPage />)

    // Module title eventually shows up after schools -> modules fetch chain
    await waitFor(() => {
      expect(screen.getByText('Phonics Foundations')).toBeInTheDocument()
    })

    // Start Module button rendered and enabled (no completion, so not "Completed")
    const startBtn = screen.getByRole('button', { name: /start module/i })
    expect(startBtn).toBeInTheDocument()
    expect(startBtn).not.toBeDisabled()

    // The four expected backend calls were issued
    const calls = (global.fetch as unknown as { mock: { calls: unknown[][] } }).mock.calls.map(
      (c) => (typeof c[0] === 'string' ? c[0] : String(c[0])),
    )
    expect(calls.some((u) => u.endsWith('/school-partnerships/schools'))).toBe(true)
    expect(calls.some((u) => u.endsWith(`/training-modules/${SCHOOL.id}`))).toBe(true)
    expect(calls.some((u) => u.endsWith(`/training-modules/${SCHOOL.id}/completions`))).toBe(true)
    expect(calls.some((u) => u.endsWith(`/training-modules/${SCHOOL.id}/certificates`))).toBe(true)
  })

  it('renders modules when /schools returns a bare list (backend actual shape)', async () => {
    mockFetchByUrl([SCHOOL])
    render(<ProfessionalDevelopmentPage />)

    // If the page failed to pick a school out of the bare list, modules
    // would never be fetched and "Phonics Foundations" would never render.
    await waitFor(() => {
      expect(screen.getByText('Phonics Foundations')).toBeInTheDocument()
    })

    const calls = (global.fetch as unknown as { mock: { calls: unknown[][] } }).mock.calls.map(
      (c) => (typeof c[0] === 'string' ? c[0] : String(c[0])),
    )
    expect(calls.some((u) => u.endsWith(`/training-modules/${SCHOOL.id}`))).toBe(true)
  })

  it('reflects a snake_case completion: browse status flips to Completed and the Start button disables', async () => {
    // Locks the real completions contract (module_id/status). With the old
    // camelCase reads (moduleId), this module would still show "Start Module".
    mockFetchByUrl([SCHOOL], { completions: [COMPLETION] })
    render(<ProfessionalDevelopmentPage />)

    await waitFor(() => {
      expect(screen.getByText('Phonics Foundations')).toBeInTheDocument()
    })

    expect(screen.getByText(/✓ completed/i)).toBeInTheDocument()
    const completedBtn = screen.getByRole('button', { name: /^completed$/i })
    expect(completedBtn).toBeDisabled()
    // Score read from quiz_score (not the old assessmentScore)
    expect(screen.getByText(/83%/)).toBeInTheDocument()
  })
})
