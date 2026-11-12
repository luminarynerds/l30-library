/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect, useRef } from 'react'
import { Link, useSearchParams, useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

export default function MagicLinkVerifyPage(): React.ReactElement {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const token = searchParams.get('token')
  const { loginWithMagicLink } = useAuth()

  const [isVerifying, setIsVerifying] = useState(true)
  const [error, setError] = useState('')
  const failHeadingRef = useRef<HTMLHeadingElement>(null)

  useEffect(() => {
    if (!isVerifying) failHeadingRef.current?.focus()
  }, [isVerifying])

  useEffect(() => {
    const doVerify = async () => {
      if (!token) {
        setError("This magic link isn't valid. Please request a new one.")
        setIsVerifying(false)
        return
      }

      try {
        await loginWithMagicLink(token)
        // Redirect to account page on success
        navigate('/account', { replace: true })
      } catch (_err) {
        setError(_err instanceof Error ? _err.message : 'Magic link verification failed')
        setIsVerifying(false)
      }
    }

    doVerify()
  }, [token, loginWithMagicLink, navigate])

  if (isVerifying) {
    return (
      <main id="main-content" className="min-h-screen flex items-center justify-center bg-earth-50 dark:bg-earth-900 px-4">
        <div role="status" aria-live="polite" className="max-w-md w-full bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg p-8 text-center">
          <div className="w-16 h-16 border-4 border-lsc-border dark:border-earth-700 border-t-status-warning-600 rounded-full motion-safe:animate-spin mx-auto mb-4"></div>
          <h2 className="text-2xl font-serif font-bold text-earth-800 dark:text-earth-100 mb-2">Signing you in...</h2>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
            Please wait while we verify your magic link.
          </p>
        </div>
      </main>
    )
  }

  return (
    <main id="main-content" className="min-h-screen flex items-center justify-center bg-earth-50 dark:bg-earth-900 px-4">
      <div className="max-w-md w-full bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg p-8 text-center">
        <div className="w-16 h-16 bg-status-danger-100 dark:bg-status-danger-900 rounded-full flex items-center justify-center mx-auto mb-4">
          <svg className="w-8 h-8 text-status-danger-600 dark:text-status-danger-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </div>
        <h2 ref={failHeadingRef} tabIndex={-1} className="text-2xl font-serif font-bold text-earth-800 dark:text-earth-100 mb-2">Magic Link Failed</h2>
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-6">
          {error || "This magic link may have expired or already been used."}
        </p>
        <div className="space-y-3">
          <Link
            to="/login"
            className="inline-block px-6 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-xl transition-colors"
          >
            Return to Login
          </Link>
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
            You can request a new magic link from the login page.
          </p>
        </div>
      </div>
    </main>
  )
}
