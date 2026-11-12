/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import React, { useRef, useState } from 'react'
import { usePanicAlert } from '@/contexts/PanicAlertContext'
import { t } from '@/i18n'

interface DiscretePanicButtonProps {
  /**
   * Whether the button is visible. Even when visible, it looks like a normal UI element.
   */
  visible?: boolean

  /**
   * Position in the corner of the screen
   */
  position?: 'top-left' | 'top-right' | 'bottom-left' | 'bottom-right'

  /**
   * Require double-tap to activate
   */
  requireDoubleTap?: boolean

  /**
   * Require hold to activate
   */
  requireHold?: boolean

  /**
   * Duration of hold required (ms)
   */
  holdDurationMs?: number

  /**
   * Callback when alert is triggered
   */
  onTriggered?: () => void
}

/**
 * Discreet Panic Button
 *
 * A hidden button that looks like a normal UI element but can be used to trigger
 * a silent panic alert. Requires double-tap or hold to prevent accidental activation.
 *
 * Design: Looks like a subtle "?" help icon in the corner to avoid suspicion.
 */
export const DiscretePanicButton: React.FC<DiscretePanicButtonProps> = ({
  visible = true,
  position = 'bottom-right',
  requireDoubleTap = true,
  requireHold = false,
  holdDurationMs = 500,
  onTriggered,
}) => {
  const { triggerAlert, isLoading } = usePanicAlert()

  const [isPressed, setIsPressed] = useState(false)
  const [tapCount, setTapCount] = useState(0)
  const [holdProgress, setHoldProgress] = useState(0)

  const tapTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const holdTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const holdStartTimeRef = useRef<number | null>(null)
  const progressIntervalRef = useRef<NodeJS.Timeout | null>(null)

  if (!visible) return null

  const positionStyles: Record<string, React.CSSProperties> = {
    'top-left': { top: '1rem', left: '1rem' },
    'top-right': { top: '1rem', right: '1rem' },
    'bottom-left': { bottom: '8rem', left: '1rem' },
    'bottom-right': { bottom: '8rem', right: '1rem' },
  }

  const handleMouseDown = async () => {
    if (isLoading) return

    setIsPressed(true)
    const now = Date.now()
    holdStartTimeRef.current = now

    if (requireHold) {
      // Show progress bar
      holdTimeoutRef.current = setTimeout(async () => {
        try {
          await triggerAlert('hidden_ui_button')
          setHoldProgress(100)
          onTriggered?.()
          // Reset after animation
          setTimeout(() => {
            setHoldProgress(0)
            setIsPressed(false)
          }, 300)
        } catch (err: unknown) {
          Sentry.captureException(err instanceof Error ? err : new Error(String(err)))
          setIsPressed(false)
        }
      }, holdDurationMs)

      // Update progress indicator
      progressIntervalRef.current = setInterval(() => {
        const elapsed = Date.now() - (holdStartTimeRef.current || now)
        setHoldProgress(Math.min((elapsed / holdDurationMs) * 100, 100))
      }, 10)
    } else if (requireDoubleTap) {
      setTapCount((prev) => prev + 1)

      // Reset tap counter after 500ms
      if (tapTimeoutRef.current) clearTimeout(tapTimeoutRef.current)

      tapTimeoutRef.current = setTimeout(() => {
        setTapCount(0)
      }, 500)

      // Trigger on double tap
      if (tapCount === 1) {
        // Second tap
        try {
          await triggerAlert('hidden_ui_button')
          onTriggered?.()
          setTapCount(0)
        } catch (err: unknown) {
          Sentry.captureException(err instanceof Error ? err : new Error(String(err)))
        }
      }
    } else {
      // Single tap/click
      try {
        await triggerAlert('hidden_ui_button')
        onTriggered?.()
      } catch (err: unknown) {
        Sentry.captureException(err instanceof Error ? err : new Error(String(err)))
      }
    }
  }

  const handleMouseUp = () => {
    setIsPressed(false)
    holdStartTimeRef.current = null

    if (holdTimeoutRef.current) {
      clearTimeout(holdTimeoutRef.current)
      holdTimeoutRef.current = null
    }

    if (progressIntervalRef.current) {
      clearInterval(progressIntervalRef.current)
      progressIntervalRef.current = null
    }

    // If hold was cancelled, reset progress
    if (requireHold && holdProgress < 100) {
      setHoldProgress(0)
    }
  }

  const handleTouchStart = handleMouseDown
  const handleTouchEnd = handleMouseUp

  return (
    <div
      className="fixed z-50 cursor-pointer"
      style={{...positionStyles[position], pointerEvents: 'auto'}}
      role="button"
      tabIndex={0}
      onMouseDown={handleMouseDown}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
      onTouchStart={handleTouchStart}
      onTouchEnd={handleTouchEnd}
      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); handleMouseDown() } }}
      onKeyUp={(e) => { if (e.key === 'Enter' || e.key === ' ') handleMouseUp() }}
      aria-label={t('aria.discretePanicButton.help')}
      title={
        requireHold
          ? 'Hold this button to request help'
          : requireDoubleTap
            ? 'Double-tap this button to request help'
            : 'Click to request help'
      }
    >
      {/* Outer container with subtle animation */}
      <div
        className={`
          relative w-10 h-10 rounded-full
          flex items-center justify-center
          transition-all duration-200
          shadow-md
          ${isPressed ? 'scale-95' : 'scale-100'}
          ${isLoading ? 'opacity-50' : 'opacity-100 hover:opacity-100'}
          bg-earth-200 dark:bg-earth-700 border border-lsc-border dark:border-earth-600
        `}
      >
        {/* Help icon - looks innocent */}
        <span className="text-lg font-semibold text-earth-600 dark:text-earth-200">?</span>

        {/* Progress ring for hold activation */}
        {requireHold && holdProgress > 0 && (
          <div
            className={`
              absolute inset-0 rounded-full
              border-2 border-status-danger-500
              transition-all duration-100
            `}
            style={{
              clipPath: `polygon(
                50% 50%,
                50% 0%,
                ${50 + 50 * Math.cos((holdProgress * 2 * Math.PI) / 100 - Math.PI / 2)}%
                ${50 + 50 * Math.sin((holdProgress * 2 * Math.PI) / 100 - Math.PI / 2)}%
              )`,
            }}
          />
        )}

        {/* Double-tap indicator */}
        {requireDoubleTap && tapCount === 1 && (
          <div className="absolute inset-0 rounded-full border-2 border-status-warning-500 motion-safe:animate-pulse" />
        )}

        {/* Loading indicator */}
        {isLoading && (
          <div className="absolute inset-0 rounded-full motion-safe:animate-spin border-2 border-transparent border-t-blue-500" />
        )}
      </div>

      {/* Tooltip showing status */}
      {requireHold && holdProgress > 0 && holdProgress < 100 && (
        <div className="absolute -top-8 left-1/2 -translate-x-1/2 whitespace-nowrap">
          <div className="text-xs bg-earth-900 text-white px-2 py-1 rounded">
            {Math.round(holdProgress)}%
          </div>
        </div>
      )}

      {requireDoubleTap && tapCount === 1 && (
        <div className="absolute -top-8 left-1/2 -translate-x-1/2 whitespace-nowrap">
          <div className="text-xs bg-earth-900 text-white px-2 py-1 rounded">Tap again</div>
        </div>
      )}
    </div>
  )
}
