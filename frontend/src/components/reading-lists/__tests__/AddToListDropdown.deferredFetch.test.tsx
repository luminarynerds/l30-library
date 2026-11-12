/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, expect, it, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AddToListDropdown } from '../AddToListDropdown'

vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => ({ token: 'test-token', user: { id: 1 } }),
}))

vi.mock('react-hot-toast', () => ({
  default: vi.fn(Object.assign(() => {}, { error: vi.fn(), success: vi.fn() })),
}))

const getListsContainingItemMock = vi.fn(async (..._args: unknown[]) => [] as number[])
vi.mock('@/api/domains/content/reading-lists-api', () => ({
  getMyReadingLists: vi.fn(async () => []),
  getListsContainingItem: (...args: unknown[]) => getListsContainingItemMock(...args),
  addItemToList: vi.fn(async () => ({})),
  removeItemFromList: vi.fn(async () => ({})),
  createReadingList: vi.fn(async () => ({})),
}))

function renderDropdown() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={qc}>
      <AddToListDropdown catalogItemId={42} />
    </QueryClientProvider>,
  )
}

describe('AddToListDropdown — deferred membership fetch', () => {
  beforeEach(() => {
    getListsContainingItemMock.mockClear()
  })

  it('does not fetch list membership on mount (avoids per-card fan-out)', async () => {
    renderDropdown()
    // Give React Query a tick to flush any eager queries.
    await waitFor(() => {
      expect(screen.getByLabelText('Add to reading list')).toBeInTheDocument()
    })
    expect(getListsContainingItemMock).not.toHaveBeenCalled()
  })

  it('fetches list membership once the dropdown is opened', async () => {
    const user = userEvent.setup()
    renderDropdown()
    await user.click(screen.getByLabelText('Add to reading list'))
    await waitFor(() => {
      expect(getListsContainingItemMock).toHaveBeenCalledWith('test-token', 42)
    })
  })
})
