/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Featured Book Hero Banner
 * Staff-controlled hero banner for a featured indie ebook on the catalog page.
 * Mirrors FeaturedEventHero design pattern.
 */

import { Link } from 'react-router-dom'
import { BookOpen, Star, Users, BookMarked } from 'lucide-react'
import type { BookCard } from '@/api/indie-catalog-api'
import { generateSlug, penNameToSlug } from '@/api/indie-catalog-api'
import { useNeurodivergentUX } from '@/hooks/useNeurodivergentUX'
import { getRatingInfo } from '@/utils/content-ratings'
import ShareButton from '@/components/ShareButton'

interface FeaturedBookHeroProps {
  book: BookCard
  onBookClick: (slug: string) => void
}

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
          className={`h-4 w-4 ${
            i <= rounded
              ? 'text-status-warning-400 fill-yellow-400'
              : 'text-lsc-dark/30 dark:text-lsc-cream/60'
          }`}
          aria-hidden="true"
        />
      ))}
      <span className="ml-1 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{rating.toFixed(1)}</span>
    </span>
  )
}

export default function FeaturedBookHero({
  book,
  onBookClick: _onBookClick,
}: FeaturedBookHeroProps): React.ReactElement {
  const { shouldHideFOMO } = useNeurodivergentUX()
  const ratingInfo = getRatingInfo(book.content_rating)
  const isAvailable = book.available_copies > 0
  const hasAuthor = !!book.author_pen_name && book.author_pen_name.trim().length > 0

  return (
    <section
      aria-label={hasAuthor ? `Featured book: ${book.title} by ${book.author_pen_name}` : `Featured book: ${book.title}`}
      className="relative mb-8 overflow-hidden rounded-xl bg-lsc-cream dark:bg-earth-800 border border-lsc-border dark:border-earth-700"
    >
      {/* Content */}
      <div className="relative z-10 flex flex-col gap-6 p-6 md:flex-row md:items-center md:gap-8 md:p-8 lg:p-10">
        {/* Book Cover */}
        <div className="flex-shrink-0 self-center md:self-start">
          <div className="w-48 h-64 rounded-lg shadow-lg overflow-hidden bg-earth-200 dark:bg-earth-700 flex items-center justify-center">
            {book.cover_url ? (
              <img
                src={book.cover_url}
                alt={`Cover of ${book.title}`}
                className="w-full h-full object-cover" decoding="async"
                onError={(e) => {
                  (e.target as HTMLImageElement).style.display = 'none'
                }}
              />
            ) : (
              <div
                aria-hidden="true"
                className="w-full h-full flex flex-col items-center justify-center gap-3 bg-gradient-to-b from-lsc-dark to-lsc-brown p-4 text-center"
              >
                <BookOpen className="w-6 h-6 text-lsc-cream/40" />
                <span className="font-serif text-lg leading-snug text-lsc-cream line-clamp-4">{book.title}</span>
                <span className="block h-px w-12 bg-lsc-gold" />
                {hasAuthor && <span className="text-xs text-lsc-cream/70">{book.author_pen_name}</span>}
              </div>
            )}
          </div>
        </div>

        {/* Details */}
        <div className="flex flex-col gap-3 min-w-0">
          {/* Top row: badges */}
          <div className="flex flex-wrap items-center gap-3">
            {/* Featured badge */}
            <span className="inline-flex items-center gap-1.5 rounded-full bg-lsc-rose px-3 py-1 text-xs font-bold text-white">
              <Star className="h-3.5 w-3.5" aria-hidden="true" />
              Featured
            </span>

            {/* Genre badge */}
            {book.genre && (
              <span className="rounded-full bg-lsc-dark/10 dark:bg-lsc-cream/10 px-3 py-1 text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70">
                {formatGenre(book.genre)}
              </span>
            )}

            {/* Content rating badge */}
            {book.content_rating && book.content_rating !== 'unrated' && (
              <span
                className={`rounded-full px-3 py-1 text-xs font-medium ${ratingInfo.color}`}
                title={ratingInfo.description}
                aria-label={ratingInfo.description}
              >
                {ratingInfo.label}
              </span>
            )}
          </div>

          {/* Title */}
          <h2 className="max-w-2xl text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream md:text-3xl">
            <Link
              to={`/indie/book/${book.slug || generateSlug(book.title, book.id)}`}
              className="hover:text-lsc-rose transition-colors"
            >
              {book.title}
            </Link>
          </h2>

          {/* Author -- hidden when the pen name is missing/blank */}
          {hasAuthor && (
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
              by{' '}
              <Link
                to={`/indie/author/${penNameToSlug(book.author_pen_name)}`}
                className="font-medium text-lsc-rose underline hover:text-lsc-rose/80"
              >
                {book.author_pen_name}
              </Link>
            </p>
          )}

          {/* Rating + Reader count */}
          <div className="flex flex-wrap items-center gap-4">
            {book.average_rating !== null && book.average_rating > 0 && (
              <StarRating rating={book.average_rating} />
            )}
            {!shouldHideFOMO && book.total_borrows > 0 && (
              <span className="flex items-center gap-1.5 text-sm text-lsc-dark/70 dark:text-lsc-cream/60">
                <Users className="h-4 w-4 text-lsc-dark/70 dark:text-lsc-cream/60" aria-hidden="true" />
                {book.total_borrows} reader{book.total_borrows === 1 ? '' : 's'}
              </span>
            )}
          </div>

          {/* Description */}
          {book.description && (
            <p className="max-w-2xl text-sm leading-relaxed text-lsc-dark/70 dark:text-lsc-cream/60 line-clamp-2" title={book.description}>
              {book.description}
            </p>
          )}

          {/* Actions row */}
          <div className="flex flex-wrap items-center gap-3 pt-1">
            {/* Borrow / Unavailable CTA */}
            {isAvailable ? (
              <Link
                to={`/indie/book/${book.slug || generateSlug(book.title, book.id)}`}
                aria-label={`Borrow ${book.title}`}
                className="inline-flex items-center gap-2 rounded-xl bg-lsc-rose px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-lsc-rose/90 focus:outline-none focus:ring-2 focus:ring-lsc-rose focus:ring-offset-2"
              >
                <BookMarked className="h-4 w-4" aria-hidden="true" />
                Borrow
              </Link>
            ) : (
              <span className="inline-flex items-center gap-2 rounded-xl bg-lsc-dark/10 dark:bg-lsc-cream/10 border-2 border-lsc-dark/20 dark:border-lsc-cream/20 px-5 py-2.5 text-sm font-semibold text-lsc-dark/70 dark:text-lsc-cream/60">
                Unavailable
              </span>
            )}

            {/* Share button */}
            <ShareButton
              resourceType="book"
              resourceId={book.id}
              title={book.title}
              author={book.author_pen_name}
              {...(book.description ? { description: book.description } : {})}
              {...(book.cover_url ? { imageUrl: book.cover_url } : {})}
              variant="compact"
            />
          </div>
        </div>
      </div>
    </section>
  )
}
