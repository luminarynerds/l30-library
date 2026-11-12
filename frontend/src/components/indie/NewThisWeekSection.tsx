/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * New This Week Section
 * Compact horizontal scrollable strip showcasing recently added indie books.
 * Simpler than Staff Picks — fewer details, more visual.
 */

import { useRef, useState, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { ChevronLeft, ChevronRight, Sparkles, BookOpen, Star } from 'lucide-react'
import { generateSlug, type BookCard } from '@/api/indie-catalog-api'
import { useAccessibility } from '@/features/accessibility/hooks/useAccessibility'
import { t } from '@/i18n'

interface NewThisWeekSectionProps {
  books: BookCard[]
  onBookClick: (slug: string) => void
}

const CARD_WIDTH = 180
const GAP = 16
const SCROLL_AMOUNT = (CARD_WIDTH + GAP) * 2

function NewBookCard({
  book,
}: {
  book: BookCard
  onBookClick: (slug: string) => void
}): React.ReactElement {
  return (
    <li className="flex-shrink-0 w-[70vw] sm:w-[180px]">
      <Link
        to={`/indie/book/${book.slug || generateSlug(book.title, book.id)}`}
        aria-label={`${book.title} by ${book.author_pen_name} — new this week`}
        className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm hover:shadow-md transition-shadow overflow-hidden group block"
      >
        {/* Cover image with "New" badge overlay */}
        <div className="h-48 bg-lsc-cream dark:bg-earth-700 flex items-center justify-center overflow-hidden relative">
          {book.cover_url ? (
            <img
              src={book.cover_url}
              alt={`Cover of ${book.title}`}
              className="w-full h-full object-cover"
              loading="lazy"
              onError={(e) => {
                (e.target as HTMLImageElement).style.display = 'none'
              }}
            />
          ) : (
            <BookOpen className="w-10 h-10 text-lsc-rose/40" aria-hidden="true" />
          )}

          {/* "New" badge */}
          <span className="absolute top-2 left-2 inline-flex items-center gap-1 rounded-full bg-lsc-rose px-2.5 py-0.5 text-xs font-bold text-white shadow-sm">
            <Sparkles className="h-3 w-3" aria-hidden="true" />
            New
          </span>
        </div>

        {/* Card content — compact */}
        <div className="p-2.5">
          {/* Title */}
          <h3 className="font-serif font-semibold text-sm text-lsc-dark dark:text-lsc-cream line-clamp-2 leading-snug mb-0.5" title={book.title}>
            {book.title}
          </h3>

          {/* Author */}
          <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 truncate">
            {book.author_pen_name}
          </p>

          {/* Rating — only shown if book has at least 1 rating */}
          {book.rating_count > 0 && book.average_rating && (
            <p className="flex items-center gap-0.5 mt-1 text-[11px] text-lsc-dark/50 dark:text-lsc-cream/60">
              <Star className="w-3 h-3 text-status-warning-500 dark:text-status-warning-400 fill-yellow-500 dark:fill-yellow-400" aria-hidden="true" />
              <span>{book.average_rating.toFixed(1)}</span>
            </p>
          )}
        </div>
      </Link>
    </li>
  )
}

export default function NewThisWeekSection({
  books,
  onBookClick,
}: NewThisWeekSectionProps): React.ReactElement | null {
  const scrollRef = useRef<HTMLUListElement>(null)
  const [canScrollLeft, setCanScrollLeft] = useState(false)
  const [canScrollRight, setCanScrollRight] = useState(true)
  const { settings } = useAccessibility()

  const updateScrollButtons = useCallback(() => {
    const el = scrollRef.current
    if (!el) return
    setCanScrollLeft(el.scrollLeft > 0)
    setCanScrollRight(el.scrollLeft + el.clientWidth < el.scrollWidth - 1)
  }, [])

  const scroll = useCallback((direction: 'left' | 'right') => {
    const el = scrollRef.current
    if (!el) return
    const offset = direction === 'left' ? -SCROLL_AMOUNT : SCROLL_AMOUNT
    el.scrollBy({
      left: offset,
      behavior: settings.reduceMotion ? 'auto' : 'smooth',
    })
  }, [settings.reduceMotion])

  if (books.length === 0) return null

  return (
    <section role="region" aria-label={t('aria.indie.newThisWeek')}>
      {/* Section header */}
      <div className="flex items-center gap-2 mb-4">
        <Sparkles className="w-5 h-5 text-lsc-rose" aria-hidden="true" />
        <h2 className="text-xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
          New This Week
        </h2>
      </div>

      {/* Carousel */}
      <div className="relative">
        {/* Left arrow */}
        {canScrollLeft && (
          <button
            onClick={() => scroll('left')}
            className="absolute left-0 top-1/2 -translate-y-1/2 z-10 w-9 h-9 flex items-center justify-center rounded-full bg-lsc-white dark:bg-earth-700 shadow-md text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-earth-600 transition-colors -ml-3"
            aria-label={t('aria.indie.scrollNewBooksLeft')}
          >
            <ChevronLeft className="w-5 h-5" aria-hidden="true" />
          </button>
        )}

        {/* Right arrow */}
        {canScrollRight && (
          <button
            onClick={() => scroll('right')}
            className="absolute right-0 top-1/2 -translate-y-1/2 z-10 w-9 h-9 flex items-center justify-center rounded-full bg-lsc-white dark:bg-earth-700 shadow-md text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-earth-600 transition-colors -mr-3"
            aria-label={t('aria.indie.scrollNewBooksRight')}
          >
            <ChevronRight className="w-5 h-5" aria-hidden="true" />
          </button>
        )}

        {/* Scrollable container */}
        <ul
          ref={scrollRef}
          role="list"
          onScroll={updateScrollButtons}
          className="flex gap-4 overflow-x-auto scrollbar-hide scroll-smooth px-1 py-2 list-none m-0 p-0"
        >
          {books.map((book) => (
            <NewBookCard
              key={book.id}
              book={book}
              onBookClick={onBookClick}
            />
          ))}
        </ul>
      </div>
    </section>
  )
}
