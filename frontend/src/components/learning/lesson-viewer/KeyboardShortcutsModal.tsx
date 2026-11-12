/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Keyboard } from 'lucide-react'
import FocusTrap from 'focus-trap-react'

interface Props {
  open: boolean
  onClose: () => void
}

const ROWS: { label: string; keys: string[] }[] = [
  { label: 'Previous lesson', keys: ['←', 'J'] },
  { label: 'Next lesson', keys: ['→', 'K'] },
  { label: 'Toggle bookmark', keys: ['B'] },
  { label: 'Mark complete', keys: ['M'] },
  { label: 'Show/hide shortcuts', keys: ['?'] },
]

export function KeyboardShortcutsModal({ open, onClose }: Props) {
  if (!open) return null

  return (
    <div
      className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
      onClick={onClose}
      onKeyDown={e => {
        if (e.key === 'Escape') onClose()
      }}
      role="presentation"
    >
      <FocusTrap active={true} focusTrapOptions={{ escapeDeactivates: false, allowOutsideClick: true, returnFocusOnDeactivate: true, fallbackFocus: () => document.body }}>
      {/* eslint-disable-next-line jsx-a11y/click-events-have-key-events */}
      <div
        className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg max-w-md w-full p-6"
        onClick={e => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="keyboard-shortcuts-title"
      >
        <h3
          id="keyboard-shortcuts-title"
          className="text-lg font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2"
        >
          <Keyboard className="w-5 h-5" />
          Keyboard Shortcuts
        </h3>
        <div className="space-y-3">
          {ROWS.map((row, i) => (
            <div
              key={row.label}
              className={`flex justify-between items-center py-2 ${
                i < ROWS.length - 1 ? 'border-b border-lsc-border dark:border-earth-700' : ''
              }`}
            >
              <span className="text-lsc-dark/70 dark:text-lsc-cream/70">{row.label}</span>
              <div className="flex gap-1 items-center">
                {row.keys.map((key, idx) => (
                  <span key={key} className="flex gap-1 items-center">
                    {idx > 0 && (
                      <span className="text-lsc-dark/70 dark:text-lsc-cream/70">or</span>
                    )}
                    <kbd className="px-2 py-1 bg-lsc-cream dark:bg-lsc-brown rounded text-xs font-mono">
                      {key}
                    </kbd>
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
        <button
          onClick={onClose}
          className="mt-6 w-full py-2 bg-lsc-cream dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream rounded-xl font-medium hover:bg-lsc-cream/80 dark:hover:bg-lsc-brown/80"
        >
          Close
        </button>
      </div>
      </FocusTrap>
    </div>
  )
}
