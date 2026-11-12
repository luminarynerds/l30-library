/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * Shape-tolerance regression test for /api/v1/school-partnerships/schools.
 *
 * Backend route responds with `response_model=List[dict]` -- a bare array.
 * Several teacher pages were doing `data.schools || []` and silently
 * rendering empty school dropdowns. The fixed code accepts both shapes:
 *
 *   const list = Array.isArray(data) ? data : (data?.schools ?? [])
 *
 * These tests prove each affected page renders the school option under
 * both the bare-list (real backend) and wrapped (defensive future) shapes.
 */
import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'

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
  default: { success: vi.fn(), error: vi.fn() },
}))

vi.mock('@sentry/browser', () => ({
  captureException: vi.fn(),
}))

// sentry-lazy file isn't checked in but is referenced; stub for transform.
vi.mock('@/lib/sentry-lazy', () => ({
  captureException: vi.fn(),
}))

vi.mock('@/components/ui/ModalBackdrop', () => ({
  ModalBackdrop: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}))

import LibraryVisitSchedulingPage from '../LibraryVisitSchedulingPage'
import FamilyReadingChallengesPage from '../FamilyReadingChallengesPage'
import TeacherReadingListsPage from '../TeacherReadingListsPage'

// NOTE: PartnershipTierManagementPage and LibrarianConsultationPage share
// the same shape-tolerance fix but render schools inside AdminShell / wider
// flows that need auth context. The fix is mechanically identical to the
// pages exercised here; covering 3 representative consumers + the existing
// ProfessionalDevelopmentPage test is sufficient regression coverage.

const SCHOOL = { id: '1', name: 'Maple Elementary' }

function mockFetch(schoolsBody: unknown) {
  return vi.spyOn(global, 'fetch').mockImplementation(async (input: RequestInfo | URL) => {
    const url = typeof input === 'string' ? input : (input as URL).toString()
    // The exact-list endpoint we are exercising the shape contract for.
    if (url.endsWith('/school-partnerships/schools')) {
      return new Response(JSON.stringify(schoolsBody), { status: 200 })
    }
    // Everything else: return an empty wrapper so downstream effects
    // don't blow up. Pages render their school dropdown regardless of
    // these results because the dropdown is bound to the schools state.
    return new Response(JSON.stringify({}), { status: 200 })
  })
}

afterEach(() => {
  vi.restoreAllMocks()
})

describe.each([
  ['bare list (backend actual)', [SCHOOL]],
  ['wrapped { schools: [...] }', { schools: [SCHOOL] }],
])('schools dropdown tolerates %s', (_label, body) => {
  it('LibraryVisitSchedulingPage renders the school option', async () => {
    mockFetch(body)
    render(<LibraryVisitSchedulingPage />)
    await waitFor(() => {
      expect(screen.getByRole('option', { name: 'Maple Elementary' })).toBeInTheDocument()
    })
  })

  it('FamilyReadingChallengesPage renders the school option', async () => {
    mockFetch(body)
    render(<FamilyReadingChallengesPage />)
    await waitFor(() => {
      expect(screen.getByRole('option', { name: 'Maple Elementary' })).toBeInTheDocument()
    })
  })

  it('TeacherReadingListsPage renders the school option', async () => {
    mockFetch(body)
    render(<TeacherReadingListsPage />)
    await waitFor(() => {
      expect(screen.getByRole('option', { name: 'Maple Elementary' })).toBeInTheDocument()
    })
  })
})
