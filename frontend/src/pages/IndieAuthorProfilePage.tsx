/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Public Author Page
 * Lists every indie title by a given author. Authorship in the owned catalog
 * is keyed on pen name; the route param is a hyphenated slug of that pen name
 * (e.g. "clara-nightingale") so the URL is clean and crawler/SEO-safe. The
 * canonical display name comes from the resolved books/profile, not the slug.
 * Registered authors (an indie_authors row) additionally get a bio and photo.
 */
import { useEffect, useMemo, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  BookOpen,
  Calendar,
  Loader2,
  AlertCircle,
  CheckCircle,
  Clock,
} from 'lucide-react'
import { clsx } from '@/utils/helpers'
import { formatGenre } from '@/utils/format-utils'
import { getRatingInfo } from '@/utils/content-ratings'
import {
  getPublicAuthorBooks,
  getPublicAuthorDetail,
  browseIndieCatalog,
  penNameToSlug,
  generateSlug,
  type BookCard as BookCardType,
} from '@/api/indie-catalog-api'
import { useBranding } from '@/contexts/BrandingContext'

type SortKey = 'title' | 'newest' | 'available'

function BookCard({ book }: { book: BookCardType }): React.ReactElement {
  const ratingInfo = getRatingInfo(book.content_rating)
  const isAvailable = book.available_copies > 0

  return (
    <Link
      to={`/indie/book/${book.slug}`}
      className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm p-4 hover:shadow-md transition-shadow block h-full"
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
            <BookOpen className="w-8 h-8 text-lsc-rose/50" aria-hidden="true" />
          )}
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream truncate" title={book.title}>
            {book.title}
          </h3>

          <div className="flex items-center gap-2 mt-2 flex-wrap">
            {book.genre && (
              <span className="text-xs px-2 py-1 bg-lsc-cream dark:bg-lsc-brown text-lsc-dark/70 dark:text-lsc-cream/70 rounded">
                {formatGenre(book.genre)}
              </span>
            )}
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
                <CheckCircle className="w-3 h-3" aria-hidden="true" />
                Available
              </span>
            ) : (
              <span className="text-xs px-2 py-1 bg-status-warning-100 text-status-warning-700 dark:bg-status-warning-900 dark:text-status-warning-200 rounded flex items-center gap-1">
                <Clock className="w-3 h-3" aria-hidden="true" />
                Waitlist
              </span>
            )}
          </div>

          {book.description && (
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-3 line-clamp-2" title={book.description}>
              {book.description}
            </p>
          )}
        </div>
      </div>
    </Link>
  )
}

export default function IndieAuthorProfilePage(): React.ReactElement {
  const branding = useBranding()
  const { slug } = useParams<{ slug: string }>()
  const authorSlug = slug ?? ''
  const [sort, setSort] = useState<SortKey>('title')
  const [viewMode, setViewMode] = useState<'flat' | 'grouped'>('flat')

  const { data: books, isLoading, error } = useQuery({
    queryKey: ['indie-author-books', authorSlug],
    queryFn: () => getPublicAuthorBooks(authorSlug),
    enabled: !!authorSlug,
  })

  // Registered authors (indie_authors row) get a bio + photo; others resolve to null.
  const { data: profile } = useQuery({
    queryKey: ['indie-author-profile', authorSlug],
    queryFn: () => getPublicAuthorDetail(authorSlug),
    enabled: !!authorSlug,
  })

  // Canonical pen name from the resolved data; the slug itself is lossy.
  const displayName = profile?.pen_name ?? books?.[0]?.author_pen_name ?? ''

  const { data: catalogPage } = useQuery({
    queryKey: ['indie-catalog-rail'],
    queryFn: () => browseIndieCatalog({ per_page: 20, sort: 'newest' }),
    staleTime: 5 * 60 * 1000,
  })

  // Filter out this author's own books; take up to 10 for the discovery rail.
  const railBooks = useMemo(() => {
    const items = catalogPage?.items ?? []
    return items
      .filter((b) => b.author_pen_name !== displayName)
      .slice(0, 10)
  }, [catalogPage, displayName])

  useEffect(() => {
    if (displayName) {
      document.title = `${displayName} | Indie Author`
    }
    return () => {
      document.title = branding.library_name
    }
  }, [displayName, branding.library_name])

  const sortedBooks = useMemo(() => {
    const arr = [...(books ?? [])]
    if (sort === 'newest') {
      arr.sort(
        (a, b) => (b.publication_year ?? 0) - (a.publication_year ?? 0) || a.title.localeCompare(b.title),
      )
    } else if (sort === 'available') {
      arr.sort(
        (a, b) =>
          (b.available_copies > 0 ? 1 : 0) - (a.available_copies > 0 ? 1 : 0) ||
          a.title.localeCompare(b.title),
      )
    } else {
      arr.sort((a, b) => a.title.localeCompare(b.title))
    }
    return arr
  }, [books, sort])

  // Distinct genres for the toggle guard: only show when 2+ genres present.
  const distinctGenres = useMemo(
    () => Array.from(new Set((books ?? []).map((b) => b.genre).filter((g): g is string => !!g))),
    [books],
  )

  // Groups ordered by descending title count; ungrouped books trail as "Other".
  const genreGroups = useMemo(() => {
    if (viewMode !== 'grouped') return []
    const map = new Map<string, BookCardType[]>()
    const noGenre: BookCardType[] = []
    for (const book of sortedBooks) {
      if (book.genre) {
        const arr = map.get(book.genre) ?? []
        arr.push(book)
        map.set(book.genre, arr)
      } else {
        noGenre.push(book)
      }
    }
    const sorted = [...map.entries()].sort((a, b) => b[1].length - a[1].length)
    if (noGenre.length) sorted.push(['__other__', noGenre])
    return sorted
  }, [sortedBooks, viewMode])

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" aria-label="Loading author" />
      </div>
    )
  }

  if (error || !books || books.length === 0) {
    return (
      <div className="text-center py-16">
        <AlertCircle className="w-16 h-16 mx-auto mb-4 text-status-danger-500" aria-hidden="true" />
        <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-2">
          No books found
        </h1>
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
          We couldn't find any indie titles by this author.
        </p>
        <Link to="/indie" className="text-lsc-rose hover:underline">
          Browse indie books
        </Link>
      </div>
    )
  }

  const bookCount = books.length
  const initial = displayName.trim().charAt(0).toUpperCase() || '?'

  const genres = Array.from(
    new Set(books.map((b) => b.genre).filter((g): g is string => !!g)),
  ).sort((a, b) => a.localeCompare(b))

  const years = books
    .map((b) => b.publication_year)
    .filter((y): y is number => y != null)
  const minYear = years.length ? Math.min(...years) : null
  const maxYear = years.length ? Math.max(...years) : null
  const publishedSpan =
    minYear == null ? null : minYear === maxYear ? `${minYear}` : `${minYear}–${maxYear}`

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      {/* Breadcrumb */}
      <nav aria-label="Breadcrumb" className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
        <Link to="/indie" className="hover:text-lsc-rose hover:underline">Indie Books</Link>
        <span className="mx-2" aria-hidden="true">/</span>
        <Link to="/indie/author/browse" className="hover:text-lsc-rose hover:underline">Authors</Link>
        <span className="mx-2" aria-hidden="true">/</span>
        <span className="text-lsc-dark dark:text-lsc-cream">{displayName}</span>
      </nav>

      {/* Author Header */}
      <div className="bg-gradient-to-r from-lsc-rose/10 to-lsc-cream dark:from-lsc-rose/20 dark:to-earth-800 rounded-xl p-6 md:p-8">
        <div className="flex items-center gap-5">
          {profile?.profile_image_url ? (
            <img
              src={profile.profile_image_url}
              alt={`Photo of ${displayName}`}
              className="w-20 h-20 rounded-full object-cover flex-shrink-0"
            />
          ) : (
            <div
              aria-hidden="true"
              className="w-20 h-20 rounded-full bg-lsc-rose text-lsc-white flex items-center justify-center flex-shrink-0"
            >
              <span className="text-3xl font-serif font-bold">{initial}</span>
            </div>
          )}
          <div className="min-w-0">
            <h1 className="text-3xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
              {displayName}
            </h1>
            <p className="mt-1 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 flex flex-wrap items-center gap-x-4 gap-y-1">
              <span className="flex items-center gap-1.5">
                <BookOpen className="w-4 h-4" aria-hidden="true" />
                {bookCount} {bookCount === 1 ? 'title' : 'titles'} in the indie collection
              </span>
              {publishedSpan && (
                <span className="flex items-center gap-1.5">
                  <Calendar className="w-4 h-4" aria-hidden="true" />
                  Published {publishedSpan}
                </span>
              )}
            </p>
          </div>
        </div>

        {genres.length > 0 && (
          <div className="mt-4 flex flex-wrap items-center gap-2">
            <span className="text-sm text-lsc-dark/60 dark:text-lsc-cream/60">Writes in:</span>
            {genres.map((g) => (
              <span
                key={g}
                className="text-xs px-2.5 py-1 bg-lsc-white/70 dark:bg-earth-800/70 text-lsc-dark/80 dark:text-lsc-cream/80 rounded-full"
              >
                {formatGenre(g)}
              </span>
            ))}
          </div>
        )}

        {profile?.bio && (
          <p className="mt-4 text-sm leading-relaxed text-lsc-dark/80 dark:text-lsc-cream/80 max-w-2xl">
            {profile.bio}
          </p>
        )}
      </div>

      {/* Books */}
      <section aria-labelledby="author-books-heading">
        <div className="flex items-center justify-between gap-4 mb-4 flex-wrap">
          <h2
            id="author-books-heading"
            className="text-lg font-serif font-semibold text-lsc-dark dark:text-lsc-cream"
          >
            Titles
          </h2>
          <div className="flex items-center gap-3 flex-wrap">
            {distinctGenres.length >= 2 && (
              <fieldset className="flex items-center gap-1 text-sm border-0 p-0 m-0">
                <legend className="sr-only">View mode</legend>
                {(['flat', 'grouped'] as const).map((mode) => {
                  const label = mode === 'flat' ? 'All titles' : 'By genre'
                  const id = `view-mode-${mode}`
                  return (
                    <label
                      key={mode}
                      htmlFor={id}
                      className={clsx(
                        'cursor-pointer px-3 py-1 rounded-full text-xs font-medium transition-colors',
                        viewMode === mode
                          ? 'bg-lsc-rose text-lsc-white'
                          : 'bg-lsc-cream dark:bg-earth-800 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-rose/10',
                      )}
                    >
                      <input
                        type="radio"
                        id={id}
                        name="view-mode"
                        value={mode}
                        checked={viewMode === mode}
                        onChange={() => setViewMode(mode)}
                        className="sr-only"
                      />
                      {label}
                    </label>
                  )
                })}
              </fieldset>
            )}
            {books.length > 1 && (
              <div className="flex items-center gap-2 text-sm">
                <label htmlFor="author-sort" className="text-lsc-dark/70 dark:text-lsc-cream/70">
                  Sort
                </label>
                <select
                  id="author-sort"
                  value={sort}
                  onChange={(e) => setSort(e.target.value as SortKey)}
                  className="rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream px-2 py-1"
                >
                  <option value="title">Title (A-Z)</option>
                  <option value="newest">Newest</option>
                  <option value="available">Available first</option>
                </select>
              </div>
            )}
          </div>
        </div>

        {viewMode === 'grouped' && genreGroups.length > 0 ? (
          <div className="space-y-8">
            {genreGroups.map(([genre, groupBooks]) => {
              const headingId = `genre-group-${genre}`
              const label = genre === '__other__' ? 'Other' : formatGenre(genre)
              return (
                <section key={genre} aria-labelledby={headingId}>
                  <h3
                    id={headingId}
                    className="text-sm font-medium text-lsc-dark/60 dark:text-lsc-cream/60 mb-3 flex items-center gap-2"
                  >
                    <span>{label}</span>
                    <span className="text-lsc-dark/40 dark:text-lsc-cream/40 font-normal">
                      · {groupBooks.length}
                    </span>
                  </h3>
                  <ul className="grid grid-cols-1 md:grid-cols-2 gap-4 list-none p-0 m-0">
                    {groupBooks.map((book) => (
                      <li key={book.id}>
                        <BookCard book={book} />
                      </li>
                    ))}
                  </ul>
                </section>
              )
            })}
          </div>
        ) : (
          <ul className="grid grid-cols-1 md:grid-cols-2 gap-4 list-none p-0 m-0">
            {sortedBooks.map((book) => (
              <li key={book.id}>
                <BookCard book={book} />
              </li>
            ))}
          </ul>
        )}
      </section>

      {/* Discovery Rail */}
      {railBooks.length >= 3 && (
        <section aria-labelledby="indie-rail-heading">
          <h2
            id="indie-rail-heading"
            className="text-lg font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4"
          >
            More from the indie collection
          </h2>
          <div
            role="group"
            aria-label="More indie titles"
            className="flex gap-4 overflow-x-auto pb-3 snap-x snap-mandatory scrollbar-thin scrollbar-track-transparent scrollbar-thumb-lsc-border"
          >
            {railBooks.map((book) => {
              const bookSlug = generateSlug(book.title, book.id)
              return (
                <div
                  key={book.id}
                  className="snap-start flex-shrink-0 w-36 bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm hover:shadow-md transition-shadow"
                >
                  <Link
                    to={`/indie/book/${bookSlug}`}
                    aria-hidden="true"
                    tabIndex={-1}
                    className="block rounded-t-xl"
                  >
                    <div className="w-full h-48 rounded-t-xl overflow-hidden bg-lsc-cream dark:bg-lsc-brown flex items-center justify-center">
                      {book.cover_url ? (
                        <img
                          src={book.cover_url}
                          alt=""
                          className="w-full h-full object-cover"
                        />
                      ) : (
                        <BookOpen className="w-8 h-8 text-lsc-rose/50" aria-hidden="true" />
                      )}
                    </div>
                  </Link>
                  <div className="p-2">
                    <Link
                      to={`/indie/book/${bookSlug}`}
                      className="text-xs font-serif font-semibold text-lsc-dark dark:text-lsc-cream line-clamp-2 hover:text-lsc-rose block focus-visible:outline focus-visible:outline-2 focus-visible:outline-lsc-rose focus-visible:outline-offset-2 rounded"
                      title={book.title}
                    >
                      {book.title}
                    </Link>
                    <Link
                      to={`/indie/author/${penNameToSlug(book.author_pen_name)}`}
                      className="text-xs text-lsc-rose hover:underline mt-0.5 block truncate focus-visible:outline focus-visible:outline-2 focus-visible:outline-lsc-rose focus-visible:outline-offset-2 rounded"
                    >
                      {book.author_pen_name}
                    </Link>
                  </div>
                </div>
              )
            })}
          </div>
        </section>
      )}
    </div>
  )
}
