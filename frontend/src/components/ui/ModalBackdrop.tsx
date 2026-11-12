/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useRef, useCallback, useId, type ReactNode } from 'react'
import FocusTrap from 'focus-trap-react'

interface ModalBackdropProps {
  children: ReactNode
  onClose?: () => void
  /** Title text for aria-labelledby. Pass the same string shown in your <h2>. */
  title?: string
  /**
   * ID of an existing element (typically the visible heading) to use as
   * the accessible name. Takes precedence over `title`. Preferred — avoids
   * the duplicate sr-only span.
   */
  labelledBy?: string
  /**
   * ID of an existing element providing supplementary description (e.g.
   * a subtitle paragraph). Maps to aria-describedby.
   */
  describedBy?: string
  /** Set to false to prevent Escape from closing. */
  dismissible?: boolean
  className?: string
  /** Use "alertdialog" for urgent/destructive confirmations. */
  role?: 'dialog' | 'alertdialog'
}

export function ModalBackdrop({
  children,
  onClose,
  title,
  labelledBy,
  describedBy,
  dismissible = true,
  className = '',
  role: dialogRole = 'dialog',
}: ModalBackdropProps) {
  const titleId = useId()
  const backdropRef = useRef<HTMLDivElement>(null)
  const previousFocus = useRef<HTMLElement | null>(null)

  useEffect(() => {
    previousFocus.current = document.activeElement as HTMLElement
    document.body.style.overflow = 'hidden'
    return () => {
      document.body.style.overflow = ''
      previousFocus.current?.focus()
    }
  }, [])

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Escape' && dismissible && onClose) {
        e.preventDefault()
        onClose()
      }
    },
    [dismissible, onClose]
  )

  const handleBackdropClick = (e: React.MouseEvent) => {
    if (dismissible && onClose && e.target === backdropRef.current) {
      onClose()
    }
  }

  return (
    <FocusTrap
      focusTrapOptions={{
        escapeDeactivates: false,
        allowOutsideClick: true,
        returnFocusOnDeactivate: true,
        fallbackFocus: () => document.body,
      }}
    >
      <div
        ref={backdropRef}
        className={`fixed inset-0 z-50 flex items-center justify-center motion-safe:backdrop-blur-md bg-black/50 p-4 ${className}`}
        role={dialogRole}
        aria-modal="true"
        aria-labelledby={labelledBy ?? (title ? titleId : undefined)}
        aria-describedby={describedBy}
        onClick={handleBackdropClick}
        onKeyDown={handleKeyDown}
      >
        {!labelledBy && title && <span id={titleId} className="sr-only">{title}</span>}
        {children}
      </div>
    </FocusTrap>
  )
}

export default ModalBackdrop
