/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Staff Picks Section
 * Horizontal scrollable row of staff-curated indie book picks.
 * Mirrors HorizontalEventCarousel scroll pattern.
 */

import { useRef, useState, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { ChevronLeft, ChevronRight, Heart, BookOpen, Star } from 'lucide-react'
import { generateSlug, type BookCard } from '@/api/indie-catalog-api'
import { useAccessibility } from '@/features/accessibility/hooks/useAccessibility'
import { t } from '@/i18n'

interface StaffPicksSectionProps {
  books: BookCard[]
  onBookClick: (slug: string) => void
}

const CARD_WIDTH = 200
const GAP = 16
const SCROLL_AMOUNT = (CARD_WIDTH + GAP) * 2

function formatGenre(genre: string): string {
  return genre
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase())
}

function StarRating({ rating }: { rating: number }): React.ReactElement {
  const rounded = Math.round(rating * 2) / 2
  return (
    <span className="inline-flex items-center gap-0.5" aria-label={`${rating.toFixed(1)} out of 5 stars`}>
      {[1, 2, 3, 4, 5].map((i) => (
        <Star
          key={i}
          className={`h-3 w-3 ${
            i <= rounded
              ? 'text-status-warning-400 fill-yellow-400'
              : 'text-lsc-dark/20 dark:text-lsc-cream/20'
          }`}
          aria-hidden="true"
        />
      ))}
    </span>
  )
}

function StaffPickCard({
  book,
}: {
  book: BookCard
  onBookClick: (slug: string) => void
}): React.ReactElement {
  return (
    <li className="flex-shrink-0 w-[75vw] sm:w-[200px]">
      <Link
        to={`/indie/book/${book.slug || generateSlug(book.title, book.id)}`}
        aria-label={`${book.title} by ${book.author_pen_name}`}
        className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm hover:shadow-md transition-shadow overflow-hidden group block"
      >
        {/* Cover image */}
        <div className="h-52 bg-lsc-cream dark:bg-earth-700 flex items-center justify-center overflow-hidden">
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
        </div>

        {/* Card content */}
        <div className="p-3">
          {/* Title */}
          <h3 className="font-serif font-semibold text-sm text-lsc-dark dark:text-lsc-cream line-clamp-2 leading-snug mb-1" title={book.title}>
            {book.title}
          </h3>

          {/* Author */}
          <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 truncate mb-1.5">
            by {book.author_pen_name}
          </p>

          {/* Star rating */}
          {book.average_rating !== null && book.average_rating > 0 && (
            <div className="mb-1.5">
              <StarRating rating={book.average_rating} />
            </div>
          )}

          {/* Genre badge */}
          {book.genre && (
            <span className="inline-block text-xs px-2 py-0.5 rounded bg-lsc-cream dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70 font-medium">
              {formatGenre(book.genre)}
            </span>
          )}
        </div>
      </Link>
    </li>
  )
}

export default function StaffPicksSection({
  books,
  onBookClick,
}: StaffPicksSectionProps): React.ReactElement | null {
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
    <section role="region" aria-label={t('aria.indie.staffPicks')}>
      {/* Section header */}
      <div className="flex items-center gap-2 mb-4">
        <Heart className="w-5 h-5 text-lsc-rose" aria-hidden="true" />
        <h2 className="text-xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
          Staff Picks
        </h2>
      </div>

      {/* Carousel */}
      <div className="relative">
        {/* Left arrow */}
        {canScrollLeft && (
          <button
            onClick={() => scroll('left')}
            className="absolute left-0 top-1/2 -translate-y-1/2 z-10 w-9 h-9 flex items-center justify-center rounded-full bg-lsc-white dark:bg-earth-700 shadow-md text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-earth-600 transition-colors -ml-3"
            aria-label={t('aria.indie.scrollStaffPicksLeft')}
          >
            <ChevronLeft className="w-5 h-5" aria-hidden="true" />
          </button>
        )}

        {/* Right arrow */}
        {canScrollRight && (
          <button
            onClick={() => scroll('right')}
            className="absolute right-0 top-1/2 -translate-y-1/2 z-10 w-9 h-9 flex items-center justify-center rounded-full bg-lsc-white dark:bg-earth-700 shadow-md text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-earth-600 transition-colors -mr-3"
            aria-label={t('aria.indie.scrollStaffPicksRight')}
          >
            <ChevronRight className="w-5 h-5" aria-hidden="true" />
          </button>
        )}

        {/* Scrollable container */}
        <ul
          ref={scrollRef}
          onScroll={updateScrollButtons}
          className="flex gap-4 overflow-x-auto scrollbar-hide scroll-smooth px-1 py-2 list-none m-0 p-0"
        >
          {books.map((book) => (
            <StaffPickCard
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
