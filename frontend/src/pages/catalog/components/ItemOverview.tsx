/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/* eslint-disable react-refresh/only-export-components */
import { Link } from 'react-router-dom'
import {
  Calendar,
  MapPin,
  Clock,
  BookText,
  Eye,
  AlertTriangle,
} from 'lucide-react'
import { clsx } from '@/utils/helpers'
import type { CatalogItem } from '@/api/api'

// Re-export utilities from canonical location for backward compatibility
export {
  FORMAT_ICONS,
  SENSORY_WARNINGS,
  getItemIcon,
  formatItemType,
  getStatusConfig,
  getReadingTimeEstimate,
  getComplexityRating,
} from '../utils/catalogItemUtils'
import { CatalogCover } from './CatalogItemThumbnail'

import { buildCoverAlt } from '@/pages/catalog/utils/catalogHelpers'
import { LexileBadge } from '@/components/LexileBadge'
import {
  FORMAT_ICONS,
  SENSORY_WARNINGS,
  formatItemType,
  getStatusConfig,
  getReadingTimeEstimate,
  getComplexityRating,
} from '../utils/catalogItemUtils'

interface ItemOverviewProps {
  item: CatalogItem
  simplifiedView: boolean
  showImages: boolean | undefined
  statusDescriptionId: string
}

export function ItemOverview({
  item,
  simplifiedView,
  showImages,
  statusDescriptionId,
}: ItemOverviewProps): React.ReactElement {
  const statusConfig = getStatusConfig(item.status)
  const subjects = item.subjects?.split(',').map((s) => s.trim()).filter(Boolean) || []
  const readingTime = getReadingTimeEstimate(item.page_count, item.item_type)
  const complexity = getComplexityRating(item.page_count, item.item_type)
  const sensoryWarnings = SENSORY_WARNINGS[item.item_type]

  return (
    <div className="flex flex-col md:flex-row gap-8">
      {/* Cover image placeholder */}
      {showImages !== false && (
        <div className="flex-shrink-0">
          <div className="w-48 h-64 bg-lsc-cream dark:bg-lsc-brown rounded-xl flex items-center justify-center shadow-md">
            <CatalogCover
              coverUrl={item.cover_url}
              itemId={item.id}
              alt={buildCoverAlt(item.title, item.author, item.item_type)}
              title={item.title}
              itemType={item.item_type}
              size="lg"
              className="w-full rounded-xl"
              imgClassName="w-full h-full object-cover"
              loading="eager"
            />
          </div>
        </div>
      )}

      {/* Item details */}
      <div className="flex-1 min-w-0">
        {/* Title and badges */}
        <div className="mb-4">
          <div className="flex flex-wrap items-center gap-2 mb-2">
            <span className="text-sm px-3 py-1 bg-lsc-cream dark:bg-lsc-dark text-lsc-rose dark:text-earth-300 rounded-full font-medium flex items-center gap-1">
              {FORMAT_ICONS[item.item_type] ? (
                <span className="scale-[0.3] -my-2 -mx-1">
                  {FORMAT_ICONS[item.item_type]?.icon}
                </span>
              ) : null}
              {formatItemType(item.item_type)}
            </span>
            <span
              className={clsx('text-sm px-3 py-1 rounded-full font-medium', statusConfig.className)}
              aria-describedby={simplifiedView ? 'status-description-sr' : statusDescriptionId}
            >
              {statusConfig.label}
            </span>
            {simplifiedView && (
              <span id="status-description-sr" className="sr-only">
                {statusConfig.description}
              </span>
            )}
          </div>
          <h1 className="text-3xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
            {item.title}
          </h1>
          {item.author && (
            <p className="text-lg text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
              by {item.author}
            </p>
          )}
          {item.series_name && (
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-2">
              <Link
                to={`/catalog?q=${encodeURIComponent(item.series_name)}`}
                className="text-lsc-rose dark:text-lsc-rose-light hover:underline font-medium"
              >
                {item.series_name}
              </Link>
              {item.series_number && <span className="ml-2">• {item.series_number}</span>}
            </p>
          )}
        </div>

        {/* Quick info */}
        <div className="flex flex-wrap gap-4 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
          {item.publication_year && (
            <div className="flex items-center gap-1">
              <Calendar aria-hidden="true" className="w-4 h-4" />
              <span>{item.publication_year}</span>
            </div>
          )}
          {item.location && (
            <div className="flex items-center gap-1">
              <MapPin aria-hidden="true" className="w-4 h-4" />
              <span>{item.location}</span>
            </div>
          )}
        </div>

        {/* Reading time and complexity */}
        {!simplifiedView && (readingTime || complexity) && (
          <div className="flex flex-wrap gap-3 mb-4">
            {readingTime && (
              <span className="text-sm px-3 py-1.5 bg-earth-50 text-lsc-rose dark:text-lsc-rose-light dark:bg-earth-800/30 dark:text-lsc-rose-light rounded-lg flex items-center gap-2">
                <Clock className="w-4 h-4" aria-hidden="true" />
                {readingTime}
              </span>
            )}
            {complexity && (
              <span
                className={clsx(
                  'text-sm px-3 py-1.5 rounded-lg flex items-center gap-2',
                  complexity.level === 'easy' && 'bg-status-success-50 text-status-success-600 dark:bg-status-success-900/30 dark:text-status-success-300',
                  complexity.level === 'medium' && 'bg-status-warning-50 text-status-warning-700 dark:bg-status-warning-900/30 dark:text-status-warning-300',
                  complexity.level === 'complex' && 'bg-category-50 text-category-600 dark:bg-category-900/30 dark:text-category-300'
                )}
                title={complexity.description}
              >
                <BookText className="w-4 h-4" aria-hidden="true" />
                {complexity.label}
              </span>
            )}
          </div>
        )}

        {/* Sensory warnings */}
        {sensoryWarnings && !simplifiedView && (
          <div className="mb-4 p-3 bg-status-warning-50 dark:bg-status-warning-900/20 border border-status-warning-200 dark:border-status-warning-800 rounded-lg">
            <div className="flex items-start gap-2">
              <AlertTriangle className="w-5 h-5 text-status-warning-600 dark:text-status-warning-400 flex-shrink-0 mt-0.5" aria-hidden="true" />
              <div>
                <p className="font-medium text-status-warning-800 dark:text-status-warning-200 text-sm mb-1">Sensory Information</p>
                <ul className="text-sm text-status-warning-700 dark:text-status-warning-300 space-y-1">
                  {sensoryWarnings.map((warning, idx) => (
                    <li key={idx}>• {warning}</li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        )}

        {/* Status description */}
        {!simplifiedView && (
          <p
            id={statusDescriptionId}
            className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-4 p-3 bg-lsc-cream/50 dark:bg-lsc-dark/50 rounded-lg"
          >
            {statusConfig.description}
          </p>
        )}

        {/* Description */}
        {item.description && (
          <div className="mb-6">
            <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-2 flex items-center gap-2">
              <Eye className="w-5 h-5 text-lsc-rose" aria-hidden="true" />
              Description
            </h2>
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70 leading-relaxed">
              {item.description}
            </p>
          </div>
        )}

        {item.lexile_measure && (
          <div className="mb-4">
            <LexileBadge measure={item.lexile_measure} />
          </div>
        )}

        {/* Subjects/Genres */}
        {subjects.length > 0 && (
          <div className="mb-6">
            <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-2">
              Subjects
            </h2>
            <div className="flex flex-wrap gap-2">
              {subjects.map((subject, index) => (
                <Link
                  key={index}
                  to={`/catalog?q=${encodeURIComponent(subject)}`}
                  className="text-sm px-3 py-1 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream/80 rounded-full hover:bg-lsc-cream dark:hover:bg-lsc-dark transition-colors"
                >
                  {subject}
                </Link>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
