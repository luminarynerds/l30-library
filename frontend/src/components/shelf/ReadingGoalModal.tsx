/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect, useRef } from 'react'
import { X, Target } from 'lucide-react'
import FocusTrap from 'focus-trap-react'
import { clsx } from '@/utils/helpers'
import { t } from '@/i18n'

interface ReadingGoalModalProps {
  year: number
  currentTarget?: number | undefined
  onSave: (target: number) => void
  onRemove?: (() => void) | undefined
  onClose: () => void
}

export default function ReadingGoalModal({
  year,
  currentTarget,
  onSave,
  onRemove,
  onClose,
}: ReadingGoalModalProps) {
  const [value, setValue] = useState(currentTarget?.toString() || '')
  const inputRef = useRef<HTMLInputElement>(null)
  const previousActiveElement = useRef<HTMLElement | null>(null)

  useEffect(() => {
    previousActiveElement.current = document.activeElement as HTMLElement
    document.body.style.overflow = 'hidden'
    inputRef.current?.focus()
    return () => {
      document.body.style.overflow = ''
      previousActiveElement.current?.focus()
    }
  }, [])

  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [onClose])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const num = parseInt(value, 10)
    if (num > 0 && num <= 500) {
      onSave(num)
      onClose()
    }
  }

  const parsed = parseInt(value, 10)
  const isValid = !isNaN(parsed) && parsed > 0 && parsed <= 500

  return (
    <FocusTrap focusTrapOptions={{ escapeDeactivates: false, allowOutsideClick: true, returnFocusOnDeactivate: false, fallbackFocus: () => document.body }}>
      <>
      <div className="fixed inset-0 bg-black/40 z-40" onClick={onClose} aria-hidden="true" />
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="reading-goal-modal-title"
        className="fixed inset-0 z-50 flex items-center justify-center p-4"
        onKeyDown={(e) => { if (e.key === 'Escape') onClose() }}
      >
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg border border-lsc-border dark:border-earth-700 w-full max-w-sm p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 id="reading-goal-modal-title" className="font-serif text-lg font-bold text-lsc-dark dark:text-lsc-cream flex items-center gap-2">
              <Target className="w-5 h-5 text-lsc-rose" aria-hidden="true" />
              {currentTarget ? 'Edit' : 'Set'} Reading Goal
            </h2>
            <button
              onClick={onClose}
              aria-label={t('aria.authModals.close')}
              className="text-lsc-dark/70 dark:text-lsc-cream/60 hover:text-lsc-dark dark:hover:text-lsc-cream"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          <form onSubmit={handleSubmit}>
            <label
              htmlFor="goal-input"
              className="block text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-2"
            >
              How many books would you like to finish in {year}?
            </label>
            <input
              ref={inputRef}
              id="goal-input"
              type="number"
              min={1}
              max={500}
              value={value}
              onChange={(e) => setValue(e.target.value)}
              placeholder={t('placeholder.shelf.eg24')}
              className="w-full px-4 py-3 text-lg rounded-xl border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose/50"
            />
            <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60 mt-1">
              No pressure — you can change or remove this anytime.
            </p>

            <div className="flex gap-2 mt-5">
              <button
                type="submit"
                disabled={!isValid}
                className={clsx(
                  'flex-1 py-2.5 rounded-xl text-sm font-semibold transition-colors',
                  isValid
                    ? 'bg-lsc-rose text-white hover:bg-lsc-rose/90'
                    : 'bg-earth-200 dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/60 cursor-not-allowed',
                )}
              >
                {currentTarget ? 'Update Goal' : 'Set Goal'}
              </button>
              {onRemove && currentTarget && (
                <button
                  type="button"
                  onClick={() => { onRemove(); onClose() }}
                  className="px-4 py-2.5 rounded-xl text-sm font-medium text-status-danger-500 dark:text-status-danger-400 hover:bg-status-danger-50 dark:hover:bg-status-danger-900/20 transition-colors"
                >
                  Remove
                </button>
              )}
            </div>
          </form>
        </div>
      </div>
      </>
    </FocusTrap>
  )
}
