/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'

vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => ({ token: 'test-token', user: { id: 1 } }),
}))

const redeemMock = vi.fn()
vi.mock('@/api/domains/content/reading-programs-api', () => ({
  redeemPaperLog: (..._args: unknown[]) => redeemMock(..._args),
}))

vi.mock('@/lib/api-client', () => ({
  isApiError: (e: unknown) =>
    typeof e === 'object' && e !== null && 'status' in e && 'detail' in e,
}))

import PaperLogRedeemPage from '../PaperLogRedeemPage'


function renderWithCode(code?: string) {
  const initial = code ? `/programs/redeem?code=${code}` : '/programs/redeem'
  return render(
    <MemoryRouter initialEntries={[initial]}>
      <PaperLogRedeemPage />
    </MemoryRouter>,
  )
}

describe('PaperLogRedeemPage', () => {
  it('pre-fills code from URL ?code= param', () => {
    renderWithCode('ABCD1234')
    const input = screen.getByLabelText(/claim code/i) as HTMLInputElement
    expect(input.value).toBe('ABCD1234')
  })

  it('submits redemption and shows success summary with entries_created and goal_percent', async () => {
    redeemMock.mockResolvedValueOnce({
      registration_id: 1,
      program_id: 5,
      entries_created: 3,
      new_achievements: 1,
      total_books: 3,
      total_minutes: 90,
      total_pages: 0,
      goal_percent: 30.0,
    })
    renderWithCode('ABCD1234')
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: /submit reading log/i }))
    expect(await screen.findByText(/reading log credited/i)).toBeInTheDocument()
    expect(screen.getByText('3')).toBeInTheDocument()
    expect(screen.getByText(/30\.0%/)).toBeInTheDocument()
    expect(screen.getByText('1')).toBeInTheDocument()
  })

  it('shows already-redeemed error on 409', async () => {
    redeemMock.mockRejectedValueOnce({ status: 409, detail: 'dup' })
    renderWithCode('ABCD1234')
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: /submit reading log/i }))
    expect(await screen.findByRole('alert')).toHaveTextContent(/already redeemed/i)
  })

  it('shows expired error on 410', async () => {
    redeemMock.mockRejectedValueOnce({ status: 410, detail: 'gone' })
    renderWithCode('ABCD1234')
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: /submit reading log/i }))
    expect(await screen.findByRole('alert')).toHaveTextContent(/code expired/i)
  })
})
