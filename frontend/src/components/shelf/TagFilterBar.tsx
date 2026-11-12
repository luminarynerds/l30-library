/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Settings2, X } from 'lucide-react'
import { t } from '@/i18n'

interface TagFilterBarProps {
  allTags: string[]
  activeFilters: string[]
  onToggleFilter: (tag: string) => void
  onClearFilters: () => void
  onOpenManager?: () => void
}

export default function TagFilterBar({
  allTags,
  activeFilters,
  onToggleFilter,
  onClearFilters,
  onOpenManager,
}: TagFilterBarProps) {
  if (allTags.length === 0) return null

  return (
    <div className="mb-4" role="group" aria-label={t('aria.shelf.tagFilters')}>
      <div className="flex items-center gap-2 overflow-x-auto pb-1 scrollbar-hide">
        {/* Tag manager gear */}
        {onOpenManager && (
          <button
            onClick={onOpenManager}
            aria-label={t('aria.shelf.manageTags')}
            className="shrink-0 w-7 h-7 rounded-full border border-lsc-border dark:border-earth-600 flex items-center justify-center text-lsc-dark/70 dark:text-lsc-cream/60 hover:text-lsc-rose dark:hover:text-lsc-rose-light hover:border-lsc-rose transition-colors"
          >
            <Settings2 className="w-3.5 h-3.5" aria-hidden="true" />
          </button>
        )}

        {/* Tag chips */}
        {allTags.map((tag) => {
          const isActive = activeFilters.includes(tag)
          return (
            <button
              key={tag}
              onClick={() => onToggleFilter(tag)}
              aria-pressed={isActive}
              className={`shrink-0 text-xs px-3 py-1.5 min-h-[44px] sm:min-h-0 sm:py-1 rounded-full border transition-colors whitespace-nowrap flex items-center ${
                isActive
                  ? 'bg-lsc-rose text-white border-lsc-rose'
                  : 'bg-lsc-white dark:bg-earth-800 text-lsc-dark/70 dark:text-lsc-cream/70 border-lsc-border dark:border-earth-600 hover:border-lsc-rose dark:hover:border-lsc-rose-light'
              }`}
            >
              {tag}
            </button>
          )
        })}

        {/* Clear all */}
        {activeFilters.length > 0 && (
          <button
            onClick={onClearFilters}
            className="shrink-0 inline-flex items-center gap-1 text-xs text-status-danger-500 dark:text-status-danger-400 hover:text-status-danger-600 transition-colors"
          >
            <X className="w-3 h-3" aria-hidden="true" />
            Clear
          </button>
        )}
      </div>
    </div>
  )
}
