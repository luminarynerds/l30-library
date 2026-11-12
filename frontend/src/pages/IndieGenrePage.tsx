/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Genre/Category Page
 * SEO-friendly page for browsing books by genre
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
  Filter,
  Rss,
  Tag,
} from 'lucide-react'
import { clsx } from '@/utils/helpers'
import {
  getGenrePage,
  getGenreList,
  getRssFeedUrl,
  type BookCard as BookCardType,
  type ContentRating,
} from '@/api/indie-catalog-api'
import { t } from '@/i18n'
import { useBranding } from '@/contexts/BrandingContext'

const CONTENT_RATING_LABELS: Record<ContentRating, { label: string; description: string; color: string }> = {
  g: { label: 'All Ages', description: 'Content rating: All Ages', color: 'bg-status-success-100 text-status-success-700 dark:bg-status-success-900 dark:text-status-success-200' },
  pg: { label: 'PG', description: 'Content rating: Parental Guidance suggested', color: 'bg-status-info-100 text-status-info-700 dark:bg-status-info-900 dark:text-status-info-200' },
  pg13: { label: 'PG-13', description: 'Content rating: Parents strongly cautioned (13+)', color: 'bg-status-warning-100 text-status-warning-700 dark:bg-status-warning-900 dark:text-status-warning-200' },
  t: { label: 'Teen', description: 'Content rating: Teen (13+)', color: 'bg-status-warning-100 text-status-warning-700 dark:bg-status-warning-900 dark:text-status-warning-200' },
  m: { label: '18+', description: 'Content rating: Mature (18+)', color: 'bg-status-danger-100 text-status-danger-700 dark:bg-status-danger-900 dark:text-status-danger-200' },
  r: { label: 'R', description: 'Content rating: Restricted (17+)', color: 'bg-status-warning-100 text-status-warning-700 dark:bg-status-warning-900 dark:text-status-warning-200' },
  nc17: { label: 'NC-17', description: 'Content rating: Adults only (18+)', color: 'bg-status-danger-100 text-status-danger-700 dark:bg-status-danger-900 dark:text-status-danger-200' },
  e: { label: 'Everyone', description: 'Content rating: Everyone', color: 'bg-status-success-100 text-status-success-700 dark:bg-status-success-900 dark:text-status-success-200' },
  e10: { label: '10+', description: 'Content rating: Everyone 10+', color: 'bg-teal-100 text-teal-700 dark:bg-teal-900 dark:text-teal-200' },
  general: { label: 'All Ages', description: 'Content rating: All Ages', color: 'bg-status-success-100 text-status-success-700 dark:bg-status-success-900 dark:text-status-success-200' },
  teen: { label: '13+', description: 'Content rating: Teen (13+)', color: 'bg-status-warning-100 text-status-warning-700 dark:bg-status-warning-900 dark:text-status-warning-200' },
  mature: { label: '18+', description: 'Content rating: Mature (18+)', color: 'bg-status-danger-100 text-status-danger-700 dark:bg-status-danger-900 dark:text-status-danger-200' },
  ao: { label: 'Adults Only', description: 'Content rating: Adults Only', color: 'bg-status-danger-200 text-status-danger-800 dark:bg-status-danger-900 dark:text-status-danger-200' },
  explicit: { label: 'Explicit', description: 'Content rating: Explicit', color: 'bg-status-danger-200 text-status-danger-800 dark:bg-status-danger-900 dark:text-status-danger-200' },
  clean: { label: 'Clean', description: 'Content rating: Clean', color: 'bg-status-success-100 text-status-success-700 dark:bg-status-success-900 dark:text-status-success-200' },
  unrated: { label: 'Unrated', description: 'Content rating: Unrated', color: 'bg-earth-100 text-earth-700 dark:bg-earth-800 dark:text-earth-300' },
  not_rated: { label: 'Not Rated', description: 'Content rating: Not Rated', color: 'bg-earth-100 text-earth-700 dark:bg-earth-800 dark:text-earth-300' },
}

function formatGenreName(name: string): string {
  return name
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase())
}

function BookCard({ book }: { book: BookCardType }): React.ReactElement {
  const ratingInfo = CONTENT_RATING_LABELS[book.content_rating] ?? { label: 'Unrated', description: 'Content rating: Unrated', color: 'bg-earth-100 text-earth-700 dark:bg-earth-800 dark:text-earth-300' }
  const isAvailable = book.available_copies > 0

  return (
    <Link
      to={`/indie/book/${book.slug}`}
      aria-label={`${book.title} by ${book.author_pen_name}`}
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
            <BookOpen aria-hidden="true" className="w-8 h-8 text-lsc-rose/50" />
          )}
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream truncate" title={book.title}>
            {book.title}
          </h3>
          <p className="text-sm text-lsc-rose truncate" title={`by ${book.author_pen_name}`}>by {book.author_pen_name}</p>

          <div className="flex items-center gap-2 mt-2 flex-wrap">
            {book.content_rating && book.content_rating !== 'unrated' && (
            <span
              className={clsx('text-xs px-2 py-1 rounded', ratingInfo.color)}
              title={ratingInfo.description}
              aria-label={ratingInfo.description}
            >
              {ratingInfo.label}
            </span>
            )}
            {isAvailable ? (
              <span className="text-xs px-2 py-1 bg-status-success-100 text-status-success-700 dark:bg-status-success-900 dark:text-status-success-200 rounded flex items-center gap-1">
                <CheckCircle aria-hidden="true" className="w-3 h-3" />
                Available
              </span>
            ) : (
              <span className="text-xs px-2 py-1 bg-status-warning-100 text-status-warning-700 dark:bg-status-warning-900 dark:text-status-warning-200 rounded flex items-center gap-1">
                <Clock aria-hidden="true" className="w-3 h-3" />
                Waitlist
              </span>
            )}
          </div>

          <div className="flex items-center gap-4 mt-2 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
            <span className="flex items-center gap-1">
              <Star aria-hidden="true" className={clsx('w-3 h-3', book.average_rating ? 'text-status-warning-500 fill-yellow-500' : 'text-lsc-dark/30 dark:text-lsc-cream/60')} />
              {book.average_rating
                ? <>{book.average_rating.toFixed(1)} ({book.rating_count})</>
                : <span className="text-lsc-dark/70 dark:text-lsc-cream/50">No ratings yet</span>
              }
            </span>
            <span className="flex items-center gap-1">
              <Users aria-hidden="true" className="w-3 h-3" />
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

export default function IndieGenrePage(): React.ReactElement {
  const branding = useBranding()
  const { genre } = useParams<{ genre: string }>()
  const [searchParams, setSearchParams] = useSearchParams()
  const page = parseInt(searchParams.get('page') || '1', 10)
  const sort = (searchParams.get('sort') || 'popular') as 'popular' | 'new' | 'rating'

  const { data, isLoading, error } = useQuery({
    queryKey: ['indie-genre', genre, page, sort],
    queryFn: () => getGenrePage(genre!, { page, sort }),
    enabled: !!genre,
  })

  const { data: allGenres } = useQuery({
    queryKey: ['indie-genres'],
    queryFn: getGenreList,
  })

  const handleSortChange = (newSort: 'popular' | 'new' | 'rating') => {
    setSearchParams({ sort: newSort, page: '1' })
  }

  const handlePageChange = (newPage: number) => {
    setSearchParams({ sort, page: newPage.toString() })
  }
  // Set page title
  useEffect(() => {
    if (data) {
      document.title = `${formatGenreName(data.genre)} Books | Indie eBooks`
    }
    return () => { document.title = branding.library_name }
  }, [data])

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
          Genre Not Found
        </h1>
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
          This genre may not exist or has no available books.
        </p>
        <Link to="/indie/discover" className="text-lsc-rose underline hover:text-lsc-rose/80">
          Browse all genres
        </Link>
      </div>
    )
  }


  return (
    
    <div className="max-w-5xl mx-auto space-y-8">
        {/* Breadcrumb */}
        <nav aria-label={t('aria.indieGenre.indieSectionNavigation')} className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
          <Link to="/indie" className="text-lsc-rose underline hover:text-lsc-rose/80">Indie Books</Link>
          <span className="mx-2">/</span>
          <Link to="/indie/discover" className="text-lsc-rose underline hover:text-lsc-rose/80">Discover</Link>
          <span className="mx-2">/</span>
          <span className="text-lsc-dark dark:text-lsc-cream">{formatGenreName(data.genre)}</span>
        </nav>

        {/* Header */}
        <div className="bg-gradient-to-r from-lsc-rose/10 to-lsc-cream dark:from-lsc-rose/20 dark:to-earth-800 rounded-xl p-6 md:p-8">
          <div className="flex items-start justify-between gap-4">
            <div>
              <div className="flex items-center gap-3 mb-2">
                <Tag className="w-8 h-8 text-lsc-rose" />
                <h1 className="text-3xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
                  {formatGenreName(data.genre)}
                </h1>
              </div>
              {data.description && (
                <p className="text-lsc-dark/70 dark:text-lsc-cream/70 max-w-xl">
                  {data.description}
                </p>
              )}
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-2">
                {data.total} {data.total === 1 ? 'book' : 'books'} available
              </p>
            </div>
            <a
              href={getRssFeedUrl(data.genre)}
              className="p-2 border border-lsc-border dark:border-earth-700 rounded-lg hover:bg-lsc-cream dark:hover:bg-earth-800"
              title="RSS Feed"
            >
              <Rss className="w-5 h-5 text-status-warning-500" />
            </a>
          </div>

          {/* Related Genres */}
          {data.related_genres.length > 0 && (
            <div className="mt-4 pt-4 border-t border-lsc-border/50 dark:border-earth-700">
              <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mr-2">Related:</span>
              {data.related_genres.map((related, i) => (
                <span key={related}>
                  <Link
                    to={`/indie/genre/${encodeURIComponent(related)}`}
                    className="text-sm text-lsc-rose underline hover:text-lsc-rose/80"
                  >
                    {formatGenreName(related)}
                  </Link>
                  {i < data.related_genres.length - 1 && (
                    <span className="text-lsc-dark/70 dark:text-lsc-cream/70 mx-2">·</span>
                  )}
                </span>
              ))}
            </div>
          )}
        </div>

        {/* Sort Controls */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/70" />
            <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Sort by:</span>
            <div role="group" aria-label={t('aria.indieGenre.sortBy')} className="flex gap-1">
              {[
                { value: 'popular', label: 'Popular' },
                { value: 'new', label: 'Newest' },
                { value: 'rating', label: 'Top Rated' },
              ].map((option) => (
                <button
                  key={option.value}
                  onClick={() => handleSortChange(option.value as 'popular' | 'new' | 'rating')}
                  aria-pressed={sort === option.value}
                  className={clsx(
                    'px-3 py-1.5 text-sm rounded-lg transition-colors',
                    sort === option.value
                      ? 'bg-lsc-rose text-white'
                      : 'bg-lsc-cream dark:bg-earth-800 hover:bg-lsc-rose/20'
                  )}
                >
                  {option.label}
                </button>
              ))}
            </div>
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
              No books found in this genre yet.
            </p>
          </div>
        )}

        {/* Pagination */}
        {data.pages > 1 && (
          <div className="flex items-center justify-center gap-2">
            <button
              onClick={() => handlePageChange(Math.max(1, page - 1))}
              disabled={page === 1}
              className="px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 disabled:opacity-50"
            >
              Previous
            </button>
            <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
              Page {page} of {data.pages}
            </span>
            <button
              onClick={() => handlePageChange(Math.min(data.pages, page + 1))}
              disabled={page === data.pages}
              className="px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 disabled:opacity-50"
            >
              Next
            </button>
          </div>
        )}

        {/* Other Genres Sidebar */}
        {allGenres && allGenres.length > 0 && (
          <section className="bg-lsc-cream/50 dark:bg-earth-800 rounded-xl p-6">
            <h2 className="font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-4">
              Browse Other Genres
            </h2>
            <div className="flex flex-wrap gap-2">
              {allGenres
                .filter((g) => g.name !== data.genre)
                .map((g) => (
                  <Link
                    key={g.name}
                    to={`/indie/genre/${encodeURIComponent(g.name)}`}
                    className="px-3 py-1.5 bg-lsc-white dark:bg-earth-700 rounded-lg text-sm hover:bg-lsc-rose/20 transition-colors"
                  >
                    {formatGenreName(g.name)}
                    <span className="ml-1 text-lsc-dark/70 dark:text-lsc-cream/70">({g.count})</span>
                  </Link>
                ))}
            </div>
          </section>
        )}
      </div>
  
  )
}
