/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React, { useEffect, useRef, useCallback, useId } from 'react'
import FocusTrap from 'focus-trap-react'
import { X } from 'lucide-react'
import { t } from '@/i18n'

export interface ModalProps {
  isOpen: boolean
  onClose: () => void
  title?: string
  children: React.ReactNode
  footer?: React.ReactNode
  size?: 'sm' | 'md' | 'lg' | 'xl' | '2xl'
  dismissible?: boolean
  className?: string
  /**
   * Override which element receives focus when the modal opens. Passed
   * straight through to focus-trap's `initialFocus` option (selector,
   * element, a function returning either, or `false` for none). Defaults
   * to focus-trap's own behavior (first tabbable node) when omitted —
   * use this when a caller needs to steer focus away from that default,
   * e.g. onto a Cancel button for a destructive confirmation.
   */
  initialFocus?: string | HTMLElement | (() => HTMLElement | null) | false
}

const sizeClasses: Record<string, string> = {
  sm: 'max-w-sm',
  md: 'max-w-md',
  lg: 'max-w-lg',
  xl: 'max-w-xl',
  '2xl': 'max-w-2xl',
}

export function Modal({
  isOpen,
  onClose,
  title,
  children,
  footer,
  size = 'md',
  dismissible = true,
  className,
  initialFocus,
}: ModalProps) {
  const backdropRef = useRef<HTMLDivElement>(null)
  const titleId = useId()
  // Lock body scroll
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

  // Handle Escape key
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Escape' && dismissible) {
        e.preventDefault()
        onClose()
      }
    },
    [dismissible, onClose]
  )

  const handleBackdropClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (dismissible && e.target === backdropRef.current) {
      onClose()
    }
  }

  if (!isOpen) return null

  return (
    <FocusTrap
      active={isOpen}
      focusTrapOptions={{
        escapeDeactivates: false,
        allowOutsideClick: true,
        returnFocusOnDeactivate: true,
        fallbackFocus: () => document.body,
        ...(initialFocus !== undefined ? { initialFocus } : {}),
      }}
    >
      <div
        ref={backdropRef}
        className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4"
        onClick={handleBackdropClick}
        onKeyDown={handleKeyDown}
        role="presentation"
      >
        <div
          className={`relative w-full bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg max-h-[90vh] overflow-y-auto ${sizeClasses[size] || sizeClasses.md} ${className || ''}`}
          role="dialog"
          aria-modal="true"
          aria-labelledby={title ? titleId : undefined}
        >
          {title && (
            <div className="flex items-center justify-between border-b border-lsc-border dark:border-earth-700 px-6 py-4 sticky top-0 bg-lsc-white dark:bg-earth-800 rounded-t-2xl z-10">
              <h2
                id={titleId}
                className="text-lg font-serif font-semibold text-lsc-dark dark:text-lsc-cream"
              >
                {title}
              </h2>
              {dismissible && (
                <button
                  onClick={onClose}
                  className="p-2 rounded-full text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-earth-700 transition-colors focus:outline-none focus:ring-2 focus:ring-lsc-rose"
                  aria-label={t('aria.addRoleModal.closeModal')}
                >
                  <X aria-hidden="true" className="w-5 h-5" />
                </button>
              )}
            </div>
          )}

          <div className="p-6">{children}</div>

          {footer && (
            <div className="flex gap-3 p-6 border-t border-lsc-border dark:border-earth-700">
              {footer}
            </div>
          )}
        </div>
      </div>
    </FocusTrap>
  )
}

export default Modal
