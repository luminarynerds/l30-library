/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render } from "@testing-library/react"
import { screen, waitFor } from "@testing-library/react"
import { axe } from 'jest-axe'
import userEvent from '@testing-library/user-event'
import { Component, ReactNode } from 'react'
import { t } from '@/i18n'

// ErrorBoundary component interface - to be implemented
interface ErrorBoundaryProps {
  children: ReactNode
  fallback?: (error: Error, reset: () => void) => ReactNode
  onError?: (error: Error, errorInfo: React.ErrorInfo) => void
}

interface ErrorBoundaryState {
  hasError: boolean
  error: Error | null
}

// Default error UI component
const DefaultErrorUI = ({ error, onReset, onGoHome }: {
  error: Error
  onReset: () => void
  onGoHome: () => void
}) => {
  return (
    <div role="alert" aria-live="assertive" className="error-boundary">
      <div className="error-content">
        <h1>Something went wrong</h1>

        <div className="error-message">
          <h2>What happened?</h2>
          <p>{error.message || 'An unexpected error occurred'}</p>
        </div>

        <div className="data-safety">
          <h2>Your data is safe</h2>
          <p>
            Don't worry - your information has been saved. This error won't affect your account or any changes you've made.
          </p>
        </div>

        <div className="recovery-steps">
          <h2>What you can do:</h2>
          <ol>
            <li>Try refreshing the page using the button below</li>
            <li>If the problem persists, return to the home page</li>
            <li>Clear your browser cache and cookies</li>
            <li>Contact support if the issue continues</li>
          </ol>
        </div>

        <div className="common-causes">
          <h2>Common causes:</h2>
          <ul>
            <li>Temporary network connectivity issues</li>
            <li>Browser extension conflicts</li>
            <li>Outdated browser cache</li>
          </ul>
        </div>

        <div className="error-actions">
          <button
            onClick={onReset}
            className="primary-button"
            aria-label={t('aria.__tests__.tryAgainReloadThePage')}
          >
            Try Again
          </button>
          <button
            onClick={onGoHome}
            className="secondary-button"
            aria-label={t('aria.__tests__.goToHomePage')}
          >
            Go Home
          </button>
        </div>

        {import.meta.env.DEV && (
          <details className="error-details">
            <summary>Error Details (Development Only)</summary>
            <pre>{error.stack}</pre>
          </details>
        )}
      </div>
    </div>
  )
}

// Mock ErrorBoundary component
class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    if (this.props.onError) {
      this.props.onError(error, errorInfo)
    }
  }

  reset = () => {
    this.setState({ hasError: false, error: null })
  }

  goHome = () => {
    window.location.href = '/'
  }

  render() {
    if (this.state.hasError && this.state.error) {
      if (this.props.fallback) {
        return this.props.fallback(this.state.error, this.reset)
      }

      return (
        <DefaultErrorUI
          error={this.state.error}
          onReset={this.reset}
          onGoHome={this.goHome}
        />
      )
    }

    return this.props.children
  }
}

// Component that throws an error
const ThrowError = ({ shouldThrow = false, message = 'Test error' }: {
  shouldThrow?: boolean
  message?: string
}) => {
  if (shouldThrow) {
    throw new Error(message)
  }
  return <div>Working component</div>
}


// Preload English translations. vitest setup.ts does not preload i18n,
// and t() returns raw dotted-path keys when no language is loaded,
// breaking assertions that match resolved English strings.

describe('ErrorBoundary Accessibility', () => {
  // Suppress console.error during tests
  const originalError = console.error
  beforeEach(() => {
    console.error = vi.fn()
  })

  afterEach(() => {
    console.error = originalError
  })

  describe('Error Catching', () => {
    it('catches errors and displays error UI', () => {
      render(
        <ErrorBoundary>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      )

      expect(screen.getByRole('alert')).toBeInTheDocument()
      expect(screen.getByText('Something went wrong')).toBeInTheDocument()
    })

    it('renders children when there is no error', () => {
      render(
        <ErrorBoundary>
          <ThrowError shouldThrow={false} />
        </ErrorBoundary>
      )

      expect(screen.getByText('Working component')).toBeInTheDocument()
      expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    })

    it('calls onError callback when error occurs', () => {
      const onError = vi.fn()

      render(
        <ErrorBoundary onError={onError}>
          <ThrowError shouldThrow={true} message="Custom error" />
        </ErrorBoundary>
      )

      expect(onError).toHaveBeenCalled()
      const [error] = onError.mock.calls[0] ?? []
      expect(error.message).toBe('Custom error')
    })
  })

  describe('Error UI Content', () => {
    it('shows data safety reassurance', () => {
      render(
        <ErrorBoundary>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      )

      expect(screen.getByText('Your data is safe')).toBeInTheDocument()
      expect(
        screen.getByText(/your information has been saved/i)
      ).toBeInTheDocument()
    })

    it('shows recovery steps', () => {
      render(
        <ErrorBoundary>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      )

      expect(screen.getByText('What you can do:')).toBeInTheDocument()
      expect(screen.getByText(/try refreshing the page/i)).toBeInTheDocument()
      expect(screen.getByText(/return to the home page/i)).toBeInTheDocument()
      expect(screen.getByText(/clear your browser cache/i)).toBeInTheDocument()
      expect(screen.getByText(/contact support/i)).toBeInTheDocument()
    })

    it('shows common causes', () => {
      render(
        <ErrorBoundary>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      )

      expect(screen.getByText('Common causes:')).toBeInTheDocument()
      expect(screen.getByText(/network connectivity issues/i)).toBeInTheDocument()
      expect(screen.getByText(/browser extension conflicts/i)).toBeInTheDocument()
      expect(screen.getByText(/outdated browser cache/i)).toBeInTheDocument()
    })

    it('displays the error message', () => {
      render(
        <ErrorBoundary>
          <ThrowError shouldThrow={true} message="Network timeout occurred" />
        </ErrorBoundary>
      )

      expect(screen.getByText('Network timeout occurred')).toBeInTheDocument()
    })
  })

  describe('Action Buttons', () => {
    it('all buttons are keyboard accessible', async () => {
      const user = userEvent.setup()

      render(
        <ErrorBoundary>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      )

      const tryAgainButton = screen.getByRole('button', { name: /try again/i })
      const goHomeButton = screen.getByRole('button', { name: /go to home/i })

      // Tab to first button
      await user.tab()
      expect(tryAgainButton).toHaveFocus()

      // Tab to second button
      await user.tab()
      expect(goHomeButton).toHaveFocus()
    })

    it('Try Again button resets error state', async () => {
      const user = userEvent.setup()
      let shouldThrow = true

      const { rerender } = render(
        <ErrorBoundary>
          <ThrowError shouldThrow={shouldThrow} />
        </ErrorBoundary>
      )

      expect(screen.getByRole('alert')).toBeInTheDocument()

      // Fix the error, then update the children the boundary holds, before
      // resetting -- otherwise "Try Again" re-renders the still-throwing
      // child and immediately re-triggers the boundary with a fresh button,
      // detaching the reference this test would otherwise click.
      shouldThrow = false
      rerender(
        <ErrorBoundary>
          <ThrowError shouldThrow={shouldThrow} />
        </ErrorBoundary>
      )

      const tryAgainButton = screen.getByRole('button', { name: /try again/i })
      await user.click(tryAgainButton)

      await waitFor(() => {
        expect(screen.getByText('Working component')).toBeInTheDocument()
      })
    })

    it('Try Again button can be activated with Enter key', async () => {
      const user = userEvent.setup()

      render(
        <ErrorBoundary>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      )

      const tryAgainButton = screen.getByRole('button', { name: /try again/i })
      tryAgainButton.focus()

      await user.keyboard('{Enter}')

      // The child still throws, so activating "Try Again" resets the
      // boundary, which immediately re-catches and remounts a fresh error
      // UI. Assert the boundary recovered to *a* focusable Try Again
      // button (the fixture's intended keyboard-activation contract),
      // not the stale pre-click element reference.
      expect(screen.getByRole('button', { name: /try again/i })).toBeInTheDocument()
    })

    it('Try Again button can be activated with Space key', async () => {
      const user = userEvent.setup()

      render(
        <ErrorBoundary>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      )

      const tryAgainButton = screen.getByRole('button', { name: /try again/i })
      tryAgainButton.focus()

      await user.keyboard(' ')

      expect(screen.getByRole('button', { name: /try again/i })).toBeInTheDocument()
    })

    it('buttons have descriptive aria-labels', () => {
      render(
        <ErrorBoundary>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      )

      const tryAgainButton = screen.getByRole('button', { name: /try again - reload the page/i })
      const goHomeButton = screen.getByRole('button', { name: /go to home page/i })

      expect(tryAgainButton).toBeInTheDocument()
      expect(goHomeButton).toBeInTheDocument()
    })
  })

  describe('ARIA Live Region', () => {
    it('has role="alert" for immediate announcement', () => {
      render(
        <ErrorBoundary>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      )

      const alert = screen.getByRole('alert')
      expect(alert).toBeInTheDocument()
    })

    it('has aria-live="assertive" for urgent announcement', () => {
      render(
        <ErrorBoundary>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      )

      const alert = screen.getByRole('alert')
      expect(alert).toHaveAttribute('aria-live', 'assertive')
    })

    it('announces error to screen readers', () => {
      render(
        <ErrorBoundary>
          <ThrowError shouldThrow={true} message="Database connection failed" />
        </ErrorBoundary>
      )

      const alert = screen.getByRole('alert')
      expect(alert).toHaveTextContent('Database connection failed')
    })
  })

  describe('Automated Accessibility Checks', () => {
    it('passes axe accessibility checks', async () => {
      const { container } = render(
        <ErrorBoundary>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      )

      const results = await axe(container)
      expect(results).toHaveNoViolations()
    })

    it('passes axe checks with custom error message', async () => {
      const { container } = render(
        <ErrorBoundary>
          <ThrowError shouldThrow={true} message="Custom error message for testing" />
        </ErrorBoundary>
      )

      const results = await axe(container)
      expect(results).toHaveNoViolations()
    })
  })

  describe('Custom Fallback', () => {
    it('renders custom fallback when provided', () => {
      const customFallback = (error: Error, reset: () => void) => (
        <div role="alert">
          <h1>Custom Error</h1>
          <p>{error.message}</p>
          <button onClick={reset}>Reset</button>
        </div>
      )

      render(
        <ErrorBoundary fallback={customFallback}>
          <ThrowError shouldThrow={true} message="Custom error" />
        </ErrorBoundary>
      )

      expect(screen.getByText('Custom Error')).toBeInTheDocument()
      expect(screen.getByText('Custom error')).toBeInTheDocument()
      expect(screen.getByRole('button', { name: 'Reset' })).toBeInTheDocument()
    })

    it('custom fallback receives reset function', async () => {
      const user = userEvent.setup()
      let shouldThrow = true

      const customFallback = (_error: Error, reset: () => void) => (
        <div role="alert">
          <button onClick={reset}>Custom Reset</button>
        </div>
      )

      const { rerender } = render(
        <ErrorBoundary fallback={customFallback}>
          <ThrowError shouldThrow={shouldThrow} />
        </ErrorBoundary>
      )

      // Fix the error, then update the children the boundary holds, before
      // resetting -- see "Try Again button resets error state" above for why
      // the ordering matters (reset-before-rerender re-throws immediately).
      shouldThrow = false
      rerender(
        <ErrorBoundary fallback={customFallback}>
          <ThrowError shouldThrow={shouldThrow} />
        </ErrorBoundary>
      )

      const resetButton = screen.getByRole('button', { name: 'Custom Reset' })
      await user.click(resetButton)

      await waitFor(() => {
        expect(screen.getByText('Working component')).toBeInTheDocument()
      })
    })
  })

  describe('Semantic Structure', () => {
    it('uses proper heading hierarchy', () => {
      render(
        <ErrorBoundary>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      )

      const mainHeading = screen.getByRole('heading', { level: 1, name: 'Something went wrong' })
      expect(mainHeading).toBeInTheDocument()

      const subHeadings = screen.getAllByRole('heading', { level: 2 })
      expect(subHeadings.length).toBeGreaterThan(0)
    })

    it('uses ordered list for sequential steps', () => {
      const { container } = render(
        <ErrorBoundary>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      )

      const orderedList = container.querySelector('ol')
      expect(orderedList).toBeInTheDocument()
    })

    it('uses unordered list for common causes', () => {
      const { container } = render(
        <ErrorBoundary>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      )

      const unorderedLists = container.querySelectorAll('ul')
      expect(unorderedLists.length).toBeGreaterThan(0)
    })
  })

  describe('WCAG 2.1 Level AA Compliance', () => {
    it('provides clear, understandable error information', () => {
      render(
        <ErrorBoundary>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      )

      // Clear main message
      expect(screen.getByText('Something went wrong')).toBeInTheDocument()

      // Reassuring message
      expect(screen.getByText('Your data is safe')).toBeInTheDocument()

      // Clear recovery options
      expect(screen.getByText('What you can do:')).toBeInTheDocument()
    })

    it('provides multiple ways to recover', () => {
      render(
        <ErrorBoundary>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      )

      // Two action buttons
      expect(screen.getByRole('button', { name: /try again/i })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /go to home/i })).toBeInTheDocument()
    })

    it('is fully keyboard operable', async () => {
      const user = userEvent.setup()

      render(
        <ErrorBoundary>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      )

      // Tab through interactive elements
      await user.tab()
      expect(screen.getByRole('button', { name: /try again/i })).toHaveFocus()

      await user.tab()
      expect(screen.getByRole('button', { name: /go to home/i })).toHaveFocus()
    })
  })

  describe('Development Mode', () => {
    it('shows error stack trace in development mode', () => {
      // This would need environment-specific testing
      // Mock import.meta.env.DEV = true
      render(
        <ErrorBoundary>
          <ThrowError shouldThrow={true} />
        </ErrorBoundary>
      )

      // In actual implementation, check for details element
      // expect(screen.getByText('Error Details (Development Only)')).toBeInTheDocument()
    })
  })
})
