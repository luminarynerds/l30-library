/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import { useEffect, useRef } from 'react'
import { usePanicAlert } from '@/contexts/PanicAlertContext'

interface UsePanicAlertShortcutOptions {
  enabled?: boolean
  onTriggered?: () => void
  requireHold?: boolean
  holdDurationMs?: number
}

/**
 * Hook for keyboard shortcut activation of panic alert.
 * Default: Ctrl+Shift+H (or Cmd+Shift+H on Mac)
 *
 * Requires hold or double-tap to prevent accidental activation.
 */
export const usePanicAlertShortcut = ({
  enabled = true,
  onTriggered,
  requireHold = true,
  holdDurationMs = 500,
}: UsePanicAlertShortcutOptions = {}) => {
  const { triggerAlert } = usePanicAlert()

  const keysHeldRef = useRef<Set<string>>(new Set())
  const holdStartTimeRef = useRef<number | null>(null)
  const holdTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const lastShortcutTimeRef = useRef<number>(0)

  useEffect(() => {
    if (!enabled) return

    const handleKeyDown = (event: KeyboardEvent) => {
      // Track which keys are currently held
      const key = event.key.toLowerCase()
      keysHeldRef.current.add(key)

      // Ctrl+Shift+H or Cmd+Shift+H
      const isCtrlOrCmd = event.ctrlKey || event.metaKey
      const isShift = event.shiftKey
      const isH = key === 'h'

      if (isCtrlOrCmd && isShift && isH) {
        // Prevent default behavior
        event.preventDefault()

        const now = Date.now()

        // Prevent spam - don't trigger twice within 3 seconds
        if (now - lastShortcutTimeRef.current < 3000) {
          return
        }

        if (requireHold) {
          // Start tracking hold duration
          if (!holdStartTimeRef.current) {
            holdStartTimeRef.current = now
          }

          // Cancel previous timeout if key was released and pressed again
          if (holdTimeoutRef.current) {
            clearTimeout(holdTimeoutRef.current)
          }

          // Set timeout to trigger alert if key is held long enough
          holdTimeoutRef.current = setTimeout(async () => {
            try {
              lastShortcutTimeRef.current = Date.now()
              await triggerAlert('keyboard_shortcut')
              holdStartTimeRef.current = null
              onTriggered?.()
            } catch (err: unknown) {
              Sentry.captureException(err instanceof Error ? err : new Error(String(err)))
            }
          }, holdDurationMs)
        } else {
          // No hold required, trigger immediately
          lastShortcutTimeRef.current = now
          void triggerAlert('keyboard_shortcut')
          onTriggered?.()
        }
      }
    }

    const handleKeyUp = (event: KeyboardEvent) => {
      const key = event.key.toLowerCase()
      keysHeldRef.current.delete(key)

      // If user releases during hold, cancel the shortcut
      if (requireHold && event.ctrlKey === false && event.metaKey === false) {
        if (holdTimeoutRef.current) {
          clearTimeout(holdTimeoutRef.current)
          holdTimeoutRef.current = null
        }
        holdStartTimeRef.current = null
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    window.addEventListener('keyup', handleKeyUp)

    return () => {
      window.removeEventListener('keydown', handleKeyDown)
      window.removeEventListener('keyup', handleKeyUp)
      if (holdTimeoutRef.current) {
        clearTimeout(holdTimeoutRef.current)
      }
    }
  }, [enabled, holdDurationMs, requireHold, triggerAlert, onTriggered])
}
