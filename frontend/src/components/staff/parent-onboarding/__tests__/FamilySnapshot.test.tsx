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
const getSnapshotMock = vi.fn()
const revealSnapshotMock = vi.fn()
const getConsentMock = vi.fn()
const recordConsentMock = vi.fn()

vi.mock('@/api/parent-onboarding-api', async () => {
  const actual =
    await vi.importActual<typeof import('@/api/parent-onboarding-api')>(
      '@/api/parent-onboarding-api',
    )
  return {
    ...actual,
    getSessionFamilySnapshot: (...a: unknown[]) => getSnapshotMock(...a),
    revealSessionFamilySnapshot: (...a: unknown[]) => revealSnapshotMock(...a),
    getPatronFamilySnapshotConsent: (...a: unknown[]) => getConsentMock(...a),
    recordPatronFamilySnapshotConsent: (...a: unknown[]) =>
      recordConsentMock(...a),
  }
})

// Real i18n in English -- see feedback_l30_vitest_i18n_no_preload.
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

import { FamilySnapshot } from '@/components/staff/parent-onboarding/FamilySnapshot'

beforeAll(async () => {
  await loadLanguage('en')
})

beforeEach(() => {
  getSnapshotMock.mockReset()
  revealSnapshotMock.mockReset()
  getConsentMock.mockReset()
  recordConsentMock.mockReset()
  vi.useRealTimers()
})

function renderSnapshot(props: { sessionId?: number; patronId?: number } = {}) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={client}>
      <FamilySnapshot
        sessionId={props.sessionId ?? 42}
        patronId={props.patronId ?? 1421}
      />
    </QueryClientProvider>,
  )
}

const REDACTED_PAYLOAD = {
  patron_id: 1421,
  consent_status: 'granted' as const,
  consent_recorded_at: '2026-03-04T10:12:00Z',
  language_preference: 'es',
  language_preference_label: 'Español',
  household_size: 4,
  household_members: [
    { first_name_revealed: 'M.', age_range: '0-5', is_parent: false },
    { first_name_revealed: 'E.', age_range: '6-8', is_parent: false },
  ],
  household_notes_summary: 'Two adults, two children. Infant on visit form.',
  baby_age_months: 7,
  sensitive_fields_hidden: true,
}

const REVEALED_PAYLOAD = {
  ...REDACTED_PAYLOAD,
  household_members: [
    { first_name_revealed: 'Mia', age_range: '0-5', is_parent: false },
    { first_name_revealed: 'Eli', age_range: '6-8', is_parent: false },
  ],
  household_notes_summary:
    'Two adults, two children. Infant on visit form. Patron mentioned grandmother lives next door.',
  sensitive_fields_hidden: false,
}

const NO_CONSENT_PAYLOAD = {
  patron_id: 1421,
  consent_status: 'not_requested' as const,
  language_preference: 'es',
  language_preference_label: 'Español',
  household_size: null,
  household_members: [],
  household_notes_summary: null,
  baby_age_months: null,
  sensitive_fields_hidden: true,
}

describe('FamilySnapshot -- consent granted, redacted by default', () => {
  it('renders the heading, language pref, and redacted child initials', async () => {
    getSnapshotMock.mockResolvedValue(REDACTED_PAYLOAD)
    renderSnapshot()

    // Wait for data-driven content -- the heading also renders in the
    // loading state, so getByRole('heading') would resolve too early.
    await screen.findByText(/Español/)

    // Heading is the labelled landmark anchor.
    expect(
      screen.getByRole('heading', { name: /family snapshot/i, level: 2 }),
    ).toBeInTheDocument()

    // Language preference + label rendered.
    expect(screen.getByText(/Español/)).toBeInTheDocument()
    expect(screen.getByText(/\(es\)/)).toBeInTheDocument()

    // Children appear as initial-redacted chips.
    expect(screen.getByText(/0-5 \(M\.\)/)).toBeInTheDocument()
    expect(screen.getByText(/6-8 \(E\.\)/)).toBeInTheDocument()

    // Raw first names are NOT in the DOM yet.
    expect(screen.queryByText(/\bMia\b/)).not.toBeInTheDocument()
    expect(screen.queryByText(/\bEli\b/)).not.toBeInTheDocument()
  })

  it('Reveal button starts as aria-pressed=false', async () => {
    getSnapshotMock.mockResolvedValue(REDACTED_PAYLOAD)
    renderSnapshot()

    const button = await screen.findByRole('button', {
      name: /reveal sensitive/i,
    })
    expect(button).toHaveAttribute('aria-pressed', 'false')
  })
})

describe('FamilySnapshot -- reveal flow', () => {
  it('clicking Reveal swaps in full names and flips aria-pressed', async () => {
    getSnapshotMock.mockResolvedValue(REDACTED_PAYLOAD)
    revealSnapshotMock.mockResolvedValue(REVEALED_PAYLOAD)
    const user = userEvent.setup()
    renderSnapshot()

    const button = await screen.findByRole('button', {
      name: /reveal sensitive/i,
    })
    await user.click(button)

    // Reveal mutation called exactly once.
    await waitFor(() => {
      expect(revealSnapshotMock).toHaveBeenCalledTimes(1)
    })

    // Button text flips, aria-pressed flips.
    const hideButton = await screen.findByRole('button', {
      name: /hide sensitive/i,
    })
    expect(hideButton).toHaveAttribute('aria-pressed', 'true')

    // Full first names now visible.
    expect(screen.getByText(/0-5 \(Mia\)/)).toBeInTheDocument()
    expect(screen.getByText(/6-8 \(Eli\)/)).toBeInTheDocument()
  })

  it('clicking Hide collapses back without a second reveal call', async () => {
    getSnapshotMock.mockResolvedValue(REDACTED_PAYLOAD)
    revealSnapshotMock.mockResolvedValue(REVEALED_PAYLOAD)
    const user = userEvent.setup()
    renderSnapshot()

    const button = await screen.findByRole('button', {
      name: /reveal sensitive/i,
    })
    await user.click(button)
    await screen.findByRole('button', { name: /hide sensitive/i })

    // Make the second snapshot load (triggered by invalidateQueries on
    // collapse) return the redacted shape again.
    getSnapshotMock.mockResolvedValue(REDACTED_PAYLOAD)

    const hideButton = screen.getByRole('button', { name: /hide sensitive/i })
    await user.click(hideButton)

    await screen.findByRole('button', { name: /reveal sensitive/i })

    // Only one reveal POST in total.
    expect(revealSnapshotMock).toHaveBeenCalledTimes(1)
  })
})

describe('FamilySnapshot -- consent missing state', () => {
  it('renders the "Not on file" copy + Record consent affordance', async () => {
    getSnapshotMock.mockResolvedValue(NO_CONSENT_PAYLOAD)
    renderSnapshot()

    // Wait for the Record consent button (only renders after data lands;
    // the loading state shows the heading but no buttons).
    await screen.findByRole('button', { name: /record consent/i })

    // Affordance is "Record consent", not "Reveal".
    expect(
      screen.getByRole('button', { name: /record consent/i }),
    ).toBeInTheDocument()
    expect(
      screen.queryByRole('button', { name: /reveal sensitive/i }),
    ).not.toBeInTheDocument()

    // "Not on file" copy is real text, not a placeholder.
    const notOnFile = screen.getAllByText(
      /Not on file — patron has not consented\./i,
    )
    expect(notOnFile.length).toBeGreaterThanOrEqual(1)
  })

  it('clicking Record consent reveals the inline prompt with patron-script copy', async () => {
    getSnapshotMock.mockResolvedValue(NO_CONSENT_PAYLOAD)
    const user = userEvent.setup()
    renderSnapshot()

    const recordButton = await screen.findByRole('button', {
      name: /record consent/i,
    })
    expect(recordButton).toHaveAttribute('aria-expanded', 'false')

    await user.click(recordButton)
    expect(recordButton).toHaveAttribute('aria-expanded', 'true')

    expect(
      screen.getByText(/May we save details about your children/i),
    ).toBeInTheDocument()
  })
})

describe('FamilySnapshot -- error + loading', () => {
  it('renders error copy when snapshot query fails', async () => {
    getSnapshotMock.mockRejectedValue(new Error('500'))
    renderSnapshot()

    await waitFor(() => {
      expect(
        screen.getByText(/Could not load family snapshot/i),
      ).toBeInTheDocument()
    })
  })
})

describe('FamilySnapshot -- accessibility', () => {
  it('uses paired <dt>/<dd> rows for the field grid', async () => {
    getSnapshotMock.mockResolvedValue(REDACTED_PAYLOAD)
    renderSnapshot()

    // Wait for data so the <dl> rows are mounted.
    await screen.findByText(/Español/)

    const dts = document.querySelectorAll('dl dt')
    const dds = document.querySelectorAll('dl dd')
    // Language pref, Household size, Baby, Children, Notes -- five pairs.
    expect(dts.length).toBeGreaterThanOrEqual(5)
    expect(dds.length).toBeGreaterThanOrEqual(5)
    expect(dts.length).toEqual(dds.length)
  })

  it('section has aria-labelledby anchored to the h2', async () => {
    getSnapshotMock.mockResolvedValue(REDACTED_PAYLOAD)
    renderSnapshot()

    await screen.findByText(/Español/)
    const section = document.querySelector(
      'section[aria-labelledby="family-snapshot-heading"]',
    )
    expect(section).not.toBeNull()
    const h2 = within(section as HTMLElement).getByRole('heading', { level: 2 })
    expect(h2).toHaveAttribute('id', 'family-snapshot-heading')
  })
})
