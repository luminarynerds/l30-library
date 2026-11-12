/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import { Component, ReactNode } from 'react'
import { RefreshCw, Home, Info, Shield, BookOpen } from 'lucide-react'
import { useBranding } from '@/contexts/BrandingContext'

interface Props {
  children: ReactNode
  fallback?: ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
}

/**
 * Enhanced Error Boundary with neurodivergent-friendly messaging
 * - Clear, supportive language
 * - Specific recovery steps
 * - Reassurance about data safety
 * - Common causes explanation
 */
// ErrorBoundary renders outside I18nProvider when the provider itself crashes,
// so we can't use useTranslation(). Use plain English strings instead.
function ErrorBoundaryFallbackContent({ error, onRefresh }: { error: Error | null; onRefresh: () => void }) {
  const branding = useBranding()
  return (
    <div className="min-h-screen flex items-center justify-center bg-lsc-cream dark:bg-lsc-dark p-4">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg p-8 max-w-2xl w-full">
        {/* Icon and Title */}
        <div className="text-center mb-6">
          <div className="mb-4 flex justify-center">
            <BookOpen className="w-16 h-16 text-lsc-rose" aria-hidden="true" />
          </div>
          <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-3">
            Something unexpected happened
          </h1>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70 text-lg">
            Don't worry - this happens sometimes, and we're here to help you get back on track.
          </p>
        </div>

        {/* Data Safety Reassurance */}
        <div className="bg-status-success-50 dark:bg-status-success-900/20 border border-status-success-200 dark:border-status-success-800 rounded-xl p-4 mb-6">
          <div className="flex items-start gap-3">
            <Shield className="w-5 h-5 text-status-success-600 dark:text-status-success-400 flex-shrink-0 mt-0.5" aria-hidden="true" />
            <div>
              <h2 className="font-serif font-semibold text-status-success-900 dark:text-status-success-100 mb-1">Your data is safe</h2>
              <p className="text-sm text-status-success-800 dark:text-status-success-200">
                Any information you've entered has been saved. You won't lose your work.
              </p>
            </div>
          </div>
        </div>

        {/* Recovery Steps */}
        <div className="bg-lsc-cream dark:bg-lsc-dark/50 rounded-xl p-5 mb-6">
          <h2 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-3 flex items-center gap-2">
            <Info className="w-5 h-5" aria-hidden="true" />
            Here's what you can try:
          </h2>
          <ol className="space-y-2 text-sm text-lsc-dark/80 dark:text-lsc-cream/80 list-decimal list-inside">
            <li className="pl-2">
              <strong>Refresh the page</strong> - Click "Refresh Page" below or press F5 on your keyboard.
            </li>
            <li className="pl-2">
              <strong>Go back home</strong> - Return to the homepage and navigate to where you were.
            </li>
            <li className="pl-2">
              <strong>Clear your browser cache</strong> - Sometimes old data causes conflicts. Try clearing your cache and cookies.
            </li>
            <li className="pl-2">
              <strong>Contact us</strong> - If the problem continues, please email{' '}
              <a
                href={`mailto:${branding.contact_email}`}
                className="text-lsc-rose dark:text-lsc-rose-light hover:underline font-medium"
              >
                {branding.contact_email}
              </a>
            </li>
          </ol>
        </div>

        {/* Common Causes */}
        <div className="bg-earth-50 dark:bg-earth-800/20 border border-lsc-border dark:border-earth-700 rounded-xl p-4 mb-6">
          <h2 className="font-serif font-semibold text-earth-900 dark:text-earth-200 mb-2">Common causes:</h2>
          <ul className="text-sm text-earth-800 dark:text-lsc-rose-light/80 space-y-1 list-disc list-inside">
            <li>Your internet connection was interrupted</li>
            <li>The page took too long to load</li>
            <li>Your browser needs to be updated</li>
            <li>A temporary server issue occurred</li>
          </ul>
        </div>

        {/* Error Details (only in development) */}
        {error && import.meta.env.DEV && (
          <details className="mb-6 p-4 bg-lsc-cream dark:bg-lsc-dark/50 rounded-xl text-sm">
            <summary className="cursor-pointer text-lsc-dark/70 dark:text-lsc-cream/70 font-medium hover:text-lsc-rose dark:hover:text-lsc-rose">
              Technical details (for advanced users)
            </summary>
            <pre className="mt-3 text-status-danger-600 dark:text-status-danger-400 whitespace-pre-wrap break-words p-3 bg-lsc-white dark:bg-earth-900 rounded border border-status-danger-200 dark:border-status-danger-800">
              {error.message}
            </pre>
          </details>
        )}

        {/* Action Buttons */}
        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          <button
            onClick={onRefresh}
            className="inline-flex items-center justify-center gap-2 px-6 py-3 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-xl font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose"
          >
            <RefreshCw className="w-5 h-5" aria-hidden="true" />
            Refresh Page
          </button>
          <button
            onClick={() => { window.location.href = '/' }}
            className="inline-flex items-center justify-center gap-2 px-6 py-3 border border-lsc-brown text-lsc-brown dark:text-lsc-rose-light dark:border-lsc-rose-light hover:bg-lsc-brown/5 dark:hover:bg-lsc-rose/10 rounded-xl font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-brown"
          >
            <Home className="w-5 h-5" aria-hidden="true" />
            Go Home
          </button>
        </div>
      </div>
    </div>
  )
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo): void {
    // Forward errorInfo.componentStack so Sentry payloads include the
    // React component tree where the error originated, not just the JS
    // stack. Saves a debugging hop when triaging boundary-caught errors.
    Sentry.captureException(error, {
      contexts: { react: { componentStack: errorInfo.componentStack ?? '' } },
    })
  }

  handleRefresh = (): void => {
    window.location.reload()
  }

  render(): ReactNode {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback
      }

      return (
        <ErrorBoundaryFallbackContent
          error={this.state.error}
          onRefresh={this.handleRefresh}
        />
      )
    }

    return this.props.children
  }
}

export default ErrorBoundary
