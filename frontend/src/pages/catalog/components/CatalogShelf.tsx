/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useRef } from 'react'
import { Link } from 'react-router-dom'
import { ChevronLeft, ChevronRight, CircleCheck, Clock } from 'lucide-react'
import { useTranslation } from '@/i18n/I18nContext'
import CatalogItemThumbnail, { CatalogCover } from './CatalogItemThumbnail'
import { catalogItemLink } from '../utils/catalogHelpers'

interface ShelfItem {
  id: number
  title: string
  author: string | null
  item_type: string
  status: string
  cover_url: string | null
  page_count: number | null
  source?: string
}

interface CatalogShelfProps {
  title: string
  items: ShelfItem[]
  quietMode?: boolean
}

function ShelfCard({ item }: { item: ShelfItem }) {
  const { t } = useTranslation()
  const coverSrc = item.cover_url
  const shortTime = item.page_count
    ? `~${Math.round(item.page_count * 250 / 200 / 60)} hrs \u00b7 ${item.page_count}p`
    : null

  return (
    <Link
      to={catalogItemLink(item.id, item.title, item.source)}
      state={{ fromCatalog: true }}
      className="flex-shrink-0 w-[65vw] sm:w-[160px] group focus:outline-none focus:ring-2 focus:ring-lsc-rose rounded-xl"
    >
      <div className="w-full h-[220px] rounded-xl overflow-hidden bg-lsc-border dark:bg-earth-700 shadow-sm mb-2 relative">
        {coverSrc ? (
          <CatalogCover coverUrl={coverSrc} itemId={item.id} alt="" title={item.title} itemType={item.item_type} />
        ) : (
          <CatalogItemThumbnail title={item.title} itemType={item.item_type} />
        )}
        <span className="absolute bottom-1.5 right-1.5 w-6 h-6 rounded-full bg-black/50 backdrop-blur-sm flex items-center justify-center">
          {item.status === 'available' ? (
            <CircleCheck className="w-4 h-4 text-status-success-400" aria-label={t('catalog.shelf.available')} />
          ) : (
            <Clock className="w-4 h-4 text-status-warning-400" aria-label={t('catalog.shelf.checkedOut')} />
          )}
        </span>
        {item.source === 'indie' && (
          <span className="absolute top-1.5 left-1.5 text-[10px] font-semibold uppercase px-1.5 py-0.5 rounded-full bg-category-100 text-category-700 dark:bg-category-900/30 dark:text-category-300 backdrop-blur-sm">
            Indie
          </span>
        )}
      </div>
      <h3 className="text-sm font-bold text-lsc-dark dark:text-lsc-cream leading-snug line-clamp-2 group-hover:text-lsc-rose transition-colors" title={item.title}>
        {item.title}
      </h3>
      {item.author && (
        <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60 truncate" title={item.author}>{item.author}</p>
      )}
      {shortTime && (
        <p className="text-xs text-earth-600 dark:text-earth-400 mt-0.5">{shortTime}</p>
      )}
    </Link>
  )
}

export default function CatalogShelf({ title, items, quietMode }: CatalogShelfProps) {
  const { t } = useTranslation()
  const scrollRef = useRef<HTMLDivElement>(null)

  if (items.length === 0) return null

  const scroll = (dir: 'left' | 'right') => {
    if (!scrollRef.current) return
    scrollRef.current.scrollBy({ left: dir === 'left' ? -320 : 320, behavior: 'smooth' })
  }

  if (quietMode) {
    return (
      <div className="mb-8">
        <h2 className="font-serif text-base font-bold text-lsc-dark dark:text-lsc-cream mb-3">{title}</h2>
        <div className="space-y-1">
          {items.map(item => (
            <Link
              key={item.id}
              to={catalogItemLink(item.id, item.title, item.source)}
              state={{ fromCatalog: true }}
              className="flex items-center gap-3 py-2 px-3 rounded-lg hover:bg-lsc-cream dark:hover:bg-earth-800 text-sm focus:outline-none focus:ring-2 focus:ring-lsc-rose"
            >
              {item.status === 'available' ? (
                <CircleCheck className="w-4 h-4 text-status-success-600 dark:text-status-success-400 flex-shrink-0" aria-label={t('catalog.shelf.available')} />
              ) : (
                <Clock className="w-4 h-4 text-status-warning-500 dark:text-status-warning-400 flex-shrink-0" aria-label={t('catalog.shelf.checkedOut')} />
              )}
              {item.source === 'indie' && (
                <span className="text-[10px] font-semibold uppercase px-1.5 py-0.5 rounded-full bg-category-100 text-category-700 dark:bg-category-900/30 dark:text-category-300">
                  Indie
                </span>
              )}
              <span className="font-semibold text-lsc-dark dark:text-lsc-cream truncate" title={item.title}>{item.title}</span>
              {item.author && <span className="text-lsc-dark/70 dark:text-lsc-cream/50 truncate hidden sm:inline" title={`— ${item.author}`}>— {item.author}</span>}
            </Link>
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="mb-8">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-lg font-serif font-bold text-lsc-dark dark:text-lsc-cream">{title}</h2>
        <div className="flex gap-1">
          <button onClick={() => scroll('left')} className="min-w-[44px] min-h-[44px] w-11 h-11 rounded-lg flex items-center justify-center text-lsc-dark/70 dark:text-lsc-cream/50 hover:bg-lsc-cream dark:hover:bg-earth-800" aria-label={t('catalog.shelf.scrollLeft', { title })}>
            <ChevronLeft className="w-5 h-5" />
          </button>
          <button onClick={() => scroll('right')} className="min-w-[44px] min-h-[44px] w-11 h-11 rounded-lg flex items-center justify-center text-lsc-dark/70 dark:text-lsc-cream/50 hover:bg-lsc-cream dark:hover:bg-earth-800" aria-label={t('catalog.shelf.scrollRight', { title })}>
            <ChevronRight className="w-5 h-5" />
          </button>
        </div>
      </div>
      <div
        ref={scrollRef}
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === 'ArrowRight') { e.preventDefault(); scroll('right') }
          if (e.key === 'ArrowLeft') { e.preventDefault(); scroll('left') }
        }}
        role="region"
        aria-label={title}
        className="flex overflow-x-auto scrollbar-hide pb-2 snap-x snap-mandatory focus:outline-none focus:ring-2 focus:ring-lsc-rose focus:ring-offset-2 dark:focus:ring-offset-lsc-dark"
      >
        <div role="list" className="flex gap-4">
          {items.map(item => (
            <div key={item.id} role="listitem" className="snap-start">
              <ShelfCard item={item} />
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
