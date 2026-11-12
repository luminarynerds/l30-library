/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { Search, X, Filter, History, Tag, ChevronDown, Users, Layers, Accessibility, Clock, DoorOpen, Languages, MapPin } from 'lucide-react'
import { useTranslation } from '@/i18n/I18nContext'
import type { EventFilters, EventWhenWindow } from '@/api/api'
import { getCategoryDisplayName } from '@/pages/events/utils/eventCategoryColors'
import { formatLanguageName } from '@/pages/events/utils/formatters'
import { t } from '@/i18n'

// Accessibility provisions a patron can filter by. `value` is the Event
// column name — it is the contract shared with the backend whitelist and the
// `accessibility` query param. AND semantics: an event must provide them all.
const ACCESSIBILITY_OPTIONS: { value: string; key: string; fallback: string }[] = [
  { value: 'wheelchair_accessible', key: 'events.filters.accessibility.wheelchair', fallback: 'Wheelchair accessible' },
  { value: 'asl_provided', key: 'events.filters.accessibility.asl', fallback: 'ASL provided' },
  { value: 'captioning_provided', key: 'events.filters.accessibility.captioning', fallback: 'Captioning provided' },
  { value: 'assistive_listening', key: 'events.filters.accessibility.assistiveListening', fallback: 'Assistive listening' },
  { value: 'sensory_friendly', key: 'events.filters.accessibility.sensory', fallback: 'Sensory-friendly' },
  { value: 'large_print_available', key: 'events.filters.accessibility.largePrint', fallback: 'Large print available' },
]

// Labels for the time-window quick filter, reused for the active-filter pill.
// `when`/`drop_in` are set by EventQuickChips; the panel just summarizes them.
const WHEN_LABEL_KEYS: Record<EventWhenWindow, { key: string; fallback: string }> = {
  today: { key: 'events.quickChips.today', fallback: 'Today' },
  weekend: { key: 'events.quickChips.thisWeekend', fallback: 'This weekend' },
  week: { key: 'events.quickChips.next7Days', fallback: 'Next 7 days' },
}

function deduplicateCategories(categories: string[]): { display: string; value: string }[] {
  const seen = new Map<string, string>()
  for (const cat of categories) {
    const display = getCategoryDisplayName(cat)
    if (!seen.has(display)) seen.set(display, cat)
  }
  return Array.from(seen.entries()).map(([display, value]) => ({ display, value }))
}

interface EventFiltersProps {
  filters: EventFilters
  onChange: (filters: EventFilters) => void
  showPastEvents?: boolean
  onTogglePastEvents?: (show: boolean) => void
  availableTags?: string[]
  availableCategories?: string[]
  availableAudiences?: string[]
  /**
   * ISO 639-1 codes present on currently loaded events. The language facet
   * renders only when non-empty (most events carry no language).
   */
  availableLanguages?: string[]
  /**
   * Branches hosting currently loaded events (plus any selected ids, so an
   * active branch filter keeps its facet visible). The facet renders only
   * when there are 2+ branches — a single-branch library never sees it.
   */
  availableBranches?: { id: number; name: string }[]
  /**
   * If true, the panel renders with its body collapsed on first mount.
   * Used by EventsPageContent to start mobile users with the filter section
   * collapsed when no filters are active on URL load.
   */
  initialCollapsed?: boolean
}

// Note: Categories and audiences are now fetched dynamically from the backend
// and passed as props to this component

// Chip component for filter selection
interface FilterChipProps {
  label: string
  isSelected: boolean
  onClick: () => void
}

function FilterChip({ label, isSelected, onClick }: FilterChipProps): React.ReactElement {
  return (
    <button
      onClick={onClick}
      className={`px-3 py-1.5 rounded-full text-sm font-medium transition-all focus:outline-none focus:ring-2 focus:ring-forest-500 focus:ring-offset-1 ${
        isSelected
          ? 'bg-lsc-dark dark:bg-lsc-cream text-white dark:text-lsc-dark shadow-sm'
          : 'bg-lsc-cream dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream/80 hover:bg-lsc-border dark:hover:bg-earth-600 border border-lsc-border dark:border-earth-700'
      }`}
      aria-pressed={isSelected}
    >
      {label}
      {isSelected && (
        <X className="w-3 h-3 ml-1.5 inline-block" aria-hidden="true" />
      )}
    </button>
  )
}

// Expandable filter section
interface FilterSectionProps {
  title: string
  icon: React.ReactNode
  children: React.ReactNode
  isExpanded: boolean
  onToggle: () => void
  hasActiveFilter?: boolean
}

function FilterSection({ title, icon, children, isExpanded, onToggle, hasActiveFilter }: FilterSectionProps): React.ReactElement {
  const sectionId = `filter-section-${title.toLowerCase().replace(/\s+/g, '-')}`
  return (
    <div className="border-b border-lsc-border/50 dark:border-earth-700/50 last:border-b-0">
      <button
        onClick={onToggle}
        className="w-full flex items-center justify-between py-2 text-left focus:outline-none focus:ring-2 focus:ring-lsc-rose focus:ring-inset rounded-lg"
        aria-expanded={isExpanded}
        aria-controls={sectionId}
      >
        <div className="flex items-center gap-2">
          <span className="text-lsc-rose dark:text-lsc-rose-light">{icon}</span>
          <span className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">{title}</span>
          {hasActiveFilter && (
            <span className="w-2 h-2 rounded-full bg-lsc-rose motion-safe:animate-pulse" aria-label={t('aria.eventFilters.filterActive')} />
          )}
        </div>
        <ChevronDown
          className={`w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/70 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
          aria-hidden="true"
        />
      </button>
      {isExpanded && (
        <div id={sectionId} className="pb-3 pt-1">
          {children}
        </div>
      )}
    </div>
  )
}

export default function EventFilters({
  filters,
  onChange,
  showPastEvents = false,
  onTogglePastEvents,
  availableTags = [],
  availableCategories = [],
  availableAudiences = [],
  availableLanguages = [],
  availableBranches = [],
  initialCollapsed = false,
}: EventFiltersProps): React.ReactElement {
  const { t } = useTranslation()
  // Track which sections are expanded
  const [isCollapsed, setIsCollapsed] = useState(initialCollapsed)
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    category: true,
    audience: false,
    accessibility: false,
    languages: false,
    branches: false,
    tags: false,
  })

  const toggleSection = (section: string) => {
    setExpandedSections(prev => ({ ...prev, [section]: !prev[section] }))
  }

  const selectedAudiences = filters.audiences ?? []
  const selectedAccessibility = filters.accessibility ?? []
  const selectedLanguages = filters.languages ?? []
  const selectedBranches = filters.branch_ids ?? []
  const branchNameById = new Map(availableBranches.map((b) => [b.id, b.name]))
  const activeFilterCount =
    [filters.category, filters.search, filters.tag, filters.when, filters.drop_in].filter(Boolean).length +
    (selectedAudiences.length > 0 ? 1 : 0) +
    (selectedAccessibility.length > 0 ? 1 : 0) +
    (selectedLanguages.length > 0 ? 1 : 0) +
    (selectedBranches.length > 0 ? 1 : 0)

  const handleClearFilters = () => {
    onChange({})
  }

  const handleCategoryClick = (category: string) => {
    const rest = { ...filters }
    if (filters.category === category) {
      delete rest.category
    } else {
      rest.category = category
    }
    onChange(rest)
  }

  const handleAudienceClick = (audience: string) => {
    const current = filters.audiences ?? []
    const next = current.includes(audience)
      ? current.filter(a => a !== audience)
      : [...current, audience]
    const rest = { ...filters }
    if (next.length === 0) {
      delete rest.audiences
    } else {
      rest.audiences = next
    }
    onChange(rest)
  }

  const handleClearAudiences = () => {
    const rest = { ...filters }
    delete rest.audiences
    onChange(rest)
  }

  // Accessibility provisions: multi-select with AND semantics (an event must
  // provide every selected provision). Mirrors the audience handler.
  const handleAccessibilityClick = (provision: string) => {
    const current = filters.accessibility ?? []
    const next = current.includes(provision)
      ? current.filter(p => p !== provision)
      : [...current, provision]
    const rest = { ...filters }
    if (next.length === 0) {
      delete rest.accessibility
    } else {
      rest.accessibility = next
    }
    onChange(rest)
  }

  const handleClearAccessibility = () => {
    const rest = { ...filters }
    delete rest.accessibility
    onChange(rest)
  }

  // Program language: multi-select with OR semantics (match any selected
  // language). Mirrors the audience handler.
  const handleLanguageClick = (code: string) => {
    const current = filters.languages ?? []
    const next = current.includes(code)
      ? current.filter(c => c !== code)
      : [...current, code]
    const rest = { ...filters }
    if (next.length === 0) {
      delete rest.languages
    } else {
      rest.languages = next
    }
    onChange(rest)
  }

  const handleClearLanguages = () => {
    const rest = { ...filters }
    delete rest.languages
    onChange(rest)
  }

  // Hosting branch: multi-select with OR semantics. Mirrors the audience handler.
  const handleBranchClick = (branchId: number) => {
    const current = filters.branch_ids ?? []
    const next = current.includes(branchId)
      ? current.filter(b => b !== branchId)
      : [...current, branchId]
    const rest = { ...filters }
    if (next.length === 0) {
      delete rest.branch_ids
    } else {
      rest.branch_ids = next
    }
    onChange(rest)
  }

  const handleClearBranches = () => {
    const rest = { ...filters }
    delete rest.branch_ids
    onChange(rest)
  }

  const handleTagClick = (tag: string) => {
    const rest = { ...filters }
    if (filters.tag === tag) {
      delete rest.tag
    } else {
      rest.tag = tag
    }
    onChange(rest)
  }

  const handleSearchChange = (value: string) => {
    const rest = { ...filters }
    if (value) {
      rest.search = value
    } else {
      delete rest.search
    }
    onChange(rest)
  }

  const clearFilter = (filterKey: 'category' | 'tag' | 'search' | 'when' | 'drop_in') => {
    const rest = { ...filters }
    delete rest[filterKey]
    onChange(rest)
  }

  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 space-y-4 w-full">
      {/* Header - click to collapse/expand */}
      <div className="flex items-center justify-between">
        <button
          onClick={() => setIsCollapsed(!isCollapsed)}
          className="flex items-center gap-2 focus:outline-none focus:ring-2 focus:ring-lsc-rose focus:ring-offset-1 rounded-lg"
          aria-expanded={!isCollapsed}
          aria-controls="event-filters-body"
        >
          <Filter className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
          <h2 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
            {t('events.filters.title')}
          </h2>
          {activeFilterCount > 0 && (
            <span className="px-2 py-0.5 text-xs bg-lsc-rose text-white rounded-full">
              {activeFilterCount}
            </span>
          )}
          <ChevronDown
            className={`w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/70 transition-transform ${isCollapsed ? '' : 'rotate-180'}`}
            aria-hidden="true"
          />
        </button>
        {activeFilterCount > 0 && !isCollapsed && (
          <button
            onClick={handleClearFilters}
            className="text-sm text-lsc-rose dark:text-lsc-rose-light hover:text-lsc-rose/80 font-medium flex items-center gap-1"
          >
            <X className="w-4 h-4" />
            {t('events.filters.clearAll')}
          </button>
        )}
      </div>

      {!isCollapsed && (<div id="event-filters-body" className="space-y-4">
      {/* Active Filters Pills - Show what's currently selected */}
      {activeFilterCount > 0 && (
        <div className="flex flex-wrap gap-2 pb-2 border-b border-lsc-border/50 dark:border-earth-700/50">
          {filters.search && (
            <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-medium bg-earth-100 dark:bg-earth-800/30 text-lsc-rose dark:text-lsc-rose-light">
              <Search className="w-3 h-3" aria-hidden="true" />
              "{filters.search}"
              <button
                onClick={() => clearFilter('search')}
                className="ml-1 hover:bg-earth-200 dark:hover:bg-earth-800/50 rounded-full p-0.5"
                aria-label={`Remove search filter: ${filters.search}`}
              >
                <X className="w-3 h-3" />
              </button>
            </span>
          )}
          {filters.category && (
            <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-medium bg-category-100 dark:bg-category-900/30 text-category-700 dark:text-category-300">
              <Layers className="w-3 h-3" aria-hidden="true" />
              {filters.category}
              <button
                onClick={() => clearFilter('category')}
                className="ml-1 hover:bg-category-200 dark:hover:bg-category-800/50 rounded-full p-0.5"
                aria-label={`Remove category filter: ${filters.category}`}
              >
                <X className="w-3 h-3" />
              </button>
            </span>
          )}
          {selectedAudiences.map((aud) => (
            <span
              key={aud}
              className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-medium bg-status-success-100 dark:bg-status-success-900/30 text-status-success-700 dark:text-status-success-300"
            >
              <Users className="w-3 h-3" aria-hidden="true" />
              {aud}
              <button
                onClick={() => handleAudienceClick(aud)}
                className="ml-1 hover:bg-status-success-200 dark:bg-status-success-900/40 dark:hover:bg-status-success-800/50 rounded-full p-0.5"
                aria-label={`Remove audience filter: ${aud}`}
              >
                <X className="w-3 h-3" />
              </button>
            </span>
          ))}
          {filters.when && (
            <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-medium bg-lsc-cream dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream">
              <Clock className="w-3 h-3" aria-hidden="true" />
              {t(WHEN_LABEL_KEYS[filters.when].key, WHEN_LABEL_KEYS[filters.when].fallback)}
              <button
                onClick={() => clearFilter('when')}
                className="ml-1 hover:bg-lsc-border dark:hover:bg-earth-600 rounded-full p-0.5"
                aria-label="Remove time filter"
              >
                <X className="w-3 h-3" />
              </button>
            </span>
          )}
          {filters.drop_in && (
            <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-medium bg-lsc-cream dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream">
              <DoorOpen className="w-3 h-3" aria-hidden="true" />
              {t('events.quickChips.dropIn', 'Drop-in only')}
              <button
                onClick={() => clearFilter('drop_in')}
                className="ml-1 hover:bg-lsc-border dark:hover:bg-earth-600 rounded-full p-0.5"
                aria-label="Remove drop-in filter"
              >
                <X className="w-3 h-3" />
              </button>
            </span>
          )}
          {selectedAccessibility.map((value) => {
            const opt = ACCESSIBILITY_OPTIONS.find(o => o.value === value)
            const label = opt ? t(opt.key, opt.fallback) : value
            return (
              <span
                key={value}
                className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-medium bg-lsc-cream dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
              >
                <Accessibility className="w-3 h-3" aria-hidden="true" />
                {label}
                <button
                  onClick={() => handleAccessibilityClick(value)}
                  className="ml-1 hover:bg-lsc-border dark:hover:bg-earth-600 rounded-full p-0.5"
                  aria-label={`Remove accessibility filter: ${label}`}
                >
                  <X className="w-3 h-3" />
                </button>
              </span>
            )
          })}
          {selectedLanguages.map((code) => {
            const label = formatLanguageName(code)
            return (
              <span
                key={code}
                className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-medium bg-lsc-cream dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
              >
                <Languages className="w-3 h-3" aria-hidden="true" />
                {label}
                <button
                  onClick={() => handleLanguageClick(code)}
                  className="ml-1 hover:bg-lsc-border dark:hover:bg-earth-600 rounded-full p-0.5"
                  aria-label={`Remove language filter: ${label}`}
                >
                  <X className="w-3 h-3" />
                </button>
              </span>
            )
          })}
          {selectedBranches.map((branchId) => {
            const label = branchNameById.get(branchId) ?? `#${branchId}`
            return (
              <span
                key={branchId}
                className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-medium bg-lsc-cream dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
              >
                <MapPin className="w-3 h-3" aria-hidden="true" />
                {label}
                <button
                  onClick={() => handleBranchClick(branchId)}
                  className="ml-1 hover:bg-lsc-border dark:hover:bg-earth-600 rounded-full p-0.5"
                  aria-label={`Remove branch filter: ${label}`}
                >
                  <X className="w-3 h-3" />
                </button>
              </span>
            )
          })}
          {filters.tag && (
            <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-medium bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-700 dark:text-status-warning-300">
              <Tag className="w-3 h-3" aria-hidden="true" />
              {filters.tag}
              <button
                onClick={() => clearFilter('tag')}
                className="ml-1 hover:bg-status-warning-200 dark:hover:bg-status-warning-800/50 rounded-full p-0.5"
                aria-label={`Remove tag filter: ${filters.tag}`}
              >
                <X className="w-3 h-3" />
              </button>
            </span>
          )}
        </div>
      )}

      {/* Search Input */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/70" />
        <input
          type="text"
          placeholder={t('events.filters.searchPlaceholder')}
          aria-label={t('events.filters.searchPlaceholder')}
          value={filters.search || ''}
          onChange={(e) => handleSearchChange(e.target.value)}
          className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-dark text-lsc-dark dark:text-lsc-cream placeholder-earth-500 dark:placeholder-earth-500 focus:outline-none focus:ring-2 focus:ring-lsc-rose"
        />
        {filters.search && (
          <button
            onClick={() => clearFilter('search')}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream"
            aria-label={t('aria.advancedStaffSearchModal.clearSearch')}
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* Filter Sections */}
      <div className="space-y-1">
        {/* Category Section */}
        <FilterSection
          title={t('events.filters.filterByCategory')}
          icon={<Layers className="w-4 h-4" />}
          isExpanded={expandedSections.category ?? false}
          onToggle={() => toggleSection('category')}
          hasActiveFilter={!!filters.category}
        >
          <div className="flex flex-wrap gap-2">
            {deduplicateCategories(availableCategories).map(({ display, value }) => (
              <FilterChip
                key={value}
                label={display}
                isSelected={filters.category === value}
                onClick={() => handleCategoryClick(value)}
              />
            ))}
          </div>
        </FilterSection>

        {/* Audience & Skill Level Section - multi-select with OR semantics */}
        <FilterSection
          title={t('events.filters.filterByAudience')}
          icon={<Users className="w-4 h-4" />}
          isExpanded={expandedSections.audience ?? false}
          onToggle={() => toggleSection('audience')}
          hasActiveFilter={selectedAudiences.length > 0}
        >
          <div className="flex flex-wrap items-center gap-2">
            {availableAudiences.map((audience) => (
              <FilterChip
                key={audience}
                label={audience}
                isSelected={selectedAudiences.includes(audience)}
                onClick={() => handleAudienceClick(audience)}
              />
            ))}
            {selectedAudiences.length > 0 && (
              <button
                onClick={handleClearAudiences}
                className="ml-1 inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium text-lsc-rose dark:text-lsc-rose-light hover:bg-lsc-rose/10 focus:outline-none focus:ring-2 focus:ring-lsc-rose"
                aria-label={t('events.filters.clearAudiences', 'Clear all audience filters')}
              >
                <X className="w-3 h-3" aria-hidden="true" />
                {t('events.filters.clearAudiences', 'Clear')}
              </button>
            )}
          </div>
        </FilterSection>

        {/* Tags Section */}
        {availableTags.length > 0 && (
          <FilterSection
            title={t('events.filters.filterByTag')}
            icon={<Tag className="w-4 h-4" />}
            isExpanded={expandedSections.tags ?? false}
            onToggle={() => toggleSection('tags')}
            hasActiveFilter={!!filters.tag}
          >
            <div className="flex flex-wrap gap-2">
              {availableTags.map((tag) => (
                <FilterChip
                  key={tag}
                  label={tag}
                  isSelected={filters.tag === tag}
                  onClick={() => handleTagClick(tag)}
                />
              ))}
            </div>
          </FilterSection>
        )}

        {/* Program Language Section — multi-select, OR semantics; only shown
            when at least one loaded event declares a language. */}
        {availableLanguages.length > 0 && (
          <FilterSection
            title={t('events.filters.filterByLanguage', 'Program language')}
            icon={<Languages className="w-4 h-4" />}
            isExpanded={expandedSections.languages ?? false}
            onToggle={() => toggleSection('languages')}
            hasActiveFilter={selectedLanguages.length > 0}
          >
            <div className="flex flex-wrap items-center gap-2">
              {availableLanguages.map((code) => (
                <FilterChip
                  key={code}
                  label={formatLanguageName(code)}
                  isSelected={selectedLanguages.includes(code)}
                  onClick={() => handleLanguageClick(code)}
                />
              ))}
              {selectedLanguages.length > 0 && (
                <button
                  onClick={handleClearLanguages}
                  className="ml-1 inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium text-lsc-rose dark:text-lsc-rose-light hover:bg-lsc-rose/10 focus:outline-none focus:ring-2 focus:ring-lsc-rose"
                  aria-label={t('events.filters.clearLanguages', 'Clear all language filters')}
                >
                  <X className="w-3 h-3" aria-hidden="true" />
                  {t('events.filters.clearLanguages', 'Clear')}
                </button>
              )}
            </div>
          </FilterSection>
        )}

        {/* Branch Section — multi-select, OR semantics; only shown when the
            loaded events span 2+ branches (single-branch libraries never
            see it). */}
        {availableBranches.length >= 2 && (
          <FilterSection
            title={t('events.filters.filterByBranch', 'Location / branch')}
            icon={<MapPin className="w-4 h-4" />}
            isExpanded={expandedSections.branches ?? false}
            onToggle={() => toggleSection('branches')}
            hasActiveFilter={selectedBranches.length > 0}
          >
            <div className="flex flex-wrap items-center gap-2">
              {availableBranches.map((branch) => (
                <FilterChip
                  key={branch.id}
                  label={branch.name}
                  isSelected={selectedBranches.includes(branch.id)}
                  onClick={() => handleBranchClick(branch.id)}
                />
              ))}
              {selectedBranches.length > 0 && (
                <button
                  onClick={handleClearBranches}
                  className="ml-1 inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium text-lsc-rose dark:text-lsc-rose-light hover:bg-lsc-rose/10 focus:outline-none focus:ring-2 focus:ring-lsc-rose"
                  aria-label={t('events.filters.clearBranches', 'Clear all branch filters')}
                >
                  <X className="w-3 h-3" aria-hidden="true" />
                  {t('events.filters.clearBranches', 'Clear')}
                </button>
              )}
            </div>
          </FilterSection>
        )}

        {/* Accessibility Provisions Section — multi-select, AND semantics */}
        <FilterSection
          title={t('events.filters.filterByAccessibility', 'Accessibility provisions')}
          icon={<Accessibility className="w-4 h-4" />}
          isExpanded={expandedSections.accessibility ?? false}
          onToggle={() => toggleSection('accessibility')}
          hasActiveFilter={selectedAccessibility.length > 0}
        >
          <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">
            {t('events.filters.accessibilityHint', 'Show only events that provide all selected provisions.')}
          </p>
          <div className="flex flex-wrap items-center gap-2">
            {ACCESSIBILITY_OPTIONS.map((opt) => (
              <FilterChip
                key={opt.value}
                label={t(opt.key, opt.fallback)}
                isSelected={selectedAccessibility.includes(opt.value)}
                onClick={() => handleAccessibilityClick(opt.value)}
              />
            ))}
            {selectedAccessibility.length > 0 && (
              <button
                onClick={handleClearAccessibility}
                className="ml-1 inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium text-lsc-rose dark:text-lsc-rose-light hover:bg-lsc-rose/10 focus:outline-none focus:ring-2 focus:ring-lsc-rose"
                aria-label={t('events.filters.clearAccessibility', 'Clear all accessibility filters')}
              >
                <X className="w-3 h-3" aria-hidden="true" />
                {t('events.filters.clearAccessibility', 'Clear')}
              </button>
            )}
          </div>
        </FilterSection>
      </div>

      {/* Past Events Toggle */}
      {onTogglePastEvents && (
        <div className="flex items-center justify-between pt-3 border-t border-lsc-border dark:border-earth-700">
          <button
            onClick={() => onTogglePastEvents(!showPastEvents)}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-all focus:outline-none focus:ring-2 focus:ring-earth-500 ${
              showPastEvents
                ? 'bg-earth-600 dark:bg-earth-500 text-white'
                : 'bg-lsc-cream dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream/80 hover:bg-lsc-border dark:hover:bg-earth-600 border border-lsc-border dark:border-earth-700'
            }`}
            role="switch"
            aria-checked={showPastEvents}
            aria-label={showPastEvents ? t('events.filters.showingPastEvents') : t('events.filters.showPastEvents')}
          >
            <History className="w-4 h-4" aria-hidden="true" />
            <span>{showPastEvents ? t('events.filters.showingPastEvents') : t('events.filters.showPastEvents')}</span>
          </button>
          {showPastEvents && (
            <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 ml-4">
              {t('events.filters.browsingArchive')}
            </p>
          )}
        </div>
      )}
    </div>)}
    </div>
  )
}
