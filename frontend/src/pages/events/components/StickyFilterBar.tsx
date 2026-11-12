/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect, useCallback } from 'react'
import { Search, X } from 'lucide-react'
import { useAccessibility } from '@/features/accessibility/hooks/useAccessibility'
import { useTranslation } from '@/i18n/I18nContext'

interface StickyFilterBarProps {
  filterRef: React.RefObject<HTMLElement>
  activeFilterCount: number
  searchQuery: string
  onClearFilters: () => void
  onExpandFilters: () => void
}

export default function StickyFilterBar({
  filterRef,
  activeFilterCount,
  searchQuery,
  onClearFilters,
  onExpandFilters,
}: StickyFilterBarProps): React.ReactElement | null {
  const { t } = useTranslation()
  const [isVisible, setIsVisible] = useState(false)
  const { settings } = useAccessibility()
  const reduceMotion = settings.reduceMotion || false

  useEffect(() => {
    const target = filterRef.current
    if (!target) return

    const observer = new IntersectionObserver(
      (entries) => {
        const entry = entries[0]
        if (!entry) return
        // Show sticky bar when the inline filter section is NOT intersecting (scrolled out of view)
        setIsVisible(!entry.isIntersecting)
      },
      { threshold: 0 }
    )

    observer.observe(target)
    return () => observer.disconnect()
  }, [filterRef])

  const handleExpand = useCallback(() => {
    onExpandFilters()
  }, [onExpandFilters])

  const handleClear = useCallback((e: React.MouseEvent) => {
    e.stopPropagation()
    onClearFilters()
  }, [onClearFilters])

  if (!isVisible) return null

  return (
    <div
      className={`sticky top-0 z-40 h-12 flex items-center justify-between px-4
        bg-lsc-white/95 dark:bg-earth-900/95 backdrop-blur-sm
        border-b border-lsc-border dark:border-earth-700
        shadow-soft-sm
        ${reduceMotion ? '' : 'transition-opacity duration-200'}`}
      aria-label={t('aria.stickyFilterBar.eventFilters')}
      role="toolbar"
    >
      <button
        type="button"
        onClick={handleExpand}
        className="flex items-center gap-2 text-sm text-lsc-dark dark:text-lsc-cream hover:text-lsc-rose dark:hover:text-lsc-rose transition-colors focus:outline-none focus:ring-2 focus:ring-lsc-rose focus:ring-offset-1 rounded-lg px-1 py-0.5"
        aria-label={
          activeFilterCount > 0
            ? `${t('events.actions.showFilters', 'Show filters')} (${activeFilterCount} active)`
            : t('events.actions.showFilters', 'Show filters')
        }
      >
        <Search className="w-4 h-4" aria-hidden="true" />
        {searchQuery && (
          <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 max-w-[7.5rem] truncate" title={searchQuery}>
            {searchQuery}
          </span>
        )}
        {activeFilterCount > 0 && (
          <span
            className="bg-lsc-rose text-white text-xs px-2 py-0.5 rounded-full font-medium"
            aria-live="polite"
          >
            {activeFilterCount}
          </span>
        )}
      </button>

      {activeFilterCount > 0 && (
        <button
          type="button"
          onClick={handleClear}
          className="flex items-center gap-1 text-xs text-lsc-dark/70 dark:text-lsc-cream/60 hover:text-status-danger-600 dark:hover:text-status-danger-400 transition-colors focus:outline-none focus:ring-2 focus:ring-lsc-rose focus:ring-offset-1 rounded-lg px-1 py-0.5"
          aria-label={t('aria.catalog.clearAllFilters')}
        >
          <X className="w-3 h-3" aria-hidden="true" />
          {t('events.actions.clearShort', 'Clear')}
        </button>
      )}
    </div>
  )
}
