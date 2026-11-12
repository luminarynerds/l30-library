/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

// i18n: passthrough. We assert wiring, not translations.
vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string, params?: Record<string, unknown>) => {
      if (!params) return key
      let out = key
      for (const [k, v] of Object.entries(params)) {
        out = out.split(`{${k}}`).join(String(v))
      }
      return out
    },
  }),
  useLanguage: () => ({ language: 'en', setLanguage: vi.fn(), isRTL: false }),
}))

vi.mock('@/lib/sentry-lazy', () => ({
  captureException: vi.fn(),
  captureMessage: vi.fn(),
}))

vi.mock('react-hot-toast', () => ({
  default: { success: vi.fn(), error: vi.fn() },
}))

// AdminShell wraps the page; stub so we don't need its providers.
vi.mock('../components/shells/AdminShell', () => ({
  AdminShell: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="admin-shell">{children}</div>
  ),
}))

// Mock the API: one available session.
const mockList = vi.fn()
const mockRegister = vi.fn()
const mockRoster = vi.fn()
const mockUpdate = vi.fn()
const mockCreate = vi.fn()
vi.mock('@/api/parent-onboarding-api', () => ({
  listChildcareSessions: (...args: unknown[]) => mockList(...args),
  registerForChildcare: (...args: unknown[]) => mockRegister(...args),
  getChildcareRoster: (...args: unknown[]) => mockRoster(...args),
  updateChildcareRegistration: (...args: unknown[]) => mockUpdate(...args),
  createChildcareSession: (...args: unknown[]) => mockCreate(...args),
}))

// Mock the branches API. The page uses listBranches to resolve branch
// names for card headings + filter dropdown + create-modal select.
const mockBranches = vi.fn()
vi.mock('@/api/branch-api', () => ({
  listBranches: (...args: unknown[]) => mockBranches(...args),
}))

// Default: patron user. Tests that need a staff user override via
// vi.mocked(useAuth).mockReturnValue(...).
vi.mock('@/contexts/AuthContext', () => ({
  useAuth: vi.fn(() => ({
    user: { id: 1, role: 'patron', email: 'p@example.com' },
    isAuthenticated: true,
  })),
}))

// Default: pickup_authorization_enabled OFF. Tests that need it on
// override via vi.mocked(useOrganizationFeatures).mockReturnValue(...).
vi.mock('@/contexts/OrganizationFeaturesContext', () => ({
  useOrganizationFeatures: vi.fn(() => ({
    features: null,
    loading: false,
    isFeatureEnabled: (_: string) => false,
    fetchFeatures: vi.fn(),
  })),
}))

// Stub the staff modal so the existing a11y tests don't need to mock its
// internals; the dedicated StaffChildcareCheckoutModal.test.tsx covers it.
vi.mock('../components/staff/parent-onboarding/StaffChildcareCheckoutModal', () => ({
  default: ({ open, registration }: { open: boolean; registration: { id: number } }) =>
    open ? <div data-testid="staff-checkout-modal" data-reg-id={registration.id} /> : null,
}))

import { MemoryRouter } from 'react-router-dom'
import ChildcarePage from './ChildcarePage'
import { useAuth } from '@/contexts/AuthContext'
import { useOrganizationFeatures } from '@/contexts/OrganizationFeaturesContext'

// Shape matches the corrected `ChildcareSession` interface (which now
// mirrors the backend `ChildcareSessionResponse`). The old shape had
// fictional `name` / `location` / `capacity` fields the backend never
// returned -- see comment in parent-onboarding-api.ts.
const session = {
  id: 7,
  branch_id: 1,
  room_id: null,
  staff_id: null,
  date: '2026-06-02',
  start_time: '10:00',
  end_time: '11:30',
  max_children: 8,
  age_range_min_months: 24,
  age_range_max_months: 60,
  registered_count: 2,
  status: 'available' as const,
  created_at: '2026-06-01T00:00:00Z',
}

function renderPage(opts: { initialEntry?: string } = {}) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <MemoryRouter initialEntries={[opts.initialEntry ?? '/staff/parent-onboarding/childcare']}>
      <QueryClientProvider client={client}>
        <ChildcarePage />
      </QueryClientProvider>
    </MemoryRouter>
  )
}

async function openModal() {
  renderPage()
  const registerBtn = await screen.findByRole('button', { name: /Register/i })
  fireEvent.click(registerBtn)
  return await screen.findByRole('dialog')
}

describe('ChildcarePage a11y', () => {
  beforeEach(() => {
    mockList.mockReset()
    mockRegister.mockReset()
    mockBranches.mockReset()
    mockList.mockResolvedValue({ sessions: [session] })
    // Default: an empty branch list -- the existing a11y tests don't care
    // about branch names; the new filter tests below override this.
    mockBranches.mockResolvedValue([])
    // Reset auth + features back to PATRON defaults (the staff-suite
    // overrides them; without this reset, the second-run a11y tests
    // inherited staff context).
    vi.mocked(useAuth).mockReturnValue({
      user: { id: 1, role: 'patron', email: 'p@example.com' },
      isAuthenticated: true,
    } as unknown as ReturnType<typeof useAuth>)
    vi.mocked(useOrganizationFeatures).mockReturnValue({
      features: null,
      loading: false,
      isFeatureEnabled: () => false,
      fetchFeatures: vi.fn(),
    } as unknown as ReturnType<typeof useOrganizationFeatures>)
  })

  it('wires every form input to its label via htmlFor/id', async () => {
    await openModal()

    // getByLabelText fails if the label is not associated to the input.
    // These calls are the assertion.
    const childName = screen.getByLabelText(/Child Name/i) as HTMLInputElement
    const childAgeYears = screen.getByLabelText(/Child Age \(in years\)/i) as HTMLInputElement
    const ecName = screen.getByLabelText(/Emergency Contact Name/i) as HTMLInputElement
    const ecPhone = screen.getByLabelText(/Emergency Contact Phone/i) as HTMLInputElement
    const allergies = screen.getByLabelText(/Allergies/i) as HTMLInputElement
    const specialNeeds = screen.getByLabelText(/Special Needs/i) as HTMLTextAreaElement

    expect(childName.tagName).toBe('INPUT')
    expect(childAgeYears.tagName).toBe('INPUT')
    expect(ecName.tagName).toBe('INPUT')
    expect(ecPhone.tagName).toBe('INPUT')
    expect(allergies.tagName).toBe('INPUT')
    expect(specialNeeds.tagName).toBe('TEXTAREA')

    // Every input/textarea should have a non-empty id (proves label htmlFor target exists).
    expect(childName.id).not.toBe('')
    expect(specialNeeds.id).not.toBe('')
  })

  it('marks required fields with aria-required and switches age to numeric input mode', async () => {
    await openModal()

    const childName = screen.getByLabelText(/Child Name/i)
    const childAgeYears = screen.getByLabelText(/Child Age \(in years\)/i)
    const ecName = screen.getByLabelText(/Emergency Contact Name/i)
    const ecPhone = screen.getByLabelText(/Emergency Contact Phone/i)
    const allergies = screen.getByLabelText(/Allergies/i)

    expect(childName.getAttribute('aria-required')).toBe('true')
    expect(childAgeYears.getAttribute('aria-required')).toBe('true')
    expect(ecName.getAttribute('aria-required')).toBe('true')
    expect(ecPhone.getAttribute('aria-required')).toBe('true')

    // Optional fields must NOT claim required.
    expect(allergies.getAttribute('aria-required')).not.toBe('true')

    // Age: text + inputMode="numeric" (NOT type="number" — avoids scroll-change gotcha).
    expect(childAgeYears.getAttribute('type')).toBe('text')
    expect(childAgeYears.getAttribute('inputmode')).toBe('numeric')
  })

  it('shows inline error text with role="alert" and links aria-describedby when a required field is empty', async () => {
    await openModal()

    // aria-invalid defaults to false before submit attempt.
    expect(screen.getByLabelText(/Child Name/i).getAttribute('aria-invalid')).toBe('false')

    // Submit empty form -> validation kicks in.
    const submit = screen.getAllByRole('button', { name: /Register/i }).pop()!
    fireEvent.click(submit)

    await waitFor(() => {
      expect(screen.getByLabelText(/Child Name/i).getAttribute('aria-invalid')).toBe('true')
    })

    // Inline error nodes should exist with role=alert.
    const alerts = screen.getAllByRole('alert')
    expect(alerts.length).toBeGreaterThanOrEqual(4)

    // aria-describedby on the invalid field must point at an id that exists in the DOM.
    const childName = screen.getByLabelText(/Child Name/i) as HTMLInputElement
    const describedBy = childName.getAttribute('aria-describedby')
    expect(describedBy).toBeTruthy()
    expect(document.getElementById(describedBy!)).not.toBeNull()
    expect(document.getElementById(describedBy!)?.getAttribute('role')).toBe('alert')
  })

  it('clears the per-field error after a valid retry', async () => {
    await openModal()
    const submit = screen.getAllByRole('button', { name: /Register/i }).pop()!
    fireEvent.click(submit)

    await waitFor(() => {
      expect(screen.getByLabelText(/Child Name/i).getAttribute('aria-invalid')).toBe('true')
    })

    mockRegister.mockResolvedValue({})

    fireEvent.change(screen.getByLabelText(/Child Name/i), { target: { value: 'Alex' } })
    fireEvent.change(screen.getByLabelText(/Child Age \(in years\)/i), { target: { value: '3' } })
    fireEvent.change(screen.getByLabelText(/Emergency Contact Name/i), { target: { value: 'Jamie' } })
    fireEvent.change(screen.getByLabelText(/Emergency Contact Phone/i), { target: { value: '555-0100' } })

    fireEvent.click(submit)

    await waitFor(() => {
      expect(mockRegister).toHaveBeenCalledTimes(1)
    })
    // Regression guard: backend expects `child_age_months` (0-60), not the
    // hand-typed years value. Form collects years, client converts.
    // See ChildcareRegistrationCreate in app/schemas/parent_onboarding.py.
    expect(mockRegister).toHaveBeenCalledWith(7, expect.objectContaining({
      child_name: 'Alex',
      child_age_months: 36, // 3 years * 12
      emergency_contact_name: 'Jamie',
      emergency_contact_phone: '555-0100',
    }))
    // Belt-and-braces: never resurrect the old field name (would 422 on
    // backend's StrictInputSchema/extra=forbid).
    const callArgs = mockRegister.mock.calls[0]![1]
    expect(callArgs).not.toHaveProperty('child_age')
    expect(callArgs).not.toHaveProperty('allergies')
    expect(callArgs).not.toHaveProperty('special_needs')
  })

  it('rejects ages over 5 years inline (backend caps child_age_months at 60)', async () => {
    await openModal()

    fireEvent.change(screen.getByLabelText(/Child Name/i), { target: { value: 'Alex' } })
    fireEvent.change(screen.getByLabelText(/Child Age \(in years\)/i), { target: { value: '7' } })
    fireEvent.change(screen.getByLabelText(/Emergency Contact Name/i), { target: { value: 'Jamie' } })
    fireEvent.change(screen.getByLabelText(/Emergency Contact Phone/i), { target: { value: '555-0100' } })

    const submit = screen.getAllByRole('button', { name: /Register/i }).pop()!
    fireEvent.click(submit)

    await waitFor(() => {
      expect(screen.getByLabelText(/Child Age \(in years\)/i).getAttribute('aria-invalid')).toBe('true')
    })
    expect(mockRegister).not.toHaveBeenCalled()
  })

  it('folds the allergies input into special_needs_notes (no backend field for allergies)', async () => {
    await openModal()
    mockRegister.mockResolvedValue({})

    fireEvent.change(screen.getByLabelText(/Child Name/i), { target: { value: 'Alex' } })
    fireEvent.change(screen.getByLabelText(/Child Age \(in years\)/i), { target: { value: '2' } })
    fireEvent.change(screen.getByLabelText(/Emergency Contact Name/i), { target: { value: 'Jamie' } })
    fireEvent.change(screen.getByLabelText(/Emergency Contact Phone/i), { target: { value: '555-0100' } })
    fireEvent.change(screen.getByLabelText(/Allergies/i), { target: { value: 'peanut' } })
    fireEvent.change(screen.getByLabelText(/Special Needs/i), { target: { value: 'needs nap' } })

    const submit = screen.getAllByRole('button', { name: /Register/i }).pop()!
    fireEvent.click(submit)

    await waitFor(() => {
      expect(mockRegister).toHaveBeenCalledTimes(1)
    })
    const payload = mockRegister.mock.calls[0]![1] as Record<string, unknown>
    expect(payload.child_age_months).toBe(24)
    expect(payload.special_needs_notes).toMatch(/Allergies: peanut/)
    expect(payload.special_needs_notes).toMatch(/needs nap/)
  })

  it('labels the modal via aria-labelledby pointing at the session-aware heading', async () => {
    const dialog = await openModal()

    const labelledBy = dialog.getAttribute('aria-labelledby')
    expect(labelledBy).toBeTruthy()

    const heading = document.getElementById(labelledBy!)
    expect(heading).not.toBeNull()
    expect(heading?.tagName).toBe('H2')

    // The heading should include a session-specific token (the date or the
    // session id), not a generic "Dialog". Backend has no `name` column,
    // so the page derives a label from "<branch?> | <date>" and falls
    // back to "<pageTitle> #<id>" when branches haven't loaded.
    const text = heading?.textContent ?? ''
    expect(text).toMatch(/#7|2026-06-02|Jun 2/i)
  })
})

describe('ChildcarePage staff roster + checkout wiring', () => {
  beforeEach(() => {
    mockList.mockReset()
    mockRoster.mockReset()
    mockBranches.mockReset()
    mockList.mockResolvedValue({ sessions: [session], total: 1 })
    mockBranches.mockResolvedValue([])
    // Staff user + flag ON.
    vi.mocked(useAuth).mockReturnValue({
      user: { id: 2, role: 'staff', email: 's@example.com' },
      isAuthenticated: true,
    } as unknown as ReturnType<typeof useAuth>)
    vi.mocked(useOrganizationFeatures).mockReturnValue({
      features: null,
      loading: false,
      isFeatureEnabled: (k: string) => k === 'pickup_authorization_enabled',
      fetchFeatures: vi.fn(),
    } as unknown as ReturnType<typeof useOrganizationFeatures>)
  })

  it('shows the "View roster" disclosure for staff with the flag on, and opens the checkout modal on row click', async () => {
    mockRoster.mockResolvedValue({
      session_id: 7,
      entries: [
        {
          registration: {
            id: 99, session_id: 7, patron_id: 1, child_name: 'Mae',
            child_age_months: 48, status: 'checked_in',
            emergency_contact_name: 'E', emergency_contact_phone: '555',
            created_at: '2026-06-01T00:00:00Z',
            authorized_pickup: [
              { name: 'Aunt Jo', phone: '5552223333', relationship: 'aunt', id_required: false },
            ],
          },
          parent_name: 'Parent P',
          parent_email: 'pp@example.com',
        },
      ],
    })

    renderPage()
    const toggle = await screen.findByRole('button', { name: /View roster/i })
    fireEvent.click(toggle)

    // Roster row appears + the Check out button. Looked up via data-testid
    // because the live button label is now an i18n key path, which the
    // test's passthrough mock returns verbatim ("parentOnboarding...").
    const checkoutBtn = await screen.findByTestId('check-out-99')
    fireEvent.click(checkoutBtn)

    // The stubbed modal renders with the correct registration id.
    await waitFor(() => {
      const modal = screen.getByTestId('staff-checkout-modal')
      expect(modal.getAttribute('data-reg-id')).toBe('99')
    })
    // Confirm the roster query was invoked for the correct session.
    expect(mockRoster).toHaveBeenCalledWith(7)
  })
})

// ---------------------------------------------------------------------------
// Roster check-in / no-show wiring (this PR).
// ---------------------------------------------------------------------------

describe('ChildcarePage staff roster check-in + no-show', () => {
  beforeEach(() => {
    mockList.mockReset()
    mockRoster.mockReset()
    mockUpdate.mockReset()
    mockBranches.mockReset()
    mockList.mockResolvedValue({ sessions: [session], total: 1 })
    mockBranches.mockResolvedValue([])
    vi.mocked(useAuth).mockReturnValue({
      user: { id: 2, role: 'staff', email: 's@example.com' },
      isAuthenticated: true,
    } as unknown as ReturnType<typeof useAuth>)
    // Roster works without pickup flag now (PR widens gate).
    vi.mocked(useOrganizationFeatures).mockReturnValue({
      features: null,
      loading: false,
      isFeatureEnabled: (_: string) => false,
      fetchFeatures: vi.fn(),
    } as unknown as ReturnType<typeof useOrganizationFeatures>)
  })

  function makeReg(overrides: Record<string, unknown> = {}) {
    return {
      registration: {
        id: 42, session_id: 7, patron_id: 1,
        child_name: 'Mae',
        child_age_months: 48,
        status: 'registered',
        emergency_contact_name: 'E', emergency_contact_phone: '555',
        created_at: '2026-06-01T00:00:00Z',
        authorized_pickup: [],
        ...overrides,
      },
      parent_name: 'Parent P',
      parent_email: 'pp@example.com',
    }
  }

  it('renders count chips from the roster response', async () => {
    mockRoster.mockResolvedValue({
      session_id: 7,
      entries: [makeReg({ status: 'registered' }), makeReg({ id: 43, status: 'checked_in' })],
      counts: { registered: 1, checked_in: 1, checked_out: 0, no_show: 0, cancelled: 0 },
    })

    renderPage()
    fireEvent.click(await screen.findByRole('button', { name: /View roster/i }))

    // Wait for roster panel to render.
    const list = await screen.findByLabelText('parentOnboarding.childcare.roster.countsLabel')
    expect(list).toBeInTheDocument()
    // The list has 4 chip <li>s (registered / checked_in / checked_out /
    // no_show). i18n is passthrough in the mock so we assert structure
    // rather than the translated copy.
    const chips = list.querySelectorAll('li')
    expect(chips.length).toBe(4)
  })

  it('clicking Check in for a registered row issues PATCH status=checked_in', async () => {
    mockRoster.mockResolvedValue({
      session_id: 7,
      entries: [makeReg({ id: 42, status: 'registered' })],
      counts: { registered: 1, checked_in: 0, checked_out: 0, no_show: 0, cancelled: 0 },
    })
    mockUpdate.mockResolvedValue({})

    renderPage()
    fireEvent.click(await screen.findByRole('button', { name: /View roster/i }))

    const btn = await screen.findByTestId('check-in-42')
    fireEvent.click(btn)

    await waitFor(() => {
      expect(mockUpdate).toHaveBeenCalledTimes(1)
    })
    expect(mockUpdate).toHaveBeenCalledWith(42, expect.objectContaining({ status: 'checked_in' }))
  })

  it('Mark no-show opens a modal that PATCHes status=no_show with the reason', async () => {
    mockRoster.mockResolvedValue({
      session_id: 7,
      entries: [makeReg({ id: 51, status: 'registered' })],
      counts: { registered: 1, checked_in: 0, checked_out: 0, no_show: 0, cancelled: 0 },
    })
    mockUpdate.mockResolvedValue({})

    renderPage()
    fireEvent.click(await screen.findByRole('button', { name: /View roster/i }))
    fireEvent.click(await screen.findByTestId('mark-no-show-51'))

    // Type a reason + confirm.
    const reasonField = await screen.findByLabelText(/Reason/i)
    fireEvent.change(reasonField, { target: { value: 'never showed' } })
    fireEvent.click(screen.getByTestId('no-show-confirm'))

    await waitFor(() => {
      expect(mockUpdate).toHaveBeenCalledTimes(1)
    })
    expect(mockUpdate).toHaveBeenCalledWith(51, expect.objectContaining({
      status: 'no_show',
      no_show_reason: 'never showed',
    }))
  })

  it('omits no_show_reason from the payload when the field is left blank', async () => {
    mockRoster.mockResolvedValue({
      session_id: 7,
      entries: [makeReg({ id: 52, status: 'registered' })],
      counts: { registered: 1, checked_in: 0, checked_out: 0, no_show: 0, cancelled: 0 },
    })
    mockUpdate.mockResolvedValue({})

    renderPage()
    fireEvent.click(await screen.findByRole('button', { name: /View roster/i }))
    fireEvent.click(await screen.findByTestId('mark-no-show-52'))
    fireEvent.click(await screen.findByTestId('no-show-confirm'))

    await waitFor(() => {
      expect(mockUpdate).toHaveBeenCalledTimes(1)
    })
    const payload = mockUpdate.mock.calls[0]![1] as Record<string, unknown>
    expect(payload.status).toBe('no_show')
    expect(payload).not.toHaveProperty('no_show_reason')
  })

  it('checked_in rows show Check out disabled when pickup_authorization is OFF', async () => {
    mockRoster.mockResolvedValue({
      session_id: 7,
      entries: [makeReg({ id: 60, status: 'checked_in' })],
      counts: { registered: 0, checked_in: 1, checked_out: 0, no_show: 0, cancelled: 0 },
    })

    renderPage()
    fireEvent.click(await screen.findByRole('button', { name: /View roster/i }))

    const btn = await screen.findByTestId('check-out-60')
    expect((btn as HTMLButtonElement).disabled).toBe(true)
  })

  it('roster panel renders for staff even with pickup_authorization OFF', async () => {
    // Regression guard for the gate-widening done in this PR. Pre-PR the
    // disclosure was hidden until pickup_authorization_enabled flipped on;
    // the check-in flow shouldn't depend on that flag.
    mockRoster.mockResolvedValue({
      session_id: 7,
      entries: [],
      counts: { registered: 0, checked_in: 0, checked_out: 0, no_show: 0, cancelled: 0 },
    })

    renderPage()
    // The disclosure button is visible without the pickup flag.
    expect(await screen.findByRole('button', { name: /View roster/i })).toBeInTheDocument()
  })
})

// ---------------------------------------------------------------------------
// Session management: filter row + admin-only New session + create modal.
// ---------------------------------------------------------------------------

describe('ChildcarePage session management', () => {
  beforeEach(() => {
    mockList.mockReset()
    mockBranches.mockReset()
    mockCreate.mockReset()
    mockList.mockResolvedValue({ sessions: [session], total: 1 })
    mockBranches.mockResolvedValue([
      { id: 1, name: 'Main Branch', short_name: 'Main' },
      { id: 2, name: 'East Branch', short_name: 'East' },
    ])
    // Default to non-admin staff for visibility tests; the create-modal
    // tests below upgrade to library_admin.
    vi.mocked(useAuth).mockReturnValue({
      user: { id: 2, role: 'staff', email: 's@example.com' },
      isAuthenticated: true,
    } as unknown as ReturnType<typeof useAuth>)
    vi.mocked(useOrganizationFeatures).mockReturnValue({
      features: null,
      loading: false,
      isFeatureEnabled: () => false,
      fetchFeatures: vi.fn(),
    } as unknown as ReturnType<typeof useOrganizationFeatures>)
  })

  // -- "New session" visibility ---------------------------------------------

  it('hides the "New session" button for non-admin staff', async () => {
    renderPage()
    await screen.findByTestId('childcare-filters')
    expect(screen.queryByTestId('childcare-new-session')).not.toBeInTheDocument()
  })

  it('hides the "New session" button for patron', async () => {
    vi.mocked(useAuth).mockReturnValue({
      user: { id: 99, role: 'patron', email: 'p@example.com' },
      isAuthenticated: true,
    } as unknown as ReturnType<typeof useAuth>)
    renderPage()
    await screen.findByTestId('childcare-filters')
    expect(screen.queryByTestId('childcare-new-session')).not.toBeInTheDocument()
  })

  it('shows the "New session" button for library_admin only', async () => {
    vi.mocked(useAuth).mockReturnValue({
      user: { id: 3, role: 'library_admin', email: 'la@example.com' },
      isAuthenticated: true,
    } as unknown as ReturnType<typeof useAuth>)
    renderPage()
    expect(await screen.findByTestId('childcare-new-session')).toBeInTheDocument()
  })

  it('does NOT show the "New session" button for admin / super_admin (backend require_library_admin is strict)', async () => {
    // Belt-and-braces guard: ADMIN / SUPER_ADMIN / DIRECTOR do NOT pass
    // backend `require_library_admin`. UI must match server policy to
    // avoid a 403-toast surprise. See app/api/v1/dependencies.py.
    for (const role of ['admin', 'super_admin', 'director'] as const) {
      vi.mocked(useAuth).mockReturnValue({
        user: { id: 4, role, email: `${role}@example.com` },
        isAuthenticated: true,
      } as unknown as ReturnType<typeof useAuth>)
      const { unmount } = renderPage()
      await screen.findByTestId('childcare-filters')
      expect(screen.queryByTestId('childcare-new-session')).not.toBeInTheDocument()
      unmount()
    }
  })

  // -- Filter URL sync -------------------------------------------------------

  it('refetches with the URL-encoded filters as listChildcareSessions params', async () => {
    renderPage({
      initialEntry:
        '/staff/parent-onboarding/childcare?status=cancelled&branch_id=2&from_date=2026-06-01&to_date=2026-06-30',
    })

    await waitFor(() => {
      expect(mockList).toHaveBeenCalled()
    })
    const lastCall = mockList.mock.calls[mockList.mock.calls.length - 1]![0]
    expect(lastCall).toMatchObject({
      status: 'cancelled',
      branch_id: 2,
      from_date: '2026-06-01',
      to_date: '2026-06-30',
    })
  })

  it('clicking a status pill triggers a refetch with the new status', async () => {
    renderPage()
    await waitFor(() => {
      expect(mockList).toHaveBeenCalled()
    })

    // Switch status to `cancelled` -> URL updates -> refetch.
    fireEvent.click(await screen.findByTestId('status-pill-cancelled'))

    await waitFor(() => {
      const lastCall = mockList.mock.calls[mockList.mock.calls.length - 1]![0]
      expect(lastCall.status).toBe('cancelled')
    })
  })

  it('reset button clears all filters', async () => {
    renderPage({
      initialEntry:
        '/staff/parent-onboarding/childcare?status=full&branch_id=2&from_date=2026-06-01&to_date=2026-06-30',
    })
    await waitFor(() => {
      expect(mockList).toHaveBeenCalled()
    })

    fireEvent.click(await screen.findByTestId('childcare-reset-filters'))

    await waitFor(() => {
      const lastCall = mockList.mock.calls[mockList.mock.calls.length - 1]![0]
      // After reset: status falls back to the default ("available"),
      // branch_id and to_date drop from the URL entirely, from_date
      // defaults to today (sent on every call). We assert what the user
      // would observe: status reset to default, branch + to_date cleared.
      expect(lastCall.status).toBe('available')
      expect(lastCall.branch_id).toBeUndefined()
      expect(lastCall.to_date).toBeUndefined()
    })
  })

  // -- Create modal ---------------------------------------------------------

  function openCreateModalAsAdmin() {
    vi.mocked(useAuth).mockReturnValue({
      user: { id: 3, role: 'library_admin', email: 'la@example.com' },
      isAuthenticated: true,
    } as unknown as ReturnType<typeof useAuth>)
    return renderPage()
  }

  it('create-modal: end time before start time -> form-level validation error, no submit', async () => {
    openCreateModalAsAdmin()
    fireEvent.click(await screen.findByTestId('childcare-new-session'))

    // Use stable ids to disambiguate from the filter-row controls (which
    // also carry "Branch" / "Start time" / "End time" labels). The form-
    // label-collision pattern is documented in
    // feedback_l30_form_label_collision; getByLabelText returns multiple
    // matches when both filter + create-modal are mounted.
    fireEvent.change(document.getElementById('childcare-create-branch')!, {
      target: { value: '1' },
    })
    fireEvent.change(document.getElementById('childcare-create-start')!, {
      target: { value: '12:00' },
    })
    fireEvent.change(document.getElementById('childcare-create-end')!, {
      target: { value: '11:00' },
    })

    fireEvent.click(screen.getByTestId('childcare-create-submit'))

    await waitFor(() => {
      const err = screen.getByTestId('childcare-create-error')
      expect(err.textContent ?? '').toMatch(/End time must be after start time|errorEndBeforeStart/i)
    })
    expect(mockCreate).not.toHaveBeenCalled()
  })

  it('create-modal: posts the right shape on submit and closes the modal', async () => {
    openCreateModalAsAdmin()
    mockCreate.mockResolvedValue({
      id: 99,
      branch_id: 1,
      date: '2026-07-01',
      start_time: '10:00',
      end_time: '11:30',
      max_children: 6,
      age_range_min_months: 0,
      age_range_max_months: 60,
      status: 'available',
      registered_count: 0,
    })

    fireEvent.click(await screen.findByTestId('childcare-new-session'))

    // See comment in the prior test re: label collisions.
    fireEvent.change(document.getElementById('childcare-create-branch')!, {
      target: { value: '1' },
    })
    fireEvent.change(document.getElementById('childcare-create-date')!, {
      target: { value: '2026-07-01' },
    })
    fireEvent.change(document.getElementById('childcare-create-start')!, {
      target: { value: '10:00' },
    })
    fireEvent.change(document.getElementById('childcare-create-end')!, {
      target: { value: '11:30' },
    })
    fireEvent.change(document.getElementById('childcare-create-max')!, {
      target: { value: '6' },
    })

    fireEvent.click(screen.getByTestId('childcare-create-submit'))

    await waitFor(() => {
      expect(mockCreate).toHaveBeenCalledTimes(1)
    })
    // Critical guard against the openapi-drift trap (memory:
    // feedback_l30_openapi_handwritten_drift). Backend uses StrictInputSchema
    // (extra=forbid); any drift here returns 422. react-query v5 calls
    // mutationFn with (variables, context) so we inspect calls[0][0].
    const payload = mockCreate.mock.calls[0]![0] as Record<string, unknown>
    expect(payload).toMatchObject({
      branch_id: 1,
      date: '2026-07-01',
      start_time: '10:00',
      end_time: '11:30',
      max_children: 6,
      age_range_min_months: 0,
      age_range_max_months: 60,
    })
    // Belt-and-braces: never resurrect the old fictional field names.
    expect(payload).not.toHaveProperty('name')
    expect(payload).not.toHaveProperty('location')
    expect(payload).not.toHaveProperty('capacity')
    expect(payload).not.toHaveProperty('description')

    // Modal closes after successful create.
    await waitFor(() => {
      expect(screen.queryByText(/Create childcare session|sessions\.create\.heading/i)).not.toBeInTheDocument()
    })
  })
})
