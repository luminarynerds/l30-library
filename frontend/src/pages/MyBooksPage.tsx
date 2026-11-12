/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * My Books - Unified view of all borrowed ebooks across sources
 * Combines MetisLib checkouts, Indie borrows, and Vault cards.
 */
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  BookOpen,
  Clock,
  Download,
  RotateCcw,
  Loader2,
  Library,
  Sparkles,
  Star,
  CreditCard,
  RefreshCw,
} from 'lucide-react'
import toast from 'react-hot-toast'
import { clsx } from '@/utils/helpers'
import { PAGE_WIDTH } from '@/components/layout/page-width'
import { useAuth } from '@/contexts/AuthContext'
import { getMyMetisLibCheckouts, returnMetisLibEbook, type MetisLibCheckout } from '@/api/domains/catalog/metislib-api'
import { fetchApi } from '@/lib/api-client'
import api from '@/lib/api-client'
import { API_BASE } from '@/api/types'
import { friendlyErrorMessage } from '@/utils/friendlyError'
import { t } from '@/i18n'
import { StatusBadge } from '@/components/ui/StatusBadge'
import PageContainer from '@/components/layout/PageContainer'
import { Modal } from '@/components/ui/Modal'

// ── Types ─────────────────────────────────────────────────────

interface IndieBorrow {
  id: number
  ebook_id: number
  ebook_title: string
  ebook_cover_url: string | null
  author_pen_name: string
  borrowed_at: string
  due_at: string
  access_token: string
  status: string
  download_count: number
  max_downloads: number
}

interface VaultCard {
  id: number
  ebook_id: number
  ebook_title: string
  status: string
  access_count: number
  last_accessed_at: string | null
  created_at: string
}

type UnifiedBook =
  | { source: 'metislib'; data: MetisLibCheckout }
  | { source: 'indie'; data: IndieBorrow }

function getDueDate(book: UnifiedBook): Date | null {
  if (book.source === 'metislib') {
    return book.data.expires_at ? new Date(book.data.expires_at) : null
  }
  return new Date(book.data.due_at)
}

function daysUntil(date: Date | null): number | null {
  if (!date) return null
  return Math.ceil((date.getTime() - Date.now()) / (1000 * 60 * 60 * 24))
}

// ── Rating Dialog ─────────────────────────────────────────────

function RatingDialog({
  title,
  onConfirm,
  onCancel,
}: {
  title: string
  onConfirm: (rating: number | null) => void
  onCancel: () => void
}) {
  const [rating, setRating] = useState<number>(0)
  const [hovering, setHovering] = useState<number>(0)

  return (
    <Modal isOpen={true} onClose={onCancel} title={t('myBooks.returnBook', 'Return Book')} size="md">
      <p className="text-sm text-earth-600 dark:text-earth-400 mb-2">
        Returning <strong className="text-lsc-dark dark:text-lsc-cream">{title}</strong>
      </p>
      <p className="text-xs text-earth-600 dark:text-earth-500 mb-4">
        This will remove the book from your library. You can borrow it again later if available.
      </p>

      <p className="text-sm text-earth-600 dark:text-earth-400 mb-2">
        Rate this book (optional):
      </p>
      <div className="flex gap-1 mb-6">
        {[1, 2, 3, 4, 5].map((star) => (
          <button
            key={star}
            type="button"
            onMouseEnter={() => setHovering(star)}
            onMouseLeave={() => setHovering(0)}
            onClick={() => setRating(star === rating ? 0 : star)}
            className="p-0.5"
            aria-label={
              star === 1
                ? t('myBooks.rateOneStar', 'Rate 1 star')
                : t('myBooks.rateStars', 'Rate {{count}} stars').replace('{{count}}', String(star))
            }
            aria-pressed={rating === star}
          >
            <Star
              className={clsx(
                'w-7 h-7 transition-colors',
                (hovering || rating) >= star
                  ? 'text-status-warning-400 fill-status-warning-400'
                  : 'text-earth-300 dark:text-earth-600'
              )}
            />
          </button>
        ))}
        {rating > 0 && (
          <span className="ml-2 text-sm text-earth-600 self-center">{rating}/5</span>
        )}
      </div>

      <div className="flex gap-3">
        <button
          type="button"
          onClick={() => onConfirm(rating > 0 ? rating : null)}
          className="flex-1 py-2.5 bg-lsc-rose text-white rounded-lg font-medium hover:bg-lsc-rose/90 transition-colors"
        >
          {rating > 0 ? 'Return & Rate' : 'Return Without Rating'}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="px-4 py-2.5 border border-lsc-border dark:border-earth-600 rounded-lg text-earth-600 dark:text-earth-400 hover:bg-earth-50 dark:hover:bg-earth-750"
        >
          Cancel
        </button>
      </div>
    </Modal>
  )
}

// ── Book Card ─────────────────────────────────────────────────

function BookCard({
  book,
  onReturn,
  isReturning,
}: {
  book: UnifiedBook
  onReturn: (book: UnifiedBook) => void
  isReturning: boolean
}) {
  const [coverFailed, setCoverFailed] = useState(false)
  const due = getDueDate(book)
  const days = daysUntil(due)
  const overdue = days !== null && days < 0
  const urgent = days !== null && days >= 0 && days <= 2

  const title = book.source === 'metislib' ? book.data.title : book.data.ebook_title
  const author = book.source === 'metislib' ? book.data.author_name : book.data.author_pen_name
  const coverUrl = book.source === 'metislib' ? book.data.cover_url : book.data.ebook_cover_url
  const detailLink = book.source === 'metislib'
    ? `/ebooks/${book.data.ebook_id}`
    : `/indie/book/${book.data.ebook_id}`

  return (
    <div className="flex gap-4 bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm border border-lsc-border dark:border-earth-700 p-4">
      {/* Cover */}
      <div className="w-16 h-24 bg-lsc-cream dark:bg-earth-700 rounded-lg flex items-center justify-center flex-shrink-0 overflow-hidden">
        {coverUrl && !coverFailed ? (
          <img
            src={coverUrl}
            alt={`Cover of ${title}`}
            className="w-full h-full object-cover"
            onError={() => setCoverFailed(true)}
          />
        ) : (
          <BookOpen className="w-6 h-6 text-lsc-rose/30" aria-hidden="true" />
        )}
      </div>

      {/* Info */}
      <div className="flex-1 min-w-0">
        <Link to={detailLink} className="hover:text-lsc-rose transition-colors">
          <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream truncate" title={title}>
            {title}
          </h3>
        </Link>
        <p className="text-sm text-earth-600 dark:text-earth-400 truncate" title={author}>{author}</p>

        <div className="flex items-center gap-3 mt-2 flex-wrap">
          <span className={clsx(
            'text-xs px-2 py-0.5 rounded font-medium',
            book.source === 'indie'
              ? 'bg-lsc-rose/10 text-lsc-rose dark:bg-lsc-rose/20'
              : 'bg-sage-100 text-sage-700 dark:bg-sage-900/30 dark:text-sage-300'
          )}>
            {book.source === 'indie' ? 'Indie' : 'Library'}
          </span>

          {book.source === 'metislib' && book.data.format && (
            <span className="text-xs px-2 py-0.5 rounded bg-earth-100 text-earth-600 dark:bg-earth-700 dark:text-earth-300 uppercase">
              {book.data.format}
            </span>
          )}

          {days !== null && (
            <span className={clsx(
              'flex items-center gap-1 text-xs',
              overdue ? 'text-status-danger-600 dark:text-status-danger-400 font-medium'
                : urgent ? 'text-status-warning-700 dark:text-status-warning-400 font-medium'
                : 'text-earth-600 dark:text-earth-400'
            )}>
              <Clock className="w-3 h-3" />
              {overdue
                ? `Overdue by ${Math.abs(days)} day${Math.abs(days) !== 1 ? 's' : ''}`
                : days === 0 ? 'Expires today'
                : `Expires in ${days} day${days !== 1 ? 's' : ''}`}
            </span>
          )}

          {book.source === 'indie' && (
            <span className="text-xs text-earth-600 dark:text-earth-400">
              {book.data.download_count}/{book.data.max_downloads} downloads
            </span>
          )}
        </div>
      </div>

      {/* Actions */}
      <div className="flex flex-col gap-2 items-end flex-shrink-0">
        {book.source === 'metislib' && book.data.download_url && (
          <a
            href={book.data.download_url}
            className="flex items-center gap-1.5 px-3 py-2 bg-lsc-rose text-white rounded-lg text-sm font-medium hover:bg-lsc-rose/90 transition-colors"
          >
            <Download className="w-4 h-4" /> Read
          </a>
        )}
        {book.source === 'indie' && book.data.download_count < book.data.max_downloads && (
          <a
            href={`${API_BASE}/indie/lending/download/${book.data.access_token}`}
            className="flex items-center gap-1.5 px-3 py-2 bg-lsc-rose text-white rounded-lg text-sm font-medium hover:bg-lsc-rose/90 transition-colors"
          >
            <Download className="w-4 h-4" /> Read
          </a>
        )}
        <button
          onClick={() => onReturn(book)}
          disabled={isReturning}
          className="flex items-center gap-1 px-3 py-1.5 text-xs border border-lsc-border dark:border-earth-600 rounded-lg hover:bg-earth-50 dark:hover:bg-earth-750 text-earth-600 dark:text-earth-400"
        >
          <RotateCcw className="w-3 h-3" /> Return
        </button>
      </div>
    </div>
  )
}

// ── Vault Card Row ────────────────────────────────────────────

function VaultCardRow({ card }: { card: VaultCard }) {
  return (
    <div className="flex items-center gap-4 bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm border border-lsc-border dark:border-earth-700 p-4">
      <div className="w-10 h-14 bg-lsc-rose/10 dark:bg-lsc-rose/20 rounded-lg flex items-center justify-center flex-shrink-0">
        <CreditCard className="w-5 h-5 text-lsc-rose" />
      </div>
      <div className="flex-1 min-w-0">
        <Link to={`/indie/book/${card.ebook_id}`} className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream hover:text-lsc-rose truncate block" title={card.ebook_title}>
          {card.ebook_title}
        </Link>
        <p className="text-xs text-earth-600 dark:text-earth-400">
          Purchased {new Date(card.created_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })}
          {card.access_count > 0 && ` · ${card.access_count} download${card.access_count !== 1 ? 's' : ''}`}
        </p>
      </div>
      <StatusBadge variant="success">Owned</StatusBadge>
      <a
        href={`${API_BASE}/indie/vault/cards/${card.id}/download`}
        className="flex items-center gap-1.5 px-3 py-2 bg-lsc-rose text-white rounded-lg text-sm font-medium hover:bg-lsc-rose/90 transition-colors"
      >
        <Download className="w-4 h-4" /> Read
      </a>
    </div>
  )
}

// ── Main Page ─────────────────────────────────────────────────

// eslint-disable-next-line complexity
export default function MyBooksPage({ embedded }: { embedded?: boolean } = {}): React.ReactElement {
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const [filter, setFilter] = useState<'all' | 'metislib' | 'indie'>('all')
  const [returningBook, setReturningBook] = useState<UnifiedBook | null>(null)

  // Fetch all three sources in parallel
  const metislib = useQuery({
    queryKey: ['metislib-checkouts'],
    queryFn: getMyMetisLibCheckouts,
    enabled: !!user,
  })

  const indie = useQuery<IndieBorrow[]>({
    queryKey: ['indie-my-borrows'],
    queryFn: () => api.get(`${API_BASE}/indie/lending/borrows/active`),
    enabled: !!user,
  })

  const vault = useQuery<{ items: VaultCard[] }>({
    queryKey: ['vault-cards'],
    queryFn: () => fetchApi<{ items: VaultCard[] }>('/indie/vault/cards'),
    enabled: !!user,
  })

  const returnMetislibMutation = useMutation({
    mutationFn: ({ accessId, rating }: { accessId: number; rating: number | null }) =>
      returnMetisLibEbook(accessId, rating ?? undefined),
    onSuccess: () => {
      toast.success(t('toast.myBooks.ebookReturned'))
      queryClient.invalidateQueries({ queryKey: ['metislib-checkouts'] })
    },
    onError: (err: unknown) => {
      toast.error(friendlyErrorMessage(err))
    },
  })

  const returnIndieMutation = useMutation({
    mutationFn: ({ borrowId, rating }: { borrowId: number; rating: number | null }) =>
      api.post(`${API_BASE}/indie/lending/borrows/${borrowId}/return`, { rating }),
    onSuccess: () => {
      toast.success(t('toast.indieMyBorrows.bookReturned'))
      queryClient.invalidateQueries({ queryKey: ['indie-my-borrows'] })
    },
    onError: (err: unknown) => {
      toast.error(friendlyErrorMessage(err))
    },
  })

  function handleReturnConfirm(rating: number | null) {
    if (!returningBook) return
    if (returningBook.source === 'metislib') {
      returnMetislibMutation.mutate({ accessId: returningBook.data.access_id, rating })
    } else {
      returnIndieMutation.mutate({ borrowId: returningBook.data.id, rating })
    }
    setReturningBook(null)
  }

  function handleRetry() {
    if (metislib.error) metislib.refetch()
    if (indie.error) indie.refetch()
  }

  if (!user) {
    return (
      <PageContainer className="py-16 text-center">
        <BookOpen className="w-16 h-16 text-earth-300 dark:text-earth-600 mx-auto mb-4" />
        <h1 className="font-serif text-2xl font-bold text-lsc-dark dark:text-lsc-cream mb-2">
          My Books
        </h1>
        <p className="text-earth-600 dark:text-earth-400 mb-4">
          Sign in to view your borrowed eBooks.
        </p>
        <Link to="/login" className="text-lsc-rose hover:underline">Sign in</Link>
      </PageContainer>
    )
  }

  const isLoading = metislib.isLoading || indie.isLoading

  // Build unified list sorted by due date (soonest first)
  const allBooks: UnifiedBook[] = []
  if (filter !== 'indie' && metislib.data) {
    for (const c of metislib.data) {
      allBooks.push({ source: 'metislib', data: c })
    }
  }
  if (filter !== 'metislib' && indie.data) {
    for (const b of indie.data) {
      allBooks.push({ source: 'indie', data: b })
    }
  }
  allBooks.sort((a, b) => {
    const da = getDueDate(a)
    const db = getDueDate(b)
    if (!da && !db) return 0
    if (!da) return 1
    if (!db) return -1
    return da.getTime() - db.getTime()
  })

  const metislibCount = metislib.data?.length ?? 0
  const indieCount = indie.data?.length ?? 0
  const totalCount = metislibCount + indieCount
  const vaultCards = vault.data?.items ?? []
  const isReturning = returnMetislibMutation.isPending || returnIndieMutation.isPending

  const returningTitle = returningBook
    ? (returningBook.source === 'metislib' ? returningBook.data.title : returningBook.data.ebook_title)
    : ''

  return (
    <div className={embedded ? undefined : clsx(PAGE_WIDTH.read, 'mx-auto px-4 py-8')}>
      {/* Rating dialog */}
      {returningBook && (
        <RatingDialog
          title={returningTitle}
          onConfirm={handleReturnConfirm}
          onCancel={() => setReturningBook(null)}
        />
      )}

      {/* Header - hidden when embedded in AccountPage */}
      {!embedded && (<>
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <Library className="w-7 h-7 text-lsc-rose" />
          <div>
            <h1 className="font-serif text-2xl font-bold text-lsc-dark dark:text-lsc-cream">
              My Books
            </h1>
            {!isLoading && (
              <p className="text-sm text-earth-600 dark:text-earth-400" aria-live="polite" aria-atomic="true">
                {totalCount} active borrow{totalCount !== 1 ? 's' : ''}
                {vaultCards.length > 0 && ` · ${vaultCards.length} owned`}
              </p>
            )}
          </div>
        </div>
        <div className="flex gap-2">
          <Link to="/ebooks" className="text-sm text-lsc-rose hover:underline">Browse eBooks</Link>
          <span className="text-earth-300 dark:text-earth-600">|</span>
          <Link to="/indie" className="text-sm text-lsc-rose hover:underline">Browse indie</Link>
        </div>
      </div>
      </>)}

      {/* Filter tabs */}
      {!isLoading && totalCount > 0 && (metislibCount > 0 && indieCount > 0) && (
        <div className="flex gap-2 mb-4">
          {([
            ['all', `All (${totalCount})`],
            ['metislib', `Library (${metislibCount})`],
            ['indie', `Indie (${indieCount})`],
          ] as const).map(([key, label]) => (
            <button
              key={key}
              onClick={() => setFilter(key)}
              className={clsx(
                'px-3 py-1.5 text-sm rounded-lg transition-colors',
                filter === key
                  ? 'bg-lsc-rose text-white'
                  : 'bg-earth-100 dark:bg-earth-700 text-earth-600 dark:text-earth-300 hover:bg-earth-200 dark:hover:bg-earth-650'
              )}
            >
              {label}
            </button>
          ))}
        </div>
      )}

      {/* Loading */}
      {isLoading && (
        <div className="flex items-center justify-center py-20" role="status" aria-live="polite">
          <Loader2 className="w-8 h-8 text-lsc-rose motion-safe:animate-spin" aria-hidden="true" />
          <span className="sr-only">Loading your books…</span>
        </div>
      )}

      {/* Error */}
      {!isLoading && (metislib.error || indie.error) && (
        <div className="text-center py-8 mb-4">
          <p className="text-earth-600 dark:text-earth-400 text-sm">
            {metislib.error && indie.error
              ? 'Unable to load your books.'
              : metislib.error
                ? 'Unable to load library eBooks. Showing indie borrows only.'
                : 'Unable to load indie borrows. Showing library eBooks only.'}
          </p>
          <button
            onClick={handleRetry}
            className="inline-flex items-center gap-1.5 mt-3 px-3 py-1.5 text-sm text-lsc-rose border border-lsc-rose/40 rounded-lg hover:bg-lsc-rose/5 transition-colors"
          >
            <RefreshCw className="w-3.5 h-3.5" /> Retry
          </button>
        </div>
      )}

      {/* Active borrows */}
      {!isLoading && allBooks.length > 0 && (
        <div className="space-y-3">
          {allBooks.map((book) => (
            <BookCard
              key={book.source === 'metislib' ? `m-${book.data.access_id}` : `i-${book.data.id}`}
              book={book}
              onReturn={setReturningBook}
              isReturning={isReturning}
            />
          ))}
        </div>
      )}

      {/* Empty state */}
      {!isLoading && totalCount === 0 && !metislib.error && !indie.error && vaultCards.length === 0 && (
        <div className="text-center py-20">
          <BookOpen className="w-12 h-12 text-earth-300 dark:text-earth-600 mx-auto mb-4" />
          <h3 className="font-serif text-lg text-lsc-dark dark:text-lsc-cream mb-1">
            No books checked out
          </h3>
          <p className="text-earth-600 dark:text-earth-400 mb-6">
            Browse our collections and borrow something to read.
          </p>
          <div className="flex items-center justify-center gap-4">
            <Link
              to="/ebooks"
              className="inline-flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 transition-colors"
            >
              <Library className="w-4 h-4" /> Library eBooks
            </Link>
            <Link
              to="/indie"
              className="inline-flex items-center gap-2 px-4 py-2 border border-lsc-rose text-lsc-rose rounded-lg hover:bg-lsc-rose/5 transition-colors"
            >
              <Sparkles className="w-4 h-4" /> Indie Catalog
            </Link>
          </div>
        </div>
      )}

      {/* Vault cards (owned books) */}
      {vaultCards.length > 0 && (
        <div className="mt-8">
          <h2 className="font-serif text-lg font-bold text-lsc-dark dark:text-lsc-cream mb-3 flex items-center gap-2">
            <CreditCard className="w-5 h-5 text-lsc-rose" />
            Purchased Books
          </h2>
          <div className="space-y-3">
            {vaultCards.map((card) => (
              <VaultCardRow key={card.id} card={card} />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
