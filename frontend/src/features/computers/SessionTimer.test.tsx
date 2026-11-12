/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, act } from '@testing-library/react'
import { SessionTimer } from './SessionTimer'
import type { ComputerSession } from '@/types/computer'

function makeSession(overrides: Partial<ComputerSession> = {}): ComputerSession {
  const now = new Date('2026-05-12T12:00:00Z')
  return {
    id: 1,
    reservation_id: 1,
    computer_id: 1,
    session_start_time: now.toISOString(),
    session_end_time: new Date(now.getTime() + 60 * 60 * 1000).toISOString(),
    is_active: true,
    was_extended: false,
    extension_count: 0,
    user_initiated_logout: false,
    auto_logout_executed: false,
    print_jobs_count: 0,
    created_at: now.toISOString(),
    updated_at: now.toISOString(),
    ...overrides,
  }
}

describe('SessionTimer', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-05-12T12:00:00Z'))
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('renders a countdown that decrements after 1 second', () => {
    const session = makeSession()
    render(<SessionTimer session={session} />)

    // At t=0, remaining = 60:00
    const initial = screen.getByText('60:00')
    expect(initial).toBeInTheDocument()

    act(() => { vi.advanceTimersByTime(1000) })

    expect(screen.getByText('59:59')).toBeInTheDocument()
  })

  it('shows the warning alert with computed minutes when < 5 minutes remain', () => {
    const session = makeSession({
      session_end_time: new Date('2026-05-12T12:03:00Z').toISOString(),
    })
    render(<SessionTimer session={session} />)

    const alerts = screen.getAllByRole('alert')
    // First alert is the warning banner
    expect(alerts.length).toBeGreaterThan(0)
    // 3 minutes remaining
    expect(alerts[0]!.textContent).toMatch(/3/)
  })

  it('renders expired state and Log Off Now button when time is up', () => {
    const session = makeSession({
      session_end_time: new Date('2026-05-12T11:55:00Z').toISOString(),
    })
    const onLogoff = vi.fn()
    render(<SessionTimer session={session} onLogoff={onLogoff} />)

    expect(screen.getByText('0:00')).toBeInTheDocument()
    // expired state shows the dedicated Log Off Now button
    const buttons = screen.getAllByRole('button')
    expect(buttons.length).toBe(1)
    fireEvent.click(buttons[0]!)
    expect(onLogoff).toHaveBeenCalledTimes(1)
  })

  it('Extend button click calls onExtensionRequest', () => {
    const session = makeSession()
    const onExtensionRequest = vi.fn()
    render(<SessionTimer session={session} onExtensionRequest={onExtensionRequest} />)

    const buttons = screen.getAllByRole('button')
    // first button in the active row is Extend (per JSX order)
    fireEvent.click(buttons[0]!)
    expect(onExtensionRequest).toHaveBeenCalledTimes(1)
  })

  it('Logoff button click calls onLogoff (active state)', () => {
    const session = makeSession()
    const onLogoff = vi.fn()
    render(<SessionTimer session={session} onLogoff={onLogoff} />)

    const buttons = screen.getAllByRole('button')
    fireEvent.click(buttons[buttons.length - 1]!)
    expect(onLogoff).toHaveBeenCalledTimes(1)
  })

  it('progress bar width is a finite number (no NaN) when session_start_time is supplied', () => {
    const session = makeSession()
    const { container } = render(<SessionTimer session={session} />)

    const progress = container.querySelector('[style*="width"]') as HTMLElement
    expect(progress).not.toBeNull()
    const widthStyle = progress.style.width
    expect(widthStyle).toMatch(/^\d+(\.\d+)?%$/)
    expect(widthStyle).not.toMatch(/NaN/)
  })
})
