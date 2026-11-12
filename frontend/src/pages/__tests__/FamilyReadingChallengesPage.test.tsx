/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
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
  default: {
    success: vi.fn(),
    error: vi.fn(),
  },
}))

vi.mock('@sentry/browser', () => ({
  captureException: vi.fn(),
}))

vi.mock('@/components/ui/ModalBackdrop', () => ({
  ModalBackdrop: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}))

import FamilyReadingChallengesPage from '../FamilyReadingChallengesPage'

const SCHOOL = { id: '1', name: 'Maple Elementary' }

const CHALLENGE = {
  id: 'c-1',
  title: 'Summer Reading Sprint',
  description: 'Read together every day',
  startDate: '2026-05-01',
  endDate: '2026-12-31',
  goalMinutes: 600,
  goalBooks: 0,
  targetAgeGroup: 'parent-child',
  theme: 'parent-child',
  prizes: 'Free coffee',
  participantCount: 3,
  schoolId: '1',
}

function mockFetchByUrl(opts: {
  challenges?: unknown[]
  registrations?: unknown[]
} = {}) {
  const { challenges = [CHALLENGE], registrations = [] } = opts
  return vi.spyOn(global, 'fetch').mockImplementation(async (input: RequestInfo | URL) => {
    const url = typeof input === 'string' ? input : (input as URL).toString()
    if (url.endsWith('/school-partnerships/schools')) {
      return new Response(JSON.stringify({ schools: [SCHOOL] }), { status: 200 })
    }
    if (url.endsWith(`/school-partnerships/family-challenges/${SCHOOL.id}/registrations`)) {
      return new Response(JSON.stringify({ registrations }), { status: 200 })
    }
    if (url.endsWith(`/school-partnerships/family-challenges/${SCHOOL.id}`)) {
      return new Response(JSON.stringify({ challenges }), { status: 200 })
    }
    return new Response(JSON.stringify({}), { status: 404 })
  })
}

describe('FamilyReadingChallengesPage', () => {
  beforeEach(() => {
    mockFetchByUrl()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('loads schools then challenges + registrations and renders challenge title', async () => {
    render(<FamilyReadingChallengesPage />)

    await waitFor(() => {
      expect(screen.getByText('Summer Reading Sprint')).toBeInTheDocument()
    })

    const calls = (global.fetch as unknown as { mock: { calls: unknown[][] } }).mock.calls.map(
      (c) => (typeof c[0] === 'string' ? c[0] : String(c[0])),
    )
    expect(calls.some((u) => u.endsWith('/school-partnerships/schools'))).toBe(true)
    expect(calls.some((u) => u.endsWith(`/family-challenges/${SCHOOL.id}`))).toBe(true)
    expect(calls.some((u) => u.endsWith(`/family-challenges/${SCHOOL.id}/registrations`))).toBe(true)
  })

  it('renders empty-state when both challenges and registrations are empty', async () => {
    vi.restoreAllMocks()
    mockFetchByUrl({ challenges: [], registrations: [] })

    render(<FamilyReadingChallengesPage />)

    // Wait for the challenges fetch to settle
    await waitFor(() => {
      const calls = (global.fetch as unknown as { mock: { calls: unknown[][] } }).mock.calls.map(
        (c) => (typeof c[0] === 'string' ? c[0] : String(c[0])),
      )
      expect(calls.some((u) => u.endsWith(`/family-challenges/${SCHOOL.id}`))).toBe(true)
    })

    // Default view is 'challenges'; empty-state copy
    await waitFor(() => {
      expect(screen.getByText(/No challenges available\./i)).toBeInTheDocument()
    })
  })
})
