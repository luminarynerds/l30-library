/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * DestructiveActionDialog Component
 * Displays confirmation dialog for destructive actions
 */

import { useEffect } from 'react'
import FocusTrap from 'focus-trap-react'

export interface DestructiveActionDialogProps {
  isOpen: boolean
  title: string
  message: string
  type?: 'destructive' | 'important' | 'normal'
  isDangerous?: boolean
  isLoading?: boolean
  onConfirm: () => void
  onCancel: () => void
}

export function DestructiveActionDialog({
  isOpen,
  title,
  message,
  type = 'destructive',
  isDangerous = true,
  isLoading = false,
  onConfirm,
  onCancel,
}: DestructiveActionDialogProps): React.ReactElement | null {
  // Handle Escape key
  useEffect(() => {
    if (!isOpen) return

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault()
        onCancel()
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isOpen, onCancel])

  // Lock body scroll when open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden'
    } else {
      document.body.style.overflow = ''
    }
    return () => {
      document.body.style.overflow = ''
    }
  }, [isOpen])

  if (!isOpen) return null

  const getTypeStyles = () => {
    switch (type) {
      case 'destructive':
        return {
          icon: 'bg-status-danger-100 dark:bg-status-danger-900/30',
          iconColor: 'text-status-danger-600 dark:text-status-danger-400',
          button: 'bg-status-danger-600 hover:bg-status-danger-700 text-white',
          title: 'text-status-danger-900 dark:text-status-danger-100',
        }
      case 'important':
        return {
          icon: 'bg-status-warning-100 dark:bg-status-warning-900/30',
          iconColor: 'text-status-warning-600 dark:text-status-warning-400',
          button: 'bg-status-warning-600 hover:bg-status-warning-700 text-white',
          title: 'text-status-warning-900 dark:text-status-warning-100',
        }
      default:
        return {
          icon: 'bg-earth-100 dark:bg-earth-800/30',
          iconColor: 'text-lsc-rose dark:text-lsc-rose-light',
          button: 'bg-lsc-rose hover:bg-lsc-rose/90 text-white',
          title: 'text-earth-900 dark:text-earth-200',
        }
    }
  }

  const styles = getTypeStyles()

  return (
    <FocusTrap active={isOpen} focusTrapOptions={{ escapeDeactivates: true }}>
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 animate-in fade-in duration-200"
      role="dialog"
      aria-modal="true"
      aria-labelledby="destructive-title"
    >
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg max-w-sm w-full p-6 space-y-4 animate-in slide-in-from-bottom duration-200">
        {/* Icon */}
        <div className={`inline-flex items-center justify-center w-12 h-12 rounded-full ${styles.icon}`}>
          <svg className={`w-6 h-6 ${styles.iconColor}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
            />
          </svg>
        </div>

        {/* Title */}
        <h2 id="destructive-title" className={`text-lg font-bold ${styles.title}`}>
          {title}
        </h2>

        {/* Message */}
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
          {message}
        </p>

        {/* Warning for dangerous actions */}
        {isDangerous && (
          <div className="p-3 bg-status-danger-50 dark:bg-status-danger-900/20 rounded-lg border border-status-danger-200 dark:border-status-danger-800 flex gap-2">
            <svg className="w-4 h-4 text-status-danger-600 dark:text-status-danger-400 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
            <p className="text-xs font-medium text-status-danger-700 dark:text-status-danger-400">
              This action cannot be undone.
            </p>
          </div>
        )}

        {/* Action buttons */}
        <div className="flex gap-3 pt-4">
          <button
            onClick={onCancel}
            disabled={isLoading}
            className="flex-1 px-4 py-2 rounded-lg font-medium text-lsc-dark dark:text-lsc-cream bg-lsc-cream dark:bg-earth-700 hover:bg-lsc-border dark:hover:bg-earth-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            disabled={isLoading}
            className={`flex-1 px-4 py-2 rounded-lg font-medium text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${styles.button}`}
          >
            {isLoading ? (
              <span className="flex items-center justify-center gap-2">
                <svg className="w-4 h-4 motion-safe:animate-spin" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 2v20m10-10H2" />
                </svg>
                Processing...
              </span>
            ) : (
              'Confirm'
            )}
          </button>
        </div>
      </div>
    </div>
    </FocusTrap>
  )
}
