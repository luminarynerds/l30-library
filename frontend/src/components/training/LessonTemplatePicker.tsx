// SPDX-FileCopyrightText: 2026 Luminary Nerds
// SPDX-License-Identifier: AGPL-3.0-or-later
import { useEffect, useRef } from 'react'
import { X as CloseIcon } from 'lucide-react'
import { LESSON_TEMPLATES, type LessonTemplate } from '@/lib/lesson-templates'
import FocusTrap from 'focus-trap-react'

interface Props {
  onSelect: (template: LessonTemplate) => void
  onCancel: () => void
}

export default function LessonTemplatePicker({ onSelect, onCancel }: Props) {
  const cancelBtnRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    cancelBtnRef.current?.focus()
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onCancel()
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onCancel])

  return (
    <FocusTrap>
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="template-picker-heading"
        className="fixed inset-0 z-50 flex items-center justify-center p-4"
      >
        {/* Backdrop */}
        <div
          className="absolute inset-0 bg-black/40"
          onClick={onCancel}
          aria-hidden="true"
        />
        <div className="relative z-10 w-full max-w-sm bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg border border-lsc-border dark:border-earth-700 flex flex-col">
          <div className="flex items-center justify-between px-4 py-3 border-b border-lsc-border dark:border-earth-700">
            <h2
              id="template-picker-heading"
              className="text-sm font-semibold text-lsc-dark dark:text-lsc-cream"
            >
              Choose a lesson template
            </h2>
            <button
              ref={cancelBtnRef}
              type="button"
              onClick={onCancel}
              aria-label="Cancel"
              className="p-1 rounded hover:bg-lsc-cream dark:hover:bg-earth-700 focus:outline-none focus:ring-2 focus:ring-lsc-rose"
            >
              <CloseIcon className="w-4 h-4 text-lsc-dark dark:text-lsc-cream" aria-hidden="true" />
            </button>
          </div>
          <ul className="flex flex-col gap-1 p-3" role="list">
            {LESSON_TEMPLATES.map((tpl) => (
              <li key={tpl.id} role="none">
                <button
                  type="button"
                  onClick={() => onSelect(tpl)}
                  className="
                    w-full text-left px-3 py-2.5 rounded-lg text-sm
                    text-lsc-dark dark:text-lsc-cream
                    hover:bg-lsc-cream dark:hover:bg-earth-700
                    focus:outline-none focus:ring-2 focus:ring-lsc-rose
                    motion-safe:transition-colors
                  "
                >
                  {tpl.label}
                </button>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </FocusTrap>
  )
}
