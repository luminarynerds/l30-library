/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * NavigationProgress Component
 *
 * Shows a progress bar at the top of the header during route transitions.
 *
 * Two suppression rules:
 *  - Cached routes (settle within 200ms) never show the bar — avoids a flash
 *    that's worse than no feedback at all.
 *  - prefers-reduced-motion: reduce skips the animation. The bar is also
 *    aria-hidden because RouteAnnouncer handles SR messaging.
 */

import { useState, useEffect, useRef } from 'react'
import { useLocation } from 'react-router-dom'
import { clsx } from '@/utils/helpers'
import { t } from '@/i18n'

export default function NavigationProgress(): React.ReactElement | null {
  const location = useLocation()
  const [isNavigating, setIsNavigating] = useState(false)
  const [progress, setProgress] = useState(0)
  const prevPathRef = useRef(location.pathname)

  // Respect prefers-reduced-motion (live — system setting can flip mid-session).
  const [reducedMotion, setReducedMotion] = useState<boolean>(() =>
    typeof window !== 'undefined' && typeof window.matchMedia === 'function'
      ? window.matchMedia('(prefers-reduced-motion: reduce)').matches
      : false,
  )
  useEffect(() => {
    if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') return
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)')
    const handler = (e: MediaQueryListEvent) => setReducedMotion(e.matches)
    if (typeof mq.addEventListener === 'function') {
      mq.addEventListener('change', handler)
      return () => mq.removeEventListener('change', handler)
    }
    mq.addListener(handler)
    return () => mq.removeListener(handler)
  }, [])

  useEffect(() => {
    // Only animate on actual path changes, not initial mount
    if (prevPathRef.current === location.pathname) {
      return
    }
    prevPathRef.current = location.pathname

    // Reduced-motion: don't animate at all.
    if (reducedMotion) {
      return
    }

    // Delay before showing — if navigation finishes within 200ms (cached route,
    // back/forward, hash change), don't flash the bar.
    const timers: ReturnType<typeof setTimeout>[] = []
    const startTimer = setTimeout(() => {
      setIsNavigating(true)
      setProgress(0)
      // Animate progress to 90%
      timers.push(setTimeout(() => setProgress(30), 50))
      timers.push(setTimeout(() => setProgress(60), 150))
      timers.push(setTimeout(() => setProgress(90), 300))
      // Complete and hide
      timers.push(setTimeout(() => setProgress(100), 400))
      timers.push(setTimeout(() => {
        setIsNavigating(false)
        setProgress(0)
      }, 600))
    }, 200)

    return () => {
      clearTimeout(startTimer)
      timers.forEach(clearTimeout)
    }
  }, [location.pathname, reducedMotion])

  if (!isNavigating) return null

  return (
    <div
      className="absolute top-0 left-0 right-0 h-0.5 bg-transparent overflow-hidden z-50"
      role="progressbar"
      aria-valuenow={progress}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-label={t('aria.navigationProgress.pageLoading')}
      aria-hidden="true"
    >
      <div
        className={clsx(
          'h-full bg-lsc-rose transition-all duration-200 ease-out',
          progress === 100 && 'opacity-0'
        )}
        style={{ width: `${progress}%` }}
      />
    </div>
  )
}
