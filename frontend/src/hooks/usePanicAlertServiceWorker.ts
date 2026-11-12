/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import { useEffect } from 'react'

/**
 * Hook to set up panic alert handling via the main service worker
 *
 * Panic alert functionality is integrated into the main service worker (sw.js)
 * to avoid scope conflicts. This hook sets up the message listener for
 * confirmation that alerts have been sent.
 */
export const usePanicAlertServiceWorker = () => {
  useEffect(() => {
    if (!('serviceWorker' in navigator)) {
      Sentry.captureMessage('[PanicAlert] Service Workers not supported', 'warning')
      return
    }

    const handleMessage = (event: MessageEvent) => {
      if (event.data.type === 'PANIC_ALERT_SENT') {
        console.log('[PanicAlert] Alert confirmed sent:', event.data.alertId)
      }
    }

    navigator.serviceWorker.addEventListener('message', handleMessage)

    // Request periodic sync for pending alerts if supported
    const setupPeriodicSync = async () => {
      try {
        const registration = await navigator.serviceWorker.ready
        if ('periodicSync' in registration) {
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          await (registration as any).periodicSync.register('sync-panic-alerts', {
            minInterval: 24 * 60 * 60 * 1000, // 24 hours
          })
        }
      } catch (error: unknown) {
        if (error instanceof Error && error.name === 'NotAllowedError') {
          console.log('[PanicAlert] Periodic sync permission denied')
        } else {
          Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
        }
      }
    }

    setupPeriodicSync()

    return () => {
      navigator.serviceWorker.removeEventListener('message', handleMessage)
    }
  }, [])
}
