/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi, beforeEach } from 'vitest'

import CollectionAnalyticsPage from './CollectionAnalyticsPage'
import {
  getAnalyticsCollectionUsage,
  getAnalyticsCollectionDetails,
} from '../../api/analytics-api'

vi.mock('../../api/analytics-api', () => ({
  getAnalyticsCollectionUsage: vi.fn(),
  getAnalyticsCollectionDetails: vi.fn(),
}))

vi.mock('../../contexts/AuthContext', () => ({
  useAuth: () => ({ token: 'test-token' }),
}))

vi.mock('../../components/shells', () => ({
  AdminShell: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}))

const SAVED_VIEW_KEY = 'l30:collection-analytics-view'

function wrap(node: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return (
    <QueryClientProvider client={qc}>
      <MemoryRouter>{node}</MemoryRouter>
    </QueryClientProvider>
  )
}

describe('CollectionAnalyticsPage save-view', () => {
  beforeEach(() => {
    // setup.ts globally stubs localStorage with no-op vi.fn()s; back them
    // with a real in-memory store so the save/restore round-trip is exercised.
    const store = new Map<string, string>()
    ;(localStorage.getItem as ReturnType<typeof vi.fn>).mockImplementation(
      (k: string) => (store.has(k) ? store.get(k)! : null)
    )
    ;(localStorage.setItem as ReturnType<typeof vi.fn>).mockImplementation(
      (k: string, v: string) => {
        store.set(k, v)
      }
    )
    ;(localStorage.clear as ReturnType<typeof vi.fn>).mockImplementation(() => {
      store.clear()
    })
    localStorage.clear()
    ;(getAnalyticsCollectionUsage as ReturnType<typeof vi.fn>).mockResolvedValue({
      totalTitles: 0,
      turnoverRate: 0,
      neverCirculated: 0,
      byCategory: [],
    })
    ;(getAnalyticsCollectionDetails as ReturnType<typeof vi.fn>).mockResolvedValue({
      totalItems: 0,
      avgCheckoutsPerItem: 0,
      avgAgeYears: 0,
      byCondition: {},
      topCirculated: [],
      leastCirculated: [],
      costEfficiency: { copiesWithCost: 0 },
    })
  })

  it('persists the selected preset to localStorage when the view is saved', async () => {
    render(wrap(<CollectionAnalyticsPage />))
    // pick a non-default preset
    fireEvent.click(screen.getByRole('button', { name: '7 days' }))
    fireEvent.click(
      screen.getByRole('button', { name: /save this view/i })
    )
    await waitFor(() => {
      const stored = JSON.parse(localStorage.getItem(SAVED_VIEW_KEY) || '{}')
      expect(stored.preset).toBe('7d')
    })
  })

  it('restores the saved preset on mount', async () => {
    localStorage.setItem(
      SAVED_VIEW_KEY,
      JSON.stringify({ preset: '90d', customStart: '', customEnd: '' })
    )
    render(wrap(<CollectionAnalyticsPage />))
    // The restored preset button is the active one (rose background).
    const btn = await screen.findByRole('button', { name: '90 days' })
    expect(btn.className).toMatch(/bg-lsc-rose/)
  })
})
