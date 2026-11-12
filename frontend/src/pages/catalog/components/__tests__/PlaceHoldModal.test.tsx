/// <reference types="@testing-library/jest-dom" />
/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * Covers the friendly 422 (ITEM_NOT_HOLDABLE) error surfacing added when
 * /holds POST started enforcing NON_HOLDABLE_STATUSES server-side. The
 * server's user-facing detail message must reach the inline alert in the
 * modal instead of being collapsed into the generic friendly fallback.
 */
import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ApiError } from '@/lib/api-client'
import { PlaceHoldModal } from '../PlaceHoldModal'

// ---- Hoisted mocks ------------------------------------------------------

const mocks = vi.hoisted(() => ({
  placeHold: vi.fn(),
  listBranches: vi.fn(),
  fetchApi: vi.fn(),
}))

vi.mock('@/api/fetchApi', () => ({
  fetchApi: mocks.fetchApi,
}))

vi.mock('@/api/api', async () => ({
  placeHold: mocks.placeHold,
}))

vi.mock('@/api/branch-api', () => ({
  listBranches: mocks.listBranches,
}))

vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => ({ token: 'test-token', user: { id: 1 } }),
}))

vi.mock('@/features/accessibility/hooks/useUnifiedAccessibility', () => ({
  useUnifiedAccessibility: () => ({
    explicitConfirmations: false,
    announceToScreenReader: vi.fn(),
  }),
}))

vi.mock('@/hooks/useJourneyTracker', () => ({
  useJourneyTracker: () => ({ trackStage: vi.fn() }),
}))

vi.mock('../../hooks/useRelatedFormats', () => ({
  useRelatedFormats: () => ({ formats: [] }),
}))

// Use the real translator so the modal's English copy (and interpolated
// status labels) render as users see them.
vi.mock('@/i18n', async () => {
  const actual = await vi.importActual<typeof import('@/i18n/translations')>('@/i18n/translations')
  return { t: actual.t }
})

vi.mock('@/i18n/I18nContext', () => ({
  useTranslation: () => ({
    language: 'en-US',
    t: (key: string, fallback?: string) => fallback ?? key,
  }),
  useLanguage: () => 'en-US',
  I18nProvider: ({ children }: { children: React.ReactNode }) => children,
}))

vi.mock('react-hot-toast', () => ({
  default: { success: vi.fn(), error: vi.fn() },
}))

// ---- Fixtures -----------------------------------------------------------

const ITEM = {
  id: 99,
  title: 'A Lost Book',
  author: 'Anon',
  item_type: 'book',
  status: 'available',
  isbn: null,
  publisher: null,
  publication_year: null,
  description: null,
  subjects: null,
  cover_url: null,
  page_count: null,
  location: null,
  barcode: null,
  created_at: '2026-01-01T00:00:00Z',
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
} as any

function renderModal(item = ITEM) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  mocks.listBranches.mockResolvedValue([])
  return render(
    <QueryClientProvider client={qc}>
      <PlaceHoldModal item={item} onClose={vi.fn()} onSuccess={vi.fn()} />
    </QueryClientProvider>,
  )
}

// ---- Tests --------------------------------------------------------------

describe('PlaceHoldModal — server-side NON_HOLDABLE_STATUSES (422) surfacing', () => {
  it('renders the server-provided 422 detail message inline (ITEM_NOT_HOLDABLE)', async () => {
    const user = userEvent.setup()
    const serverMsg =
      'This item is not currently available for hold (status: lost). Please ask staff if you need help finding another copy.'
    mocks.placeHold.mockRejectedValueOnce(new ApiError(serverMsg, 422, serverMsg))

    renderModal()

    await user.click(screen.getByRole('button', { name: /confirm hold/i }))

    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent(/status: lost/)
    expect(alert).toHaveTextContent(/not currently available for hold/i)
    // The generic friendly fallback (An unexpected error occurred) must NOT show.
    expect(alert.textContent).not.toMatch(/unexpected error occurred/i)
  })

  it('renders the eligibility explanation returned by the hold API', async () => {
    const user = userEvent.setup()
    const serverMsg = 'Your library card has expired. Please contact the library to renew it.'
    // placeHold normalizes API errors into Error instances before the modal sees them.
    mocks.placeHold.mockRejectedValueOnce(new Error(serverMsg))

    renderModal()

    await user.click(screen.getByRole('button', { name: /confirm hold/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent(serverMsg)
  })

  it('falls back to the generic friendly message for non-422 errors', async () => {
    const user = userEvent.setup()
    mocks.placeHold.mockRejectedValueOnce(new ApiError('Boom', 500, 'Boom'))

    renderModal()

    await user.click(screen.getByRole('button', { name: /confirm hold/i }))

    const alert = await screen.findByRole('alert')
    // friendlyErrorMessage maps 500 to a server-error blurb; the raw Boom detail must not leak.
    await waitFor(() => {
      expect(alert).toHaveTextContent(/something went wrong on our end/i)
    })
  })
})


// ---- Queue info in the modal --------------------------------------------

describe('PlaceHoldModal — hold queue info', () => {
  it('shows queue size and a rough wait estimate when the item has a queue', async () => {
    mocks.fetchApi.mockResolvedValueOnce({
      queue_size: 3,
      estimated_wait_days: 21,
      total_copies: 1,
    })

    renderModal({ ...ITEM, status: 'checked_out' })

    expect(await screen.findByText(/3 people waiting/i)).toBeInTheDocument()
    expect(screen.getByText(/roughly 3 weeks/i)).toBeInTheDocument()
  })

  it('still confirms the hold when queue info is unavailable', async () => {
    const user = userEvent.setup()
    mocks.fetchApi.mockRejectedValueOnce(new Error('network down'))
    mocks.placeHold.mockResolvedValueOnce({ id: 1 })

    renderModal({ ...ITEM, status: 'checked_out' })

    await user.click(screen.getByRole('button', { name: /confirm hold/i }))

    await waitFor(() => {
      expect(mocks.placeHold).toHaveBeenCalledWith('test-token', ITEM.id, undefined)
    })
    expect(screen.queryByText(/waiting/i)).not.toBeInTheDocument()
  })

  it('does not fetch queue info for available items', () => {
    mocks.fetchApi.mockClear()
    renderModal()
    expect(mocks.fetchApi).not.toHaveBeenCalled()
  })
})

// ---- i18n / status enum surfacing -----------------------------------------

describe('PlaceHoldModal — translated copy and status labels', () => {
  it('renders a human status label instead of the raw enum', async () => {
    mocks.fetchApi.mockResolvedValueOnce({ queue_size: 0, estimated_wait_days: null, total_copies: 1 })
    renderModal({ ...ITEM, status: 'checked_out' })

    expect(
      await screen.findByText(/this item is currently checked out\./i),
    ).toBeInTheDocument()
    // Raw enum must not leak into the UI.
    expect(screen.queryByText(/checked_out/)).not.toBeInTheDocument()
  })

  it('renders translated modal chrome (title, labels, buttons)', () => {
    renderModal()

    expect(screen.getByRole('heading', { name: 'Place Hold' })).toBeInTheDocument()
    expect(screen.getByLabelText('Format')).toBeInTheDocument()
    expect(screen.getByLabelText('Pickup location')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Cancel' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /confirm hold/i })).toBeInTheDocument()
  })
})
