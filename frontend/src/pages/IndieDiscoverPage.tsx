/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Indie Discovery Landing Page
 * Main entry point for public discovery with featured, trending, and new arrivals
 */
import { useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  BookOpen,
  TrendingUp,
  Sparkles,
  Clock,
  Star,
  Heart,
  ChevronRight,
  Loader2,
  AlertCircle,
  Rss,
  Award,
  BookMarked,
  User,
  Tag,
} from 'lucide-react'
import { clsx } from '@/utils/helpers'
import { useAuth } from '@/contexts/AuthContext'
import {
  getDiscoveryPage,
  getCollectionList,
  getRssFeedUrl,
  type BookCard,
} from '@/api/indie-catalog-api'
import {
  getForYouFeed,
  type ForYouFeedResponse,
} from '@/api/indie-engagement-api'
import { getRatingInfo } from '@/utils/content-ratings'
import { useBranding } from '@/contexts/BrandingContext'

function formatGenreName(name: string): string {
  return name
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ")
}



function BookCard({ book, featured = false }: { book: BookCard; featured?: boolean }): React.ReactElement {
  const ratingInfo = getRatingInfo(book.content_rating)

  if (featured) {
    return (
      <Link
        to={`/indie/book/${book.slug}`}
        className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-md hover:shadow-lg transition-all overflow-hidden group"
      >
        <div className="aspect-[2/3] bg-lsc-cream dark:bg-lsc-brown overflow-hidden">
          {book.cover_url ? (
            <img
              src={book.cover_url}
              alt={`Cover of ${book.title}`}
              className="w-full h-full object-cover group-hover:scale-105 transition-transform"
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center">
              <BookOpen className="w-16 h-16 text-lsc-rose/30" aria-hidden="true" />
            </div>
          )}
        </div>
        <div className="p-4">
          <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream truncate" title={book.title}>
            {book.title}
          </h3>
          <p className="text-sm text-lsc-rose truncate" title={book.author_pen_name}>{book.author_pen_name}</p>
          <div className="flex items-center gap-2 mt-2">
            {book.average_rating && (
              <span className="flex items-center gap-1 text-xs">
                <Star className="w-3 h-3 text-status-warning-500 fill-yellow-500" aria-hidden="true" />
                <span className="sr-only">{book.average_rating.toFixed(1)} out of 5 stars</span>
                <span aria-hidden="true">{book.average_rating.toFixed(1)}</span>
              </span>
            )}
            {book.content_rating && book.content_rating !== 'unrated' && (
            <span className={clsx('text-xs px-2 py-0.5 rounded', ratingInfo.color)} aria-label={ratingInfo.description}>
              {ratingInfo.label}
            </span>
            )}
          </div>
        </div>
      </Link>
    )
  }

  return (
    <Link
      to={`/indie/book/${book.slug}`}
      className="bg-lsc-white dark:bg-earth-800 rounded-xl p-3 hover:shadow-md transition-shadow flex gap-3"
    >
      <div className="w-14 h-20 bg-lsc-cream dark:bg-lsc-brown rounded flex items-center justify-center flex-shrink-0 overflow-hidden">
        {book.cover_url ? (
          <img src={book.cover_url} alt={`Cover of ${book.title}`} className="w-full h-full object-cover" />
        ) : (
          <BookOpen className="w-6 h-6 text-lsc-rose/50" aria-hidden="true" />
        )}
      </div>
      <div className="flex-1 min-w-0">
        <h3 className="font-medium text-sm text-lsc-dark dark:text-lsc-cream truncate" title={book.title}>
          {book.title}
        </h3>
        <p className="text-xs text-lsc-rose truncate" title={book.author_pen_name}>{book.author_pen_name}</p>
        <div className="flex items-center gap-2 mt-1">
          {book.average_rating && (
            <span className="flex items-center gap-0.5 text-xs">
              <Star className="w-3 h-3 text-status-warning-500 fill-yellow-500" aria-hidden="true" />
              <span className="sr-only">{book.average_rating.toFixed(1)} out of 5 stars</span>
              <span aria-hidden="true">{book.average_rating.toFixed(1)}</span>
            </span>
          )}
          <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
            {book.total_borrows} borrows
          </span>
        </div>
      </div>
    </Link>
  )
}

function SectionHeader({
  icon: Icon,
  title,
  link,
  linkText,
}: {
  icon: React.ElementType
  title: string
  link?: string
  linkText?: string
}): React.ReactElement {
  return (
    <div className="flex items-center justify-between mb-4">
      <h2 className="flex items-center gap-2 text-xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
        <Icon className="w-5 h-5 text-lsc-rose" aria-hidden="true" />
        {title}
      </h2>
      {link && (
        <Link
          to={link}
          className="flex items-center gap-1 text-sm text-lsc-rose hover:underline"
        >
          {linkText || 'View all'}
          <ChevronRight className="w-4 h-4" />
        </Link>
      )}
    </div>
  )
}

export default function IndieDiscoverPage(): React.ReactElement {
  const branding = useBranding()
  const { user } = useAuth()

  const { data, isLoading, error } = useQuery({
    queryKey: ['indie-discover'],
    queryFn: getDiscoveryPage,
  })

  const { data: collections } = useQuery({
    queryKey: ['indie-collections'],
    queryFn: getCollectionList,
  })
  const { data: forYouData } = useQuery<ForYouFeedResponse>({
    queryKey: ['indie-for-you'],
    queryFn: () => getForYouFeed(1),
    enabled: !!user,
    staleTime: 120_000,
  })
  // Set page title
  useEffect(() => {
    document.title = 'Discover Indie Books | Local Authors, Local Stories'
    return () => { document.title = branding.library_name }
  }, [])

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]" role="status">
        <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" aria-hidden="true" />
        <span className="sr-only">Loading indie books...</span>
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="text-center py-16">
        <AlertCircle className="w-16 h-16 mx-auto mb-4 text-status-danger-500" aria-hidden="true" />
        <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-2">
          Unable to Load
        </h1>
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
          Please refresh the page or try again later.
        </p>
      </div>
    )
  }

  return (
    
    <div className="space-y-10">
        {/* Hero Section */}
        <div className="text-center py-8 bg-gradient-to-b from-lsc-rose/10 to-transparent dark:from-lsc-rose/5 rounded-xl">
          <Heart className="w-12 h-12 mx-auto mb-4 text-lsc-rose" aria-hidden="true" />
          <h1 className="text-4xl md:text-5xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-3">
            Discover Local Stories
          </h1>
          <p className="text-lg text-lsc-dark/70 dark:text-lsc-cream/70 max-w-2xl mx-auto mb-6">
            {data.total_books} eBooks from {data.total_authors} local authors.
            Your neighbor might just be your next favorite writer.
          </p>
          <div className="flex flex-wrap justify-center gap-4">
            <Link
              to="/indie"
              className="px-6 py-3 bg-lsc-rose text-white rounded-xl font-medium hover:bg-lsc-rose/90 flex items-center gap-2"
            >
              <BookOpen className="w-5 h-5" aria-hidden="true" />
              Browse All Books
            </Link>
            <Link
              to="/indie/author/register"
              className="px-6 py-3 border-2 border-lsc-rose text-lsc-rose rounded-xl font-medium hover:bg-lsc-rose/10 flex items-center gap-2"
            >
              <User className="w-5 h-5" aria-hidden="true" />
              Become an Author
            </Link>
          </div>
        </div>


        {/* For You Section (authenticated users only) */}
        {user && forYouData && forYouData.items.length > 0 && (
          <section>
            <SectionHeader icon={Heart} title="For You" link="/indie/feed" linkText="See more" />
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4">
              {forYouData.items.slice(0, 6).map((item) => (
                <Link
                  key={`${item.type}-${item.item.id}`}
                  to={item.item.slug ? `/indie/book/${item.item.slug}` : `/indie`}
                  className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm hover:shadow-md transition-all overflow-hidden group"
                >
                  <div className="aspect-[2/3] bg-lsc-cream dark:bg-earth-700 overflow-hidden flex items-center justify-center">
                    {item.item.cover_url ? (
                      <img src={item.item.cover_url} alt={`Cover of ${item.item.title}`} className="w-full h-full object-cover group-hover:scale-105 transition-transform" loading="lazy" />
                    ) : (
                      <BookOpen className="w-10 h-10 text-lsc-rose/30" aria-hidden="true" />
                    )}
                  </div>
                  <div className="p-3">
                    <h3 className="font-serif font-semibold text-sm text-lsc-dark dark:text-lsc-cream line-clamp-2 leading-snug mb-0.5" title={item.item.title}>
                      {item.item.title}
                    </h3>
                    {item.item.author_pen_name && (
                      <p className="text-xs text-lsc-rose truncate" title={item.item.author_pen_name}>{item.item.author_pen_name}</p>
                    )}
                    <p className="text-[10px] text-lsc-dark/70 dark:text-lsc-cream/50 mt-1 line-clamp-1" title={item.feed_reason_detail || item.feed_reason}>
                      {item.feed_reason_detail || item.feed_reason}
                    </p>
                  </div>
                </Link>
              ))}
            </div>
          </section>
        )}

        {/* Featured Section */}
        {data.featured.length > 0 && (
          <section>
            <SectionHeader icon={Sparkles} title="Featured" />
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4">
              {data.featured.map((book) => (
                <BookCard key={book.id} book={book} featured />
              ))}
            </div>
          </section>
        )}

        {/* Genre Grid */}
        {data.popular_genres.length > 0 && (
          <section>
            <SectionHeader icon={Tag} title="Browse by Genre" />
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
              {data.popular_genres.map((genre) => (
                <Link
                  key={genre.name}
                  to={`/indie/genre/${encodeURIComponent(genre.name)}`}
                  className="bg-lsc-cream dark:bg-earth-800 rounded-xl p-4 hover:bg-lsc-rose/20 dark:hover:bg-lsc-rose/20 transition-colors text-center"
                >
                  <div className="font-medium text-lsc-dark dark:text-lsc-cream">
                    {formatGenreName(genre.name)}
                  </div>
                  <div className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                    {genre.count} {genre.count === 1 ? 'book' : 'books'}
                  </div>
                </Link>
              ))}
            </div>
          </section>
        )}

        {/* Collections */}
        {collections && collections.length > 0 && (
          <section>
            <SectionHeader icon={BookMarked} title="Curated Collections" />
            <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {collections.map((collection) => (
                <Link
                  key={collection.id}
                  to={`/indie/collection/${collection.slug}`}
                  className="bg-gradient-to-br from-lsc-rose/20 to-lsc-cream dark:from-lsc-rose/30 dark:to-earth-800 rounded-xl p-5 hover:shadow-md transition-all"
                >
                  <h3 className="font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-1">
                    {collection.title}
                  </h3>
                  <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-2 line-clamp-2" title={collection.description ?? undefined}>
                    {collection.description}
                  </p>
                  <span className="text-xs text-lsc-rose">
                    {collection.book_count} {collection.book_count === 1 ? 'book' : 'books'}
                  </span>
                </Link>
              ))}
            </div>
          </section>
        )}

        {/* Trending and New Side by Side */}
        <div className="grid lg:grid-cols-2 gap-8">
          {/* Trending */}
          {data.trending.length > 0 && (
            <section>
              <SectionHeader icon={TrendingUp} title="Trending Now" link="/indie?sort=popular" />
              <div className="space-y-3">
                {data.trending.slice(0, 5).map((book) => (
                  <BookCard key={book.id} book={book} />
                ))}
              </div>
            </section>
          )}

          {/* New Arrivals */}
          {data.new_arrivals.length > 0 && (
            <section>
              <SectionHeader icon={Clock} title="New Arrivals" link="/indie?sort=new" />
              <div className="space-y-3">
                {data.new_arrivals.slice(0, 5).map((book) => (
                  <BookCard key={book.id} book={book} />
                ))}
              </div>
            </section>
          )}
        </div>

        {/* Staff Picks */}
        {data.staff_picks.length > 0 && (
          <section>
            <SectionHeader icon={Award} title="Staff Picks" />
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4">
              {data.staff_picks.map((book) => (
                <BookCard key={book.id} book={book} featured />
              ))}
            </div>
          </section>
        )}

        {/* Discovery Feed CTA */}
        <section className="bg-lsc-cream dark:bg-earth-800 rounded-xl p-8 text-center">
          <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-3">
            Want More?
          </h2>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-6 max-w-xl mx-auto">
            Check out our infinite scroll feed for endless discovery, or subscribe to our RSS feed for the latest releases.
          </p>
          <div className="flex flex-wrap justify-center gap-4">
            <Link
              to="/indie/feed"
              className="px-6 py-3 bg-lsc-rose text-white rounded-xl font-medium hover:bg-lsc-rose/90"
            >
              Browse Feed
            </Link>
            <a
              href={getRssFeedUrl()}
              className="px-6 py-3 border border-lsc-border dark:border-earth-700 rounded-xl font-medium hover:bg-lsc-cream/50 dark:hover:bg-earth-700 flex items-center gap-2"
            >
              <Rss className="w-4 h-4 text-status-warning-500" aria-hidden="true" />
              RSS Feed
            </a>
          </div>
        </section>
      </div>
  
  )
}
