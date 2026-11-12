/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * Per-item language chip for the parent-resource directory. Renders
 * the language autonym, switches the active filter on click, and
 * carries `lang={code}` on the visible text so assistive tech picks
 * the right voice for the autonym itself.
 *
 * A11y choices:
 *  - `<button>` (not `<a>` or `<span>` with onClick) so keyboard
 *    focus + Enter activation come for free.
 *  - `aria-pressed` reflects whether this chip is the active filter,
 *    so screen readers announce state, not just label.
 *  - Visible checkmark icon on the active chip backs up the color
 *    change (color is not the only indicator -- a11y).
 *  - `aria-label` spells out "Available in {autonym}" so the
 *    abbreviated visible label still carries meaning out loud.
 */
import { Check } from 'lucide-react'
import { useTranslation } from '@/i18n'
import { autonymOf } from './languageAutonyms'

interface LanguageChipProps {
  code: string
  active: boolean
  onSelect: (code: string) => void
}

export function LanguageChip({ code, active, onSelect }: LanguageChipProps) {
  const { t } = useTranslation()
  const autonym = autonymOf(code)
  return (
    <button
      type="button"
      aria-pressed={active}
      aria-label={t('parentResources.languageChip.label', { language: autonym })}
      onClick={() => onSelect(code)}
      data-testid={`language-chip-${code}`}
      className={
        'inline-flex items-center gap-1 px-2 py-0.5 rounded-full ' +
        'text-xs font-medium border transition-colors ' +
        'focus:outline-none focus:ring-2 focus:ring-lsc-rose focus:ring-offset-1 ' +
        (active
          ? 'bg-lsc-rose text-white border-lsc-rose'
          : 'bg-lsc-cream/40 dark:bg-earth-800 ' +
            'text-lsc-dark dark:text-lsc-cream ' +
            'border-lsc-border dark:border-earth-700 ' +
            'hover:bg-lsc-cream dark:hover:bg-earth-700')
      }
    >
      {active && <Check className="w-3 h-3" aria-hidden="true" />}
      <span lang={code}>{autonym}</span>
    </button>
  )
}
