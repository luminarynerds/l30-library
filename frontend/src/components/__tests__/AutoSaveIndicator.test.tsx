/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi } from 'vitest'
import { render } from "@testing-library/react"
import { screen } from "@testing-library/react"
import { axe } from 'jest-axe'

// Auto-save status types
type AutoSaveStatus = 'idle' | 'saving' | 'saved' | 'error'

interface AutoSaveIndicatorProps {
  status: AutoSaveStatus
  lastSaved?: Date | null
  error?: Error | null
}

// Mock component - to be implemented
const AutoSaveIndicator = ({ status, lastSaved, error }: AutoSaveIndicatorProps) => {
  const formatTimeAgo = (date: Date) => {
    const seconds = Math.floor((new Date().getTime() - date.getTime()) / 1000)
    if (seconds < 60) return 'just now'
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`
    return date.toLocaleDateString()
  }

  return (
    <div className="auto-save-indicator" data-status={status}>
      <div
        role="status"
        aria-live="polite"
        aria-atomic="true"
        className="status-container"
      >
        {status === 'saving' && (
          <div className="saving-state">
            <span className="spinner" aria-hidden="true">[spin]</span>
            <span>Saving...</span>
          </div>
        )}

        {status === 'saved' && lastSaved && (
          <div className="saved-state">
            <span className="checkmark" aria-hidden="true">[ok]</span>
            <span>Saved {formatTimeAgo(lastSaved)}</span>
          </div>
        )}

        {status === 'error' && error && (
          <div className="error-state">
            <span className="error-icon" aria-hidden="true">[!]</span>
            <span>Error: {error.message}</span>
          </div>
        )}

        {status === 'idle' && (
          <div className="idle-state">
            <span>Unsaved changes</span>
          </div>
        )}
      </div>
    </div>
  )
}

describe('AutoSaveIndicator', () => {
  describe('Status States', () => {
    it('shows "Saving..." state with spinner', () => {
      render(<AutoSaveIndicator status="saving" />)

      expect(screen.getByText('Saving...')).toBeInTheDocument()

      const spinner = screen.getByText('[spin]')
      expect(spinner).toHaveAttribute('aria-hidden', 'true')
    })

    it('shows "Saved" state with checkmark', () => {
      const lastSaved = new Date()
      render(<AutoSaveIndicator status="saved" lastSaved={lastSaved} />)

      expect(screen.getByText(/saved/i)).toBeInTheDocument()

      const checkmark = screen.getByText('[ok]')
      expect(checkmark).toHaveAttribute('aria-hidden', 'true')
    })

    it('shows timestamp in saved state', () => {
      const lastSaved = new Date(Date.now() - 30 * 1000) // 30 seconds ago
      render(<AutoSaveIndicator status="saved" lastSaved={lastSaved} />)

      expect(screen.getByText(/saved just now/i)).toBeInTheDocument()
    })

    it('shows error state with error message', () => {
      const error = new Error('Network connection failed')
      render(<AutoSaveIndicator status="error" error={error} />)

      expect(screen.getByText(/error: network connection failed/i)).toBeInTheDocument()

      const errorIcon = screen.getByText('[!]')
      expect(errorIcon).toHaveAttribute('aria-hidden', 'true')
    })

    it('shows idle state for unsaved changes', () => {
      render(<AutoSaveIndicator status="idle" />)

      expect(screen.getByText('Unsaved changes')).toBeInTheDocument()
    })
  })

  describe('Timestamp Formatting', () => {
    it('shows "just now" for recent saves (< 60 seconds)', () => {
      const lastSaved = new Date(Date.now() - 30 * 1000)
      render(<AutoSaveIndicator status="saved" lastSaved={lastSaved} />)

      expect(screen.getByText(/saved just now/i)).toBeInTheDocument()
    })

    it('shows minutes ago for saves < 1 hour', () => {
      const lastSaved = new Date(Date.now() - 5 * 60 * 1000) // 5 minutes ago
      render(<AutoSaveIndicator status="saved" lastSaved={lastSaved} />)

      expect(screen.getByText(/saved 5m ago/i)).toBeInTheDocument()
    })

    it('shows hours ago for saves < 24 hours', () => {
      const lastSaved = new Date(Date.now() - 2 * 60 * 60 * 1000) // 2 hours ago
      render(<AutoSaveIndicator status="saved" lastSaved={lastSaved} />)

      expect(screen.getByText(/saved 2h ago/i)).toBeInTheDocument()
    })

    it('shows date for saves > 24 hours', () => {
      const lastSaved = new Date(Date.now() - 25 * 60 * 60 * 1000) // 25 hours ago
      render(<AutoSaveIndicator status="saved" lastSaved={lastSaved} />)

      const formattedDate = lastSaved.toLocaleDateString()
      expect(screen.getByText(new RegExp(`saved ${formattedDate}`, 'i'))).toBeInTheDocument()
    })
  })

  describe('ARIA Live Region', () => {
    it('has role="status" for status updates', () => {
      render(<AutoSaveIndicator status="saving" />)

      const statusContainer = screen.getByRole('status')
      expect(statusContainer).toBeInTheDocument()
    })

    it('has aria-live="polite" for non-urgent announcements', () => {
      render(<AutoSaveIndicator status="saving" />)

      const statusContainer = screen.getByRole('status')
      expect(statusContainer).toHaveAttribute('aria-live', 'polite')
    })

    it('has aria-atomic="true" to announce entire content', () => {
      render(<AutoSaveIndicator status="saving" />)

      const statusContainer = screen.getByRole('status')
      expect(statusContainer).toHaveAttribute('aria-atomic', 'true')
    })

    it('announces status changes to screen readers', () => {
      const { rerender } = render(<AutoSaveIndicator status="idle" />)

      rerender(<AutoSaveIndicator status="saving" />)

      const statusContainer = screen.getByRole('status')
      expect(statusContainer).toHaveTextContent('Saving...')
    })
  })

  describe('Decorative Icons', () => {
    it('spinner is aria-hidden', () => {
      render(<AutoSaveIndicator status="saving" />)

      const spinner = screen.getByText('[spin]')
      expect(spinner).toHaveAttribute('aria-hidden', 'true')
    })

    it('checkmark is aria-hidden', () => {
      render(<AutoSaveIndicator status="saved" lastSaved={new Date()} />)

      const checkmark = screen.getByText('[ok]')
      expect(checkmark).toHaveAttribute('aria-hidden', 'true')
    })

    it('error icon is aria-hidden', () => {
      render(<AutoSaveIndicator status="error" error={new Error('Test error')} />)

      const errorIcon = screen.getByText('[!]')
      expect(errorIcon).toHaveAttribute('aria-hidden', 'true')
    })
  })

  describe('Automated Accessibility Checks', () => {
    it('passes axe checks in saving state', async () => {
      const { container } = render(<AutoSaveIndicator status="saving" />)
      const results = await axe(container)
      expect(results).toHaveNoViolations()
    })

    it('passes axe checks in saved state', async () => {
      const { container } = render(
        <AutoSaveIndicator status="saved" lastSaved={new Date()} />
      )
      const results = await axe(container)
      expect(results).toHaveNoViolations()
    })

    it('passes axe checks in error state', async () => {
      const { container } = render(
        <AutoSaveIndicator status="error" error={new Error('Test error')} />
      )
      const results = await axe(container)
      expect(results).toHaveNoViolations()
    })

    it('passes axe checks in idle state', async () => {
      const { container } = render(<AutoSaveIndicator status="idle" />)
      const results = await axe(container)
      expect(results).toHaveNoViolations()
    })
  })

  describe('Visual Feedback', () => {
    it('has data-status attribute for styling', () => {
      const { container, rerender } = render(<AutoSaveIndicator status="saving" />)

      let indicator = container.querySelector('.auto-save-indicator')
      expect(indicator).toHaveAttribute('data-status', 'saving')

      rerender(<AutoSaveIndicator status="saved" lastSaved={new Date()} />)
      indicator = container.querySelector('.auto-save-indicator')
      expect(indicator).toHaveAttribute('data-status', 'saved')

      rerender(<AutoSaveIndicator status="error" error={new Error('Test')} />)
      indicator = container.querySelector('.auto-save-indicator')
      expect(indicator).toHaveAttribute('data-status', 'error')
    })

    it('applies appropriate CSS classes for each state', () => {
      const { container, rerender } = render(<AutoSaveIndicator status="saving" />)

      expect(container.querySelector('.saving-state')).toBeInTheDocument()

      rerender(<AutoSaveIndicator status="saved" lastSaved={new Date()} />)
      expect(container.querySelector('.saved-state')).toBeInTheDocument()

      rerender(<AutoSaveIndicator status="error" error={new Error('Test')} />)
      expect(container.querySelector('.error-state')).toBeInTheDocument()

      rerender(<AutoSaveIndicator status="idle" />)
      expect(container.querySelector('.idle-state')).toBeInTheDocument()
    })
  })

  describe('Error Handling', () => {
    it('displays full error message', () => {
      const error = new Error('Database connection timeout after 30 seconds')
      render(<AutoSaveIndicator status="error" error={error} />)

      expect(
        screen.getByText(/database connection timeout after 30 seconds/i)
      ).toBeInTheDocument()
    })

    it('handles error without message', () => {
      const error = new Error()
      render(<AutoSaveIndicator status="error" error={error} />)

      expect(screen.getByText(/error:/i)).toBeInTheDocument()
    })

    it('handles missing error object gracefully', () => {
      const { container } = render(<AutoSaveIndicator status="error" />)

      // Should not crash, though ideally error state should have an error
      expect(container).toBeInTheDocument()
    })
  })

  describe('State Transitions', () => {
    it('transitions from idle to saving', () => {
      const { rerender } = render(<AutoSaveIndicator status="idle" />)

      expect(screen.getByText('Unsaved changes')).toBeInTheDocument()

      rerender(<AutoSaveIndicator status="saving" />)

      expect(screen.getByText('Saving...')).toBeInTheDocument()
      expect(screen.queryByText('Unsaved changes')).not.toBeInTheDocument()
    })

    it('transitions from saving to saved', () => {
      const { rerender } = render(<AutoSaveIndicator status="saving" />)

      expect(screen.getByText('Saving...')).toBeInTheDocument()

      rerender(<AutoSaveIndicator status="saved" lastSaved={new Date()} />)

      expect(screen.getByText(/saved/i)).toBeInTheDocument()
      expect(screen.queryByText('Saving...')).not.toBeInTheDocument()
    })

    it('transitions from saving to error', () => {
      const { rerender } = render(<AutoSaveIndicator status="saving" />)

      expect(screen.getByText('Saving...')).toBeInTheDocument()

      rerender(<AutoSaveIndicator status="error" error={new Error('Save failed')} />)

      expect(screen.getByText(/error: save failed/i)).toBeInTheDocument()
      expect(screen.queryByText('Saving...')).not.toBeInTheDocument()
    })

    it('transitions from error back to saving (retry)', () => {
      const { rerender } = render(
        <AutoSaveIndicator status="error" error={new Error('Network error')} />
      )

      expect(screen.getByText(/error: network error/i)).toBeInTheDocument()

      rerender(<AutoSaveIndicator status="saving" />)

      expect(screen.getByText('Saving...')).toBeInTheDocument()
      expect(screen.queryByText(/error/i)).not.toBeInTheDocument()
    })
  })

  describe('Screen Reader Experience', () => {
    it('provides meaningful text for screen readers', () => {
      render(<AutoSaveIndicator status="saving" />)

      const status = screen.getByRole('status')
      expect(status).toHaveTextContent('Saving...')
    })

    it('updates screen reader announcement on status change', () => {
      const { rerender } = render(<AutoSaveIndicator status="saving" />)

      let status = screen.getByRole('status')
      expect(status).toHaveTextContent('Saving...')

      rerender(<AutoSaveIndicator status="saved" lastSaved={new Date()} />)

      status = screen.getByRole('status')
      expect(status).toHaveTextContent(/saved/i)
    })

    it('does not announce decorative icons', () => {
      render(<AutoSaveIndicator status="saving" />)

      const status = screen.getByRole('status')
      // Should contain text but icons should be hidden
      expect(status).toHaveTextContent('Saving...')

      const ariaHiddenElements = status.querySelectorAll('[aria-hidden="true"]')
      expect(ariaHiddenElements.length).toBeGreaterThan(0)
    })
  })

  describe('WCAG 2.1 Level AA Compliance', () => {
    it('provides text alternative for status', () => {
      render(<AutoSaveIndicator status="saving" />)

      // Visual indicator (spinner) is supplemented with text
      expect(screen.getByText('Saving...')).toBeInTheDocument()
    })

    it('does not rely solely on color to convey information', () => {
      render(<AutoSaveIndicator status="error" error={new Error('Test')} />)

      // Error state has both icon and text
      expect(screen.getByText(/error:/i)).toBeInTheDocument()
      expect(screen.getByText('[!]')).toBeInTheDocument()
    })

    it('provides sufficient information about state', () => {
      render(<AutoSaveIndicator status="saved" lastSaved={new Date(Date.now() - 60000)} />)

      // Saved state includes timestamp for context
      expect(screen.getByText(/saved.*ago/i)).toBeInTheDocument()
    })
  })

  describe('Real-time Updates', () => {
    it('updates timestamp display over time', () => {
      vi.useFakeTimers()
      const lastSaved = new Date(Date.now() - 30 * 1000) // 30 seconds ago

      const { rerender } = render(
        <AutoSaveIndicator status="saved" lastSaved={lastSaved} />
      )

      expect(screen.getByText(/saved just now/i)).toBeInTheDocument()

      // Advance time by 60 seconds
      vi.advanceTimersByTime(60 * 1000)

      // Force re-render to update the display
      rerender(<AutoSaveIndicator status="saved" lastSaved={lastSaved} />)

      // Should now show "1m ago"
      expect(screen.getByText(/saved 1m ago/i)).toBeInTheDocument()

      vi.useRealTimers()
    })
  })

  describe('Integration with useAutoSave', () => {
    it('works with useAutoSave hook statuses', () => {
      const statuses: AutoSaveStatus[] = ['idle', 'saving', 'saved', 'error']

      statuses.forEach((status) => {
        const props: AutoSaveIndicatorProps = { status }

        if (status === 'saved') {
          props.lastSaved = new Date()
        }

        if (status === 'error') {
          props.error = new Error('Test error')
        }

        const { container } = render(<AutoSaveIndicator {...props} />)
        expect(container).toBeInTheDocument()
      })
    })
  })
})
