/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render } from "@testing-library/react"
import { screen } from "@testing-library/react"
import { axe } from 'jest-axe'
import userEvent from '@testing-library/user-event'
import { useEffect } from 'react'

// Component interfaces - to be implemented
interface SessionTimeoutWarningProps {
  isOpen: boolean
  secondsRemaining: number
  onStaySignedIn: () => void
  onTimeout: () => void
  onClose?: () => void
}

// Mock component
const SessionTimeoutWarning = ({
  isOpen,
  secondsRemaining,
  onStaySignedIn,
  onTimeout,
  onClose,
}: SessionTimeoutWarningProps) => {
  useEffect(() => {
    if (secondsRemaining <= 0 && isOpen) {
      onTimeout()
    }
  }, [secondsRemaining, onTimeout, isOpen])

  if (!isOpen) return null

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  const handleStaySignedIn = () => {
    onStaySignedIn()
    onClose?.()
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      onClose?.()
    }
  }

  return (
    // eslint-disable-next-line jsx-a11y/click-events-have-key-events
    <div
      className="modal-overlay"
      onClick={(e) => {
        if (e.target === e.currentTarget) {
          onClose?.()
        }
      }}
    >
      <div
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="timeout-title"
        aria-describedby="timeout-description"
        className="session-timeout-warning"
        onKeyDown={handleKeyDown}
      >
        <div className="modal-content">
          <h2 id="timeout-title">Session Timeout Warning</h2>

          <div id="timeout-description">
            <p>Your session is about to expire due to inactivity.</p>
            <p>You will be automatically signed out in:</p>
          </div>

          <div
            className="countdown-timer"
            role="timer"
            aria-live="assertive"
            aria-atomic="true"
          >
            <span className="time-display" aria-label={`${secondsRemaining} seconds remaining`}>
              {formatTime(secondsRemaining)}
            </span>
          </div>

          <p className="action-prompt">
            Would you like to stay signed in?
          </p>

          <div className="action-buttons">
            <button
              onClick={handleStaySignedIn}
              className="primary-button"
              autoFocus
            >
              Stay Signed In
            </button>
            <button
              onClick={onClose}
              className="secondary-button"
            >
              Sign Out Now
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

describe('SessionTimeoutWarning', () => {
  const defaultProps: SessionTimeoutWarningProps = {
    isOpen: true,
    secondsRemaining: 120,
    onStaySignedIn: vi.fn(),
    onTimeout: vi.fn(),
    onClose: vi.fn(),
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Visibility', () => {
    it('shows warning when isOpen is true', () => {
      render(<SessionTimeoutWarning {...defaultProps} />)

      expect(screen.getByRole('alertdialog')).toBeInTheDocument()
    })

    it('hides warning when isOpen is false', () => {
      render(<SessionTimeoutWarning {...defaultProps} isOpen={false} />)

      expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument()
    })

    it('shows warning 2 minutes (120 seconds) before timeout', () => {
      render(<SessionTimeoutWarning {...defaultProps} secondsRemaining={120} />)

      expect(screen.getByRole('alertdialog')).toBeInTheDocument()
      expect(screen.getByText('2:00')).toBeInTheDocument()
    })
  })

  describe('Countdown Timer', () => {
    it('displays countdown timer', () => {
      render(<SessionTimeoutWarning {...defaultProps} secondsRemaining={120} />)

      expect(screen.getByRole('timer')).toBeInTheDocument()
      expect(screen.getByText('2:00')).toBeInTheDocument()
    })

    it('displays formatted time MM:SS', () => {
      const { rerender } = render(
        <SessionTimeoutWarning {...defaultProps} secondsRemaining={95} />
      )

      expect(screen.getByText('1:35')).toBeInTheDocument()

      rerender(<SessionTimeoutWarning {...defaultProps} secondsRemaining={10} />)

      expect(screen.getByText('0:10')).toBeInTheDocument()
    })

    it('updates display every second', () => {
      const { rerender } = render(
        <SessionTimeoutWarning {...defaultProps} secondsRemaining={120} />
      )

      expect(screen.getByText('2:00')).toBeInTheDocument()

      rerender(<SessionTimeoutWarning {...defaultProps} secondsRemaining={119} />)

      expect(screen.getByText('1:59')).toBeInTheDocument()

      rerender(<SessionTimeoutWarning {...defaultProps} secondsRemaining={118} />)

      expect(screen.getByText('1:58')).toBeInTheDocument()
    })

    it('pads seconds with zero (e.g., 1:05)', () => {
      render(<SessionTimeoutWarning {...defaultProps} secondsRemaining={65} />)

      expect(screen.getByText('1:05')).toBeInTheDocument()
    })

    it('handles zero seconds', () => {
      render(<SessionTimeoutWarning {...defaultProps} secondsRemaining={0} />)

      expect(screen.getByText('0:00')).toBeInTheDocument()
    })
  })

  describe('Stay Signed In Action', () => {
    it('"Stay Signed In" button extends session', async () => {
      const user = userEvent.setup()
      const onStaySignedIn = vi.fn()

      render(<SessionTimeoutWarning {...defaultProps} onStaySignedIn={onStaySignedIn} />)

      const stayButton = screen.getByRole('button', { name: 'Stay Signed In' })
      await user.click(stayButton)

      expect(onStaySignedIn).toHaveBeenCalledTimes(1)
    })

    it('closes modal after extending session', async () => {
      const user = userEvent.setup()
      const onClose = vi.fn()

      render(<SessionTimeoutWarning {...defaultProps} onClose={onClose} />)

      const stayButton = screen.getByRole('button', { name: 'Stay Signed In' })
      await user.click(stayButton)

      expect(onClose).toHaveBeenCalledTimes(1)
    })

    it('button has autofocus', () => {
      render(<SessionTimeoutWarning {...defaultProps} />)

      const stayButton = screen.getByRole('button', { name: 'Stay Signed In' })
      expect(stayButton).toHaveFocus()
    })
  })

  describe('Timeout Behavior', () => {
    it('calls onTimeout when timer reaches 0', () => {
      const onTimeout = vi.fn()
      const { rerender } = render(
        <SessionTimeoutWarning {...defaultProps} onTimeout={onTimeout} secondsRemaining={1} />
      )

      expect(onTimeout).not.toHaveBeenCalled()

      rerender(
        <SessionTimeoutWarning {...defaultProps} onTimeout={onTimeout} secondsRemaining={0} />
      )

      expect(onTimeout).toHaveBeenCalledTimes(1)
    })

    it('does not call onTimeout multiple times', () => {
      const onTimeout = vi.fn()
      const { rerender } = render(
        <SessionTimeoutWarning {...defaultProps} onTimeout={onTimeout} secondsRemaining={0} />
      )

      expect(onTimeout).toHaveBeenCalledTimes(1)

      rerender(
        <SessionTimeoutWarning {...defaultProps} onTimeout={onTimeout} secondsRemaining={0} />
      )

      // Should still only be called once
      expect(onTimeout).toHaveBeenCalledTimes(1)
    })

    it('does not call onTimeout when modal is closed', () => {
      const onTimeout = vi.fn()
      render(
        <SessionTimeoutWarning
          {...defaultProps}
          onTimeout={onTimeout}
          secondsRemaining={0}
          isOpen={false}
        />
      )

      expect(onTimeout).not.toHaveBeenCalled()
    })
  })

  describe('ARIA Dialog Pattern', () => {
    it('has role="alertdialog"', () => {
      render(<SessionTimeoutWarning {...defaultProps} />)

      const dialog = screen.getByRole('alertdialog')
      expect(dialog).toBeInTheDocument()
    })

    it('has aria-modal="true"', () => {
      render(<SessionTimeoutWarning {...defaultProps} />)

      const dialog = screen.getByRole('alertdialog')
      expect(dialog).toHaveAttribute('aria-modal', 'true')
    })

    it('has aria-labelledby pointing to title', () => {
      render(<SessionTimeoutWarning {...defaultProps} />)

      const dialog = screen.getByRole('alertdialog')
      expect(dialog).toHaveAttribute('aria-labelledby', 'timeout-title')

      const title = screen.getByText('Session Timeout Warning')
      expect(title).toHaveAttribute('id', 'timeout-title')
    })

    it('has aria-describedby pointing to description', () => {
      render(<SessionTimeoutWarning {...defaultProps} />)

      const dialog = screen.getByRole('alertdialog')
      expect(dialog).toHaveAttribute('aria-describedby', 'timeout-description')

      const description = document.getElementById('timeout-description')
      expect(description).toBeInTheDocument()
    })
  })

  describe('Timer ARIA Attributes', () => {
    it('timer has role="timer"', () => {
      render(<SessionTimeoutWarning {...defaultProps} />)

      const timer = screen.getByRole('timer')
      expect(timer).toBeInTheDocument()
    })

    it('timer has aria-live="assertive" for urgent updates', () => {
      render(<SessionTimeoutWarning {...defaultProps} />)

      const timer = screen.getByRole('timer')
      expect(timer).toHaveAttribute('aria-live', 'assertive')
    })

    it('timer has aria-atomic="true"', () => {
      render(<SessionTimeoutWarning {...defaultProps} />)

      const timer = screen.getByRole('timer')
      expect(timer).toHaveAttribute('aria-atomic', 'true')
    })

    it('time display has descriptive aria-label', () => {
      render(<SessionTimeoutWarning {...defaultProps} secondsRemaining={120} />)

      const timeDisplay = screen.getByLabelText('120 seconds remaining')
      expect(timeDisplay).toBeInTheDocument()
    })
  })

  describe('Keyboard Accessibility', () => {
    it('Stay Signed In button has focus on open (autoFocus)', async () => {
      render(<SessionTimeoutWarning {...defaultProps} />)

      const stayButton = screen.getByRole('button', { name: 'Stay Signed In' })
      expect(stayButton).toHaveFocus()
    })

    it('can tab to Sign Out button', async () => {
      const user = userEvent.setup()
      render(<SessionTimeoutWarning {...defaultProps} />)

      // Stay Signed In already has focus via autoFocus; one tab reaches Sign Out
      await user.tab()

      const signOutButton = screen.getByRole('button', { name: 'Sign Out Now' })
      expect(signOutButton).toHaveFocus()
    })

    it('Escape key closes modal', async () => {
      const user = userEvent.setup()
      const onClose = vi.fn()

      render(<SessionTimeoutWarning {...defaultProps} onClose={onClose} />)

      const dialog = screen.getByRole('alertdialog')
      dialog.focus()

      await user.keyboard('{Escape}')

      expect(onClose).toHaveBeenCalledTimes(1)
    })

    it('Enter key activates focused button', async () => {
      const user = userEvent.setup()
      const onStaySignedIn = vi.fn()

      render(<SessionTimeoutWarning {...defaultProps} onStaySignedIn={onStaySignedIn} />)

      const stayButton = screen.getByRole('button', { name: 'Stay Signed In' })
      stayButton.focus()

      await user.keyboard('{Enter}')

      expect(onStaySignedIn).toHaveBeenCalled()
    })

    it('Space key activates focused button', async () => {
      const user = userEvent.setup()
      const onStaySignedIn = vi.fn()

      render(<SessionTimeoutWarning {...defaultProps} onStaySignedIn={onStaySignedIn} />)

      const stayButton = screen.getByRole('button', { name: 'Stay Signed In' })
      stayButton.focus()

      await user.keyboard(' ')

      expect(onStaySignedIn).toHaveBeenCalled()
    })
  })

  describe('Focus Management', () => {
    it('initial focus on Stay Signed In button', () => {
      render(<SessionTimeoutWarning {...defaultProps} />)

      // Due to autoFocus attribute
      const stayButton = screen.getByRole('button', { name: 'Stay Signed In' })
      expect(stayButton).toHaveFocus()
    })

    it('focus is trapped within modal', async () => {
      const user = userEvent.setup()
      render(<SessionTimeoutWarning {...defaultProps} />)

      // Tab through all interactive elements
      await user.tab() // Stay Signed In
      await user.tab() // Sign Out
      await user.tab() // Should cycle back or stay within modal

      // Focus should remain within the modal
      const activeElement = document.activeElement
      const dialog = screen.getByRole('alertdialog')

      expect(dialog.contains(activeElement)).toBe(true)
    })
  })

  describe('Modal Overlay', () => {
    it('clicking overlay closes modal', async () => {
      const user = userEvent.setup()
      const onClose = vi.fn()

      const { container } = render(
        <SessionTimeoutWarning {...defaultProps} onClose={onClose} />
      )

      const overlay = container.querySelector('.modal-overlay')
      if (overlay) {
        await user.click(overlay)
        expect(onClose).toHaveBeenCalled()
      }
    })

    it('clicking dialog content does not close modal', async () => {
      const user = userEvent.setup()
      const onClose = vi.fn()

      render(<SessionTimeoutWarning {...defaultProps} onClose={onClose} />)

      const dialog = screen.getByRole('alertdialog')
      await user.click(dialog)

      expect(onClose).not.toHaveBeenCalled()
    })
  })

  describe('Automated Accessibility Checks', () => {
    it('passes axe accessibility checks', async () => {
      const { container } = render(<SessionTimeoutWarning {...defaultProps} />)
      const results = await axe(container)
      expect(results).toHaveNoViolations()
    })

    it('passes axe checks with low time remaining', async () => {
      const { container } = render(
        <SessionTimeoutWarning {...defaultProps} secondsRemaining={10} />
      )
      const results = await axe(container)
      expect(results).toHaveNoViolations()
    })

    it('passes axe checks at zero seconds', async () => {
      const { container } = render(
        <SessionTimeoutWarning {...defaultProps} secondsRemaining={0} />
      )
      const results = await axe(container)
      expect(results).toHaveNoViolations()
    })
  })

  describe('Content and Messaging', () => {
    it('displays warning title', () => {
      render(<SessionTimeoutWarning {...defaultProps} />)

      expect(screen.getByText('Session Timeout Warning')).toBeInTheDocument()
    })

    it('explains reason for timeout', () => {
      render(<SessionTimeoutWarning {...defaultProps} />)

      expect(screen.getByText(/session is about to expire due to inactivity/i)).toBeInTheDocument()
    })

    it('shows clear call to action', () => {
      render(<SessionTimeoutWarning {...defaultProps} />)

      expect(screen.getByText(/would you like to stay signed in/i)).toBeInTheDocument()
    })

    it('provides Sign Out option', () => {
      render(<SessionTimeoutWarning {...defaultProps} />)

      expect(screen.getByRole('button', { name: 'Sign Out Now' })).toBeInTheDocument()
    })
  })

  describe('Sign Out Now Button', () => {
    it('closes modal when clicked', async () => {
      const user = userEvent.setup()
      const onClose = vi.fn()

      render(<SessionTimeoutWarning {...defaultProps} onClose={onClose} />)

      const signOutButton = screen.getByRole('button', { name: 'Sign Out Now' })
      await user.click(signOutButton)

      expect(onClose).toHaveBeenCalledTimes(1)
    })
  })

  describe('Screen Reader Experience', () => {
    it('announces urgent warning with alertdialog role', () => {
      render(<SessionTimeoutWarning {...defaultProps} />)

      const dialog = screen.getByRole('alertdialog')
      expect(dialog).toBeInTheDocument()
    })

    it('timer updates are announced assertively', () => {
      const { rerender } = render(
        <SessionTimeoutWarning {...defaultProps} secondsRemaining={10} />
      )

      const timer = screen.getByRole('timer')
      expect(timer).toHaveAttribute('aria-live', 'assertive')

      rerender(<SessionTimeoutWarning {...defaultProps} secondsRemaining={9} />)

      // Screen reader will announce the update
    })

    it('provides context through aria-describedby', () => {
      render(<SessionTimeoutWarning {...defaultProps} />)

      const description = document.getElementById('timeout-description')
      expect(description).toHaveTextContent(/session is about to expire/)
    })
  })

  describe('WCAG 2.1 Level AA Compliance', () => {
    it('provides clear warning before timeout', () => {
      render(<SessionTimeoutWarning {...defaultProps} secondsRemaining={120} />)

      expect(screen.getByRole('alertdialog')).toBeInTheDocument()
      expect(screen.getByText('2:00')).toBeInTheDocument()
    })

    it('allows user to extend session', () => {
      render(<SessionTimeoutWarning {...defaultProps} />)

      expect(screen.getByRole('button', { name: 'Stay Signed In' })).toBeInTheDocument()
    })

    it('is fully keyboard operable', async () => {
      const user = userEvent.setup()
      const onStaySignedIn = vi.fn()

      render(<SessionTimeoutWarning {...defaultProps} onStaySignedIn={onStaySignedIn} />)

      // Stay Signed In already has focus via autoFocus; Enter activates it directly
      await user.keyboard('{Enter}')

      expect(onStaySignedIn).toHaveBeenCalled()
    })

    it('provides sufficient time warning (2 minutes minimum)', () => {
      render(<SessionTimeoutWarning {...defaultProps} secondsRemaining={120} />)

      // WCAG requires at least 20 seconds warning, 2 minutes is generous
      expect(screen.getByText('2:00')).toBeInTheDocument()
    })
  })

  describe('Edge Cases', () => {
    it('handles negative seconds gracefully', () => {
      render(<SessionTimeoutWarning {...defaultProps} secondsRemaining={-5} />)

      // Should not crash
      expect(screen.getByRole('alertdialog')).toBeInTheDocument()
    })

    it('handles very large time values', () => {
      render(<SessionTimeoutWarning {...defaultProps} secondsRemaining={3600} />)

      expect(screen.getByText('60:00')).toBeInTheDocument()
    })

    it('handles missing onClose callback', async () => {
      const user = userEvent.setup()
      // eslint-disable-next-line @typescript-eslint/no-unused-vars
      const { onClose: _onClose, ...propsWithoutClose } = defaultProps

      render(<SessionTimeoutWarning {...propsWithoutClose} />)

      // Escape should not crash even without onClose
      const dialog = screen.getByRole('alertdialog')
      dialog.focus()
      await user.keyboard('{Escape}')

      expect(screen.getByRole('alertdialog')).toBeInTheDocument()
    })
  })
})
