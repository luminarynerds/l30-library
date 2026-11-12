/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Star, BookOpen } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { getStaffReviews, type ReviewRecord } from '@/api/domains/content/reviews-api'
import { clsx } from '@/utils/helpers'
import PageContainer from '@/components/layout/PageContainer'

const PAGE_SIZE = 12

function StarRating({ rating }: { rating: number }) {
  return (
    <div className="flex items-center gap-0.5" aria-label={`${rating} out of 5 stars`}>
      {[1, 2, 3, 4, 5].map((star) => (
        <Star
          key={star}
          className={clsx(
            'w-4 h-4',
            star <= rating
              ? 'fill-lsc-rose text-lsc-rose dark:fill-lsc-rose-light dark:text-lsc-rose-light'
              : 'fill-none text-earth-300 dark:text-earth-600',
          )}
          aria-hidden="true"
        />
      ))}
    </div>
  )
}

export default function StaffReviewsPage() {
  const [loadedCount, setLoadedCount] = useState(PAGE_SIZE)

  const { data: reviews = [], isLoading } = useQuery({
    queryKey: ['staff-reviews', loadedCount],
    queryFn: () => getStaffReviews(loadedCount, 0),
  })

  const hasMore = reviews.length === loadedCount

  return (
    <PageContainer className="py-8">
      {/* Header */}
      <div className="flex items-center gap-3 mb-8">
        <Star className="w-7 h-7 text-lsc-rose dark:text-lsc-rose-light" aria-hidden="true" />
        <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">Staff Reviews</h1>
      </div>

      {isLoading ? (
        <div className="text-center py-16">
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">Loading reviews...</p>
        </div>
      ) : reviews.length === 0 ? (
        <div className="text-center py-16">
          <BookOpen className="w-10 h-10 mx-auto mb-3 text-lsc-dark/30 dark:text-lsc-cream/60" aria-hidden="true" />
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">No staff reviews published yet.</p>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {reviews.map((review: ReviewRecord) => {
              const item = review.catalog_item
              return (
                <article
                  key={review.id}
                  className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm border border-lsc-border/60 dark:border-earth-700/80 overflow-hidden flex flex-col"
                >
                  <div className="flex gap-4 p-4">
                    {/* Cover */}
                    <Link to={`/catalog/${review.catalog_item_id}`} className="shrink-0">
                      {item?.cover_url ? (
                        <img
                          src={item.cover_url}
                          alt={`Cover of ${item.title}`}
                          className="w-16 h-24 object-cover rounded-lg"
                          loading="lazy"
                        />
                      ) : (
                        <div className="w-16 h-24 bg-earth-100 dark:bg-earth-700 rounded-lg flex items-center justify-center">
                          <BookOpen className="w-6 h-6 text-lsc-dark/30 dark:text-lsc-cream/60" aria-hidden="true" />
                        </div>
                      )}
                    </Link>

                    <div className="flex-1 min-w-0">
                      <Link
                        to={`/catalog/${review.catalog_item_id}`}
                        className="text-sm font-semibold text-lsc-dark dark:text-lsc-cream hover:text-lsc-rose dark:hover:text-lsc-rose-light line-clamp-2"
                      >
                        {item?.title ?? 'Unknown Title'}
                      </Link>
                      {item?.author && (
                        <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-0.5 line-clamp-1" title={item.author}>
                          {item.author}
                        </p>
                      )}
                      {review.rating != null && (
                        <div className="mt-1.5">
                          <StarRating rating={review.rating} />
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="px-4 pb-4 flex-1 flex flex-col">
                    {review.title && (
                      <h3 className="text-sm font-semibold text-lsc-dark dark:text-lsc-cream mb-1">
                        {review.title}
                      </h3>
                    )}
                    {review.body && (
                      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 line-clamp-3 flex-1" title={review.body}>
                        {review.body}
                      </p>
                    )}
                    <div className="flex items-center justify-between mt-3 pt-3 border-t border-lsc-border/40 dark:border-earth-700/60">
                      {review.reviewer_name && (
                        <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/50">
                          Reviewed by {review.reviewer_name}
                        </span>
                      )}
                      <Link
                        to={`/catalog/${review.catalog_item_id}`}
                        className="text-xs font-medium text-lsc-rose dark:text-lsc-rose-light hover:underline ml-auto"
                        aria-label={`Read more about ${review.title}`}
                      >
                        Read more
                      </Link>
                    </div>
                  </div>
                </article>
              )
            })}
          </div>

          {hasMore && (
            <div className="text-center mt-8">
              <button
                onClick={() => setLoadedCount((prev) => prev + PAGE_SIZE)}
                className="px-6 py-2.5 text-sm font-medium rounded-xl border border-lsc-border dark:border-earth-600 text-lsc-dark dark:text-lsc-cream hover:bg-earth-50 dark:hover:bg-earth-700 transition-colors"
              >
                Load More Reviews
              </button>
            </div>
          )}
        </>
      )}
    </PageContainer>
  )
}
