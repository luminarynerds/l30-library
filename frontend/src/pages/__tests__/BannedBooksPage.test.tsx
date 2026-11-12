/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * Covers the reconsideration form on /banned-books:
 * - Empty submit surfaces a role=alert error and never calls the API.
 * - Submit with valid payload posts the right body shape (incl turnstile_token)
 *   and collapses the form on success.
 *
 * Prevents regression of the silent-422/500 path observed live, where the
 * submit button stayed clickable and patrons duplicate-submitted.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
// This file is the first here to use jest-dom matchers (toBeInTheDocument,
// toHaveAttribute). The global setup (src/__tests__/setup.ts) covers the
// real test run, but the pre-commit hook type-checks staged files in
// isolation (tsc-files) and doesn't see that setup file, so the matcher
// augmentation needs to be visible from this file directly too.
import '@testing-library/jest-dom'
import { testAccessibility } from '../../__tests__/utils/accessibility'
import BannedBooksPage from '../BannedBooksPage'

vi.mock('react-hot-toast', () => ({
  default: { success: vi.fn(), error: vi.fn() },
}))

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    // String second arg: caller is passing a plain-English fallback -- use it.
    // Object second arg: caller is passing interpolation params -- render just
    // the interpolated values so tests can assert on the resulting text
    // (e.g. a formatted date) without needing the real translation strings.
    t: (_key: string, fallback?: string | Record<string, unknown>) =>
      typeof fallback === 'string'
        ? fallback
        : fallback
          ? Object.values(fallback).join(' ')
          : _key,
  }),
}))

vi.mock('@/utils/friendlyError', () => ({
  friendlyErrorMessage: (e: Error) => e.message,
}))

// Mock the Turnstile widget — click-driven verify (matches working pattern in
// SeriesRegistrationModal.test.tsx). Calling onVerify in the render body would
// combine with the page's setForm(f => ({ ...f, turnstile_token })) (new object
// every call) to produce an infinite render loop that hangs vitest.
vi.mock('@/components/TurnstileWidget', () => ({
  TurnstileWidget: ({ onVerify }: { onVerify: (token: string) => void }) => (
    <button
      type="button"
      data-testid="turnstile-mock"
      onClick={() => onVerify('test-turnstile-token')}
    >
      mock-verify
    </button>
  ),
}))

const submitMock = vi.fn()

vi.mock('../../api/api', () => ({
  getPublicChallenges: vi.fn().mockResolvedValue([]),
  getPublicStats: vi.fn().mockResolvedValue({
    total_challenges: 0,
    pending_challenges: 0,
    resolved_this_year: 0,
    outcomes: {},
    reasons: {},
  }),
  getIntellectualFreedomResources: vi.fn().mockResolvedValue([]),
  submitReconsiderationRequest: (...args: unknown[]) => submitMock(...args),
  CHALLENGE_OUTCOME_LABELS: {
    retained: 'Retained', removed: 'Removed', restricted: 'Restricted',
    withdrawn: 'Withdrawn', pending: 'Pending', retained_with_changes: 'Retained with changes',
  },
  CHALLENGE_REASON_LABELS: {
    sexual_content: 'Sexual content',
    lgbtq_content: 'LGBTQ+ content',
    violence: 'Violence',
    language: 'Language',
    religious_viewpoint: 'Religious viewpoint',
    political_viewpoint: 'Political viewpoint',
    age_inappropriate: 'Age-inappropriate',
    racism: 'Racism',
    drugs_alcohol: 'Drugs / alcohol',
    anti_family: 'Anti-family',
    occult_supernatural: 'Occult / supernatural',
    other: 'Other',
  },
}))

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <BannedBooksPage />
      </MemoryRouter>
    </QueryClientProvider>
  )
}

beforeEach(() => {
  submitMock.mockReset()
})

describe('BannedBooksPage — reconsideration form', () => {
  it('surfaces a role=alert error and does NOT call the API when required fields are blank', async () => {
    renderPage()

    fireEvent.click(await screen.findByRole('button', { name: /Submit a Request Online/i }))
    fireEvent.click(await screen.findByRole('button', { name: /Submit Request/i }))

    // Use the form-specific testid; TransparencyLog can render its own
    // role=alert error if its query fails, which collides with a plain
    // findByRole('alert') lookup.
    const alert = await screen.findByTestId('reconsideration-form-error')
    expect(alert).toBeTruthy()
    expect(alert.getAttribute('role')).toBe('alert')
    expect(alert.textContent || '').toMatch(/title/i)
    expect(submitMock).not.toHaveBeenCalled()
  })

  it('submits with the correct payload shape and collapses the form on success', async () => {
    submitMock.mockResolvedValue({
      message: 'Thank you',
      reference_id: 42,
      expected_response_days: 30,
    })

    renderPage()

    fireEvent.click(await screen.findByRole('button', { name: /Submit a Request Online/i }))

    fireEvent.change(screen.getByLabelText(/Title of Material/i), {
      target: { value: 'Test Book' },
    })
    fireEvent.change(screen.getByLabelText(/Primary Reason for Concern/i), {
      target: { value: 'other' },
    })
    fireEvent.change(screen.getByLabelText(/Describe Your Concern/i), {
      target: { value: 'This is a complaint long enough to satisfy validation.' },
    })
    fireEvent.change(screen.getByLabelText(/Your Name/i), {
      target: { value: 'Jane Patron' },
    })
    fireEvent.click(screen.getByLabelText(/I confirm that I have read/i))

    // Click-driven Turnstile mock: emit the token before submitting.
    fireEvent.click(screen.getByTestId('turnstile-mock'))

    fireEvent.click(screen.getByRole('button', { name: /Submit Request/i }))

    await waitFor(() => expect(submitMock).toHaveBeenCalledTimes(1))
    const payload = submitMock.mock.calls[0]![0]
    expect(payload).toMatchObject({
      title: 'Test Book',
      primary_reason: 'other',
      challenger_complaint: 'This is a complaint long enough to satisfy validation.',
      challenger_name: 'Jane Patron',
      has_read_material: true,
      turnstile_token: 'test-turnstile-token',
    })

    // Form collapses on success — the open button reappears without showing the form.
    await waitFor(() =>
      expect(screen.queryByRole('button', { name: /Submit Request/i })).toBeNull()
    )
  })
})

describe('Banned Books Week section', () => {
  beforeEach(() => {
    // shouldAdvanceTime keeps the fake clock ticking in real time so RTL's
    // findBy*/waitFor polling (which schedules via setTimeout) still resolves.
    vi.useFakeTimers({ shouldAdvanceTime: true })
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('renders the October 2026 date, not a September one', async () => {
    vi.setSystemTime(new Date(2026, 7, 4))
    renderPage()
    expect(await screen.findByText(/October 4-10, 2026/)).toBeInTheDocument()
    expect(screen.queryByText(/September/)).not.toBeInTheDocument()
  })

  it('renders the 2026 theme as an attributed quotation', async () => {
    vi.setSystemTime(new Date(2026, 7, 4))
    renderPage()
    const quote = await screen.findByText(/Let Books Be\. Protect the Freedom to Read\./)
    expect(quote).toBeInTheDocument()

    const attribution = await screen.findByText(/2026 campaign theme, Banned Books Week Coalition/)
    expect(attribution).toBeInTheDocument()
    // <cite>, not <footer>: index.css:438 forces every footer to a black
    // background under .high-contrast, which rendered this dark-on-black.
    expect(attribution.tagName.toLowerCase()).toBe('cite')
    // The attribution has to live inside the quote, not just somewhere on the page.
    expect(quote.closest('blockquote')).toContainElement(attribution)
  })

  it('omits the date block entirely once the table has run out', async () => {
    vi.setSystemTime(new Date(2028, 0, 1))
    renderPage()
    // The section still exists...
    expect(await screen.findByText('Banned Books Week')).toBeInTheDocument()
    // ...but asserts nothing about dates.
    expect(screen.queryByText(/Next:/)).not.toBeInTheDocument()
    expect(screen.queryByText(/2027/)).not.toBeInTheDocument()
  })

  // color-contrast is disabled here: jsdom does not load the compiled
  // Tailwind stylesheet or run real layout, so axe cannot compute actual
  // rendered colors in this environment -- a pass here would not be real
  // contrast evidence. This checks structure/ARIA/landmarks only. The real
  // four-state (light/dark/HC light/HC dark) contrast check is a browser
  // run against the built page, which is Task 7's job once this deploys.
  it('has no structural axe violations with the BBW date block rendered', async () => {
    vi.setSystemTime(new Date(2026, 7, 4))
    const { container } = renderPage()
    await screen.findByText(/Let Books Be\. Protect the Freedom to Read\./)
    await testAccessibility(container, { rules: { 'color-contrast': { enabled: false } } })
  })

  it('links to a live ALA frequently-challenged page', async () => {
    renderPage()
    const link = await screen.findByRole('link', {
      name: /Frequently Challenged Books/i,
    })
    expect(link).toHaveAttribute(
      'href',
      'https://www.ala.org/bbooks/frequentlychallengedbooks/top10'
    )
  })
})
