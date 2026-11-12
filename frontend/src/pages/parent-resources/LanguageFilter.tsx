/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * Page-level "show resources available in" filter. A `<select>` (not a
 * chip rail) because the union of available languages can be larger
 * than a comfortable horizontal scan -- a community might serve 10+
 * languages once translations land.
 *
 * Behavior:
 *  - Sorted alphabetically by autonym; "All languages" pinned first.
 *  - "All languages" maps to the empty string, which the parent maps
 *    to clearing the ?lang= URL param.
 *  - Status text below the select uses an `aria-live="polite"` region
 *    so screen readers announce the filtered count without stealing
 *    focus.
 *
 * A11y:
 *  - Visible `<label>` is `htmlFor` the `<select>` id (real label, no
 *    aria-label-only).
 *  - status region uses real text content (no flag emoji proxy).
 */
import { useId, useMemo } from 'react'
import { useTranslation } from '@/i18n'
import { autonymOf } from './languageAutonyms'

interface LanguageFilterProps {
  /** Union of codes across all rendered items. */
  availableCodes: string[]
  /** Currently active filter; empty string means "all". */
  selected: string
  onSelect: (code: string) => void
  /** Items visible after the filter is applied. */
  visibleCount: number
  /** Total items across all sections (filter denominator). */
  totalCount: number
}

export function LanguageFilter({
  availableCodes,
  selected,
  onSelect,
  visibleCount,
  totalCount,
}: LanguageFilterProps) {
  const { t } = useTranslation()
  const reactId = useId()
  const selectId = `parent-resources-language-filter-${reactId}`

  const options = useMemo(() => {
    // De-duplicate + sort by autonym (case-insensitive locale collation
    // so accented autonyms sort sensibly under their base letter).
    const uniq = Array.from(new Set(availableCodes.map((c) => c.toLowerCase())))
    return uniq
      .map((code) => ({ code, label: autonymOf(code) }))
      .sort((a, b) => a.label.localeCompare(b.label))
  }, [availableCodes])

  const statusText =
    selected === ''
      ? t('parentResources.languageFilter.statusAll', { total: totalCount })
      : t('parentResources.languageFilter.status', {
          visible: visibleCount,
          total: totalCount,
          language: autonymOf(selected),
        })

  return (
    <div className="flex flex-col gap-1 mb-4">
      <div className="flex items-center gap-2">
        <label
          htmlFor={selectId}
          className="text-sm font-medium text-lsc-dark dark:text-lsc-cream"
        >
          {t('parentResources.languageFilter.label')}
        </label>
        <select
          id={selectId}
          value={selected}
          onChange={(e) => onSelect(e.target.value)}
          data-testid="language-filter-select"
          className={
            'rounded border border-lsc-border dark:border-earth-700 ' +
            'bg-white dark:bg-earth-900 ' +
            'text-sm text-lsc-dark dark:text-lsc-cream ' +
            'px-2 py-1 focus:outline-none focus:ring-2 focus:ring-lsc-rose'
          }
        >
          <option value="">{t('parentResources.languageFilter.allLanguages')}</option>
          {options.map((opt) => (
            <option key={opt.code} value={opt.code} lang={opt.code}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>
      <div
        role="status"
        aria-live="polite"
        data-testid="language-filter-status"
        className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70"
      >
        {statusText}
      </div>
    </div>
  )
}
