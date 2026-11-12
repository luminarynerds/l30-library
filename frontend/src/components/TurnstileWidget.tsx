/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * Cloudflare Turnstile widget — vanilla integration, no npm dependency.
 * Loads the Turnstile script once globally, renders the widget into its mount
 * point, and calls onVerify with the token when verification succeeds (or with
 * an empty string when the widget expires / errors out).
 *
 * Because the submit buttons that consume this widget stay disabled until a
 * token arrives, a Turnstile that never verifies (script blocked by a privacy
 * extension or CSP, offline, a challenge the user can't clear) would otherwise
 * leave the form permanently un-submittable with no explanation. To avoid that
 * silent dead-end the widget surfaces its own state in an aria-live region: a
 * delayed "checking…" hint while pending, and a recoverable error message if it
 * fails, so keyboard and screen-reader users are told why they can't send yet.
 *
 * Requires VITE_TURNSTILE_SITE_KEY at build time. When the site key is empty
 * OR the literal "disabled" (a self-host escape hatch, since Docker's
 * empty-build-arg falls back to the baked default so "empty" can't be passed
 * that way), the widget short-circuits and immediately calls
 * onVerify("dev-bypass") so submission still succeeds against a backend running
 * with TURNSTILE_DISABLED=true.
 */
import { useEffect, useRef, useState } from 'react'
import { useTranslation } from '@/i18n'

const TURNSTILE_SCRIPT_URL = 'https://challenges.cloudflare.com/turnstile/v0/api.js'
// Stop polling for the script after ~5s (50 × 100ms). If it never appears it's
// blocked/offline/CSP'd — surface an error instead of retrying forever silently.
const MAX_RENDER_ATTEMPTS = 50
// Hold the "checking…" hint back so the common sub-second interaction-only path
// (token issued before the user notices) doesn't flash a message.
const CHECKING_HINT_DELAY_MS = 1500

declare global {
  interface Window {
    turnstile?: {
      render: (
        target: HTMLElement,
        opts: {
          sitekey: string
          callback?: (token: string) => void
          'expired-callback'?: () => void
          'error-callback'?: () => void
          theme?: 'light' | 'dark' | 'auto'
          size?: 'normal' | 'compact'
          appearance?: 'always' | 'execute' | 'interaction-only'
        }
      ) => string
      remove: (widgetId: string) => void
      reset: (widgetId?: string) => void
    }
  }
}

function ensureScriptLoaded(): void {
  if (typeof document === 'undefined') return
  if (document.querySelector(`script[src="${TURNSTILE_SCRIPT_URL}"]`)) return
  const script = document.createElement('script')
  script.src = TURNSTILE_SCRIPT_URL
  script.async = true
  script.defer = true
  document.head.appendChild(script)
}

type Status = 'pending' | 'verified' | 'error'

interface Props {
  onVerify: (token: string) => void
  theme?: 'light' | 'dark' | 'auto'
  className?: string
  appearance?: 'always' | 'interaction-only'
}

export function TurnstileWidget({ onVerify, theme = 'auto', className = '', appearance = 'interaction-only' }: Props): JSX.Element {
  const { t } = useTranslation()
  const mountRef = useRef<HTMLDivElement>(null)
  const widgetIdRef = useRef<string | null>(null)
  const onVerifyRef = useRef(onVerify)
  onVerifyRef.current = onVerify

  const [status, setStatus] = useState<Status>('pending')
  const [showChecking, setShowChecking] = useState(false)

  useEffect(() => {
    const rawKey = (import.meta.env.VITE_TURNSTILE_SITE_KEY as string | undefined) || ''
    const siteKey = rawKey.toLowerCase() === 'disabled' ? '' : rawKey
    if (!siteKey) {
      setStatus('verified')
      onVerifyRef.current('dev-bypass')
      return
    }

    ensureScriptLoaded()

    let cancelled = false
    let attempts = 0
    const hintTimer = window.setTimeout(() => {
      if (!cancelled) setShowChecking(true)
    }, CHECKING_HINT_DELAY_MS)

    const tryRender = () => {
      if (cancelled) return
      if (!mountRef.current) return
      if (widgetIdRef.current !== null) return
      const ts = window.turnstile
      if (!ts) {
        if (++attempts >= MAX_RENDER_ATTEMPTS) {
          setStatus('error')
          return
        }
        window.setTimeout(tryRender, 100)
        return
      }
      widgetIdRef.current = ts.render(mountRef.current, {
        sitekey: siteKey,
        theme,
        appearance,
        callback: (token) => {
          if (cancelled) return
          setStatus('verified')
          onVerifyRef.current(token)
        },
        'expired-callback': () => {
          if (cancelled) return
          // Token aged out (~5 min). Reset for a fresh one and reflect the wait
          // so a stale, silently-disabled submit button is explained.
          setStatus('pending')
          setShowChecking(true)
          onVerifyRef.current('')
          const w = window.turnstile
          if (w && widgetIdRef.current) w.reset(widgetIdRef.current)
        },
        'error-callback': () => {
          if (cancelled) return
          setStatus('error')
          onVerifyRef.current('')
        },
      })
    }
    tryRender()

    return () => {
      cancelled = true
      window.clearTimeout(hintTimer)
      const ts = window.turnstile
      if (widgetIdRef.current && ts) {
        ts.remove(widgetIdRef.current)
      }
      widgetIdRef.current = null
    }
  }, [theme, appearance])

  return (
    <div className={className}>
      <div ref={mountRef} />
      {status !== 'verified' && (
        <p role="status" aria-live="polite" className="mt-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
          {status === 'error'
            ? t('common.turnstile.error', 'We couldn’t verify your browser. Refresh the page and try again.')
            : showChecking
              ? t('common.turnstile.checking', 'Checking your browser before you can send…')
              : ''}
        </p>
      )}
    </div>
  )
}
