/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Calendar, MapPin, AlertTriangle, ChevronLeft, ChevronRight } from 'lucide-react'
import { clsx } from '@/utils/helpers'
import type { CatalogItem } from '@/api/api'
import { buildCoverAlt } from '@/pages/catalog/utils/catalogHelpers'
import {
  FORMAT_ICONS,
  SENSORY_WARNINGS,
  formatItemType,
  getStatusConfig,
  getContentTones,
} from '../utils/catalogItemUtils'
import CatalogItemThumbnail, { CatalogCover } from './CatalogItemThumbnail'
import { t } from '@/i18n'

interface ItemHeaderProps {
  item: CatalogItem
  simplifiedView: boolean
  showImages: boolean | undefined
}

export function ItemHeader({ item, simplifiedView, showImages }: ItemHeaderProps): React.ReactElement {
  const [descExpanded, setDescExpanded] = useState(false)
  const [currentImageIndex, setCurrentImageIndex] = useState(0)
  const statusConfig = getStatusConfig(item.status)
  const shortTimeLabel = item.page_count
    ? `~${Math.round(item.page_count * 250 / 200 / 60)} hrs \u00b7 ${item.page_count} pages`
    : item.runtime_minutes
      ? `${Math.floor(item.runtime_minutes / 60)}h ${item.runtime_minutes % 60}m`
      : null
  const tones = getContentTones(item.subjects)
  const subjects = [...new Set((item.subjects ?? '').split(',').flatMap((s: string) => s.split(' -- ')).map((s: string) => s.trim()).filter(Boolean))]
  const sensoryWarnings = SENSORY_WARNINGS[item.item_type]

  const SHORT_DESC_LEN = 200
  const hasLongDesc = (item.description?.length ?? 0) > SHORT_DESC_LEN
  const shortDesc = hasLongDesc
    ? (() => {
        const text = item.description!
        const withinLimit = text.slice(0, SHORT_DESC_LEN)
        const lastSentence = withinLimit.match(/^(.*[.!?])\s/s)
        if (lastSentence && lastSentence[1]!.length > 60) {
          return lastSentence[1]!
        }
        return withinLimit.replace(/\s+\S*$/, '') + '...'
      })()
    : item.description

  // Build list of all available images (uploaded images first, then cover_url as fallback)
  const allImages: { url: string; alt: string }[] = []
  if (item.images && item.images.length > 0) {
    // Show primary image first, then the rest
    const sorted = [...item.images].sort((a, b) => {
      if (a.is_primary && !b.is_primary) return -1
      if (!a.is_primary && b.is_primary) return 1
      return a.display_order - b.display_order
    })
    sorted.forEach((img) => {
      allImages.push({ url: img.image_url, alt: img.caption || buildCoverAlt(item.title, item.author, item.item_type) })
    })
  } else if (item.cover_url) {
    allImages.push({ url: item.cover_url, alt: buildCoverAlt(item.title, item.author, item.item_type) })
  }

  const hasMultipleImages = allImages.length > 1
  const safeIndex = allImages.length > 0 ? currentImageIndex % allImages.length : 0

  return (
    <div className="flex flex-col md:flex-row gap-6 md:gap-8">
      {/* Cover / Image gallery */}
      {showImages !== false && (
        <div className="flex-shrink-0 mx-auto md:mx-0">
          <div className="relative w-[200px] md:w-56 h-[300px] md:h-80 bg-lsc-cream dark:bg-lsc-brown rounded-xl flex items-center justify-center shadow-md overflow-hidden">
            {allImages.length > 0 ? (
              <>
                <CatalogCover
                  coverUrl={allImages[safeIndex]!.url}
                  // Only proxy the single-cover_url case; when the patron is
                  // paging through uploaded gallery images, those live on our
                  // own storage already and the proxy would not know which
                  // index to serve.
                  {...(!item.images?.length && { itemId: item.id })}
                  alt={allImages[safeIndex]!.alt}
                  title={item.title}
                  itemType={item.item_type}
                  subjects={item.subjects}
                  size="lg"
                />
                {hasMultipleImages && (
                  <>
                    <button
                      onClick={() => setCurrentImageIndex((safeIndex - 1 + allImages.length) % allImages.length)}
                      className="absolute left-1 top-1/2 -translate-y-1/2 p-1 bg-black/40 hover:bg-black/60 text-white rounded-full transition-colors"
                      aria-label={t('aria.itemHeader.previousImage')}
                    >
                      <ChevronLeft className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => setCurrentImageIndex((safeIndex + 1) % allImages.length)}
                      className="absolute right-1 top-1/2 -translate-y-1/2 p-1 bg-black/40 hover:bg-black/60 text-white rounded-full transition-colors"
                      aria-label={t('aria.itemHeader.nextImage')}
                    >
                      <ChevronRight className="w-4 h-4" />
                    </button>
                    <div className="absolute bottom-2 left-1/2 -translate-x-1/2 flex gap-1">
                      {allImages.map((_, idx) => (
                        <button
                          key={idx}
                          onClick={() => setCurrentImageIndex(idx)}
                          className={clsx(
                            'w-2 h-2 rounded-full transition-colors',
                            idx === safeIndex ? 'bg-lsc-white' : 'bg-lsc-white/40 hover:bg-lsc-white/70'
                          )}
                          aria-label={`View image ${idx + 1}`}
                        />
                      ))}
                    </div>
                  </>
                )}
              </>
            ) : (
              <CatalogItemThumbnail title={item.title} itemType={item.item_type} subjects={item.subjects} size="lg" className="w-full h-full rounded-xl" />
            )}
          </div>
        </div>
      )}

      {/* Content */}
      <div className="flex-1 min-w-0">
        {/* Title */}
        <h1 className="text-3xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
          {item.title}
        </h1>

        {/* Author */}
        {item.author && (
          <p className="text-lg text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
            by{' '}
            <Link
              to={`/catalog?q=${encodeURIComponent(item.author)}`}
              className="text-lsc-rose dark:text-lsc-rose-light hover:underline"
            >
              {item.author}
            </Link>
          </p>
        )}

        {/* Series context -- renders nothing when the item has no series */}
        {item.series_name && (
          <p className="text-sm text-lsc-dark/80 dark:text-lsc-cream/80 mt-2">
            <Link
              to={`/catalog?series_facets=${encodeURIComponent(item.series_name)}`}
              className="inline-flex items-center gap-1 px-2.5 py-0.5 bg-lsc-cream dark:bg-lsc-dark rounded-full text-lsc-rose dark:text-lsc-rose-light hover:underline font-medium"
              aria-label={t('aria.itemHeader.viewSeries', { seriesName: item.series_name })}
            >
              {item.series_number
                ? t('catalogItem.series.partOfNumbered', {
                    seriesName: item.series_name,
                    seriesNumber: /^\d+$/.test(item.series_number) ? `#${item.series_number}` : item.series_number,
                  })
                : t('catalogItem.series.partOf', { seriesName: item.series_name })}
            </Link>
          </p>
        )}

        {/* Badges row */}
        <div className="flex flex-wrap items-center gap-2 mt-3">
          <span className="text-sm px-3 py-1.5 bg-lsc-rose/10 dark:bg-lsc-rose/20 text-lsc-rose dark:text-lsc-rose-light rounded-full font-semibold flex items-center gap-1.5 border border-lsc-rose/30 dark:border-lsc-rose/40">
            {FORMAT_ICONS[item.item_type] ? (
              <span className="scale-[0.35] -my-2 -mx-0.5">
                {FORMAT_ICONS[item.item_type]?.icon}
              </span>
            ) : null}
            {formatItemType(item.item_type)}
          </span>
          <span className={clsx('text-sm px-3 py-1 rounded-full font-medium', statusConfig.className)}>
            {statusConfig.label}
          </span>
          {item.is_large_print && (
            <span className="text-sm px-3 py-1 bg-earth-50 text-lsc-rose dark:bg-earth-800 dark:text-lsc-rose-light/80 rounded-full font-medium">
              Large Print
            </span>
          )}
          {shortTimeLabel && (
            <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-earth-100 dark:bg-earth-800 text-xs font-medium text-earth-600 dark:text-earth-400">
              {shortTimeLabel}
            </span>
          )}
        </div>

        {/* Quick info */}
        <div className="flex flex-wrap gap-4 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-3">
          {item.publication_year && (
            <span className="flex items-center gap-1">
              <Calendar aria-hidden="true" className="w-4 h-4" />
              {item.publication_year}
            </span>
          )}
          {item.location && (
            <span className="flex items-center gap-1">
              <MapPin aria-hidden="true" className="w-4 h-4" />
              {item.location}
            </span>
          )}
        </div>

        {/* Description with read more */}
        {item.description && (
          <div className="mt-4">
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70 leading-relaxed">
              {descExpanded ? item.description : shortDesc}
            </p>
            {hasLongDesc && (
              <button
                onClick={() => setDescExpanded(!descExpanded)}
                className="text-sm text-lsc-rose dark:text-lsc-rose-light hover:underline mt-1 font-medium"
              >
                {descExpanded ? 'Show less' : 'Read more'}
              </button>
            )}
          </div>
        )}

        {/* Content tone pills */}
        {tones.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mt-3">
            {tones.map(tone => (
              <span
                key={tone.label}
                className="inline-flex items-center gap-1 px-2 py-1 rounded-lg bg-earth-50 dark:bg-earth-800/50 text-xs text-earth-600 dark:text-earth-400"
              >
                <span aria-hidden="true">{tone.emoji}</span>
                {tone.label}
              </span>
            ))}
          </div>
        )}

        {/* Sensory warnings */}
        {sensoryWarnings && !simplifiedView && (
          <div className="mt-4 p-3 bg-status-warning-50 dark:bg-status-warning-900/20 border border-status-warning-200 dark:border-status-warning-800 rounded-lg">
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

        {/* Progressive disclosure details */}
        <details className="mt-4 group">
          <summary className="inline-flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 cursor-pointer hover:text-lsc-dark dark:hover:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-earth-700/50 rounded-lg select-none list-none transition-colors">
            <ChevronRight className="w-4 h-4 transition-transform group-open:rotate-90" aria-hidden="true" />
            More details
          </summary>
          <dl className="mt-3 grid grid-cols-2 gap-x-6 gap-y-2 text-sm">
            {item.isbn && (
              <div>
                <dt className="text-lsc-dark/80 dark:text-lsc-cream/80">ISBN</dt>
                <dd className="text-lsc-dark dark:text-lsc-cream font-mono text-xs">{item.isbn}</dd>
              </div>
            )}
            {item.publisher && (
              <div>
                <dt className="text-lsc-dark/80 dark:text-lsc-cream/80">Publisher</dt>
                <dd className="text-lsc-dark dark:text-lsc-cream">{item.publisher}</dd>
              </div>
            )}
            {item.page_count && (
              <div>
                <dt className="text-lsc-dark/80 dark:text-lsc-cream/80">Pages</dt>
                <dd className="text-lsc-dark dark:text-lsc-cream">{item.page_count}</dd>
              </div>
            )}
            {item.call_number && (
              <div>
                <dt className="text-lsc-dark/80 dark:text-lsc-cream/80">Call Number</dt>
                <dd className="text-lsc-dark dark:text-lsc-cream font-mono text-xs">{item.call_number}</dd>
              </div>
            )}
            {item.location && (
              <div>
                <dt className="text-lsc-dark/80 dark:text-lsc-cream/80">Location</dt>
                <dd className="text-lsc-dark dark:text-lsc-cream">{item.location}</dd>
              </div>
            )}
            {item.barcode && (
              <div>
                <dt className="text-lsc-dark/80 dark:text-lsc-cream/80">Barcode</dt>
                <dd className="text-lsc-dark dark:text-lsc-cream font-mono text-xs">{item.barcode}</dd>
              </div>
            )}
          </dl>
        </details>

        {/* Subject tags */}
        {subjects.length > 0 && (
          <div className="flex flex-wrap gap-2 mt-4">
            {subjects.map((subject, index) => (
              <Link
                key={index}
                to={`/catalog?subject=${encodeURIComponent(subject)}`}
                className="text-xs px-2.5 py-1.5 bg-lsc-cream/60 dark:bg-earth-800 text-lsc-dark/80 dark:text-lsc-cream/80 rounded-full border border-lsc-border dark:border-earth-700 hover:border-lsc-rose hover:text-lsc-rose dark:hover:text-lsc-rose-light hover:bg-lsc-rose/5 dark:hover:bg-lsc-rose/10 transition-colors font-medium"
              >
                {subject}
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
