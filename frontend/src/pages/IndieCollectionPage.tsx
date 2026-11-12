/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Public Collection Page
 * Displays curated book collections
 */
import { useEffect } from 'react'
import { useParams, Link, useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  BookOpen,
  Star,
  Users,
  Clock,
  Loader2,
  AlertCircle,
  CheckCircle,
  BookMarked,
  User,
  ChevronRight,
} from 'lucide-react'
import { clsx } from '@/utils/helpers'
import {
  getCollection,
  getCollectionList,
  type BookCard as BookCardType,
  type ContentRating,
} from '@/api/indie-catalog-api'
import { useBranding } from '@/contexts/BrandingContext'

const CONTENT_RATING_LABELS: Record<ContentRating, { label: string; color: string }> = {
  g: { label: 'All Ages', color: 'bg-status-success-100 text-status-success-700 dark:bg-status-success-900 dark:text-status-success-200' },
  pg: { label: 'PG', color: 'bg-status-info-100 text-status-info-700 dark:bg-status-info-900 dark:text-status-info-200' },
  pg13: { label: 'PG-13', color: 'bg-status-warning-100 text-status-warning-700 dark:bg-status-warning-900 dark:text-status-warning-200' },
  t: { label: 'Teen', color: 'bg-status-warning-100 text-status-warning-700 dark:bg-status-warning-900 dark:text-status-warning-200' },
  m: { label: '18+', color: 'bg-status-danger-100 text-status-danger-700 dark:bg-status-danger-900 dark:text-status-danger-200' },
  r: { label: 'R', color: 'bg-status-warning-100 text-status-warning-700 dark:bg-status-warning-900 dark:text-status-warning-200' },
  nc17: { label: 'NC-17', color: 'bg-status-danger-100 text-status-danger-700 dark:bg-status-danger-900 dark:text-status-danger-200' },
  e: { label: 'Everyone', color: 'bg-status-success-100 text-status-success-700 dark:bg-status-success-900 dark:text-status-success-200' },
  e10: { label: '10+', color: 'bg-teal-100 text-teal-700 dark:bg-teal-900 dark:text-teal-200' },
  general: { label: 'All Ages', color: 'bg-status-success-100 text-status-success-700 dark:bg-status-success-900 dark:text-status-success-200' },
  teen: { label: '13+', color: 'bg-status-warning-100 text-status-warning-700 dark:bg-status-warning-900 dark:text-status-warning-200' },
  mature: { label: '18+', color: 'bg-status-danger-100 text-status-danger-700 dark:bg-status-danger-900 dark:text-status-danger-200' },
  ao: { label: 'Adults Only', color: 'bg-status-danger-200 text-status-danger-800 dark:bg-status-danger-900 dark:text-status-danger-200' },
  explicit: { label: 'Explicit', color: 'bg-status-danger-200 text-status-danger-800 dark:bg-status-danger-900 dark:text-status-danger-200' },
  clean: { label: 'Clean', color: 'bg-status-success-100 text-status-success-700 dark:bg-status-success-900 dark:text-status-success-200' },
  unrated: { label: 'Unrated', color: 'bg-earth-100 text-earth-700 dark:bg-earth-800 dark:text-earth-300' },
  not_rated: { label: 'Not Rated', color: 'bg-earth-100 text-earth-700 dark:bg-earth-800 dark:text-earth-300' },
}

function BookCard({ book }: { book: BookCardType }): React.ReactElement {
  const ratingInfo = CONTENT_RATING_LABELS[book.content_rating] ?? { label: 'Unrated', color: 'bg-earth-100 text-earth-700 dark:bg-earth-800 dark:text-earth-300' }
  const isAvailable = book.available_copies > 0

  return (
    <Link
      to={`/indie/book/${book.slug}`}
      className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm p-4 hover:shadow-md transition-shadow block"
    >
      <div className="flex gap-4">
        <div className="w-20 h-28 bg-lsc-cream dark:bg-lsc-brown rounded-lg flex items-center justify-center flex-shrink-0 overflow-hidden">
          {book.cover_url ? (
            <img
              src={book.cover_url}
              alt={`Cover of ${book.title}`}
              className="w-full h-full object-cover"
            />
          ) : (
            <BookOpen className="w-8 h-8 text-lsc-rose/50" />
          )}
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream truncate" title={book.title}>
            {book.title}
          </h3>
          <p className="text-sm text-lsc-rose truncate" title={`by ${book.author_pen_name}`}>by {book.author_pen_name}</p>

          <div className="flex items-center gap-2 mt-2 flex-wrap">
            {book.genre && (
              <span className="text-xs px-2 py-1 bg-lsc-cream dark:bg-lsc-brown text-lsc-dark/70 dark:text-lsc-cream/70 rounded">
                {book.genre}
              </span>
            )}
            {book.content_rating && book.content_rating !== 'unrated' && (
            <span className={clsx('text-xs px-2 py-1 rounded', ratingInfo.color)}>
              {ratingInfo.label}
            </span>
            )}
            {isAvailable ? (
              <span className="text-xs px-2 py-1 bg-status-success-100 text-status-success-700 dark:bg-status-success-900 dark:text-status-success-200 rounded flex items-center gap-1">
                <CheckCircle className="w-3 h-3" />
                Available
              </span>
            ) : (
              <span className="text-xs px-2 py-1 bg-status-warning-100 text-status-warning-700 dark:bg-status-warning-900 dark:text-status-warning-200 rounded flex items-center gap-1">
                <Clock className="w-3 h-3" />
                Waitlist
              </span>
            )}
          </div>

          <div className="flex items-center gap-4 mt-2 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
            {book.average_rating && (
              <span className="flex items-center gap-1">
                <Star className="w-3 h-3 text-status-warning-500 fill-yellow-500" />
                {book.average_rating.toFixed(1)} ({book.rating_count})
              </span>
            )}
            <span className="flex items-center gap-1">
              <Users className="w-3 h-3" />
              {book.total_borrows} borrows
            </span>
          </div>

          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-2 line-clamp-2" title={book.description}>
            {book.description}
          </p>
        </div>
      </div>
    </Link>
  )
}

export default function IndieCollectionPage(): React.ReactElement {
  const branding = useBranding()
  const { slug } = useParams<{ slug: string }>()
  const [searchParams, setSearchParams] = useSearchParams()
  const page = parseInt(searchParams.get('page') || '1', 10)

  const { data, isLoading, error } = useQuery({
    queryKey: ['indie-collection', slug, page],
    queryFn: () => getCollection(slug!, page),
    enabled: !!slug,
  })

  const { data: collections } = useQuery({
    queryKey: ['indie-collections'],
    queryFn: getCollectionList,
  })

  const handlePageChange = (newPage: number) => {
    setSearchParams({ page: newPage.toString() })
  }

  // Page-title effect runs unconditionally so hook count is stable across
  // renders (rule-of-hooks). The branding.library_name fallback handles
  // the case where `data` is undefined during loading.
  useEffect(() => {
    if (data) {
      document.title = `${data.title} | Curated Collection`
    }
    return () => { document.title = branding.library_name }
  }, [data, branding.library_name])

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" />
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="text-center py-16">
        <AlertCircle className="w-16 h-16 mx-auto mb-4 text-status-danger-500" />
        <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-2">
          Collection Not Found
        </h1>
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
          This collection may have been removed or doesn't exist.
        </p>
        <Link to="/indie/discover" className="text-lsc-rose hover:underline">
          Browse all collections
        </Link>
      </div>
    )
  }

  const totalPages = Math.ceil(data.book_count / 20)

  return (
    
    <div className="max-w-5xl mx-auto space-y-8">
        {/* Breadcrumb */}
        <nav className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
          <Link to="/indie" className="hover:text-lsc-rose hover:underline">Indie Books</Link>
          <span className="mx-2">/</span>
          <Link to="/indie/discover" className="hover:text-lsc-rose hover:underline">Discover</Link>
          <span className="mx-2">/</span>
          <span className="text-lsc-dark dark:text-lsc-cream">Collections</span>
          <span className="mx-2">/</span>
          <span className="text-lsc-dark dark:text-lsc-cream">{data.title}</span>
        </nav>

        {/* Header */}
        <div className="bg-gradient-to-r from-lsc-rose/10 to-lsc-cream dark:from-lsc-rose/20 dark:to-earth-800 rounded-xl p-6 md:p-8">
          <div className="flex items-center gap-3 mb-3">
            <BookMarked className="w-8 h-8 text-lsc-rose" />
            <h1 className="text-3xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
              {data.title}
            </h1>
          </div>
          {data.description && (
            <p className="text-lg text-lsc-dark/70 dark:text-lsc-cream/70 max-w-2xl mb-4">
              {data.description}
            </p>
          )}
          <div className="flex items-center gap-4 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
            <span className="flex items-center gap-1">
              <BookOpen className="w-4 h-4" />
              {data.book_count} {data.book_count === 1 ? 'book' : 'books'}
            </span>
            <span className="flex items-center gap-1">
              <User className="w-4 h-4" />
              Curated by {data.curator_name}
            </span>
          </div>
        </div>

        {/* Books Grid */}
        {data.books.length > 0 ? (
          <div className="grid gap-4">
            {data.books.map((book) => (
              <BookCard key={book.id} book={book} />
            ))}
          </div>
        ) : (
          <div className="text-center py-12 bg-lsc-cream/50 dark:bg-earth-800 rounded-xl">
            <BookOpen className="w-16 h-16 mx-auto mb-4 text-lsc-dark/30 dark:text-lsc-cream/60" />
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
              This collection is empty.
            </p>
          </div>
        )}

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-center gap-2">
            <button
              onClick={() => handlePageChange(Math.max(1, page - 1))}
              disabled={page === 1}
              className="px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 disabled:opacity-50"
            >
              Previous
            </button>
            <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
              Page {page} of {totalPages}
            </span>
            <button
              onClick={() => handlePageChange(Math.min(totalPages, page + 1))}
              disabled={page === totalPages}
              className="px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 disabled:opacity-50"
            >
              Next
            </button>
          </div>
        )}

        {/* Other Collections */}
        {collections && collections.length > 1 && (
          <section className="bg-lsc-cream/50 dark:bg-earth-800 rounded-xl p-6">
            <h2 className="font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-4">
              More Collections
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {collections
                .filter((c) => c.slug !== slug)
                .map((collection) => (
                  <Link
                    key={collection.id}
                    to={`/indie/collection/${collection.slug}`}
                    className="bg-lsc-white dark:bg-earth-700 rounded-xl p-4 hover:shadow-md transition-all flex items-start justify-between"
                  >
                    <div>
                      <h3 className="font-medium text-lsc-dark dark:text-lsc-cream">
                        {collection.title}
                      </h3>
                      <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                        {collection.book_count} books
                      </p>
                    </div>
                    <ChevronRight className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/70" />
                  </Link>
                ))}
            </div>
          </section>
        )}
      </div>
  
  )
}
