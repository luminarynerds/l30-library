/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { List, LayoutGrid } from 'lucide-react'
import { clsx } from '@/utils/helpers'
import { t } from '@/i18n'

interface CatalogViewToggleProps {
  viewMode: 'list' | 'grid'
  onViewChange: (mode: 'list' | 'grid') => void
  disabled?: boolean
}

export default function CatalogViewToggle({ viewMode, onViewChange, disabled }: CatalogViewToggleProps) {
  return (
    <div
      className={clsx(
        'flex items-center gap-1.5 bg-lsc-cream/80 dark:bg-earth-800 rounded-lg p-[2px] border border-lsc-border dark:border-earth-600 lg:pl-2.5',
        disabled && 'opacity-40'
      )}
      role="group"
      aria-label={t('aria.boardMembers.viewMode')}
    >
      <span className="hidden text-xs font-bold text-lsc-dark/70 dark:text-lsc-cream/60 uppercase tracking-wide select-none lg:inline" aria-hidden="true">View</span>
      <button
        type="button"
        className={clsx(
          'flex items-center justify-center gap-1 px-2 py-[5px] min-h-[36px] rounded-lg text-xs font-bold transition-[background-color,color,box-shadow] duration-150 ease-[cubic-bezier(0.23,1,0.32,1)] focus-visible:ring-2 focus-visible:ring-lsc-rose lg:px-3',
          viewMode === 'list'
            ? 'bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream shadow-sm'
            : 'text-lsc-dark/70 dark:text-lsc-cream/60 hover:text-lsc-dark dark:hover:text-lsc-cream'
        )}
        aria-pressed={viewMode === 'list'}
        aria-label={t('aria.notifications.listView')}
        disabled={disabled}
        onClick={() => onViewChange('list')}
      >
        <List className="w-4 h-4" aria-hidden="true" />
        <span className="hidden lg:inline">List</span>
      </button>
      <button
        type="button"
        className={clsx(
          'flex items-center justify-center gap-1 px-2 py-[5px] min-h-[36px] rounded-lg text-xs font-bold transition-[background-color,color,box-shadow] duration-150 ease-[cubic-bezier(0.23,1,0.32,1)] focus-visible:ring-2 focus-visible:ring-lsc-rose lg:px-3',
          viewMode === 'grid'
            ? 'bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream shadow-sm'
            : 'text-lsc-dark/70 dark:text-lsc-cream/60 hover:text-lsc-dark dark:hover:text-lsc-cream'
        )}
        aria-pressed={viewMode === 'grid'}
        aria-label={t('aria.catalogViewToggle.gridView')}
        disabled={disabled}
        onClick={() => onViewChange('grid')}
      >
        <LayoutGrid className="w-4 h-4" aria-hidden="true" />
        <span className="hidden lg:inline">Grid</span>
      </button>
    </div>
  )
}
