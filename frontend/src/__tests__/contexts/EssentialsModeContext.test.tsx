/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { EssentialsModeProvider, useEssentialsMode } from '../../contexts/EssentialsModeContext'
import { API_BASE } from '@/api/types'

const mockUseAuth = vi.fn()
const mockApiPatch = vi.fn()

vi.mock('../../contexts/AuthContext', () => ({
  useAuth: () => mockUseAuth(),
}))

vi.mock('../../lib/api-client', () => ({
  default: {
    patch: (...args: unknown[]) => mockApiPatch(...args),
  },
}))

function TestHarness() {
  const { isEssentialsMode, toggleMode } = useEssentialsMode()

  return (
    <>
      <div data-testid="mode">{isEssentialsMode ? 'essentials' : 'full'}</div>
      <button onClick={() => void toggleMode()}>toggle</button>
    </>
  )
}

describe('EssentialsModeContext', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('toggles locally for guests (no API call)', async () => {
    mockUseAuth.mockReturnValue({
      user: null,
      token: null,
      isAuthenticated: false,
    })

    const user = userEvent.setup()
    render(
      <EssentialsModeProvider>
        <TestHarness />
      </EssentialsModeProvider>
    )

    // "L30: Guests see the full editorial experience" (EssentialsModeContext.tsx)
    // — isEssentialsMode defaults to false for guests, not true.
    expect(screen.getByTestId('mode')).toHaveTextContent('full')

    await user.click(screen.getByRole('button', { name: /toggle/i }))

    expect(screen.getByTestId('mode')).toHaveTextContent('essentials')
    expect(mockApiPatch).not.toHaveBeenCalled()
  })

  it('persists authenticated mode changes via auth endpoint', async () => {
    mockUseAuth.mockReturnValue({
      user: { ui_mode: 'essentials' },
      token: 'token-123',
      isAuthenticated: true,
    })
    mockApiPatch.mockResolvedValue({ data: {} })

    const user = userEvent.setup()
    render(
      <EssentialsModeProvider>
        <TestHarness />
      </EssentialsModeProvider>
    )

    expect(screen.getByTestId('mode')).toHaveTextContent('essentials')

    await user.click(screen.getByRole('button', { name: /toggle/i }))

    await waitFor(() => {
      expect(mockApiPatch).toHaveBeenCalledWith(`${API_BASE}/auth/me/ui-mode`, { ui_mode: 'full' })
    })

    expect(screen.getByTestId('mode')).toHaveTextContent('full')
  })
})