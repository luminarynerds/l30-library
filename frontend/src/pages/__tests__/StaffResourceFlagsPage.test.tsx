/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * Vitest for StaffResourceFlagsPage -- the queue UI under
 * /staff/parent-onboarding/resource-flags.
 */
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, expect, it, vi, beforeEach } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import type { ReactNode } from 'react'

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string, params?: Record<string, unknown>) => {
      if (!params) return key
      return `${key} ${Object.entries(params).map(([k, v]) => `${k}=${v}`).join(' ')}`
    },
    i18n: { language: 'en' },
  }),
}))

vi.mock('@/lib/sentry-lazy', () => ({
  captureException: vi.fn(),
  addBreadcrumb: vi.fn(),
}))

vi.mock('react-hot-toast', () => ({
  default: { success: vi.fn(), error: vi.fn() },
}))

vi.mock('../../components/shells/AdminShell', () => ({
  AdminShell: ({ children }: { children: ReactNode }) => (
    <div data-testid="admin-shell">{children}</div>
  ),
}))

const listMock = vi.fn()
const patchMock = vi.fn()
const verifyMock = vi.fn()

vi.mock('@/api/parent-onboarding-api', () => ({
  listResourceGuideFlags: (...a: unknown[]) => listMock(...a),
  patchResourceGuideFlag: (...a: unknown[]) => patchMock(...a),
  verifyResourceGuideItem: (...a: unknown[]) => verifyMock(...a),
}))

import StaffResourceFlagsPage from '../StaffResourceFlagsPage'

function withClient(ui: ReactNode) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return (
    <MemoryRouter>
      <QueryClientProvider client={client}>{ui}</QueryClientProvider>
    </MemoryRouter>
  )
}

beforeEach(() => {
  listMock.mockReset()
  patchMock.mockReset()
  verifyMock.mockReset()
})

describe('StaffResourceFlagsPage', () => {
  it('shows an empty-state when no flags are open', async () => {
    listMock.mockResolvedValue([])
    render(withClient(<StaffResourceFlagsPage />))
    // Wait for the empty-state copy directly; query returns [] so the
    // table never renders and the empty paragraph appears once loading
    // resolves.
    await screen.findByText('parentResources.queue.empty')
    expect(screen.queryByRole('table')).toBeNull()
  })

  it('renders one row per flag with item title + reason', async () => {
    listMock.mockResolvedValue([
      {
        id: 1,
        item_id: 11,
        reason_code: 'disconnected_phone',
        comment: 'Called three times.',
        status: 'open',
        created_at: '2026-04-01T10:00:00Z',
        updated_at: '2026-04-01T10:00:00Z',
        flagged_by_name: 'Rosa T.',
        item: {
          id: 11,
          section_id: 1,
          title: 'WIC Office',
          contact_info: '(555) 555-5555',
        },
      },
      {
        id: 2,
        item_id: 12,
        reason_code: 'wrong_address',
        status: 'open',
        created_at: '2026-04-02T10:00:00Z',
        updated_at: '2026-04-02T10:00:00Z',
        flagged_by_name: 'Sam C.',
        item: {
          id: 12,
          section_id: 1,
          title: 'Local Shelter',
        },
      },
    ])
    render(withClient(<StaffResourceFlagsPage />))
    await screen.findByTestId('flag-row-1')
    await screen.findByTestId('flag-row-2')
    expect(screen.getByText('WIC Office')).toBeTruthy()
    expect(screen.getByText('Local Shelter')).toBeTruthy()
  })

  it('clicking "Verify as current" calls verifyResourceGuideItem with the item_id', async () => {
    listMock.mockResolvedValue([
      {
        id: 1,
        item_id: 11,
        reason_code: 'disconnected_phone',
        status: 'open',
        created_at: '2026-04-01T10:00:00Z',
        updated_at: '2026-04-01T10:00:00Z',
        flagged_by_name: 'Rosa T.',
        item: { id: 11, section_id: 1, title: 'WIC Office' },
      },
    ])
    verifyMock.mockResolvedValue({ id: 11 })
    render(withClient(<StaffResourceFlagsPage />))
    const btn = await screen.findByTestId('queue-verify-1')
    fireEvent.click(btn)
    await waitFor(() => expect(verifyMock).toHaveBeenCalledWith(11))
  })

  it('clicking "Dismiss" calls patch with status=dismissed/resolution=invalid', async () => {
    listMock.mockResolvedValue([
      {
        id: 7,
        item_id: 11,
        reason_code: 'other',
        status: 'open',
        created_at: '2026-04-01T10:00:00Z',
        updated_at: '2026-04-01T10:00:00Z',
        flagged_by_name: 'Sam C.',
        item: { id: 11, section_id: 1, title: 'Test Item' },
      },
    ])
    patchMock.mockResolvedValue({ id: 7 })
    render(withClient(<StaffResourceFlagsPage />))
    const btn = await screen.findByTestId('queue-dismiss-7')
    fireEvent.click(btn)
    await waitFor(() =>
      expect(patchMock).toHaveBeenCalledWith(7, {
        status: 'dismissed',
        resolution: 'invalid',
      }),
    )
  })
})
