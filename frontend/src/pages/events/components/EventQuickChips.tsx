/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useCallback } from 'react'
import { Accessibility } from 'lucide-react'
import { useTranslation } from '@/i18n/I18nContext'
import type { EventFilters as Filters, EventWhenWindow } from '@/api/api'

interface EventQuickChipsProps {
  filters: Filters
  setFilters: (next: Filters | ((prev: Filters) => Filters)) => void
}

// Time-window chips. Mutually exclusive (single-select): picking one replaces
// any other, picking the active one clears it. `getEvents` expands the chosen
// window into concrete start_time bounds for the backend.
const WHEN_CHIPS: { value: EventWhenWindow; key: string; fallback: string }[] = [
  { value: 'today', key: 'events.quickChips.today', fallback: 'Today' },
  { value: 'weekend', key: 'events.quickChips.thisWeekend', fallback: 'This weekend' },
  { value: 'week', key: 'events.quickChips.next7Days', fallback: 'Next 7 days' },
]

const AUDIENCE_CHIPS: { value: string; key: string; fallback: string }[] = [
  { value: 'kids', key: 'events.quickChips.kids', fallback: 'Kids' },
  { value: 'teens', key: 'events.quickChips.teens', fallback: 'Teens' },
  { value: 'adults', key: 'events.quickChips.adults', fallback: 'Adults' },
  { value: 'seniors', key: 'events.quickChips.seniors', fallback: 'Seniors' },
]

// Most-used accessibility provisions, surfaced as always-visible toggle chips
// so patrons never have to open the filter accordion to find them. `value` is
// the Event accessibility column name — the contract shared with the backend
// `accessibility` query param (AND semantics: an event must provide all
// selected provisions). The full provision set still lives in EventFilters.
const ACCESSIBILITY_CHIPS: { value: string; key: string; fallback: string }[] = [
  { value: 'sensory_friendly', key: 'events.quickChips.sensoryFriendly', fallback: 'Sensory-friendly' },
  { value: 'asl_provided', key: 'events.quickChips.asl', fallback: 'ASL' },
  { value: 'captioning_provided', key: 'events.quickChips.captioned', fallback: 'Captioned' },
  { value: 'wheelchair_accessible', key: 'events.quickChips.stepFree', fallback: 'Step-free' },
]

export default function EventQuickChips({ filters, setFilters }: EventQuickChipsProps): React.ReactElement {
  const { t } = useTranslation()

  // EventQuickChips only writes filter state; `useEventsFilterUrlSync` (wired
  // in EventsPageContent) is the single owner of URL <-> filter sync for every
  // param, so the chips don't touch the URL directly.

  // Time-window: single-select. Re-clicking the active window clears it.
  const toggleWhen = useCallback(
    (value: EventWhenWindow) => {
      setFilters((prev) => {
        const next = { ...prev }
        if (prev.when === value) delete next.when
        else next.when = value
        return next
      })
    },
    [setFilters]
  )

  // Drop-in: an independent boolean toggle.
  const toggleDropIn = useCallback(() => {
    setFilters((prev) => {
      const next = { ...prev }
      if (prev.drop_in) delete next.drop_in
      else next.drop_in = true
      return next
    })
  }, [setFilters])

  // Audience: multi-select, matching the EventFilters audience panel (OR
  // semantics). Both controls write `filters.audiences`; keeping them both
  // multi-select stops one from silently clobbering the other's selection.
  const toggleAudience = useCallback(
    (value: string) => {
      setFilters((prev) => {
        const current = prev.audiences ?? []
        const nextAudiences = current.includes(value)
          ? current.filter((a) => a !== value)
          : [...current, value]
        const next = { ...prev }
        if (nextAudiences.length > 0) next.audiences = nextAudiences
        else delete next.audiences
        return next
      })
    },
    [setFilters]
  )

  // Accessibility provisions: multi-select, AND semantics, writing the same
  // `filters.accessibility` array the EventFilters panel owns.
  const toggleAccessibility = useCallback(
    (value: string) => {
      setFilters((prev) => {
        const current = prev.accessibility ?? []
        const nextProvisions = current.includes(value)
          ? current.filter((p) => p !== value)
          : [...current, value]
        const next = { ...prev }
        if (nextProvisions.length > 0) next.accessibility = nextProvisions
        else delete next.accessibility
        return next
      })
    },
    [setFilters]
  )

  const chipBase =
    'inline-flex items-center gap-1.5 px-3 py-1.5 min-h-[44px] rounded-full text-xs font-semibold border-2 transition-colors focus:outline-none focus:ring-2 focus:ring-lsc-rose focus:ring-offset-2 focus:ring-offset-lsc-cream dark:focus:ring-offset-earth-900 touch-manipulation snap-start whitespace-nowrap'
  const chipOff =
    'bg-lsc-cream dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream border-lsc-border dark:border-earth-700 hover:bg-lsc-border/40 dark:hover:bg-earth-700'
  const chipOn =
    'bg-lsc-rose text-white border-lsc-rose-dark hover:bg-lsc-rose-dark'

  const accessibilityChipOn =
    'bg-forest-800 text-white border-forest-900 hover:bg-forest-900'

  return (
    <div className="space-y-2">
    <nav
      aria-label={t('events.quickChips.label', 'Event quick filters')}
      className="flex md:flex-wrap gap-2 overflow-x-auto snap-x pb-1"
    >
      {WHEN_CHIPS.map((chip) => {
        const on = filters.when === chip.value
        return (
          <button
            key={chip.value}
            type="button"
            aria-pressed={on}
            onClick={() => toggleWhen(chip.value)}
            className={`${chipBase} ${on ? chipOn : chipOff}`}
          >
            {t(chip.key, chip.fallback)}
          </button>
        )
      })}

      <button
        type="button"
        aria-pressed={!!filters.drop_in}
        onClick={toggleDropIn}
        className={`${chipBase} ${filters.drop_in ? chipOn : chipOff}`}
      >
        {t('events.quickChips.dropIn', 'Drop-in only')}
      </button>

      {AUDIENCE_CHIPS.map((chip) => {
        const on = (filters.audiences ?? []).includes(chip.value)
        return (
          <button
            key={chip.value}
            type="button"
            aria-pressed={on}
            onClick={() => toggleAudience(chip.value)}
            className={`${chipBase} ${on ? chipOn : chipOff}`}
          >
            {t(chip.key, chip.fallback)}
          </button>
        )
      })}
    </nav>

    {/* Accessibility provisions — promoted out of the filter accordion so the
        key access toggles are visible without expanding anything. */}
    <nav
      aria-label={t('events.quickChips.accessibilityLabel', 'Accessibility provisions')}
      className="flex md:flex-wrap items-center gap-2 overflow-x-auto snap-x pb-1"
    >
      <span className="inline-flex items-center gap-1 text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 whitespace-nowrap shrink-0">
        <Accessibility aria-hidden="true" className="w-4 h-4 text-lsc-rose dark:text-lsc-rose-light" />
        {t('events.quickChips.accessibilityHeading', 'Access:')}
      </span>
      {ACCESSIBILITY_CHIPS.map((chip) => {
        const on = (filters.accessibility ?? []).includes(chip.value)
        return (
          <button
            key={chip.value}
            type="button"
            aria-pressed={on}
            onClick={() => toggleAccessibility(chip.value)}
            className={`${chipBase} ${on ? accessibilityChipOn : chipOff}`}
          >
            {t(chip.key, chip.fallback)}
          </button>
        )
      })}
    </nav>
    </div>
  )
}
