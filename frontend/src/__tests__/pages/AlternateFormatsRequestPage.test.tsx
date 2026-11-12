/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/// <reference types="vitest/globals" />
import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'

// StaffLayout (via AdminShell) needs AuthContext + Preferences + sidebar config.
// Pass-through so this test focuses on the page itself.
vi.mock('@/components/staff/StaffLayout', () => ({
  StaffLayout: ({
    title,
    children,
  }: {
    title?: string
    children: React.ReactNode
  }) => (
    <div data-testid="staff-layout">
      {title ? <div data-testid="staff-layout-title">{title}</div> : null}
      {children}
    </div>
  ),
}))

vi.mock('@/lib/sentry-lazy', () => ({
  init: vi.fn(),
  captureException: vi.fn(),
  captureMessage: vi.fn(),
  addBreadcrumb: vi.fn(),
}))

import AlternateFormatsRequestPage from '@/pages/AlternateFormatsRequestPage'

const fetchMock = vi.fn((): Promise<{ ok: boolean; json: () => Promise<unknown> }> =>
  Promise.resolve({ ok: true, json: () => Promise.resolve({}) }),
)
global.fetch = fetchMock as unknown as typeof fetch

describe('AlternateFormatsRequestPage', () => {
  beforeEach(() => {
    fetchMock.mockClear()
  })

  it('describes the UDL feature in plain terms', () => {
    render(
      <MemoryRouter>
        <AlternateFormatsRequestPage />
      </MemoryRouter>,
    )
    expect(
      screen.getByText(/Multiple Means of Representation/i),
    ).toBeInTheDocument()
  })

  it('collects which lesson the requester would add an alternate format to first', async () => {
    render(
      <MemoryRouter>
        <AlternateFormatsRequestPage />
      </MemoryRouter>,
    )
    const which = screen.getByLabelText(
      /Which lesson would you add an alternate format to first/i,
    )
    const email = screen.getByLabelText(/your email/i)
    fireEvent.change(which, {
      target: { value: 'Intro to Genealogy lesson 3' },
    })
    fireEvent.change(email, { target: { value: 'trish@example.org' } })
    fireEvent.click(screen.getByRole('button', { name: /send request/i }))
    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/feature-requests'),
        expect.objectContaining({ method: 'POST' }),
      ),
    )
  })

  it('does NOT promise a ship date (no "coming soon" / no quarter dates)', () => {
    render(
      <MemoryRouter>
        <AlternateFormatsRequestPage />
      </MemoryRouter>,
    )
    expect(screen.queryByText(/coming soon/i)).toBeNull()
    expect(screen.queryByText(/Q[1-4] 202\d/)).toBeNull()
  })

  it('disables the submit button while the request is in flight, then re-enables on error', async () => {
    // Hold the fetch open so we can observe the in-flight disabled state.
    let resolveFetch: (value: { ok: boolean; json: () => Promise<unknown> }) => void = () => {}
    const pending = new Promise<{ ok: boolean; json: () => Promise<unknown> }>(
      (resolve) => {
        resolveFetch = resolve
      },
    )
    fetchMock.mockImplementationOnce(() => pending)

    render(
      <MemoryRouter>
        <AlternateFormatsRequestPage />
      </MemoryRouter>,
    )
    fireEvent.change(
      screen.getByLabelText(
        /Which lesson would you add an alternate format to first/i,
      ),
      { target: { value: 'Lesson 1' } },
    )
    fireEvent.change(screen.getByLabelText(/your email/i), {
      target: { value: 'a@b.org' },
    })

    const button = screen.getByRole('button', { name: /send request/i })
    fireEvent.click(button)

    // In-flight: button is disabled, label flips to Sending.
    await waitFor(() => {
      expect(
        screen.getByRole('button', { name: /sending/i }),
      ).toBeDisabled()
    })

    // A second click while in-flight must NOT fire a second POST.
    fireEvent.click(screen.getByRole('button', { name: /sending/i }))
    expect(fetchMock).toHaveBeenCalledTimes(1)

    // Resolve as a non-ok response -> error path.
    resolveFetch({ ok: false, json: () => Promise.resolve({}) })

    // After error path: button re-enabled and back to original label.
    await waitFor(() =>
      expect(
        screen.getByRole('button', { name: /send request/i }),
      ).not.toBeDisabled(),
    )
    expect(screen.getByRole('alert')).toHaveTextContent(/couldn't record/i)
  })

  it('disables the submit button while the request is in flight, then hides it on success', async () => {
    let resolveFetch: (value: { ok: boolean; json: () => Promise<unknown> }) => void = () => {}
    const pending = new Promise<{ ok: boolean; json: () => Promise<unknown> }>(
      (resolve) => {
        resolveFetch = resolve
      },
    )
    fetchMock.mockImplementationOnce(() => pending)

    render(
      <MemoryRouter>
        <AlternateFormatsRequestPage />
      </MemoryRouter>,
    )
    fireEvent.change(
      screen.getByLabelText(
        /Which lesson would you add an alternate format to first/i,
      ),
      { target: { value: 'Lesson 2' } },
    )
    fireEvent.change(screen.getByLabelText(/your email/i), {
      target: { value: 'c@d.org' },
    })
    fireEvent.click(screen.getByRole('button', { name: /send request/i }))

    await waitFor(() =>
      expect(
        screen.getByRole('button', { name: /sending/i }),
      ).toBeDisabled(),
    )

    resolveFetch({ ok: true, json: () => Promise.resolve({}) })

    // Success: form is replaced by the thank-you status; button is gone.
    await waitFor(() =>
      expect(screen.getByRole('status')).toHaveTextContent(/Thanks/i),
    )
    expect(
      screen.queryByRole('button', { name: /send request/i }),
    ).toBeNull()
  })
})
