/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Just Became Available Section
 * Indie ebooks whose hold queue cleared recently. Horizontally scrollable rail.
 */

import { Link } from 'react-router-dom'
import { BookOpen, CheckCircle } from 'lucide-react'
import { generateSlug, type JustAvailableEbook } from '@/api/indie-catalog-api'

interface JustAvailableSectionProps {
  books: JustAvailableEbook[]
}

function JustAvailableCard({ book }: { book: JustAvailableEbook }): React.ReactElement {
  return (
    <li className="flex-shrink-0 w-[60vw] sm:w-[160px]">
      <Link
        to={`/indie/book/${generateSlug(book.title, book.ebook_id)}`}
        aria-label={`${book.title} by ${book.author_pen_name} -- just became available`}
        className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm hover:shadow-md transition-shadow overflow-hidden block"
      >
        <div className="h-40 bg-lsc-cream dark:bg-earth-700 flex items-center justify-center overflow-hidden">
          {book.cover_url ? (
            <img
              src={book.cover_url}
              alt={`Cover of ${book.title}`}
              className="w-full h-full object-cover"
              loading="lazy"
              decoding="async"
              onError={(e) => {
                (e.target as HTMLImageElement).style.display = 'none'
              }}
            />
          ) : (
            <BookOpen className="w-8 h-8 text-lsc-dark/30 dark:text-lsc-cream/30" aria-hidden="true" />
          )}
        </div>
        <div className="p-3">
          <h3
            className="font-serif font-semibold text-sm text-lsc-dark dark:text-lsc-cream line-clamp-2"
            title={book.title}
          >
            {book.title}
          </h3>
          <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-0.5 line-clamp-1">
            by {book.author_pen_name}
          </p>
        </div>
      </Link>
    </li>
  )
}

export default function JustAvailableSection({
  books,
}: JustAvailableSectionProps): React.ReactElement | null {
  if (!books || books.length === 0) return null

  return (
    <section aria-label="Just became available">
      <div className="flex items-center gap-2 mb-4">
        <CheckCircle className="w-5 h-5 text-status-success-600 dark:text-status-success-400" aria-hidden="true" />
        <h2 className="text-xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
          Just became available
        </h2>
        <span className="text-xs px-2 py-0.5 bg-status-success-100 text-status-success-700 dark:bg-status-success-900 dark:text-status-success-200 rounded-full">
          Borrow now
        </span>
      </div>
      <ul className="flex gap-4 overflow-x-auto pb-2 scrollbar-thin" role="list">
        {books.map((book) => (
          <JustAvailableCard key={book.ebook_id} book={book} />
        ))}
      </ul>
    </section>
  )
}
