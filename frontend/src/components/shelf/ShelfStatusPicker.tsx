/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useRef } from 'react'
import { BookOpen, Clock, Pause, CheckCircle, XCircle, Trash2 } from 'lucide-react'
import { clsx } from '@/utils/helpers'
import type { ShelfStatus } from '@/api/domains/content/reading-status-api'
import { t } from '@/i18n'

const STATUS_OPTIONS: { key: ShelfStatus; label: string; icon: typeof Clock; color: string }[] = [
  { key: 'want_to_read', label: 'Want to Read', icon: Clock, color: 'text-status-info-500 dark:text-status-info-400' },
  { key: 'currently_reading', label: 'Currently Reading', icon: BookOpen, color: 'text-status-success-500 dark:text-status-success-400' },
  { key: 'on_hold', label: 'On Hold', icon: Pause, color: 'text-status-warning-500 dark:text-status-warning-400' },
  { key: 'finished', label: 'Finished', icon: CheckCircle, color: 'text-lsc-dark/70 dark:text-lsc-cream/70' },
  { key: 'did_not_finish', label: 'Did Not Finish', icon: XCircle, color: 'text-lsc-dark/70 dark:text-lsc-cream/70' },
]

interface ShelfStatusPickerProps {
  currentStatus?: ShelfStatus | undefined
  onSelect: (status: ShelfStatus) => void
  onRemove?: (() => void) | undefined
  onClose: () => void
  /** 'popover' anchored to icon (desktop), 'sheet' slides from bottom (mobile) */
  variant?: 'popover' | 'sheet' | undefined
}

export default function ShelfStatusPicker({
  currentStatus,
  onSelect,
  onRemove,
  onClose,
  variant = 'popover',
}: ShelfStatusPickerProps) {
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose()
    }
    function handleClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) onClose()
    }
    document.addEventListener('keydown', handleKeyDown)
    document.addEventListener('mousedown', handleClickOutside)
    return () => {
      document.removeEventListener('keydown', handleKeyDown)
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [onClose])

  // Focus first item on mount
  useEffect(() => {
    const firstBtn = ref.current?.querySelector('button')
    firstBtn?.focus()
  }, [])

  const isSheet = variant === 'sheet'

  return (
    <>
      {/* Backdrop for sheet variant */}
      {isSheet && (
        <div
          className="fixed inset-0 bg-black/40 z-40"
          onClick={onClose}
          aria-hidden="true"
        />
      )}
      <div
        ref={ref}
        role="listbox"
        aria-label={t('aria.shelf.chooseShelfStatus')}
        className={clsx(
          isSheet
            ? 'fixed bottom-0 left-0 right-0 z-50 rounded-t-2xl bg-lsc-white dark:bg-earth-800 shadow-lg p-4 pb-8 animate-slide-up'
            : 'absolute left-0 top-full mt-1 z-30 bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-xl shadow-lg py-1 min-w-[200px]',
        )}
      >
        {isSheet && (
          <div className="flex justify-center mb-3">
            <div className="w-10 h-1 rounded-full bg-earth-300 dark:bg-earth-600" />
          </div>
        )}
        {STATUS_OPTIONS.map(({ key, label, icon: Icon, color }) => {
          const isActive = key === currentStatus
          return (
            <button
              key={key}
              role="option"
              aria-selected={isActive}
              onClick={() => { onSelect(key); onClose() }}
              className={clsx(
                'w-full flex items-center gap-3 px-4 py-3 text-sm text-left transition-colors',
                isActive
                  ? 'bg-earth-50 dark:bg-earth-700 font-semibold text-lsc-dark dark:text-lsc-cream'
                  : 'text-lsc-dark/80 dark:text-lsc-cream/80 hover:bg-earth-50 dark:hover:bg-earth-700',
                isSheet ? 'rounded-xl' : '',
              )}
            >
              <Icon className={clsx('w-4 h-4 flex-shrink-0', color)} aria-hidden="true" />
              {label}
              {isActive && <span className="ml-auto text-xs text-lsc-dark/70 dark:text-lsc-cream/60">Current</span>}
            </button>
          )
        })}
        {onRemove && currentStatus && (
          <>
            <div className="border-t border-lsc-border dark:border-earth-700 my-1" />
            <button
              onClick={() => { onRemove(); onClose() }}
              className={clsx(
                'w-full flex items-center gap-3 px-4 py-3 text-sm text-status-danger-500 dark:text-status-danger-400 hover:bg-status-danger-50 dark:hover:bg-status-danger-900/20 transition-colors',
                isSheet ? 'rounded-xl' : '',
              )}
            >
              <Trash2 className="w-4 h-4 flex-shrink-0" aria-hidden="true" />
              Remove from shelf
            </button>
          </>
        )}
      </div>
    </>
  )
}
