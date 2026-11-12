/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useRef } from 'react'
import FocusTrap from 'focus-trap-react'
import { X } from 'lucide-react'

import { useAccessibility } from '@/features/accessibility'
import { cn } from '@/lib/utils'

interface ReaderSettingsDrawerProps {
  open: boolean
  onClose: () => void
}

interface SegmentedProps<T extends string> {
  legend: string
  value: T
  options: ReadonlyArray<{ value: T; label: string }>
  onChange: (value: T) => void
}

function Segmented<T extends string>({ legend, value, options, onChange }: SegmentedProps<T>) {
  return (
    <fieldset className="space-y-2">
      <legend className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">{legend}</legend>
      <div className="flex flex-wrap gap-2" role="radiogroup" aria-label={legend}>
        {options.map((opt) => {
          const active = opt.value === value
          return (
            <button
              key={opt.value}
              type="button"
              role="radio"
              aria-checked={active}
              onClick={() => onChange(opt.value)}
              className={cn(
                'min-h-11 px-3 rounded-lg text-sm border focus:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose',
                active
                  ? 'bg-lsc-rose text-white border-lsc-rose'
                  : 'bg-transparent text-lsc-dark dark:text-lsc-cream border-black/15 dark:border-white/20 hover:bg-black/5 dark:hover:bg-white/10',
              )}
            >
              {opt.label}
            </button>
          )
        })}
      </div>
    </fieldset>
  )
}

/**
 * Reading settings slide-over. Reads and writes the *shared* accessibility
 * settings (the same ones that govern the rest of the site) so a patron's
 * reading preferences are one source of truth, not a reader-local island.
 */
export default function ReaderSettingsDrawer({ open, onClose }: ReaderSettingsDrawerProps) {
  const { dyslexiaFont, fontSize, lineSpacing, letterSpacingBody, theme, updateSetting } = useAccessibility()
  const panelRef = useRef<HTMLDivElement | null>(null)
  const closeRef = useRef<HTMLButtonElement | null>(null)

  useEffect(() => {
    if (!open) return
    closeRef.current?.focus()
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.stopPropagation()
        onClose()
      }
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [open, onClose])

  if (!open) return null

  return (
    <div className="fixed inset-0 z-[60]" role="dialog" aria-modal="true" aria-label="Reading settings">
      <button
        type="button"
        aria-label="Close settings"
        onClick={onClose}
        className="absolute inset-0 bg-black/30"
      />
      <FocusTrap
        focusTrapOptions={{
          escapeDeactivates: false,
          allowOutsideClick: true,
          returnFocusOnDeactivate: true,
          initialFocus: () => closeRef.current ?? undefined,
          fallbackFocus: () => document.body,
        }}
      >
      <div
        ref={panelRef}
        className="absolute right-0 top-0 h-full w-full max-w-sm bg-lsc-cream dark:bg-earth-900 shadow-lg flex flex-col"
      >
        <div className="flex items-center justify-between px-4 h-14 border-b border-black/10 dark:border-white/10">
          <h2 className="text-base font-semibold text-lsc-dark dark:text-lsc-cream">Reading settings</h2>
          <button
            ref={closeRef}
            type="button"
            onClick={onClose}
            className="inline-flex items-center justify-center w-11 h-11 -mr-2 rounded-lg text-lsc-dark dark:text-lsc-cream hover:bg-black/5 dark:hover:bg-white/10 focus:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose"
            aria-label="Close settings"
          >
            <X className="w-5 h-5" aria-hidden="true" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-4 py-5 space-y-6">
          <Segmented
            legend="Theme"
            value={theme}
            onChange={(v) => updateSetting('theme', v)}
            options={[
              { value: 'light', label: 'Light' },
              { value: 'dark', label: 'Dark' },
              { value: 'high-contrast', label: 'High contrast' },
              { value: 'system', label: 'System' },
            ]}
          />
          <Segmented
            legend="Text size"
            value={fontSize}
            onChange={(v) => updateSetting('fontSize', v)}
            options={[
              { value: 'normal', label: 'Normal' },
              { value: 'large', label: 'Large' },
              { value: 'xlarge', label: 'Extra large' },
            ]}
          />
          <Segmented
            legend="Line spacing"
            value={lineSpacing}
            onChange={(v) => updateSetting('lineSpacing', v)}
            options={[
              { value: 'normal', label: 'Normal' },
              { value: 'relaxed', label: 'Relaxed' },
              { value: 'loose', label: 'Loose' },
            ]}
          />
          <Segmented
            legend="Letter spacing"
            value={letterSpacingBody}
            onChange={(v) => updateSetting('letterSpacingBody', v)}
            options={[
              { value: 'normal', label: 'Normal' },
              { value: 'wide', label: 'Wide' },
              { value: 'wider', label: 'Wider' },
            ]}
          />

          <fieldset>
            <label className="flex items-center justify-between gap-3 cursor-pointer min-h-11">
              <span className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
                Dyslexia-friendly font
                <span className="block text-xs font-normal text-lsc-dark/60 dark:text-lsc-cream/60">
                  Atkinson Hyperlegible
                </span>
              </span>
              <input
                type="checkbox"
                checked={dyslexiaFont}
                onChange={(e) => updateSetting('dyslexiaFont', e.target.checked)}
                className="w-5 h-5 accent-lsc-rose"
              />
            </label>
          </fieldset>

          <p className="text-xs text-lsc-dark/60 dark:text-lsc-cream/60 pt-2 border-t border-black/10 dark:border-white/10">
            These settings apply across L30, not just here.
          </p>
        </div>
      </div>
      </FocusTrap>
    </div>
  )
}
