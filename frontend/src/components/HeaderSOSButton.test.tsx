/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { act, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import HeaderSOSButton from './HeaderSOSButton'

const triggerPanicAlertMock = vi.fn(async (..._args: unknown[]) => ({ id: 42 }))
const resolvePanicAlertMock = vi.fn(async (..._args: unknown[]) => ({}))

vi.mock('@/api/panic-alert-api', () => ({
  triggerPanicAlert: (...args: unknown[]) => triggerPanicAlertMock(...args),
  resolvePanicAlert: (...args: unknown[]) => resolvePanicAlertMock(...args),
}))

vi.mock('react-hot-toast', () => ({
  default: { error: vi.fn(), success: vi.fn() },
}))

vi.mock('@/i18n/I18nContext', () => ({
  useTranslation: () => ({
    t: (key: string, defaultValue?: string) => {
      const map: Record<string, string> = {
        'components.headerSOSButton.cancelAlertFalseAlarm': 'Cancel alert — false alarm',
        'components.headerSOSButton.oops': 'Oops',
        'components.headerSOSButton.cancelWithCountdown': 'Oops — false alarm ({{count}}s)',
        'components.headerSOSButton.help': 'Help',
        'components.headerSOSButton.needHelp': 'Need help?',
        'components.headerSOSButton.otherSendAlert': 'Other — Send Alert',
        'components.headerSOSButton.alertSent': 'Alert sent',
        'components.headerSOSButton.alertCancelled': 'Alert cancelled',
        'aria.discretePanicButton.help': 'Help',
        'aria.headerSOSButton.emergencyAlert': 'Emergency alert',
      }
      return map[key] ?? defaultValue ?? key
    },
  }),
}))

async function triggerAlert() {
  fireEvent.click(screen.getByRole('button', { name: 'Help' }))
  fireEvent.click(screen.getByRole('button', { name: 'Other — Send Alert' }))
  await act(async () => {
    await Promise.resolve()
  })
}

describe('HeaderSOSButton countdown', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    triggerPanicAlertMock.mockClear()
    resolvePanicAlertMock.mockClear()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('shows a countdown that ticks down on the cancel button after sending', async () => {
    render(<HeaderSOSButton />)
    await triggerAlert()

    expect(screen.getByText('Oops — false alarm (30s)')).toBeInTheDocument()

    await act(async () => {
      vi.advanceTimersByTime(1000)
    })
    expect(screen.getByText('Oops — false alarm (29s)')).toBeInTheDocument()

    await act(async () => {
      vi.advanceTimersByTime(5000)
    })
    expect(screen.getByText('Oops — false alarm (24s)')).toBeInTheDocument()
  })

  it('resets to idle and clears the countdown when the 30s timer fires', async () => {
    render(<HeaderSOSButton />)
    await triggerAlert()

    await act(async () => {
      vi.advanceTimersByTime(30000)
    })

    expect(screen.getByRole('button', { name: 'Help' })).toBeInTheDocument()
  })

  it('clears the countdown interval when cancel is pressed', async () => {
    render(<HeaderSOSButton />)
    await triggerAlert()

    await act(async () => {
      vi.advanceTimersByTime(3000)
    })

    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Cancel alert — false alarm' }))
      await Promise.resolve()
    })

    expect(resolvePanicAlertMock).toHaveBeenCalledWith(42, 'False alarm — cancelled by user')
    expect(screen.getByRole('button', { name: 'Help' })).toBeInTheDocument()

    // Advancing time after cancel should not throw or resurrect the countdown button.
    await act(async () => {
      vi.advanceTimersByTime(30000)
    })
    expect(screen.getByRole('button', { name: 'Help' })).toBeInTheDocument()
  })

  it('clears timers on unmount without throwing', async () => {
    const { unmount } = render(<HeaderSOSButton />)
    await triggerAlert()

    expect(() => unmount()).not.toThrow()

    expect(() => {
      vi.advanceTimersByTime(30000)
    }).not.toThrow()
  })
})
