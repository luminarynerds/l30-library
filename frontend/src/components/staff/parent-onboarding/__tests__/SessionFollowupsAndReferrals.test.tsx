/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/// <reference types="vitest/globals" />
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

import { loadLanguage } from '@/i18n/translations'

// Mock the typed API client so the component never hits the network.
// Per memory feedback_l30_openapi_handwritten_drift, the new section uses
// its own client (parent-onboarding-followups-api.ts) -- mock that, not
// the older legacy client.
const listFollowupsMock = vi.fn()
const createFollowupMock = vi.fn()
const completeFollowupMock = vi.fn()
const deleteFollowupMock = vi.fn()
const listReferralsMock = vi.fn()
const createReferralMock = vi.fn()
const deleteReferralMock = vi.fn()
const searchAgenciesMock = vi.fn()

vi.mock(
  '@/api/domains/services/parent-onboarding-followups-api',
  () => ({
    listSessionFollowups: (...a: unknown[]) => listFollowupsMock(...a),
    createSessionFollowup: (...a: unknown[]) => createFollowupMock(...a),
    completeFollowup: (...a: unknown[]) => completeFollowupMock(...a),
    deleteFollowup: (...a: unknown[]) => deleteFollowupMock(...a),
    listSessionReferrals: (...a: unknown[]) => listReferralsMock(...a),
    createSessionReferral: (...a: unknown[]) => createReferralMock(...a),
    deleteReferral: (...a: unknown[]) => deleteReferralMock(...a),
    searchPartnerAgencies: (...a: unknown[]) => searchAgenciesMock(...a),
    updateFollowup: vi.fn(),
    updateReferral: vi.fn(),
  }),
)

// Real i18n in English. Pre-load matches the L30 vitest convention -- the
// setup file does NOT preload locales (see feedback_l30_vitest_i18n_no_preload).
vi.mock('@/i18n', async () => {
  const actual = await vi.importActual<typeof import('@/i18n')>('@/i18n')
  return {
    ...actual,
    useTranslation: () => ({
      t: (key: string, params?: Record<string, unknown>) =>
        actual.getTranslation(key, 'en', params),
      language: 'en',
      isRTL: false,
    }),
  }
})

import { SessionFollowupsAndReferrals } from '@/components/staff/parent-onboarding/SessionFollowupsAndReferrals'

beforeAll(async () => {
  await loadLanguage('en')
})

beforeEach(() => {
  listFollowupsMock.mockReset()
  createFollowupMock.mockReset()
  completeFollowupMock.mockReset()
  deleteFollowupMock.mockReset()
  listReferralsMock.mockReset()
  createReferralMock.mockReset()
  deleteReferralMock.mockReset()
  searchAgenciesMock.mockReset()

  // Default: empty lists so the panels render the "empty" copy.
  listFollowupsMock.mockResolvedValue({ followups: [], total: 0 })
  listReferralsMock.mockResolvedValue({ referrals: [], total: 0 })
  searchAgenciesMock.mockResolvedValue({ agencies: [], total: 0 })
})

function renderSection(sessionId = 42) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={client}>
      <SessionFollowupsAndReferrals sessionId={sessionId} />
    </QueryClientProvider>,
  )
}

describe('SessionFollowupsAndReferrals -- empty state', () => {
  it('renders both panels with empty-state copy', async () => {
    renderSection()
    // Both queries resolve to empty, and TanStack Query flushes
    // asynchronously, so wait on the actual empty-state copy rather
    // than the heading (which renders immediately during loading).
    await waitFor(() => {
      expect(
        screen.getByText(/No follow-ups yet\./i),
      ).toBeInTheDocument()
    })
    await waitFor(() => {
      expect(
        screen.getByText(/No referrals yet\./i),
      ).toBeInTheDocument()
    })
    // Headings are present in both states; assert them after so a
    // regression that swaps the heading still surfaces.
    expect(
      screen.getByRole('heading', { name: /Follow-up tasks/i }),
    ).toBeInTheDocument()
    expect(
      screen.getByRole('heading', { name: /Referrals/i }),
    ).toBeInTheDocument()
  })

  it('returns null when sessionId is NaN (defensive)', () => {
    const { container } = renderSection(NaN)
    expect(container).toBeEmptyDOMElement()
  })
})

describe('SessionFollowupsAndReferrals -- follow-up creation', () => {
  it('shows the add form, validates required fields, and POSTs', async () => {
    const user = userEvent.setup()
    createFollowupMock.mockResolvedValue({
      id: 1, session_id: 42, title: 'Confirm packet',
      due_date: '2026-06-01', status: 'open', priority: 'normal',
    })
    renderSection()
    await waitFor(() => {
      expect(screen.getByText(/No follow-ups yet\./i)).toBeInTheDocument()
    })
    await user.click(screen.getByRole('button', { name: /Add follow-up/i }))

    // Required fields use aria-required.
    const titleInput = screen.getByLabelText(/^Title/i)
    expect(titleInput).toHaveAttribute('aria-required', 'true')
    const dueInput = screen.getByLabelText(/^Due date/i)
    expect(dueInput).toHaveAttribute('aria-required', 'true')

    await user.type(titleInput, 'Confirm packet')
    // Type a YYYY-MM-DD into the native date input.
    await user.type(dueInput, '2026-06-01')

    await user.click(screen.getByRole('button', { name: /Save follow-up/i }))

    await waitFor(() => {
      expect(createFollowupMock).toHaveBeenCalledTimes(1)
    })
    const [sessionId, payload] = createFollowupMock.mock.calls[0]!
    expect(sessionId).toBe(42)
    expect(payload).toMatchObject({
      title: 'Confirm packet',
      due_date: '2026-06-01',
      priority: 'normal',
    })
  })
})

describe('SessionFollowupsAndReferrals -- follow-up complete flow', () => {
  it('reveals completion-note textarea on Mark done and POSTs the note', async () => {
    const user = userEvent.setup()
    listFollowupsMock.mockResolvedValue({
      followups: [
        {
          id: 7, session_id: 42, title: 'Call WIC',
          due_date: '2026-06-01', status: 'open', priority: 'normal',
          assignee_id: 11, assignee_name: 'Cleo Park',
          description: null, completed_at: null, completed_by_id: null,
          completion_note: null,
        },
      ],
      total: 1,
    })
    completeFollowupMock.mockResolvedValue({
      id: 7, status: 'completed', completion_note: 'Reached coordinator.',
    })
    renderSection()
    await waitFor(() => {
      expect(screen.getByText('Call WIC')).toBeInTheDocument()
    })

    await user.click(screen.getByRole('button', { name: /Mark done/i }))
    const note = screen.getByLabelText(/Completion note/i)
    expect(note).toHaveFocus() // focus-management requirement
    await user.type(note, 'Reached coordinator.')
    await user.click(screen.getByRole('button', { name: /^Save$/ }))

    await waitFor(() => {
      expect(completeFollowupMock).toHaveBeenCalledTimes(1)
    })
    expect(completeFollowupMock.mock.calls[0]).toEqual([
      7,
      { completion_note: 'Reached coordinator.' },
    ])
  })
})

describe('SessionFollowupsAndReferrals -- referral creation', () => {
  it('uses the agency autocomplete and submits with partner_agency_id', async () => {
    const user = userEvent.setup()
    searchAgenciesMock.mockResolvedValue({
      agencies: [
        {
          id: 5, name: 'Eastside WIC Clinic', slug: 'eastside-wic-clinic',
          agency_type: 'wic', is_active: true, languages_served: [],
        },
      ],
      total: 1,
    })
    createReferralMock.mockResolvedValue({
      id: 91, session_id: 42, partner_agency_id: 5,
      partner_agency_name: 'Eastside WIC Clinic',
      agency_name_freetext: null, purpose: 'WIC enrollment',
      status: 'made', warm_handoff: false, patron_consent_to_share: false,
      notes: null, made_at: '2026-05-18T14:30:00Z',
    })
    renderSection()
    await waitFor(() => {
      expect(screen.getByText(/No referrals yet\./i)).toBeInTheDocument()
    })
    await user.click(screen.getByRole('button', { name: /Add referral/i }))

    const agencyInput = screen.getByLabelText(/Partner agency/i)
    await user.type(agencyInput, 'wic')
    // Wait for the autocomplete to render. The listbox uses role=listbox.
    await waitFor(() => {
      expect(screen.getByRole('listbox')).toBeInTheDocument()
    })
    await user.click(
      screen.getByRole('option', { name: /Eastside WIC Clinic/i }),
    )
    await user.type(screen.getByLabelText(/^Purpose/i), 'WIC enrollment')
    await user.click(screen.getByRole('button', { name: /Save referral/i }))

    await waitFor(() => {
      expect(createReferralMock).toHaveBeenCalledTimes(1)
    })
    expect(createReferralMock.mock.calls[0]![1]).toMatchObject({
      partner_agency_id: 5,
      purpose: 'WIC enrollment',
    })
    // Freetext should NOT be set when an agency was selected.
    expect(createReferralMock.mock.calls[0]![1].agency_name_freetext).toBeUndefined()
  })

  it('captures freetext-only when the agency is not on file', async () => {
    const user = userEvent.setup()
    createReferralMock.mockResolvedValue({
      id: 92, session_id: 42, partner_agency_id: null,
      partner_agency_name: null,
      agency_name_freetext: 'Postpartum Support Network',
      purpose: 'support group', status: 'made',
      warm_handoff: false, patron_consent_to_share: false, notes: null,
      made_at: '2026-05-18T14:30:00Z',
    })
    renderSection()
    await waitFor(() => {
      expect(screen.getByText(/No referrals yet\./i)).toBeInTheDocument()
    })
    await user.click(screen.getByRole('button', { name: /Add referral/i }))
    // Toggle freetext-only and verify the label flips.
    const freetextToggle = screen.getByLabelText(
      /This agency isn't on file/i,
    )
    await user.click(freetextToggle)
    const agencyInput = screen.getByLabelText(
      /Agency name \(not on file\)/i,
    )
    await user.type(agencyInput, 'Postpartum Support Network')
    await user.type(screen.getByLabelText(/^Purpose/i), 'support group')
    await user.click(screen.getByRole('button', { name: /Save referral/i }))

    await waitFor(() => {
      expect(createReferralMock).toHaveBeenCalledTimes(1)
    })
    expect(createReferralMock.mock.calls[0]![1]).toMatchObject({
      agency_name_freetext: 'Postpartum Support Network',
      purpose: 'support group',
    })
    expect(createReferralMock.mock.calls[0]![1].partner_agency_id).toBeUndefined()
  })
})

describe('SessionFollowupsAndReferrals -- a11y', () => {
  it('renders sections with labelled headings and labelled lists', async () => {
    listFollowupsMock.mockResolvedValue({
      followups: [{
        id: 1, session_id: 42, title: 'Task A',
        due_date: '2026-06-01', status: 'open', priority: 'normal',
        assignee_name: 'Cleo Park',
      }],
      total: 1,
    })
    listReferralsMock.mockResolvedValue({
      referrals: [{
        id: 1, session_id: 42, partner_agency_name: 'Eastside WIC',
        partner_agency_id: 5, agency_name_freetext: null,
        purpose: 'WIC', status: 'made',
        warm_handoff: false, patron_consent_to_share: false,
        made_at: '2026-05-18T14:30:00Z',
      }],
      total: 1,
    })
    renderSection()
    await waitFor(() => {
      expect(screen.getByText('Task A')).toBeInTheDocument()
      expect(screen.getByText('Eastside WIC')).toBeInTheDocument()
    })
    // Each panel exposes its list with an aria-label.
    const followupList = screen.getByRole('list', {
      name: /Follow-up tasks/i,
    })
    const referralList = screen.getByRole('list', {
      name: /Referrals/i,
    })
    expect(within(followupList).getAllByRole('listitem')).toHaveLength(1)
    expect(within(referralList).getAllByRole('listitem')).toHaveLength(1)
  })
})
