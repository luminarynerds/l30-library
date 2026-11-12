/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import { useCallback } from 'react'

export type HapticIntensity = 'light' | 'medium' | 'heavy'

/**
 * Haptic feedback patterns for different interactions
 */
const HAPTIC_PATTERNS: Record<HapticIntensity, number | number[]> = {
  light: 10,           // Quick tap
  medium: 20,          // Button press
  heavy: [30, 10, 30], // Important action (double pulse)
}

export function useHapticFeedback() {
  const vibrate = useCallback((pattern: number | number[]) => {
    // Check if vibration API is available
    if (!('vibrate' in navigator)) {
      return false
    }

    // Check if user prefers reduced motion (includes reduced haptics)
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    if (prefersReducedMotion) {
      return false
    }

    try {
      navigator.vibrate(pattern)
      return true
    } catch (_error: unknown) {
      Sentry.captureMessage('Haptic feedback failed:', 'warning')
      return false
    }
  }, [])

  const light = useCallback(() => vibrate(HAPTIC_PATTERNS.light), [vibrate])
  const medium = useCallback(() => vibrate(HAPTIC_PATTERNS.medium), [vibrate])
  const heavy = useCallback(() => vibrate(HAPTIC_PATTERNS.heavy), [vibrate])

  /**
   * Stop any ongoing vibration
   */
  const stop = useCallback(() => {
    if ('vibrate' in navigator) {
      navigator.vibrate(0)
    }
  }, [])

  return {
    light,
    medium,
    heavy,
    stop,
    vibrate,
    isSupported: 'vibrate' in navigator,
  }
}
