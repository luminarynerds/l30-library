// SPDX-FileCopyrightText: 2026 Luminary Nerds
// SPDX-License-Identifier: AGPL-3.0-or-later
/**
 * Reusable multi-select facet group for the catalog filter sidebar.
 *
 * The existing FilterGroup and CheckboxGroup (in CatalogFilterSidebar.tsx) are
 * single-select by design — this is the multi-select counterpart introduced for
 * the subject facet. Author and series facets will reuse it later.
 *
 * A11y
 * ----
 * - role="group" + aria-labelledby resolving to a visible localized heading.
 * - Selection changes are announced via the injected `announceToScreenReader`
 *   helper (throttled 250ms).
 * - Native checkbox semantics; arrow keys do not override tab order.
 * - prefers-reduced-motion removes the Show-more reveal transition.
 */
import { useCallback, useMemo, useRef, useState } from 'react'
import { clsx } from '@/utils/helpers'

export interface FacetValue {
  value: string
  count: number
}

export interface MultiSelectFilterGroupProps {
  label: string
  facets: FacetValue[]
  selectedValues: string[]
  onChange: (next: string[]) => void
  defaultOpen?: boolean
  showMoreThreshold?: number
  showMoreLimit?: number
  announceToScreenReader?: (message: string) => void
}

const slugify = (s: string) =>
  s.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '')

export function MultiSelectFilterGroup({
  label,
  facets,
  selectedValues,
  onChange,
  defaultOpen = false,
  showMoreThreshold = 25,
  showMoreLimit = 50,
  announceToScreenReader,
}: MultiSelectFilterGroupProps) {
  const headingId = `msfg-${slugify(label)}-label`
  const [userExpanded, setUserExpanded] = useState(false)
  const expanded = userExpanded || facets.length <= showMoreThreshold
  const lastAnnounceRef = useRef(0)

  const visibleFacets = useMemo(
    () => (expanded ? facets.slice(0, showMoreLimit) : facets.slice(0, showMoreThreshold)),
    [facets, expanded, showMoreThreshold, showMoreLimit],
  )

  const announce = useCallback(
    (message: string) => {
      if (!announceToScreenReader) return
      const now = Date.now()
      if (now - lastAnnounceRef.current < 250) return
      lastAnnounceRef.current = now
      announceToScreenReader(message)
    },
    [announceToScreenReader],
  )

  const toggle = useCallback(
    (value: string) => {
      const isOn = selectedValues.includes(value)
      const next = isOn
        ? selectedValues.filter((v) => v !== value)
        : [...selectedValues, value]
      onChange(next)
      announce(`${label} ${value} ${isOn ? 'cleared' : 'selected'}`)
    },
    [selectedValues, onChange, announce, label],
  )

  if (facets.length === 0) return null

  const hiddenCount = facets.length - visibleFacets.length

  return (
    <details
      open={defaultOpen}
      className="border-b border-lsc-rose/15 dark:border-lsc-cream/10 py-3"
    >
      <summary className="flex items-center justify-between cursor-pointer text-base font-semibold text-lsc-dark dark:text-lsc-cream">
        <span id={headingId}>{label}</span>
      </summary>
      <div
        role="group"
        aria-labelledby={headingId}
        className="mt-2 space-y-px motion-safe:transition-[max-height] motion-reduce:transition-none"
      >
        {visibleFacets.map((facet) => {
          const isOn = selectedValues.includes(facet.value)
          return (
            <label
              key={facet.value}
              className={clsx(
                'flex items-center gap-[10px] py-[7px] px-2 -mx-2 rounded-lg text-sm cursor-pointer transition-colors',
                isOn
                  ? 'text-lsc-rose font-semibold bg-lsc-rose/10 dark:bg-lsc-rose/10'
                  : 'text-lsc-dark dark:text-lsc-cream hover:text-lsc-dark dark:hover:text-lsc-cream',
              )}
            >
              <input
                type="checkbox"
                checked={isOn}
                onChange={() => toggle(facet.value)}
                className="w-[18px] h-[18px] accent-lsc-rose cursor-pointer flex-shrink-0"
                aria-label={`${facet.value}, ${facet.count} results`}
              />
              <span className="flex-1">{facet.value}</span>
              <span className="text-xs text-lsc-dark/60 dark:text-lsc-cream/60 tabular-nums">
                ({facet.count})
              </span>
            </label>
          )
        })}
        {hiddenCount > 0 && !expanded && (
          <button
            type="button"
            onClick={() => setUserExpanded(true)}
            className="mt-1 text-sm text-lsc-rose underline underline-offset-2 hover:no-underline"
          >
            Show {hiddenCount} more
          </button>
        )}
      </div>
    </details>
  )
}
