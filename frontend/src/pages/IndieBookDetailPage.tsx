/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Public Book Detail Page
 * SEO-friendly page for individual indie ebooks
 */
import { useEffect, useState } from 'react'
import FocusTrap from 'focus-trap-react'
import { useParams, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  BookOpen,
  User,
  Star,
  Users,
  AlertCircle,
  Loader2,
  Share2,
  Calendar,
  Globe,
  ShieldCheck,
  Code,
  ShoppingCart,
  Heart,
  UserPlus,
  UserCheck,
  Send,
} from 'lucide-react'
import toast from 'react-hot-toast'
import { clsx } from '@/utils/helpers'
import { useAuth } from '@/contexts/AuthContext'
import {
  getPublicBookDetail,
  getPublicBookReviews,
  getBookEmbedUrl,
  getUserBorrowForEbook,
  submitReview,
  type PublicReview,
  penNameToSlug,
} from '@/api/indie-catalog-api'
import { overflowPurchase } from '@/api/domains/catalog/metislib-api'
import {
  favoriteEbook,
  unfavoriteEbook,
  getFavoriteStatus,
  getFavoriteCount,
  followAuthor,
  unfollowAuthor,
  getFollowStatus,
  getReadingProgress,
} from '@/api/indie-engagement-api'
import { useTranslation} from '@/i18n'
import { clean } from '@/lib/utils'
import AddToListButton from '@/components/indie/AddToListButton'
import EbookActionPanel from '@/components/indie/EbookActionPanel'
import ReadersAlsoEnjoyed from '@/components/indie/ReadersAlsoEnjoyed'
import MoreByAuthor from '@/components/indie/MoreByAuthor'
import { useAccessibility } from '@/features/accessibility/hooks/useAccessibility'
import { getContentPreferences } from '@/api/indie-engagement-api'
import ContentWarningBadges from '@/components/indie/ContentWarningBadges'

import { getRatingInfo } from '@/utils/content-ratings'
import { useBranding } from '@/contexts/BrandingContext'

function formatGenre(genre: string): string {
  try {
    return decodeURIComponent(genre)
      .replace(/_/g, ' ')
      .replace(/\b\w/g, (c) => c.toUpperCase())
  } catch {
    return genre.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
  }
}

function StarRating({ rating }: { rating: number }): React.ReactElement {
  return (
    <div className="flex items-center gap-0.5" role="img" aria-label={`${rating} out of 5 stars`}>
      {[1, 2, 3, 4, 5].map((star) => (
        <Star
          key={star}
          className={clsx(
            'w-4 h-4',
            star <= rating ? 'text-status-warning-500 fill-yellow-500' : 'text-earth-300'
          )}
          aria-hidden="true"
        />
      ))}
    </div>
  )
}

function ReviewCard({ review }: { review: PublicReview }): React.ReactElement {
  return (
    <div className="bg-lsc-cream/50 dark:bg-earth-800 rounded-xl p-4">
      <div className="flex items-center justify-between mb-2">
        <StarRating rating={review.rating} />
        <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
          {new Date(review.created_at).toLocaleDateString()}
        </span>
      </div>
      {review.review_text && (
        <p className="text-sm text-lsc-dark/80 dark:text-lsc-cream/80">
          {review.review_text}
        </p>
      )}
      <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-2">
        - {review.reviewer_name}
      </p>
    </div>
  )
}

function WriteReviewForm({ bookId, onReviewSubmitted }: { bookId: number; onReviewSubmitted: () => void }): React.ReactElement | null {
  const { user } = useAuth()
  const [rating, setRating] = useState(0)
  const [hoverRating, setHoverRating] = useState(0)
  const [reviewText, setReviewText] = useState('')
  const [initialized, setInitialized] = useState(false)

  const { data: borrowStatus, isLoading: borrowLoading } = useQuery({
    queryKey: ['user-borrow-status', bookId],
    queryFn: () => getUserBorrowForEbook(bookId),
    enabled: !!user,
  })

  // Pre-fill from existing review
  useEffect(() => {
    if (borrowStatus && !initialized) {
      if (borrowStatus.rating) setRating(borrowStatus.rating)
      if (borrowStatus.review_text) setReviewText(borrowStatus.review_text)
      setInitialized(true)
    }
  }, [borrowStatus, initialized])

  const reviewMutation = useMutation({
    mutationFn: () => submitReview(borrowStatus!.id, rating, reviewText || undefined),
    onSuccess: () => {
      toast.success('Review submitted!')
      onReviewSubmitted()
    },
    onError: (err: Error) => toast.error(err.message || 'Failed to submit review'),
  })

  if (borrowLoading) return null
  if (!user) return (
    <p className="text-lsc-dark/70 dark:text-lsc-cream/60 italic mt-4">
      <Link to={`/login?next=${encodeURIComponent(window.location.pathname)}`} className="underline text-lsc-brown dark:text-lsc-cream">Sign in</Link> to write a review.
    </p>
  )
  if (!borrowStatus) return null
  if (borrowStatus.status === 'active') return null

  // The by-ebook borrow-status endpoint returns review_text but not
  // review_submitted_at, so fall back to review_text to detect a prior review.
  const alreadyReviewed = !!borrowStatus.review_submitted_at || !!borrowStatus.review_text

  return (
    <div className="bg-lsc-cream/50 dark:bg-earth-800 rounded-xl p-5">
      <h3 className="font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-3">
        {alreadyReviewed ? 'Update Your Review' : 'Write a Review'}
      </h3>
      <div className="flex items-center gap-1 mb-3">
        {[1, 2, 3, 4, 5].map((star) => (
          <button
            key={star}
            type="button"
            onMouseEnter={() => setHoverRating(star)}
            onMouseLeave={() => setHoverRating(0)}
            onClick={() => setRating(star)}
            className="p-0.5"
            aria-label={`Rate ${star} star${star > 1 ? 's' : ''}`}
          >
            <Star
              className={clsx(
                'w-6 h-6 transition-colors',
                star <= (hoverRating || rating)
                  ? 'text-status-warning-500 fill-yellow-500'
                  : 'text-earth-300'
              )}
            />
          </button>
        ))}
        {rating > 0 && (
          <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 ml-2">
            {rating}/5
          </span>
        )}
      </div>
      <textarea
        value={reviewText}
        onChange={(e) => setReviewText(e.target.value)}
        placeholder="Share your thoughts about this book (optional)"
        rows={3}
        maxLength={2000}
        className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream text-sm resize-none focus:outline-none focus:ring-2 focus:ring-lsc-rose/50"
      />
      <div className="flex items-center justify-between mt-3">
        <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/50">
          {reviewText.length}/2000
        </span>
        <button
          onClick={() => reviewMutation.mutate()}
          disabled={reviewMutation.isPending || rating === 0}
          className="flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-lg text-sm font-medium hover:bg-lsc-rose/90 disabled:opacity-50 transition-colors"
        >
          {reviewMutation.isPending ? (
            <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
          ) : (
            <Send className="w-4 h-4" />
          )}
          {alreadyReviewed ? 'Update Review' : 'Submit Review'}
        </button>
      </div>
    </div>
  )
}

// eslint-disable-next-line complexity
export default function IndieBookDetailPage(): React.ReactElement {
  const branding = useBranding()
  const { t } = useTranslation()
  const { settings } = useAccessibility()
  const { slug } = useParams<{ slug: string }>()
  const { user: _user } = useAuth()
  const user = _user
  const queryClient = useQueryClient()
  const [showEmbedModal, setShowEmbedModal] = useState(false)
  const { data: book, isLoading, error } = useQuery({
    queryKey: ['indie-book', slug],
    queryFn: () => getPublicBookDetail(slug!),
    enabled: !!slug,
  })

  const { data: reviews } = useQuery({
    queryKey: ['indie-book-reviews', slug],
    queryFn: () => getPublicBookReviews(slug!),
    enabled: !!slug,
  })

  // Engagement queries
  const { data: favStatus } = useQuery({
    queryKey: ['fav-status', book?.id],
    queryFn: () => getFavoriteStatus(book!.id),
    enabled: !!book && !!user,
  })
  const { data: favCount } = useQuery({
    queryKey: ['fav-count', book?.id],
    queryFn: () => getFavoriteCount(book!.id),
    enabled: !!book,
  })
  const { data: contentPrefs } = useQuery({
    queryKey: ['indie-content-prefs'],
    queryFn: getContentPreferences,
    enabled: !!user,
  })

  const { data: followStatus } = useQuery({
    queryKey: ['follow-status', book?.author_id],
    queryFn: () => getFollowStatus(book!.author_id),
    enabled: !!book && !!user && !!book.author_id,
  })
  const { data: readingProgress } = useQuery({
    queryKey: ['indie-reading-progress', book?.id],
    queryFn: () => getReadingProgress(book!.id),
    enabled: !!book && !!user,
    staleTime: 60_000,
  })
  const favMutation = useMutation({
    mutationFn: () =>
      favStatus?.favorited ? unfavoriteEbook(book!.id) : favoriteEbook(book!.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['fav-status', book?.id] })
      queryClient.invalidateQueries({ queryKey: ['fav-count', book?.id] })
    },
    onError: () => toast.error(t('toast.indieBookDetail.couldNotUpdateFavorite')),
  })
  const followMutation = useMutation({
    mutationFn: () =>
      followStatus?.following ? unfollowAuthor(book!.author_id) : followAuthor(book!.author_id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['follow-status', book?.author_id] })
    },
    onError: () => toast.error(t('toast.indieAuthorProfile.couldNotUpdateFollow')),
  })

  const handleShare = async () => {
    const url = window.location.href
    if (navigator.share) {
      try {
        await navigator.share(clean({
          title: book?.title,
          text: `Check out "${book?.title}" by ${book?.author_pen_name}`,
          url,
        }))
      } catch {
        // User cancelled or share failed
      }
    } else {
      await navigator.clipboard.writeText(url)
      toast.success(t('indieBookDetail.linkCopiedToClipboard'))
    }
  }

  const handleCopyEmbed = () => {
    if (!book) return
    setShowEmbedModal(true)
  }

  const embedCode = book ? `<iframe src="${window.location.origin}${getBookEmbedUrl(book.id)}" width="400" height="180" frameborder="0" style="border:none;border-radius:12px;" title="${book.title} by ${book.author_pen_name}"></iframe>` : ''

  const handleCopyEmbedCode = () => {
    navigator.clipboard.writeText(embedCode)
    toast.success(t('toast.indieBookDetail.embedCodeCopiedToClipboard'))
  }

  // Set page title
  useEffect(() => {
    if (book) {
      document.title = `${book.title} by ${book.author_pen_name} | Indie Books`
    } else if (!isLoading && (error || !book)) {
      document.title = `Book Not Found — ${branding.library_name}`
    }
    return () => { document.title = branding.library_name }
  }, [book, isLoading, error])

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]" role="status">
        <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" aria-hidden="true" />
        <span className="sr-only">Loading book details...</span>
      </div>
    )
  }

  if (error || !book) {
    return (
      <div className="text-center py-16" role="alert">
        <AlertCircle className="w-16 h-16 mx-auto mb-4 text-status-danger-500" aria-hidden="true" />
        <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-2">
          Book Not Found
        </h1>
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
          This book may have been removed or is no longer available.
        </p>
        <Link to="/indie" className="text-lsc-rose hover:underline">
          Browse other books
        </Link>
      </div>
    )
  }

  const ratingInfo = getRatingInfo(book.content_rating)
  return (
    
    <div className="max-w-5xl mx-auto space-y-8">
        {/* Breadcrumb */}
        <nav aria-label="Breadcrumb" className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
          <Link to="/indie" className="hover:text-lsc-rose hover:underline">Indie Books</Link>
          {book.genre && (
            <>
              <span className="mx-2">/</span>
              <Link to={`/indie/genre/${encodeURIComponent(book.genre)}`} className="hover:text-lsc-rose hover:underline">
                {formatGenre(book.genre)}
              </Link>
            </>
          )}
          <span className="mx-2">/</span>
          <span className="text-lsc-dark dark:text-lsc-cream">{book.title}</span>
        </nav>

        {/* Main Content */}
        <div className="grid md:grid-cols-3 gap-8">
          {/* Cover and Actions */}
          <div className="space-y-4">
            <div className="aspect-[2/3] bg-lsc-cream dark:bg-lsc-brown rounded-xl overflow-hidden shadow-lg">
              {book.cover_url ? (
                <img
                  src={book.cover_url}
                  alt={`Cover of ${book.title}`}
                  className="w-full h-full object-cover"
                />
              ) : (
                <div className="w-full h-full flex items-center justify-center">
                  <BookOpen className="w-24 h-24 text-lsc-rose/30" aria-hidden="true" />
                </div>
              )}
            </div>

            {/* Action Panel */}
            <EbookActionPanel book={book} readingPercent={readingProgress?.percent} />

            {/* Share & Embed */}
            <div className="flex gap-2">
              <button
                onClick={handleShare}
                className="flex-1 py-2 border border-lsc-border dark:border-earth-700 rounded-lg flex items-center justify-center gap-2 text-sm text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-earth-800"
              >
                <Share2 className="w-4 h-4" aria-hidden="true" />
                Share
              </button>
              <button
                onClick={handleCopyEmbed}
                className="flex-1 py-2 border border-lsc-border dark:border-earth-700 rounded-lg flex items-center justify-center gap-2 text-sm text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-earth-800"
              >
                <Code className="w-4 h-4" aria-hidden="true" />
                Embed
              </button>
            </div>

            {/* Favorite + Add to List */}
            <div className="flex gap-2">
              <button
                onClick={() => {
                  if (!user) { toast.error(t('toast.indieBookDetail.signInToFavorite')); return }
                  favMutation.mutate()
                }}
                disabled={favMutation.isPending}
                className={clsx(
                  'flex-1 py-2 rounded-lg flex items-center justify-center gap-2 text-sm font-medium transition-colors border',
                  favStatus?.favorited
                    ? 'bg-status-danger-50 dark:bg-status-danger-900/20 border-status-danger-300 dark:border-status-danger-700 text-status-danger-600 dark:text-status-danger-400'
                    : 'border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-earth-800'
                )}
                aria-label={favStatus?.favorited ? 'Remove from favorites' : 'Add to favorites'}
              >
                <Heart className={clsx('w-4 h-4', favStatus?.favorited && 'fill-red-500')} />
                {favCount?.count ?? 0}
              </button>

              <div className="flex-1 flex items-center justify-center border border-lsc-border dark:border-earth-700 rounded-lg hover:bg-lsc-cream dark:hover:bg-earth-800">
                <AddToListButton ebookId={book.id} />
              </div>
            </div>
          </div>

          {/* Book Details */}
          <div className="md:col-span-2 space-y-6">
            {/* Title and Author */}
            <div>
              <h1 className="text-3xl md:text-4xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-2">
                {book.title}
              </h1>
              {book.author_id ? (
                <Link
                  to={`/indie/author/${penNameToSlug(book.author_pen_name)}`}
                  className="inline-flex items-center gap-2 text-lg text-lsc-rose hover:underline"
                >
                  <User className="w-5 h-5" aria-hidden="true" />
                  {book.author_pen_name}
                  {book.author_verified && (
                    <ShieldCheck className="w-4 h-4 text-earth-600" aria-label={t('aria.indieAuthorProfile.verifiedAuthor')} />
                  )}
                </Link>
              ) : (
                <span className="inline-flex items-center gap-2 text-lg text-lsc-dark dark:text-lsc-cream">
                  <User className="w-5 h-5" aria-hidden="true" />
                  {book.author_pen_name}
                </span>
              )}
            </div>

            {/* Stats Row */}
            <div className="flex flex-wrap items-center gap-4">
              {book.average_rating && (
                <div className="flex items-center gap-2">
                  <StarRating rating={Math.round(book.average_rating)} />
                  <span className="font-medium text-lsc-dark dark:text-lsc-cream">{book.average_rating.toFixed(1)}</span>
                  <a href="#reviews" className="text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-rose hover:underline cursor-pointer">
                    ({book.rating_count} reviews)
                  </a>
                </div>
              )}
              {!settings.noFOMO && book.total_borrows > 0 && (
                <span className="flex items-center gap-1 text-lsc-dark/70 dark:text-lsc-cream/70">
                  <Users className="w-4 h-4" aria-hidden="true" />
                  {book.total_borrows} {book.total_borrows === 1 ? 'reader' : 'readers'}
                </span>
              )}
              {book.content_rating && book.content_rating !== 'unrated' && (
                <span className={clsx('px-3 py-1 rounded-full text-sm font-medium', ratingInfo.color)} aria-label={ratingInfo.description}>
                  {ratingInfo.label}
                </span>
              )}
            </div>

            {/* Badges */}
            <div className="flex flex-wrap gap-2">
              {book.subjects
                ?.filter((s) => s.toLowerCase() !== (book.genre || "").toLowerCase())
                .map((subject) => (
                <Link key={subject} to={`/indie?q=${encodeURIComponent(subject)}`} className="px-3 py-1 bg-lsc-cream/50 dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream rounded-full text-xs hover:bg-lsc-rose/20 hover:text-lsc-rose transition-colors">
                  {subject}
                </Link>
              ))}
            </div>

            {/* Content Warnings */}
            {book.content_warnings?.length > 0 && (
              <div className="bg-status-warning-50 dark:bg-status-warning-900/20 border border-status-warning-200 dark:border-status-warning-800 rounded-xl p-4">
                <div className="flex items-center gap-2 text-status-warning-700 dark:text-status-warning-400 mb-2">
                  <AlertCircle className="w-5 h-5" aria-hidden="true" />
                  <span className="font-medium">Content Warnings</span>
                </div>
                <ContentWarningBadges
                  warnings={book.content_warnings}
                  flaggedWarnings={contentPrefs?.flagged_warnings || []}
                  hiddenWarnings={contentPrefs?.hidden_warnings || []}
                />
              </div>
            )}

            {/* Overflow Purchase — when no copies available */}
            {user && book.available_copies === 0 && (
              <div className="bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800 rounded-xl p-5">
                <div className="flex items-center justify-between flex-wrap gap-3">
                  <div>
                    <p className="font-semibold text-emerald-800 dark:text-emerald-200">All copies are currently borrowed</p>
                    <p className="text-sm text-emerald-700/80 dark:text-emerald-300/80 mt-1">Skip the wait — buy your own copy for $15</p>
                  </div>
                  <button
                    onClick={async () => {
                      try {
                        const data = await overflowPurchase(book.id)
                        if (data.checkout_url) window.location.href = data.checkout_url
                      } catch {
                        toast.error(t('toast.ebookDetail.purchaseUnavailableRightNow'))
                      }
                    }}
                    className="flex items-center gap-2 px-5 py-2.5 bg-emerald-600 text-white rounded-lg font-medium hover:bg-emerald-700 transition-colors"
                  >
                    <ShoppingCart className="w-4 h-4" aria-hidden="true" />
                    Buy Now — $15
                  </button>
                </div>
              </div>
            )}

            {/* Description */}
            <div>
              <h2 className="text-xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-3">
                About This Book
              </h2>
              <div className="prose dark:prose-invert max-w-none">
                <p className="text-lsc-dark/80 dark:text-lsc-cream/80 whitespace-pre-wrap">
                  {book.description}
                </p>
              </div>
            </div>

            {/* Book Details Grid */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 bg-lsc-cream/50 dark:bg-earth-800 rounded-xl p-4">
              {book.word_count && (
                <div>
                  <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Word Count</div>
                  <div className="font-medium text-lsc-dark dark:text-lsc-cream">{book.word_count.toLocaleString()}</div>
                </div>
              )}
              <div>
                <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Language</div>
                <div className="font-medium text-lsc-dark dark:text-lsc-cream flex items-center gap-1">
                  <Globe className="w-3 h-3" aria-hidden="true" />
                  {book.language.toUpperCase()}
                </div>
              </div>
              {book.publication_year && (
                <div>
                  <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Published</div>
                  <div className="font-medium text-lsc-dark dark:text-lsc-cream flex items-center gap-1">
                    <Calendar className="w-3 h-3" aria-hidden="true" />
                    {book.publication_year}
                  </div>
                </div>
              )}
              {book.isbn && (
                <div>
                  <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">ISBN</div>
                  <div className="font-medium text-sm text-lsc-dark dark:text-lsc-cream">{book.isbn}</div>
                </div>
              )}
            </div>

            {/* Author Info */}
            {book.author_bio && (
              <div className="bg-lsc-cream/50 dark:bg-earth-800 rounded-xl p-4">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="font-serif font-bold text-lsc-dark dark:text-lsc-cream">
                    About the Author
                  </h3>
                  {user && (
                    <button
                      onClick={() => followMutation.mutate()}
                      disabled={followMutation.isPending}
                      className={clsx(
                        'flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors',
                        followStatus?.following
                          ? 'bg-lsc-rose/10 text-lsc-rose border border-lsc-rose/30'
                          : 'bg-lsc-rose text-white hover:bg-lsc-rose/90'
                      )}
                      aria-label={followStatus?.following ? 'Unfollow author' : 'Follow author'}
                    >
                      {followStatus?.following ? (
                        <><UserCheck className="w-4 h-4" /> Following</>
                      ) : (
                        <><UserPlus className="w-4 h-4" /> Follow</>
                      )}
                    </button>
                  )}
                </div>
                <div className="flex gap-4">
                  {book.author_profile_image && (
                    <img
                      src={book.author_profile_image}
                      alt={book.author_pen_name}
                      className="w-16 h-16 rounded-full object-cover"
                    />
                  )}
                  <div className="flex-1">
                    <p className="text-sm text-lsc-dark/80 dark:text-lsc-cream/80 line-clamp-3" title={book.author_bio}>
                      {book.author_bio}
                    </p>
                    <Link
                      to={`/indie/author/${penNameToSlug(book.author_pen_name)}`}
                      className="text-sm text-lsc-rose hover:underline mt-2 inline-block"
                    >
                      View all books by {book.author_pen_name}
                    </Link>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Reviews Section */}
        <section id="reviews">
          <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-4">
            Reader Reviews
          </h2>
          <WriteReviewForm
            bookId={book.indie_ebook_id ?? book.id}
            onReviewSubmitted={() => {
              queryClient.invalidateQueries({ queryKey: ['indie-book-reviews', slug] })
              queryClient.invalidateQueries({ queryKey: ['user-borrow-status', book.id] })
            }}
          />
          {reviews && reviews.length > 0 ? (
            <div className="grid md:grid-cols-2 gap-4 mt-4">
              {reviews.map((review) => (
                <ReviewCard key={review.id} review={review} />
              ))}
            </div>
          ) : (
            <p className="text-lsc-dark/70 dark:text-lsc-cream/60 italic mt-4">
              No reviews yet. Be the first to share your thoughts!
            </p>
          )}
        </section>
        {/* More by this author */}
        {book?.author_pen_name && <MoreByAuthor authorPenName={book.author_pen_name} currentBookId={book.id} />}
        {/* Readers Also Enjoyed */}
        {book && <ReadersAlsoEnjoyed ebookId={book.id} />}

        {/* Embed Modal */}
        {showEmbedModal && book && (
           
          // eslint-disable-next-line jsx-a11y/click-events-have-key-events
          <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" onClick={() => setShowEmbedModal(false)}>
            <FocusTrap active={showEmbedModal} focusTrapOptions={{ escapeDeactivates: true }}>
            {/* eslint-disable-next-line jsx-a11y/click-events-have-key-events */}
            <div role="dialog" aria-modal="true" aria-labelledby="embed-modal-title" className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 max-w-lg w-full shadow-lg" onClick={(e) => e.stopPropagation()}>
              <div className="flex items-center justify-between mb-4">
                <h3 id="embed-modal-title" className="text-lg font-serif font-bold text-lsc-dark dark:text-lsc-cream">Embed This Book</h3>
                <button
                  onClick={() => setShowEmbedModal(false)}
                  className="text-lsc-dark/70 dark:text-lsc-cream/50 hover:text-lsc-dark dark:hover:text-lsc-cream"
                  aria-label={t('aria.indieBookDetail.closeEmbedModal')}
                >
                  <AlertCircle className="w-5 h-5" />
                </button>
              </div>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-3">
                Copy the code below to embed a preview card for <strong>{book.title}</strong> on your website or blog.
              </p>
              <div className="relative">
                <pre className="bg-lsc-cream/80 dark:bg-earth-900 rounded-lg p-3 text-xs text-lsc-dark dark:text-lsc-cream overflow-x-auto whitespace-pre-wrap break-all font-mono">
                  {embedCode}
                </pre>
              </div>
              <div className="flex gap-3 mt-4">
                <button
                  onClick={handleCopyEmbedCode}
                  className="flex-1 py-2 bg-lsc-rose text-white rounded-lg font-medium hover:bg-lsc-rose/90 transition-colors flex items-center justify-center gap-2"
                >
                  <Code className="w-4 h-4" />
                  Copy Code
                </button>
                <button
                  onClick={() => setShowEmbedModal(false)}
                  className="px-4 py-2 border border-lsc-border dark:border-earth-700 rounded-lg text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-earth-800"
                >
                  Close
                </button>
              </div>
            </div>
            </FocusTrap>
          </div>
        )}
      </div>
  
  )
}
