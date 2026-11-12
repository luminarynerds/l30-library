/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * Locks the POST body shape sent by the family-challenge register button.
 * The page previously sent {schoolId, familyName, studentAge} to an endpoint
 * expecting {parent_user_id, child_user_id, ...}; every click 422'd.
 * This test pins the request body to the new contract.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import FamilyReadingChallengesPage from '../FamilyReadingChallengesPage'

// ---- Mocks --------------------------------------------------------------

vi.mock('react-hot-toast', () => ({
  default: {
    success: vi.fn(),
    error: vi.fn(),
  },
}))

vi.mock('@/lib/sentry-lazy', () => ({
  captureException: vi.fn(),
}))

vi.mock('../../i18n/I18nContext', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}))

vi.mock('@/components/ui/ModalBackdrop', () => ({
  ModalBackdrop: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}))

vi.mock('@/api/types', () => ({
  API_BASE: '/api/v1',
}))

// ---- Fixtures -----------------------------------------------------------

const SCHOOL = { id: '5', name: 'Test Elementary' }

const FUTURE_CHALLENGE = {
  id: '7',
  title: 'Summer Reading Challenge',
  description: 'Read together!',
  startDate: '2020-01-01',
  endDate: '2099-12-31',
  goalMinutes: 100,
  goalBooks: 5,
  targetAgeGroup: '5-10',
  theme: 'adventure',
  participantCount: 0,
  schoolId: '5',
}

function mockFetchSequence() {
  const fetchMock = vi.fn().mockImplementation((url: string, _init?: RequestInit) => {
    if (typeof url === 'string' && url.endsWith('/school-partnerships/schools')) {
      return Promise.resolve({
        ok: true,
        json: async () => ({ schools: [SCHOOL] }),
      } as Response)
    }
    if (typeof url === 'string' && url.match(/family-challenges\/[^/]+$/)) {
      return Promise.resolve({
        ok: true,
        json: async () => ({ challenges: [FUTURE_CHALLENGE] }),
      } as Response)
    }
    if (typeof url === 'string' && url.match(/family-challenges\/[^/]+\/registrations$/)) {
      return Promise.resolve({
        ok: true,
        json: async () => ({ registrations: [] }),
      } as Response)
    }
    if (typeof url === 'string' && url.match(/family-challenges\/[^/]+\/register$/)) {
      return Promise.resolve({
        ok: true,
        json: async () => ({ id: 1 }),
      } as Response)
    }
    return Promise.resolve({ ok: false, json: async () => ({}) } as Response)
  })
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

// ---- Tests --------------------------------------------------------------

describe('FamilyReadingChallengesPage register POST', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('POSTs the page shape {schoolId, familyName, studentAge}', async () => {
    const fetchMock = mockFetchSequence()

    render(
      <MemoryRouter>
        <FamilyReadingChallengesPage />
      </MemoryRouter>
    )

    // Wait for the challenge card to render (after schools + challenges fetch).
    await waitFor(() => {
      expect(screen.getByText(/Summer Reading Challenge/i)).toBeTruthy()
    })

    // Click "Join Challenge" to open modal.
    fireEvent.click(screen.getByRole('button', { name: /Join Challenge/i }))

    // Fill the modal.  The page exposes inputs without explicit a11y labels,
    // so we target by placeholder fallback if available, else by sequence.
    const inputs = document.querySelectorAll('input')
    // Find a text input for family name + a number input for age.
    let nameInput: HTMLInputElement | undefined
    let ageInput: HTMLInputElement | undefined
    inputs.forEach((el) => {
      if (el.type === 'text' && !nameInput) nameInput = el as HTMLInputElement
      else if (el.type === 'number' && !ageInput) ageInput = el as HTMLInputElement
    })
    expect(nameInput).toBeTruthy()
    expect(ageInput).toBeTruthy()
    fireEvent.change(nameInput!, { target: { value: 'The Smiths' } })
    fireEvent.change(ageInput!, { target: { value: '8' } })

    // Submit the modal.  The modal renders a button with exact text "Join"
    // (the card button is "Join Challenge"), so an exact match disambiguates.
    const submit = screen.getByRole('button', { name: /^Join$/ })
    fireEvent.click(submit)

    // Assert a fetch call was made to the register endpoint with the right body.
    await waitFor(() => {
      const calls = fetchMock.mock.calls.filter((c: unknown[]) =>
        typeof c[0] === 'string' && (c[0] as string).includes('/register')
      )
      expect(calls.length).toBeGreaterThan(0)
    })

    const registerCall = fetchMock.mock.calls.find((c: unknown[]) =>
      typeof c[0] === 'string' && (c[0] as string).includes('/register')
    )!
    const [url, init] = registerCall as [string, RequestInit]

    expect(url).toContain('/school-partnerships/family-challenges/7/register')
    expect(init.method).toBe('POST')
    const body = JSON.parse(init.body as string)
    expect(body).toEqual({
      schoolId: '5',
      familyName: 'The Smiths',
      studentAge: 8,
    })
    // Critically, the legacy fields are NOT present (so backend won't
    // mis-route to the linked-account branch).
    expect(body).not.toHaveProperty('parent_user_id')
    expect(body).not.toHaveProperty('child_user_id')
  })
})
