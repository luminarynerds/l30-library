/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React, { useState, useEffect, useRef, useCallback } from 'react'
import { AlertCircle, CheckCircle } from 'lucide-react'
import FocusTrap from 'focus-trap-react'
import { useUnifiedAccessibility } from '../features/accessibility/hooks/useUnifiedAccessibility'

export interface ConfirmDialogProps {
  isOpen: boolean
  title: string
  message: React.ReactNode
  confirmText?: string
  /** Alias for confirmText */
  confirmLabel?: string
  cancelText?: string
  confirmVariant?: 'danger' | 'warning' | 'success' | 'primary'
  onConfirm: () => void | Promise<void>
  onCancel?: () => void
  /** Alias for onCancel */
  onClose?: () => void
  loading?: boolean
  /**
   * Disable the confirm button (e.g. a required field hasn't been filled in
   * yet). Defaults to false -- if `message` embeds an input the caller
   * treats as required (a reject-reason textarea, say), wiring the matching
   * `confirmDisabled` is on the call site. `message` is a plain
   * `React.ReactNode`, so nothing here type-checks that pairing; a call site
   * that adds a "required" field to its message and forgets `confirmDisabled`
   * compiles clean and just lets an empty submit through (see the Applications
   * tab reject-reason parity fix, 2026-07-08).
   */
  confirmDisabled?: boolean
}

export default function ConfirmDialog({
  isOpen,
  title,
  message,
  confirmText: confirmTextProp,
  confirmLabel,
  cancelText = 'Go back',
  confirmVariant = 'primary',
  onConfirm,
  onCancel: onCancelProp,
  onClose,
  loading: externalLoading,
  confirmDisabled = false,
}: ConfirmDialogProps): React.ReactElement | null {
  const confirmText = confirmTextProp ?? confirmLabel ?? 'Yes, proceed'
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const onCancel = onCancelProp ?? onClose ?? (() => {})
  const [loading, setLoading] = useState(false)
  const confirmButtonRef = useRef<HTMLButtonElement>(null)
  const cancelButtonRef = useRef<HTMLButtonElement>(null)
  const previousActiveElement = useRef<HTMLElement | null>(null)

  // For danger/warning variants, default focus to the safe (cancel) button
  // so accidental taps or Enter presses don't trigger the destructive action
  const isDangerousVariant = confirmVariant === 'danger' || confirmVariant === 'warning'

  // Access accessibility settings for reduce motion
  const { settings } = useUnifiedAccessibility()
  const reduceMotion = settings.sensory?.reduceMotion || false

  // Store the previously focused element and restore on close
  useEffect(() => {
    let focusTimer: ReturnType<typeof setTimeout> | null = null

    if (isOpen) {
      previousActiveElement.current = document.activeElement as HTMLElement
      // For destructive actions, focus the safe (cancel) button to prevent
      // accidental confirmation from random taps or Enter presses
      focusTimer = setTimeout(() => {
        if (isDangerousVariant) {
          cancelButtonRef.current?.focus()
        } else {
          confirmButtonRef.current?.focus()
        }
      }, 0)
    }

    return () => {
      // Clean up focus timer
      if (focusTimer) {
        clearTimeout(focusTimer)
      }
      // Restore focus when dialog closes
      if (previousActiveElement.current && typeof previousActiveElement.current.focus === 'function') {
        previousActiveElement.current.focus()
      }
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen])

  // Handle Escape key
  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Escape' && !loading && !externalLoading) {
      onCancel()
    }
  }, [loading, externalLoading, onCancel])

  if (!isOpen) return null

  const isLoading = loading || externalLoading
  const isConfirmDisabled = isLoading || confirmDisabled

  const getVariantStyles = () => {
    switch (confirmVariant) {
      case 'danger':
        return {
          bg: 'bg-status-danger-600 hover:bg-status-danger-700 dark:bg-status-danger-700 dark:hover:bg-status-danger-600',
          icon: 'text-status-danger-600',
          iconBg: 'bg-status-danger-100 dark:bg-status-danger-900/30',
        }
      case 'warning':
        return {
          bg: 'bg-status-warning-600 hover:bg-status-warning-700 dark:bg-status-warning-700 dark:hover:bg-status-warning-600',
          icon: 'text-status-warning-600',
          iconBg: 'bg-status-warning-100 dark:bg-status-warning-900/30',
        }
      case 'success':
        return {
          bg: 'bg-status-success-600 hover:bg-status-success-700 dark:bg-status-success-700 dark:hover:bg-status-success-600',
          icon: 'text-status-success-600',
          iconBg: 'bg-status-success-100 dark:bg-status-success-900/30',
        }
      default:
        return {
          bg: 'bg-lsc-rose hover:bg-lsc-rose/90',
          icon: 'text-lsc-rose',
          iconBg: 'bg-lsc-rose/20',
        }
    }
  }

  const variants = getVariantStyles()

  const handleConfirm = async () => {
    setLoading(true)
    try {
      await onConfirm()
    } finally {
      setLoading(false)
    }
  }

  const dialogId = 'confirm-dialog-title'
  const descriptionId = 'confirm-dialog-description'

  return (
    <FocusTrap
      active={isOpen}
      focusTrapOptions={{
        initialFocus: () =>
          isDangerousVariant
            ? cancelButtonRef.current || confirmButtonRef.current
            : confirmButtonRef.current,
        allowOutsideClick: false,
        escapeDeactivates: false, // We handle Escape manually
        fallbackFocus: () => confirmButtonRef.current || document.body,
        returnFocusOnDeactivate: true,
      }}
    >
      <div
        className="fixed inset-0 z-40"
        role="presentation"
        onKeyDown={handleKeyDown}
      >
        {/* Backdrop */}
        <div
          className="fixed inset-0 bg-black/50"
          aria-hidden="true"
          onClick={() => !isLoading && onCancel()}
        />

        {/* Dialog */}
        <div className="fixed inset-0 flex items-center justify-center z-50 p-4">
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby={dialogId}
            aria-describedby={descriptionId}
            className="bg-lsc-white dark:bg-earth-800 rounded-xl max-w-[calc(100vw-2rem)] sm:max-w-sm w-full shadow-lg"
          >
            {/* Icon & Title */}
            <div className="p-4 sm:p-6 text-center">
              <div
                className={`w-12 h-12 rounded-full ${variants.iconBg} flex items-center justify-center mx-auto mb-4`}
              >
                {confirmVariant === 'success' ? (
                  <CheckCircle className={`w-6 h-6 ${variants.icon}`} />
                ) : (
                  <AlertCircle className={`w-6 h-6 ${variants.icon}`} />
                )}
              </div>
              <h2
                id={dialogId}
                className="font-serif text-lg font-bold text-lsc-dark dark:text-lsc-cream mb-2"
              >
                {title}
              </h2>
              <div
                id={descriptionId}
                className="text-lsc-dark/70 dark:text-lsc-cream/70 text-sm"
              >
                {message}
              </div>
            </div>

            {/* Buttons */}
            <div className="flex flex-col-reverse sm:flex-row gap-3 p-4 sm:p-6 border-t border-lsc-border dark:border-earth-700">
              <button
                ref={cancelButtonRef}
                onClick={() => !isLoading && onCancel()}
                disabled={isLoading}
                className="flex-1 px-4 py-2.5 sm:py-2 rounded-lg border border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream/50 dark:hover:bg-earth-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed font-medium"
              >
                {cancelText}
              </button>
              <button
                ref={confirmButtonRef}
                onClick={handleConfirm}
                disabled={isConfirmDisabled}
                className={`flex-1 px-4 py-2.5 sm:py-2 rounded-lg text-white disabled:opacity-50 disabled:cursor-not-allowed font-medium ${variants.bg} ${reduceMotion ? '' : 'transition-colors'}`}
              >
                {confirmText}
              </button>
            </div>
          </div>
        </div>
      </div>
    </FocusTrap>
  )
}
