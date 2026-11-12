/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import {
  describe,
  it,
  expect,
  vi,
  beforeAll,
  beforeEach,
} from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { loadLanguage, getTranslation } from '@/i18n/translations'

vi.mock('@/i18n', async () => {
  const actual = await vi.importActual<typeof import('@/i18n')>('@/i18n')
  return {
    ...actual,
    t: (key: string, params?: Record<string, unknown> | string) =>
      typeof params === 'string'
        ? getTranslation(key, 'en', undefined, params)
        : getTranslation(key, 'en', params),
  }
})

vi.mock('react-hot-toast', () => ({
  default: { success: vi.fn(), error: vi.fn() },
}))

vi.mock('@/utils/tokenStore', () => ({
  getAccessToken: () => 'test-token',
}))

const getWaitlistMock = vi.fn()
const removeEntryMock = vi.fn()
vi.mock('@/api/domains/content/book-clubs-api', () => ({
  getBookClubWaitlist: (...a: unknown[]) => getWaitlistMock(...a),
  removeBookClubWaitlistEntry: (...a: unknown[]) => removeEntryMock(...a),
}))

import { StaffBookClubWaitlistModal } from '../StaffBookClubWaitlistModal'

beforeAll(async () => {
  await loadLanguage('en')
})

function renderModal() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  const onClose = vi.fn()
  render(
    <QueryClientProvider client={qc}>
      <StaffBookClubWaitlistModal
        clubId={7}
        clubName='Mystery Lovers'
        onClose={onClose}
      />
    </QueryClientProvider>,
  )
  return { onClose }
}

beforeEach(() => {
  getWaitlistMock.mockReset()
  removeEntryMock.mockReset()
})

describe('StaffBookClubWaitlistModal', () => {
  it('renders the FIFO note and the empty state when no one is waiting', async () => {
    getWaitlistMock.mockResolvedValue({ club_id: 7, total: 0, entries: [] })
    renderModal()
    await waitFor(() =>
      expect(
        screen.getByText(/No one is on the waitlist/i),
      ).toBeInTheDocument(),
    )
    expect(
      screen.getByText(/first-in, first-out/i),
    ).toBeInTheDocument()
  })

  it('renders one row per entry with position, name, email, joined date', async () => {
    getWaitlistMock.mockResolvedValue({
      club_id: 7,
      total: 2,
      entries: [
        {
          id: 1,
          user_id: 11,
          position: 1,
          display_name: 'Ada Lovelace',
          email: 'ada@example.org',
          created_at: '2026-02-01T00:00:00Z',
          notified_at: null,
        },
        {
          id: 2,
          user_id: 12,
          position: 2,
          display_name: 'Grace Hopper',
          email: null,
          created_at: '2026-02-02T00:00:00Z',
          notified_at: null,
        },
      ],
    })
    renderModal()
    await waitFor(() =>
      expect(screen.getByText('Ada Lovelace')).toBeInTheDocument(),
    )
    expect(screen.getByText('ada@example.org')).toBeInTheDocument()
    expect(screen.getByText('Grace Hopper')).toBeInTheDocument()
    // null email renders the placeholder
    expect(screen.getAllByText('--').length).toBeGreaterThanOrEqual(1)
  })

  it('shows the load-error state when the API throws (e.g. flag off → 404)', async () => {
    getWaitlistMock.mockRejectedValue(new Error('404'))
    renderModal()
    await waitFor(() =>
      expect(
        screen.getByText(/Could not load the waitlist/i),
      ).toBeInTheDocument(),
    )
  })

  it('removes an entry via the per-row remove button', async () => {
    getWaitlistMock
      .mockResolvedValueOnce({
        club_id: 7,
        total: 1,
        entries: [
          {
            id: 1,
            user_id: 11,
            position: 1,
            display_name: 'Ada Lovelace',
            email: 'ada@example.org',
            created_at: '2026-02-01T00:00:00Z',
            notified_at: null,
          },
        ],
      })
      .mockResolvedValueOnce({ club_id: 7, total: 0, entries: [] })
    removeEntryMock.mockResolvedValue(undefined)
    renderModal()
    const btn = await screen.findByRole('button', {
      name: /Remove Ada Lovelace from the waitlist/i,
    })
    await userEvent.click(btn)
    await waitFor(() =>
      expect(removeEntryMock).toHaveBeenCalledWith(7, 11, 'test-token'),
    )
    await waitFor(() =>
      expect(
        screen.getByText(/No one is on the waitlist/i),
      ).toBeInTheDocument(),
    )
  })
})
