/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * Covers /card-application/status/:token (Issue #1028):
 * - Loading state surfaces while the lookup is in flight.
 * - Valid token renders status + submitted date + estimated-decision-by.
 * - 404 / invalid token surfaces a role=alert with the "link not valid" copy
 *   (not "no application found" — that copy would oracle the existence).
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (_key: string, fallback?: string) => fallback ?? _key,
  }),
}))

const checkApplicationByTokenMock = vi.fn()
vi.mock('@/api/card-applications-api', () => ({
  checkApplicationByToken: (...args: unknown[]) =>
    checkApplicationByTokenMock(...args),
}))

import CardApplicationStatusPage from '../CardApplicationStatusPage'

function renderPage(token: string) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[`/card-application/status/${token}`]}>
        <Routes>
          <Route
            path="/card-application/status/:token"
            element={<CardApplicationStatusPage />}
          />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

beforeEach(() => {
  checkApplicationByTokenMock.mockReset()
})

describe('CardApplicationStatusPage', () => {
  it('shows the loading state while the lookup is in flight', () => {
    checkApplicationByTokenMock.mockReturnValue(new Promise(() => {}))
    renderPage('tok-loading')
    expect(
      screen.getByText(/looking up your application/i),
    ).toBeInTheDocument()
  })

  it('renders pending status + submitted date label', async () => {
    checkApplicationByTokenMock.mockResolvedValue({
      status: 'pending',
      submitted_at: '2026-05-18T12:00:00Z',
      reviewed_at: null,
    })
    renderPage('tok-ok')

    await waitFor(() => {
      expect(screen.getByText(/pending review/i)).toBeInTheDocument()
    })

    // The "Submitted" dt label anchors the formatted date next to it; copy
    // intentionally omits a calendar "decision by" date -- the few-business-
    // days promise lives in the status blurb to avoid weekend-vs-email drift.
    expect(screen.getByText(/^submitted$/i)).toBeInTheDocument()
    expect(
      screen.getByText(/usually made within a few business days/i),
    ).toBeInTheDocument()
  })

  it('shows the generic "link not valid" alert on 404 (no oracle copy)', async () => {
    checkApplicationByTokenMock.mockRejectedValue(
      new Error('This status link is invalid or has expired.'),
    )
    renderPage('tok-bogus')

    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent(/link not valid/i)
    expect(alert).toHaveTextContent(/invalid or has expired/i)
    // Must NOT say anything implying we DID/DIDN'T find a row.
    expect(alert).not.toHaveTextContent(/no application found/i)
  })
})
