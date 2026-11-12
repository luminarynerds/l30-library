/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React, { createContext, useContext, useEffect, useId, useState } from 'react'
import FocusTrap from 'focus-trap-react'

interface DialogContextValue {
  onOpenChange?: (open: boolean) => void
  titleId: string
  descriptionId: string
  hasDescription: boolean
  setHasDescription: (v: boolean) => void
}
const DialogContext = createContext<DialogContextValue | null>(null)

// Host element (inside the focus trap) that nested Radix popovers — e.g. a
// Select's listbox — portal into, so focus-trap doesn't treat the open listbox
// as "outside" and yank focus back to the dialog. Null when not inside a Dialog
// (Radix then falls back to document.body).
export const DialogPortalContext = createContext<HTMLElement | null>(null)

export interface DialogProps {
  open?: boolean
  onOpenChange?: (open: boolean) => void
  children: React.ReactNode
}

export function Dialog({ open, onOpenChange, children }: DialogProps) {
  const titleId = useId()
  const descriptionId = useId()
  const [hasDescription, setHasDescription] = useState(false)
  useEffect(() => {
    if (!open) return
    document.body.style.overflow = 'hidden'
    return () => { document.body.style.overflow = '' }
  }, [open])
  if (!open) return null
  return (
    <DialogContext.Provider value={{ onOpenChange, titleId, descriptionId, hasDescription, setHasDescription }}>
      {children}
    </DialogContext.Provider>
  )
}

export function DialogTrigger({ children, className, ...props }: React.HTMLAttributes<HTMLDivElement> & { asChild?: boolean }) {
  return <div className={className} {...props}>{children}</div>
}

export function DialogContent({ children, className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  const ctx = useContext(DialogContext)
  const [portalHost, setPortalHost] = useState<HTMLDivElement | null>(null)
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      // Don't close the whole dialog if a nested layer (an open Select's listbox,
      // etc.) already handled Escape — Radix calls preventDefault() in the capture
      // phase, which runs before this document-level listener.
      if (e.key === 'Escape' && !e.defaultPrevented) ctx?.onOpenChange?.(false)
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [ctx])
  return (
    <FocusTrap focusTrapOptions={{ escapeDeactivates: false, allowOutsideClick: true, fallbackFocus: '[role="dialog"]' }}>
      <div
        className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
        role="presentation"
        onMouseDown={e => { if (e.target === e.currentTarget) ctx?.onOpenChange?.(false) }}
      >
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby={ctx?.titleId}
          aria-describedby={ctx?.hasDescription ? ctx.descriptionId : undefined}
          tabIndex={-1}
          className={`w-full max-w-md max-h-[90vh] overflow-y-auto rounded-xl bg-lsc-white p-6 shadow-lg dark:bg-earth-900 ${className ?? ''}`}
          {...props}
        >
          <DialogPortalContext.Provider value={portalHost}>
            {children}
          </DialogPortalContext.Provider>
        </div>
        {/* Portal host for nested Radix popovers: inside the focus trap (so an open
            Select keeps focus) but a sibling of the scroll area above (so an
            absolutely-positioned dropdown isn't clipped by its overflow). */}
        <div ref={setPortalHost} style={{ display: 'contents' }} />
      </div>
    </FocusTrap>
  )
}

export function DialogHeader({ children, className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={`mb-4 ${className ?? ''}`} {...props}>{children}</div>
}

export function DialogTitle({ children, className, ...props }: React.HTMLAttributes<HTMLHeadingElement>) {
  const ctx = useContext(DialogContext)
  return <h2 id={ctx?.titleId} className={`text-lg font-semibold ${className ?? ''}`} {...props}>{children}</h2>
}

export function DialogDescription({ children, className, ...props }: React.HTMLAttributes<HTMLParagraphElement>) {
  const ctx = useContext(DialogContext)
  useEffect(() => {
    ctx?.setHasDescription(true)
    return () => ctx?.setHasDescription(false)
  }, [ctx])
  return <p id={ctx?.descriptionId} className={`text-sm opacity-80 ${className ?? ''}`} {...props}>{children}</p>
}

export function DialogFooter({ children, className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={`mt-4 flex justify-end gap-2 ${className ?? ''}`} {...props}>{children}</div>
}
