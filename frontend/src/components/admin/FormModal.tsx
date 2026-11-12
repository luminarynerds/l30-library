/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React, { useEffect } from 'react'
import { X, Loader2, Save } from 'lucide-react'
import { clsx } from '../../utils/helpers'
import FocusTrap from 'focus-trap-react'

export interface FormModalProps {
  open: boolean
  title: string
  onClose: () => void
  onSave?: () => void | Promise<void>
  saving?: boolean
  saveLabel?: string
  cancelLabel?: string
  size?: 'sm' | 'md' | 'lg'
  hideFooter?: boolean
  children: React.ReactNode
}

const SIZE_CLASSES: Record<NonNullable<FormModalProps['size']>, string> = {
  sm: 'max-w-md',
  md: 'max-w-lg',
  lg: 'max-w-2xl',
}

export function FormModal({
  open,
  title,
  onClose,
  onSave,
  saving = false,
  saveLabel = 'Save',
  cancelLabel = 'Cancel',
  size = 'md',
  hideFooter = false,
  children,
}: FormModalProps): React.ReactElement | null {
  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !saving) onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, saving, onClose])

  if (!open) return null
  return (
    <FocusTrap active={open} focusTrapOptions={{ escapeDeactivates: false, allowOutsideClick: true, returnFocusOnDeactivate: true, fallbackFocus: () => document.body }}>
    <div
      className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="form-modal-title"
      onClick={(e) => {
        if (e.target === e.currentTarget && !saving) onClose()
      }}
      onKeyDown={(e) => { if (e.key === 'Escape' && !saving) onClose() }}
    >
      <div
        className={clsx(
          'bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg w-full max-h-[90vh] flex flex-col',
          SIZE_CLASSES[size],
        )}
      >
        <div className="p-4 border-b border-lsc-border dark:border-earth-700 flex items-center justify-between shrink-0">
          <h3
            id="form-modal-title"
            className="text-xl font-serif font-semibold text-lsc-dark dark:text-lsc-cream"
          >
            {title}
          </h3>
          <button
            type="button"
            onClick={onClose}
            disabled={saving}
            aria-label="Close"
            className="p-1 rounded hover:bg-earth-100 dark:hover:bg-earth-700 disabled:opacity-50"
          >
            <X className="w-5 h-5" aria-hidden="true" />
          </button>
        </div>
        <div className="p-4 space-y-4 overflow-y-auto flex-1">{children}</div>
        {!hideFooter && (
          <div className="p-4 border-t border-lsc-border dark:border-earth-700 flex justify-end gap-3 shrink-0">
            <button
              type="button"
              onClick={onClose}
              disabled={saving}
              className="px-4 py-2 text-sm text-lsc-dark/70 hover:text-lsc-dark dark:text-lsc-cream/70 dark:hover:text-lsc-cream disabled:opacity-50"
            >
              {cancelLabel}
            </button>
            {onSave && (
              <button
                type="button"
                onClick={() => void onSave()}
                disabled={saving}
                className="inline-flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-lg text-sm font-semibold hover:bg-lsc-rose/90 disabled:opacity-50"
              >
                {saving ? (
                  <Loader2 className="w-4 h-4 motion-safe:animate-spin" aria-hidden="true" />
                ) : (
                  <Save className="w-4 h-4" aria-hidden="true" />
                )}
                {saveLabel}
              </button>
            )}
          </div>
        )}
      </div>
    </div>
    </FocusTrap>
  )
}
