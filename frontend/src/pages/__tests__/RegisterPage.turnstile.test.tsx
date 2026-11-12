/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '../../__tests__/utils/test-utils'
import userEvent from '@testing-library/user-event'

// RegisterPage was rewritten (#1484) as an invite-only waiting-list form: it
// posts directly to /waitlist via fetchApi and no longer builds an account
// (no AuthContext.register(), no multi-step flow, no Turnstile widget --
// bot-check on new-patron intake now lives on the staff-reviewed Card
// Application flow instead). This test used to pin the Turnstile token
// getting threaded through register() on submit; that flow doesn't exist on
// this page anymore, so it's retargeted to the equivalent current contract:
// the waiting-list submission reaches the backend with the right payload.
const { mockFetchApi } = vi.hoisted(() => ({ mockFetchApi: vi.fn() }))
vi.mock('@/api/fetchApi', () => ({
  fetchApi: (...args: unknown[]) => mockFetchApi(...args),
}))

import RegisterPage from '../RegisterPage'

function renderPage() {
  return render(<RegisterPage />)
}

describe('RegisterPage waiting-list wiring', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockFetchApi.mockResolvedValue({})
  })

  it('posts the email to /waitlist on submit', async () => {
    const user = userEvent.setup()
    renderPage()

    await user.type(screen.getByLabelText(/email/i), 'ada@example.com')
    await user.click(screen.getByRole('button', { name: /join the waiting list/i }))

    await waitFor(() => {
      expect(mockFetchApi).toHaveBeenCalledTimes(1)
    })
    const [path, init] = mockFetchApi.mock.calls[0]!
    expect(path).toBe('/waitlist')
    expect(JSON.parse(init.body)).toMatchObject({
      email: 'ada@example.com',
      source: 'register',
    })
  })
})
