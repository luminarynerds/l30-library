/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useMemo, useState, type ReactNode } from 'react'
import { X, Filter, ChevronDown } from 'lucide-react'
import { clsx } from '@/utils/helpers'
import { useFocusTrap } from '@/hooks/useFocusTrap'
import { useTranslation } from '@/i18n/I18nContext'
import type { FacetValue, SearchFacets } from '@/api/domains/catalog/catalog-api'
import { FORMAT_LABELS } from '@/pages/catalog/utils/catalogHelpers'
import {
  FORMAT_FACETS,
  READING_TIME_BRACKETS,
  ACCESS_FILTERS,
  TOPIC_FILTERS,
} from '@/pages/catalog/utils/catalogFilterData'
import { LexileRangeFilter } from '@/components/LexileRangeFilter'
import { MultiSelectFilterGroup } from './MultiSelectFilterGroup'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface CatalogFilterSidebarProps {
  filters: {
    item_type: string | null
    location: string
    publisher: string
    reading_time: string
    access: string
    topic: string
    language: string
    year_min: string
    year_max: string
  }
  showNewArrivals: boolean
  showLargePrintOnly: boolean
  availableNowOnly: boolean
  availableForHold: boolean
  onFilterChange: (key: string, value: string) => void
  onToggleNewArrivals: () => void
  onToggleLargePrint: () => void
  onToggleAvailableNow: () => void
  onToggleAvailableForHold: () => void
  onClearFilters: () => void
  isDrawerOpen: boolean
  onDrawerClose: () => void
  minLexile?: number | null
  maxLexile?: number | null
  onLexileChange?: (next: { min: number | null; max: number | null }) => void
  facets?: SearchFacets | undefined
  subjectFacetSelections?: string[]
  onSubjectFacetsChange?: (next: string[]) => void
  authorFacetSelections?: string[]
  onAuthorFacetsChange?: (next: string[]) => void
  seriesFacetSelections?: string[]
  onSeriesFacetsChange?: (next: string[]) => void
  announceToScreenReader?: (message: string) => void
  onClearSearchHistory?: () => void
}

type FilterContentProps = Pick<
  CatalogFilterSidebarProps,
  'filters' | 'availableNowOnly' | 'availableForHold' | 'onFilterChange' | 'onToggleAvailableNow' | 'onToggleAvailableForHold' | 'minLexile' | 'maxLexile' | 'onLexileChange' | 'facets' | 'subjectFacetSelections' | 'onSubjectFacetsChange' | 'authorFacetSelections' | 'onAuthorFacetsChange' | 'seriesFacetSelections' | 'onSeriesFacetsChange' | 'announceToScreenReader'
>

// ---------------------------------------------------------------------------
// LANGUAGE_OPTIONS -- ISO 639-2/B codes used by the BIBFRAME loader.
// We surface a fixed starter list (matches the normalization migration) and
// let Intl.DisplayNames translate each into the patron's UI locale at render
// time so we never ship per-locale strings for language names. Add a code
// here if data shows up that warrants it; missing codes fall back to the
// raw code in the UI.
// ---------------------------------------------------------------------------

const LANGUAGE_OPTIONS: ReadonlyArray<string> = [
  'eng', 'spa', 'fre', 'ger', 'chi', 'ara', 'rus', 'jpn', 'kor', 'por', 'ita', 'vie',
]

// Convert ISO 639-2/B (3-letter) to BCP-47 (2-letter) for Intl.DisplayNames.
// Codes outside this map are passed through; DisplayNames either resolves
// them or returns the raw code, which is the right fallback.
const ISO_639_2B_TO_BCP47: Record<string, string> = {
  eng: 'en', spa: 'es', fre: 'fr', ger: 'de', chi: 'zh', ara: 'ar',
  rus: 'ru', jpn: 'ja', kor: 'ko', por: 'pt', ita: 'it', vie: 'vi',
}

// ---------------------------------------------------------------------------
// CollapsibleSection -- native <details> wrapper for progressive disclosure.
// Reduces filter wall-of-text for ADHD/autistic users; keeps activeValue cue
// so collapsed sections still hint when a filter is applied.
// ---------------------------------------------------------------------------

function CollapsibleSection({
  title,
  defaultOpen,
  hasActive,
  children,
}: {
  title: string
  defaultOpen: boolean
  hasActive: boolean
  children: ReactNode
}) {
  return (
    <details open={defaultOpen || hasActive} className="mb-5 group">
      <summary
        className={clsx(
          'flex items-center justify-between cursor-pointer list-none',
          'font-serif text-[12px] font-bold uppercase tracking-[0.06em]',
          'pb-2 mb-[6px] border-b border-lsc-border dark:border-earth-700',
          'focus:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose rounded-sm',
          hasActive
            ? 'text-lsc-rose'
            : 'text-lsc-dark/70 dark:text-lsc-cream/60',
        )}
      >
        <span className="flex items-center gap-1.5">
          {title}
          {hasActive && (
            <span aria-hidden="true" className="w-1.5 h-1.5 rounded-full bg-lsc-rose" />
          )}
        </span>
        <ChevronDown
          aria-hidden="true"
          className="w-4 h-4 motion-safe:transition-transform group-open:rotate-180"
        />
      </summary>
      {children}
    </details>
  )
}

// ---------------------------------------------------------------------------
// FilterGroup -- renders a single facet group as checkboxes
// ---------------------------------------------------------------------------

function FilterGroup({
  title,
  values,
  activeValue,
  formatLabel,
  onSelect,
  defaultOpen = true,
}: {
  title: string
  values: FacetValue[]
  activeValue: string | null
  formatLabel: (v: string) => string
  onSelect: (value: string) => void
  defaultOpen?: boolean
}) {
  return (
    <CollapsibleSection title={title} defaultOpen={defaultOpen} hasActive={!!activeValue}>
      {values.map((facet) => {
        const isActive = activeValue === facet.value
        return (
          <label
            key={facet.value}
            className={clsx(
              'flex items-center gap-[10px] py-[7px] px-2 -mx-2 rounded-lg text-sm cursor-pointer transition-colors',
              isActive
                ? 'text-lsc-rose font-semibold bg-lsc-rose/10 dark:bg-lsc-rose/10'
                : 'text-lsc-dark dark:text-lsc-cream hover:text-lsc-dark dark:hover:text-lsc-cream',
            )}
          >
            <input
              type="checkbox"
              checked={isActive}
              onChange={() => onSelect(isActive ? '' : facet.value)}
              className="w-[18px] h-[18px] accent-lsc-rose cursor-pointer flex-shrink-0"
            />
            <span>{formatLabel(facet.value)}</span>
          </label>
        )
      })}
    </CollapsibleSection>
  )
}

// ---------------------------------------------------------------------------
// CheckboxGroup -- generic group for readonly filter arrays
// ---------------------------------------------------------------------------

function CheckboxGroup({
  title,
  options,
  activeValue,
  filterKey,
  onFilterChange,
  defaultOpen = false,
}: {
  title: string
  options: ReadonlyArray<{ value: string; label: string }>
  activeValue: string
  filterKey: string
  onFilterChange: (key: string, value: string) => void
  defaultOpen?: boolean
}) {
  return (
    <CollapsibleSection title={title} defaultOpen={defaultOpen} hasActive={!!activeValue}>
      {options.map((opt) => {
        const isActive = activeValue === opt.value
        return (
          <label
            key={opt.value}
            className={clsx(
              'flex items-center gap-[10px] py-[7px] px-2 -mx-2 rounded-lg text-sm cursor-pointer transition-colors',
              isActive
                ? 'text-lsc-rose font-semibold bg-lsc-rose/10 dark:bg-lsc-rose/10'
                : 'text-lsc-dark dark:text-lsc-cream hover:text-lsc-dark dark:hover:text-lsc-cream',
            )}
          >
            <input
              type="checkbox"
              checked={isActive}
              onChange={() => onFilterChange(filterKey, isActive ? '' : opt.value)}
              className="w-[18px] h-[18px] accent-lsc-rose cursor-pointer flex-shrink-0"
            />
            <span>{opt.label}</span>
          </label>
        )
      })}
    </CollapsibleSection>
  )
}

// ---------------------------------------------------------------------------
// LanguageFacet -- single-select language filter. Labels are self-translated
// via Intl.DisplayNames against the patron's current UI locale, so we never
// ship a per-locale string table for language names. Bad/unknown codes fall
// back to the raw 3-letter code (still clickable, just unlocalized).
// ---------------------------------------------------------------------------

function LanguageFacet({
  activeValue,
  onFilterChange,
}: {
  activeValue: string
  onFilterChange: (key: string, value: string) => void
}) {
  const { t, language: uiLanguage } = useTranslation()

  const labels = useMemo(() => {
    let dn: Intl.DisplayNames | null = null
    try {
      // ``Intl.DisplayNames`` is available in every browser we ship to,
      // but feature-detect anyway so a missing implementation degrades
      // gracefully instead of blowing up the sidebar.
      dn = new Intl.DisplayNames([uiLanguage], { type: 'language' })
    } catch {
      dn = null
    }
    return LANGUAGE_OPTIONS.map((code) => {
      const bcp47 = ISO_639_2B_TO_BCP47[code] ?? code
      let name: string | undefined
      try {
        name = dn?.of(bcp47)
      } catch {
        name = undefined
      }
      return { value: code, label: name && name !== bcp47 ? name : code }
    })
  }, [uiLanguage])

  return (
    <CollapsibleSection
      title={t('catalog.filterGroups.language', 'Language')}
      defaultOpen={!!activeValue}
      hasActive={!!activeValue}
    >
      {labels.map((opt) => {
        const isActive = activeValue === opt.value
        return (
          <label
            key={opt.value}
            className={clsx(
              'flex items-center gap-[10px] py-[7px] px-2 -mx-2 rounded-lg text-sm cursor-pointer transition-colors',
              isActive
                ? 'text-lsc-rose font-semibold bg-lsc-rose/10 dark:bg-lsc-rose/10'
                : 'text-lsc-dark dark:text-lsc-cream hover:text-lsc-dark dark:hover:text-lsc-cream',
            )}
          >
            <input
              type="checkbox"
              checked={isActive}
              onChange={() => onFilterChange('language', isActive ? '' : opt.value)}
              className="w-[18px] h-[18px] accent-lsc-rose cursor-pointer flex-shrink-0"
            />
            <span>{opt.label}</span>
          </label>
        )
      })}
    </CollapsibleSection>
  )
}


// ---------------------------------------------------------------------------
// YearRangeInputs -- holds local string state, only commits on blur or Enter
// so typing "1999" doesn't fire four queries (1, 19, 199, 1999) and the
// API never sees the partial value year_min=1. Clamps min <= max on commit.
// ---------------------------------------------------------------------------

const MIN_YEAR = 1900

function YearRangeInputs({
  yearMin,
  yearMax,
  onFilterChange,
}: {
  yearMin: string
  yearMax: string
  onFilterChange: (key: string, value: string) => void
}) {
  const { t } = useTranslation()
  const currentYear = new Date().getFullYear()
  const [draftMin, setDraftMin] = useState(yearMin)
  const [draftMax, setDraftMax] = useState(yearMax)

  // Re-sync the drafts when the parent filters reset (e.g. Clear All)
  useEffect(() => { setDraftMin(yearMin) }, [yearMin])
  useEffect(() => { setDraftMax(yearMax) }, [yearMax])

  const clamp = (raw: string): string => {
    if (raw === '') return ''
    const n = Number(raw)
    if (!Number.isFinite(n)) return ''
    return String(Math.min(currentYear, Math.max(MIN_YEAR, Math.trunc(n))))
  }

  const commit = () => {
    let nextMin = clamp(draftMin)
    let nextMax = clamp(draftMax)
    if (nextMin && nextMax && Number(nextMin) > Number(nextMax)) {
      ;[nextMin, nextMax] = [nextMax, nextMin]
    }
    setDraftMin(nextMin)
    setDraftMax(nextMax)
    if (nextMin !== yearMin) onFilterChange('year_min', nextMin)
    if (nextMax !== yearMax) onFilterChange('year_max', nextMax)
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      e.currentTarget.blur()
    }
  }

  return (
    <div className="flex items-center gap-2">
      <input
        type="number"
        inputMode="numeric"
        placeholder={t('catalog.filterOptions.yearFrom', 'From')}
        min={MIN_YEAR}
        max={currentYear}
        value={draftMin}
        onChange={(e) => setDraftMin(e.target.value)}
        onBlur={commit}
        onKeyDown={handleKeyDown}
        aria-label={t('catalog.filterOptions.yearFrom', 'From year')}
        className="w-full px-3 py-2 text-sm border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose/40"
      />
      <span className="text-lsc-dark/70 dark:text-lsc-cream/50 flex-shrink-0">&ndash;</span>
      <input
        type="number"
        inputMode="numeric"
        placeholder={t('catalog.filterOptions.yearTo', 'To')}
        min={MIN_YEAR}
        max={currentYear}
        value={draftMax}
        onChange={(e) => setDraftMax(e.target.value)}
        onBlur={commit}
        onKeyDown={handleKeyDown}
        aria-label={t('catalog.filterOptions.yearTo', 'To year')}
        className="w-full px-3 py-2 text-sm border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose/40"
      />
    </div>
  )
}

// ---------------------------------------------------------------------------
// TextFilterInput -- free-text filter (publisher, future location). Holds
// local draft state and only commits on blur/Enter so typing a multi-word
// value does not fire N queries. Matches YearRangeInputs commit semantics.
// ---------------------------------------------------------------------------

function TextFilterInput({
  value,
  filterKey,
  placeholder,
  ariaLabel,
  onFilterChange,
}: {
  value: string
  filterKey: string
  placeholder: string
  ariaLabel: string
  onFilterChange: (key: string, value: string) => void
}) {
  const [draft, setDraft] = useState(value)
  useEffect(() => { setDraft(value) }, [value])

  const commit = () => {
    const next = draft.trim().slice(0, 100)
    if (next !== draft) setDraft(next)
    if (next !== value) onFilterChange(filterKey, next)
  }

  return (
    <input
      type="text"
      maxLength={100}
      value={draft}
      onChange={(e) => setDraft(e.target.value)}
      onBlur={commit}
      onKeyDown={(e) => {
        if (e.key === 'Enter') {
          e.preventDefault()
          e.currentTarget.blur()
        }
      }}
      placeholder={placeholder}
      aria-label={ariaLabel}
      className="w-full px-3 py-2 text-sm border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose/40"
    />
  )
}

// ---------------------------------------------------------------------------
// FilterContent -- shared between desktop sidebar & mobile drawer
// ---------------------------------------------------------------------------

function FilterContent({
  filters,
  availableNowOnly,
  availableForHold,
  onFilterChange,
  onToggleAvailableNow,
  onToggleAvailableForHold,
  minLexile,
  maxLexile,
  onLexileChange,
  facets,
  subjectFacetSelections,
  onSubjectFacetsChange,
  authorFacetSelections,
  onAuthorFacetsChange,
  seriesFacetSelections,
  onSeriesFacetsChange,
  announceToScreenReader,
}: FilterContentProps) {
  const { t } = useTranslation()

  // Build translated reading time options
  const translatedReadingTime = READING_TIME_BRACKETS.map(b => ({
    ...b,
    label: b.value === 'under_2h' ? t('catalog.filterOptions.under2Hours')
         : b.value === '2_to_4h' ? t('catalog.filterOptions.2to4Hours')
         : t('catalog.filterOptions.over4Hours'),
  }))

  // Build translated access options
  const accessLabels = {
    has_audio: t('catalog.filterOptions.hasAudio'),
    visual_graphic: t('catalog.filterOptions.visualGraphic'),
    short_gentle: t('catalog.filterOptions.shortGentle'),
  }
  const translatedAccess = ACCESS_FILTERS.map(a => ({
    ...a,
    label: accessLabels[a.value],
  }))

  // Build translated topic options
  const topicKeyMap: Record<string, string> = {
    fiction: 'fiction', nonfiction: 'nonfiction', scifi: 'sciFi', memoir: 'memoir',
    poetry: 'poetry', lgbtq: 'lgbtq', neurodiversity: 'neurodiversity',
    middle_grade: 'middleGrade', young_adult: 'youngAdult',
    stem: 'stemScience', health: 'healthWellness', home: 'homeGarden',
  }
  const translatedTopics = TOPIC_FILTERS.map(tp => ({
    ...tp,
    label: t(`catalog.filterOptions.${topicKeyMap[tp.value] || tp.value}`),
  }))

  // "More filters" auto-expands when any advanced filter inside it is active,
  // so a deep-linked / restored advanced filter is never hidden from the
  // patron behind a collapsed disclosure.
  const hasAdvancedActive = !!(
    filters.reading_time ||
    filters.topic ||
    filters.language ||
    filters.year_min ||
    filters.year_max ||
    filters.publisher ||
    minLexile != null ||
    maxLexile != null ||
    (subjectFacetSelections?.length ?? 0) > 0 ||
    (authorFacetSelections?.length ?? 0) > 0 ||
    (seriesFacetSelections?.length ?? 0) > 0
  )

  return (
    <>
      {/* PRIMARY DECISIONS -- the three that matter first for most patrons.
          The long tail moves behind "More filters" below so the sidebar isn't
          a wall of unchecked checkboxes (where ND users abandon). */}

      {/* 1. Available now -- single checkbox after #887 collapsed the
          faux-enum status field to `available_only: boolean`. Unchecked = all
          items (default); checked = only items currently available. The
          `available_for_hold` toggle (#889) surfaces the backend filter that
          returns only items where placing a hold is meaningful. */}
      <CollapsibleSection
        title={t('catalog.filterGroups.availability')}
        defaultOpen
        hasActive={availableNowOnly || availableForHold}
      >
        <label className="flex items-center gap-[10px] py-[7px] text-sm text-lsc-dark dark:text-lsc-cream cursor-pointer">
          <input
            type="checkbox"
            checked={availableNowOnly}
            onChange={onToggleAvailableNow}
            className="w-[18px] h-[18px] accent-lsc-rose cursor-pointer flex-shrink-0"
          />
          <span>{t('catalog.filterOptions.availableNow')}</span>
        </label>
        <label className="flex items-center gap-[10px] py-[7px] text-sm text-lsc-dark dark:text-lsc-cream cursor-pointer">
          <input
            type="checkbox"
            checked={availableForHold}
            onChange={onToggleAvailableForHold}
            className="w-[18px] h-[18px] accent-lsc-rose cursor-pointer flex-shrink-0"
          />
          <span>{t('catalog.filterOptions.availableForHold', 'Holdable only')}</span>
        </label>
      </CollapsibleSection>

      {/* Active format stays visible; other format choices are disclosed on demand. */}
      <FilterGroup
        title={t('catalog.filterGroups.format')}
        values={FORMAT_FACETS}
        activeValue={filters.item_type}
        formatLabel={(v) => FORMAT_LABELS[v] || v}
        onSelect={(v) => onFilterChange('item_type', v)}
        defaultOpen={false}
      />

      {/* 3. Access & Sensory -- open by default (primary for our ND audience) */}
      <CheckboxGroup
        title={t('catalog.filterGroups.accessSensory')}
        options={translatedAccess}
        activeValue={filters.access}
        filterKey="access"
        onFilterChange={onFilterChange}
        defaultOpen
      />

      {/* MORE FILTERS -- everything else behind one disclosure. Auto-opens when
          a contained filter is already applied. */}
      <details open={hasAdvancedActive} className="mb-2 group">
        <summary
          className={clsx(
            'flex items-center justify-between cursor-pointer list-none',
            'font-serif text-[12px] font-bold uppercase tracking-[0.06em]',
            'py-2 mb-1',
            'focus:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose rounded-sm',
            'text-lsc-dark/70 dark:text-lsc-cream/60',
          )}
        >
          <span className="flex items-center gap-1.5">
            {t('catalog.filterGroups.moreFilters', 'More filters')}
            {hasAdvancedActive && (
              <span aria-hidden="true" className="w-1.5 h-1.5 rounded-full bg-lsc-rose" />
            )}
          </span>
          <ChevronDown
            aria-hidden="true"
            className="w-4 h-4 motion-safe:transition-transform group-open:rotate-180"
          />
        </summary>

        <div className="pt-1">
          {/* Reading Time */}
          <CheckboxGroup
            title={t('catalog.filterGroups.readingTime')}
            options={translatedReadingTime}
            activeValue={filters.reading_time}
            filterKey="reading_time"
            onFilterChange={onFilterChange}
          />

          {/* Topic */}
          <CheckboxGroup
            title={t('catalog.filterGroups.topic')}
            options={translatedTopics}
            activeValue={filters.topic}
            filterKey="topic"
            onFilterChange={onFilterChange}
          />

          {/* Language -- labels self-translated by Intl.DisplayNames */}
          <LanguageFacet
            activeValue={filters.language}
            onFilterChange={onFilterChange}
          />

          {/* Subjects (multi-select) -- only when backend returned subject facets */}
          {onSubjectFacetsChange && (facets?.subject?.length ?? 0) > 0 && (
            <MultiSelectFilterGroup
              label={t('catalog.facets.subjects', 'Subjects')}
              facets={facets!.subject!}
              selectedValues={subjectFacetSelections ?? []}
              onChange={onSubjectFacetsChange}
              defaultOpen={false}
              {...(announceToScreenReader ? { announceToScreenReader } : {})}
            />
          )}

          {/* Authors (multi-select) */}
          {onAuthorFacetsChange && (facets?.author?.length ?? 0) > 0 && (
            <MultiSelectFilterGroup
              label={t('catalog.facets.authors', 'Authors')}
              facets={facets!.author!}
              selectedValues={authorFacetSelections ?? []}
              onChange={onAuthorFacetsChange}
              defaultOpen={false}
              {...(announceToScreenReader ? { announceToScreenReader } : {})}
            />
          )}

          {/* Series (multi-select) -- only when >= 2 distinct values exist. */}
          {onSeriesFacetsChange && (facets?.series?.length ?? 0) >= 2 && (
            <MultiSelectFilterGroup
              label={t('catalog.facets.series', 'Series')}
              facets={facets!.series!}
              selectedValues={seriesFacetSelections ?? []}
              onChange={onSeriesFacetsChange}
              defaultOpen={false}
              {...(announceToScreenReader ? { announceToScreenReader } : {})}
            />
          )}

          {/* Publication Year */}
          <CollapsibleSection
            title={t('catalog.filterGroups.publicationYear', 'Publication Year')}
            defaultOpen={false}
            hasActive={!!(filters.year_min || filters.year_max)}
          >
            <YearRangeInputs
              yearMin={filters.year_min}
              yearMax={filters.year_max}
              onFilterChange={onFilterChange}
            />
          </CollapsibleSection>

          {/* Publisher -- free-text input (#885) */}
          <CollapsibleSection
            title={t('catalog.filterGroups.publisher', 'Publisher')}
            defaultOpen={false}
            hasActive={!!filters.publisher}
          >
            <TextFilterInput
              value={filters.publisher}
              filterKey="publisher"
              placeholder={t('catalog.filterOptions.publisherPlaceholder', 'e.g. Penguin')}
              ariaLabel={t('catalog.filterGroups.publisher', 'Publisher')}
              onFilterChange={onFilterChange}
            />
          </CollapsibleSection>

          {/* Reading Level (Lexile) */}
          {onLexileChange && (
            <div className="mb-5">
              <LexileRangeFilter
                min={minLexile ?? null}
                max={maxLexile ?? null}
                onChange={onLexileChange}
              />
            </div>
          )}
        </div>
      </details>
    </>
  )
}

// ---------------------------------------------------------------------------
// MobileFilterButton -- exported separately for use in page header area
// ---------------------------------------------------------------------------

export function MobileFilterButton({
  onClick,
  activeCount,
}: {
  onClick: () => void
  activeCount: number
}) {
  const { t } = useTranslation()

  return (
    <button
      className="flex lg:hidden items-center justify-center gap-[6px] w-full px-[18px] py-[10px] min-h-[44px] border-2 border-lsc-border dark:border-earth-700 rounded-xl text-sm font-bold text-lsc-dark dark:text-lsc-cream bg-lsc-white dark:bg-earth-800 mb-4"
      onClick={onClick}
      aria-label={t('catalog.showFilters')}
    >
      <Filter className="w-[18px] h-[18px]" />
      {t('catalog.filters')}
      {activeCount > 0 && (
        <span className="bg-lsc-rose text-white text-xs px-2 py-0.5 rounded-full min-w-[1.25rem] text-center">
          {activeCount}
        </span>
      )}
    </button>
  )
}

// ---------------------------------------------------------------------------
// CatalogFilterSidebar -- main export
// ---------------------------------------------------------------------------

export default function CatalogFilterSidebar(props: CatalogFilterSidebarProps) {
  const { t } = useTranslation()
  const { isDrawerOpen, onDrawerClose, onClearSearchHistory, ...rest } = props

  // Build filterContentProps via conditional spreads so optional undefined
  // values don't trip exactOptionalPropertyTypes (these properties are typed
  // `?:` without an explicit `| undefined`, so a literal `undefined` assignment
  // is rejected even though it is semantically equivalent).
  const filterContentProps: FilterContentProps = {
    filters: rest.filters,
    availableNowOnly: rest.availableNowOnly,
    availableForHold: rest.availableForHold,
    onFilterChange: rest.onFilterChange,
    onToggleAvailableNow: rest.onToggleAvailableNow,
    onToggleAvailableForHold: rest.onToggleAvailableForHold,
    ...(rest.minLexile !== undefined ? { minLexile: rest.minLexile } : {}),
    ...(rest.maxLexile !== undefined ? { maxLexile: rest.maxLexile } : {}),
    ...(rest.onLexileChange ? { onLexileChange: rest.onLexileChange } : {}),
    ...(rest.facets !== undefined ? { facets: rest.facets } : {}),
    ...(rest.subjectFacetSelections ? { subjectFacetSelections: rest.subjectFacetSelections } : {}),
    ...(rest.onSubjectFacetsChange ? { onSubjectFacetsChange: rest.onSubjectFacetsChange } : {}),
    ...(rest.authorFacetSelections ? { authorFacetSelections: rest.authorFacetSelections } : {}),
    ...(rest.onAuthorFacetsChange ? { onAuthorFacetsChange: rest.onAuthorFacetsChange } : {}),
    ...(rest.seriesFacetSelections ? { seriesFacetSelections: rest.seriesFacetSelections } : {}),
    ...(rest.onSeriesFacetsChange ? { onSeriesFacetsChange: rest.onSeriesFacetsChange } : {}),
    ...(rest.announceToScreenReader ? { announceToScreenReader: rest.announceToScreenReader } : {}),
  }

  const clearHistoryButton = onClearSearchHistory && (
    <button
      type="button"
      onClick={onClearSearchHistory}
      className="mt-4 text-xs text-lsc-dark/60 dark:text-lsc-cream/60 underline underline-offset-2 hover:text-lsc-rose focus:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose rounded-sm"
      title={t('catalog.facets.privacyNote', 'Your selections stay on this device only.')}
    >
      {t('catalog.facets.clearHistory', 'Clear search history')}
    </button>
  )

  // Trap focus inside the mobile drawer while open; restore focus + close on Escape.
  const drawerRef = useFocusTrap<HTMLDivElement>({
    isActive: isDrawerOpen,
    initialFocus: true,
    restoreFocus: true,
    onEscape: onDrawerClose,
  })

  // Lock body scroll while the mobile drawer is open so swipe-to-scroll doesn't
  // bleed through the overlay (sensory-overload mitigation for vestibular users).
  useEffect(() => {
    if (!isDrawerOpen) return
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => { document.body.style.overflow = previousOverflow }
  }, [isDrawerOpen])

  return (
    <>
      {/* Desktop sidebar -- hidden on mobile */}
      <aside
        className="hidden lg:block w-[260px] flex-shrink-0 sticky top-[90px] self-start max-h-[calc(100vh-110px)] overflow-y-auto pb-6 scrollbar-thin scrollbar-thumb-lsc-border dark:scrollbar-thumb-earth-600"
        aria-label={t('catalog.filters')}
        data-catalog-filters
      >
        <FilterContent {...filterContentProps} />
        {clearHistoryButton}
      </aside>

      {/* Mobile drawer overlay */}
      {isDrawerOpen && (
        <div
          className="fixed inset-0 bg-black/40 z-[200] lg:hidden"
          onClick={onDrawerClose}
          aria-hidden="true"
        />
      )}

      {/* Mobile drawer */}
      <div
        ref={drawerRef}
        className={clsx(
          'fixed top-0 left-0 bottom-0 w-[300px] max-w-[85vw] bg-lsc-cream dark:bg-lsc-dark z-[201] p-5 overflow-y-auto shadow-lg motion-safe:transition-transform motion-safe:duration-200 lg:hidden',
          isDrawerOpen ? 'translate-x-0' : '-translate-x-full'
        )}
        role="dialog"
        aria-modal={isDrawerOpen}
        aria-label={t('catalog.filters')}
        // @ts-expect-error inert is valid HTML but not in React 18 types
        inert={isDrawerOpen ? undefined : ''}
      >
        <div className="flex items-center justify-between mb-3">
          <h2 className="font-serif text-base font-bold text-lsc-dark dark:text-lsc-cream">
            {t('catalog.filters')}
          </h2>
          <button
            className="flex items-center justify-center w-10 h-10 rounded-lg text-lsc-dark/70 dark:text-lsc-cream/60 hover:bg-lsc-rose/10"
            onClick={onDrawerClose}
            aria-label={t('catalog.closeFilters')}
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        <FilterContent {...filterContentProps} />
        {clearHistoryButton}
        <div className="sticky bottom-0 pt-3 pb-1 bg-lsc-cream dark:bg-lsc-dark border-t border-lsc-border dark:border-earth-700 mt-4 -mx-5 px-5">
          <button
            onClick={onDrawerClose}
            className="w-full py-3 bg-lsc-rose text-white font-semibold rounded-xl hover:bg-lsc-rose/90 transition-colors"
          >
            {t('catalog.showResults', 'Show Results')}
          </button>
        </div>
      </div>
    </>
  )
}
