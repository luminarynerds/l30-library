/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useRef, useState } from 'react'
import { Settings2, ChevronDown } from 'lucide-react'
import { useTranslation } from '@/i18n/I18nContext'
import { useAccessibility } from '@/features/accessibility/hooks/useAccessibility'
import { clsx } from '@/utils/helpers'

interface CatalogDisplayMenuProps {
  hideCovers: boolean
  onToggleHideCovers: () => void
  onResetCovers: () => void
}

interface ToggleRowProps {
  label: string
  description?: string
  checked: boolean
  onChange: () => void
}

/**
 * A single switch row. State is rendered FROM the source of truth (the caller's
 * boolean), never a local copy — the original catalog dyslexia button broke
 * because its UI state diverged from what was actually applied.
 */
function ToggleRow({ label, description, checked, onChange }: ToggleRowProps) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={onChange}
      className="w-full flex items-center justify-between gap-3 px-2 py-2 rounded-lg text-left hover:bg-lsc-cream dark:hover:bg-earth-800 focus:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose"
    >
      <span className="min-w-0">
        <span className="block text-sm text-lsc-dark dark:text-lsc-cream">{label}</span>
        {description && (
          <span className="block text-[11px] text-lsc-dark/55 dark:text-lsc-cream/55">{description}</span>
        )}
      </span>
      <span
        aria-hidden="true"
        className={clsx(
          'flex-shrink-0 inline-flex w-9 h-5 rounded-full p-0.5 items-center motion-safe:transition-colors',
          checked ? 'bg-lsc-rose justify-end' : 'bg-earth-300 dark:bg-earth-600 justify-start',
        )}
      >
        <span className="w-4 h-4 rounded-full bg-white shadow-sm" />
      </span>
    </button>
  )
}

/**
 * Consolidated "Display" popover for the catalog toolbar. Folds the reading-comfort
 * controls (dyslexia-friendly text, quiet mode) and the layout control (hide covers)
 * into one menu, replacing the floating dyslexia button and the quiet-mode banner.
 *
 * Reading-comfort toggles drive the shared accessibility settings via updateSetting
 * (the same source of truth as the account accessibility panel and cssApplicator),
 * so they persist across the site and never fight a logged-in patron's global
 * preference. Persistence is localStorage-only, so this works for anonymous visitors.
 */
export default function CatalogDisplayMenu({ hideCovers, onToggleHideCovers, onResetCovers }: CatalogDisplayMenuProps): JSX.Element {
  const { t } = useTranslation()
  const { settings, updateSetting } = useAccessibility()
  const [open, setOpen] = useState(false)
  const rootRef = useRef<HTMLDivElement>(null)
  const triggerRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    if (!open) return
    const onDocPointer = (e: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) setOpen(false)
    }
    // Escape closes and returns focus to the trigger (keyboard users don't lose their place).
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') { setOpen(false); triggerRef.current?.focus() } }
    document.addEventListener('mousedown', onDocPointer)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onDocPointer)
      document.removeEventListener('keydown', onKey)
    }
  }, [open])

  // Default state for everything this menu controls. Reset restores all three.
  const atDefaults = !settings.dyslexiaFont && !settings.quietMode && !hideCovers
  const handleReset = () => {
    if (settings.dyslexiaFont) updateSetting('dyslexiaFont', false)
    if (settings.quietMode) updateSetting('quietMode', false)
    if (hideCovers) onResetCovers()
  }

  return (
    <div ref={rootRef} className="relative">
      <button
        ref={triggerRef}
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="true"
        aria-expanded={open}
        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream text-sm hover:border-lsc-rose/60 focus:outline-none focus:ring-2 focus:ring-lsc-rose"
      >
        <Settings2 className="w-4 h-4" aria-hidden="true" />
        {t('catalog.display.button', 'Display')}
        <ChevronDown className={clsx('w-3.5 h-3.5 motion-safe:transition-transform', open && 'rotate-180')} aria-hidden="true" />
      </button>
      {/* w-64 is 256px flat, anchored right-0, so on a narrow viewport the panel
          extends LEFT past the edge rather than growing scrollWidth -- the content
          simply becomes unreachable, with no horizontal scrollbar to hint at it.
          At 200% zoom on a 360px device (180 CSS px) it overflowed by 108px.
          max-w caps it to the viewport so every control stays reachable
          (WCAG 1.4.10 Reflow); it is a no-op at normal widths, where 256px fits. */}
      {open && (
        <div
          className="absolute right-0 mt-2 w-64 max-w-[calc(100vw-2rem)] rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 shadow-lg p-2 z-20"
        >
          <p className="px-2 py-1 text-[11px] font-semibold uppercase tracking-wider text-lsc-dark/60 dark:text-lsc-cream/60">
            {t('catalog.display.comfortHeading', 'Reading comfort')}
          </p>
          <ToggleRow
            label={t('catalog.dyslexiaMode.toggle', 'Dyslexia-friendly text')}
            checked={settings.dyslexiaFont}
            onChange={() => updateSetting('dyslexiaFont', !settings.dyslexiaFont)}
          />
          <ToggleRow
            label={t('catalog.display.quietMode', 'Quiet mode')}
            description={t('catalog.display.quietModeHint', 'Fewer tags, calmer page')}
            checked={settings.quietMode}
            onChange={() => updateSetting('quietMode', !settings.quietMode)}
          />
          <div className="h-px bg-lsc-border dark:bg-earth-700 my-1.5" />
          <p className="px-2 py-1 text-[11px] font-semibold uppercase tracking-wider text-lsc-dark/60 dark:text-lsc-cream/60">
            {t('catalog.display.layoutHeading', 'Layout')}
          </p>
          <ToggleRow
            label={t('catalog.hideCovers', 'Hide covers')}
            checked={hideCovers}
            onChange={onToggleHideCovers}
          />
          <div className="h-px bg-lsc-border dark:bg-earth-700 my-1.5" />
          <button
            type="button"
            onClick={handleReset}
            disabled={atDefaults}
            className="w-full text-left px-2 py-2 rounded-lg text-sm text-lsc-rose hover:bg-lsc-cream dark:hover:bg-earth-800 focus:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:bg-transparent"
          >
            {t('catalog.display.reset', 'Reset display to defaults')}
          </button>
        </div>
      )}
    </div>
  )
}
