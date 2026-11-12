/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Tag, Globe, Clock, Hash } from 'lucide-react'
import { clsx } from '@/utils/helpers'
import { formatGenre } from '@/utils/format-utils'
import type { BibframeWork } from '@/api/domains/catalog/bibframe-api'

interface WorkCardProps {
  work: BibframeWork
  onClick: (id: number) => void
}

export function WorkCard({ work, onClick }: WorkCardProps): React.ReactElement {
  return (
    // eslint-disable-next-line jsx-a11y/click-events-have-key-events
    <article
      className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-sm p-5 hover:shadow-md transition-all duration-200 cursor-pointer focus-within:ring-2 focus-within:ring-lsc-rose border border-transparent hover:border-lsc-rose/20 dark:hover:border-lsc-rose/20"
      onClick={() => onClick(work.id)}
    >
      <button
        type="button"
        className="w-full text-left focus:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose focus-visible:ring-offset-2"
        onClick={() => onClick(work.id)}
        aria-label={`View BIBFRAME details for ${work.title}`}
      >
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream leading-snug">
              {work.title}
            </h3>
            {work.subtitle && (
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-0.5 truncate" title={work.subtitle}>
                {work.subtitle}
              </p>
            )}
          </div>
          <div className="flex items-center gap-1.5 flex-shrink-0">
            {typeof work.instance_count === 'number' && (
              <span
                className="text-xs px-2 py-0.5 rounded-full bg-earth-50 text-lsc-rose dark:bg-earth-800/30 dark:text-lsc-rose-light font-medium"
                title={`${work.instance_count} edition(s) / format(s)`}
              >
                {work.instance_count} ed.
              </span>
            )}
            {typeof work.item_count === 'number' && (
              <span
                className={clsx(
                  'text-xs px-2 py-0.5 rounded-full font-medium',
                  work.item_count > 0
                    ? 'bg-status-success-50 text-status-success-700 dark:bg-status-success-900/30 dark:text-status-success-300'
                    : 'bg-lsc-cream text-lsc-dark/70 dark:bg-earth-700 dark:text-lsc-cream/70'
                )}
                title={`${work.item_count} physical/digital cop${work.item_count === 1 ? 'y' : 'ies'}`}
              >
                {work.item_count} cop{work.item_count === 1 ? 'y' : 'ies'}
              </span>
            )}
          </div>
        </div>

        <div className="mt-3 flex items-center gap-3 flex-wrap text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
          {work.genre_form && (
            <span className="inline-flex items-center gap-1">
              <Tag className="w-3 h-3" aria-hidden="true" />
              {formatGenre(work.genre_form)}
            </span>
          )}
          {work.language && (
            <span className="inline-flex items-center gap-1">
              <Globe className="w-3 h-3" aria-hidden="true" />
              {work.language.toUpperCase()}
            </span>
          )}
          {work.origin_date && (
            <span className="inline-flex items-center gap-1">
              <Clock className="w-3 h-3" aria-hidden="true" />
              {work.origin_date}
            </span>
          )}
          {work.dewey_classification && (
            <span className="inline-flex items-center gap-1 font-mono">
              <Hash className="w-3 h-3" aria-hidden="true" />
              {work.dewey_classification}
            </span>
          )}
        </div>

        {work.summary && (
          <p className="mt-3 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 line-clamp-2 leading-relaxed" title={work.summary}>
            {work.summary}
          </p>
        )}
      </button>
    </article>
  )
}
