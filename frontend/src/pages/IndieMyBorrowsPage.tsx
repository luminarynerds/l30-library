/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { BookOpen, Clock, Download, RefreshCw, RotateCcw, Loader2, ExternalLink, Star, MessageSquare, History } from 'lucide-react'
import toast from 'react-hot-toast'
import api from '@/lib/api-client'
import { API_BASE } from '@/api/types'
import { getAccessToken } from '@/utils/tokenStore'
import { generateSlug, getBorrowHistory } from '@/api/indie-catalog-api'
import type { HistoryBorrow } from '@/api/indie-catalog-api'
import { getActiveReadingProgress } from '@/api/indie-engagement-api'
import ReadingProgressBar from '@/components/indie/ReadingProgressBar'
import { useTranslation} from '@/i18n'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { useBranding } from '@/contexts/BrandingContext'
import PageContainer from '@/components/layout/PageContainer'

interface ActiveBorrow {
  id: number
  ebook_id: number
  indie_ebook_id?: number
  ebook_title: string
  ebook_cover_url: string | null
  author_pen_name: string
  borrowed_at: string
  due_at: string
  access_token: string
  status: string
  download_count: number
  max_downloads: number
  renewal_count: number
  can_renew: boolean
}

type Tab = 'active' | 'history'

export default function IndieMyBorrowsPage() {
  const { t } = useTranslation()
  const branding = useBranding()

  useEffect(() => {
    document.title = 'My Indie Books | Borrowing'
    return () => { document.title = branding.library_name }
  }, [branding.library_name])
  const [now] = useState(() => Date.now())
  const [tab, setTab] = useState<Tab>('active')
  const [historyPage, setHistoryPage] = useState(1)
  const queryClient = useQueryClient()

  const { data: borrows, isLoading } = useQuery<ActiveBorrow[]>({
    queryKey: ['indie-my-borrows'],
    queryFn: () => api.get(`${API_BASE}/indie/lending/borrows/active`),
    staleTime: 30_000,
  })

  const { data: progressData } = useQuery({
    queryKey: ['indie-reading-progress-active'],
    queryFn: getActiveReadingProgress,
    staleTime: 60_000,
  })
  const progressMap = new Map(progressData?.map(p => [p.ebook_id, p]) ?? [])

  const { data: history, isLoading: historyLoading } = useQuery({
    queryKey: ['indie-borrow-history', historyPage],
    queryFn: () => getBorrowHistory(historyPage),
    staleTime: 60_000,
    enabled: tab === 'history',
  })

  const [returningId, setReturningId] = useState<number | null>(null)
  const [returnRating, setReturnRating] = useState<number>(0)
  const [returnReviewText, setReturnReviewText] = useState('')

  const returnMutation = useMutation({
    mutationFn: ({ borrowId, rating, reviewText }: { borrowId: number; rating?: number; reviewText?: string }) =>
      api.post(`${API_BASE}/indie/lending/borrows/${borrowId}/return`, {
        ...(rating ? { rating } : {}),
        ...(reviewText ? { review_text: reviewText } : {}),
      }),
    onSuccess: () => {
      toast.success(t('toast.indieMyBorrows.bookReturned'))
      queryClient.invalidateQueries({ queryKey: ['indie-my-borrows'] })
      queryClient.invalidateQueries({ queryKey: ['indie-borrow-history'] })
      setReturningId(null)
      setReturnRating(0)
      setReturnReviewText('')
    },
    onError: (err: unknown) => {
      toast.error(err instanceof Error ? err.message : t('toast.indieMyBorrows.failedToReturnBook'))
    },
  })

  const renewMutation = useMutation({
    mutationFn: (borrowId: number) =>
      api.post(`${API_BASE}/indie/lending/borrows/${borrowId}/renew`, {}),
    onSuccess: () => {
      toast.success('Borrow renewed for 21 more days')
      queryClient.invalidateQueries({ queryKey: ['indie-my-borrows'] })
    },
    onError: (err: unknown) => {
      toast.error(err instanceof Error ? err.message : 'Failed to renew borrow')
    },
  })

  const daysLeft = (due: string) => {
    const d = Math.ceil((new Date(due).getTime() - now) / (1000 * 60 * 60 * 24))
    return d
  }

  const formatDate = (iso: string) => {
    return new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
  }

  return (
    <PageContainer className="py-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream flex items-center gap-2">
          <BookOpen className="h-6 w-6" aria-hidden="true" /> My Indie Books
        </h1>
        <Link to="/indie" className="text-sm text-lsc-blue hover:underline flex items-center gap-1">
          Browse more <ExternalLink className="h-3 w-3" aria-hidden="true" />
        </Link>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-6 border-b border-lsc-border dark:border-earth-700">
        <button
          onClick={() => setTab('active')}
          className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
            tab === 'active'
              ? 'border-lsc-blue text-lsc-blue'
              : 'border-transparent text-earth-600 dark:text-earth-400 hover:text-lsc-dark dark:hover:text-lsc-cream'
          }`}
        >
          <BookOpen className="h-4 w-4 inline mr-1.5 -mt-0.5" aria-hidden="true" />
          Active{borrows?.length ? ` (${borrows.length})` : ''}
        </button>
        <button
          onClick={() => setTab('history')}
          className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
            tab === 'history'
              ? 'border-lsc-blue text-lsc-blue'
              : 'border-transparent text-earth-600 dark:text-earth-400 hover:text-lsc-dark dark:hover:text-lsc-cream'
          }`}
        >
          <History className="h-4 w-4 inline mr-1.5 -mt-0.5" aria-hidden="true" />
          History{history?.total ? ` (${history.total})` : ''}
        </button>
      </div>

      {tab === 'active' ? (
        <>
          {isLoading ? (
            <div className="text-center py-16" role="status">
              <Loader2 className="h-8 w-8 motion-safe:animate-spin mx-auto text-lsc-dark/70 dark:text-lsc-cream/50" aria-hidden="true" />
              <span className="sr-only">Loading your borrowed books...</span>
            </div>
          ) : !borrows?.length ? (
            <div className="text-center py-16 bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700">
              <BookOpen className="h-12 w-12 mx-auto text-earth-300 dark:text-earth-600 mb-4" aria-hidden="true" />
              <p className="text-earth-600 dark:text-earth-400 mb-2">{t('indieMyBorrows.noBorrowedIndieBooks')}</p>
              <Link to="/indie" className="text-lsc-blue hover:underline text-sm">
                Discover indie books to borrow
              </Link>
            </div>
          ) : (
            <div className="space-y-4">
              {borrows.map((b) => {
                const days = daysLeft(b.due_at)
                const overdue = days < 0
                const urgent = days >= 0 && days <= 2

                return (
                  <div key={b.id} className="flex flex-wrap gap-4 bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-4">
                    {b.ebook_cover_url ? (
                      <img
                        src={b.ebook_cover_url}
                        alt={`Cover of ${b.ebook_title}`}
                        className="w-16 h-24 object-cover rounded-lg shrink-0"
                      />
                    ) : (
                      <div className="w-16 h-24 bg-earth-100 dark:bg-earth-700 rounded-lg shrink-0 flex items-center justify-center">
                        <BookOpen className="h-6 w-6 text-earth-600" aria-hidden="true" />
                      </div>
                    )}

                    <div className="flex-1 min-w-0">
                      <Link
                        to={`/indie/book/${generateSlug(b.ebook_title, b.ebook_id)}`}
                        className="font-medium text-lsc-dark dark:text-lsc-cream hover:text-lsc-blue truncate block"
                        title={b.ebook_title}
                      >
                        {b.ebook_title}
                      </Link>
                      <p className="text-sm text-earth-600 dark:text-earth-400">{b.author_pen_name}</p>

                      <div className="flex items-center gap-4 mt-2 text-xs">
                        <span className="flex items-center gap-1 text-earth-600">
                          <Clock className="h-3 w-3" aria-hidden="true" />
                          {overdue ? (
                            <span className="text-status-danger-600 dark:text-status-danger-400 font-medium">Overdue by {Math.abs(days)} day{Math.abs(days) !== 1 ? 's' : ''}</span>
                          ) : urgent ? (
                            <span className="text-status-warning-600 dark:text-status-warning-400 font-medium">Due in {days} day{days !== 1 ? 's' : ''}</span>
                          ) : (
                            <span>{days} day{days !== 1 ? 's' : ''} left</span>
                          )}
                        </span>
                        <span className="text-earth-600">
                          {b.download_count}/{b.max_downloads} downloads
                        </span>
                      </div>
                      {progressMap.get(b.indie_ebook_id ?? b.ebook_id)?.percent ? <ReadingProgressBar percent={progressMap.get(b.indie_ebook_id ?? b.ebook_id)!.percent} className="mt-2" /> : null}
                    </div>

                    <div className="flex flex-col gap-2 shrink-0">
                      <Link
                        to={`/indie/read/${b.indie_ebook_id ?? b.ebook_id}`}
                        state={{ title: b.ebook_title }}
                        aria-label={`Read ${b.ebook_title} in your browser`}
                        className="flex items-center gap-1 px-3 py-1.5 text-xs bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90"
                      >
                        <BookOpen className="h-3 w-3" aria-hidden="true" /> Read
                      </Link>
                      {b.download_count < b.max_downloads && (
                        <button
                          onClick={async () => {
                            try {
                              const token = getAccessToken()
                              // eslint-disable-next-line no-restricted-syntax -- EPUB binary download; fetchApi parses JSON
                              const resp = await fetch(`${API_BASE}/indie/lending/download/${b.access_token}`, {
                                headers: token ? { Authorization: `Bearer ${token}` } : {},
                              })
                              if (!resp.ok) {
                                const err = await resp.json().catch(() => null)
                                throw new Error(err?.detail || 'Download failed')
                              }
                              const blob = await resp.blob()
                              const url = URL.createObjectURL(blob)
                              const a = document.createElement('a')
                              a.href = url
                              a.download = `${b.ebook_title}.epub`
                              a.click()
                              URL.revokeObjectURL(url)
                              toast.success(t('toast.indieMyBorrows.downloadStarted'))
                            } catch (err) {
                              toast.error(err instanceof Error ? err.message : t('toast.myEbooks.downloadFailed'))
                            }
                          }}
                          aria-label={`Download ${b.ebook_title} as an EPUB`}
                          className="flex items-center gap-1 px-3 py-1.5 text-xs border border-lsc-border dark:border-earth-600 rounded-lg hover:bg-earth-50 dark:hover:bg-earth-750 text-earth-600 dark:text-earth-400"
                        >
                          <Download className="h-3 w-3" aria-hidden="true" /> Download
                        </button>
                      )}
                      <button
                        onClick={() => renewMutation.mutate(b.id)}
                        disabled={!b.can_renew || renewMutation.isPending}
                        title={!b.can_renew ? (b.renewal_count >= 1 ? 'Already renewed' : 'Renewal unavailable') : 'Extend by 21 days'}
                        aria-label={`Renew ${b.ebook_title}`}
                        className="flex items-center gap-1 px-3 py-1.5 text-xs border border-lsc-border dark:border-earth-600 rounded-lg hover:bg-earth-50 dark:hover:bg-earth-750 text-earth-600 dark:text-earth-400 disabled:opacity-40 disabled:cursor-not-allowed"
                      >
                        {renewMutation.isPending && renewMutation.variables === b.id ? (
                          <Loader2 className="h-3 w-3 motion-safe:animate-spin" />
                        ) : (
                          <RefreshCw className="h-3 w-3" />
                        )} Renew
                      </button>
                      <button
                        onClick={() => setReturningId(returningId === b.id ? null : b.id)}
                        disabled={returnMutation.isPending}
                        aria-label={`Return ${b.ebook_title}`}
                        className="flex items-center gap-1 px-3 py-1.5 text-xs border border-lsc-border dark:border-earth-600 rounded-lg hover:bg-earth-50 dark:hover:bg-earth-750 text-earth-600 dark:text-earth-400"
                      >
                        <RotateCcw className="h-3 w-3" /> Return
                      </button>
                    </div>

                    {/* Return + Review Panel */}
                    {returningId === b.id && (
                      <div className="w-full mt-3 pt-3 border-t border-lsc-border dark:border-earth-700">
                        <p className="text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2 flex items-center gap-1">
                          <MessageSquare className="h-4 w-4" /> Leave a review (optional)
                        </p>
                        <div className="flex items-center gap-1 mb-2">
                          {[1, 2, 3, 4, 5].map((star) => (
                            <button
                              key={star}
                              type="button"
                              onClick={() => setReturnRating(returnRating === star ? 0 : star)}
                              className="p-0.5"
                              aria-label={`Rate ${star} star${star !== 1 ? 's' : ''}`}
                            >
                              <Star className={`h-5 w-5 ${star <= returnRating ? 'text-status-warning-500 fill-yellow-500' : 'text-earth-300 dark:text-earth-600'}`} />
                            </button>
                          ))}
                          {returnRating > 0 && <span className="text-xs text-earth-600 ml-1">{returnRating}/5</span>}
                        </div>
                        <textarea
                          value={returnReviewText}
                          onChange={(e) => setReturnReviewText(e.target.value)}
                          placeholder="What did you think of this book?"
                          rows={3}
                          maxLength={2000}
                          className="w-full px-3 py-2 text-sm border border-lsc-border dark:border-earth-600 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream placeholder:text-earth-400 resize-none focus:outline-none focus:ring-1 focus:ring-lsc-blue"
                        />
                        <div className="flex items-center justify-between mt-2">
                          <span className="text-xs text-earth-600">{returnReviewText.length}/2000</span>
                          <div className="flex gap-2">
                            <button
                              onClick={() => { setReturningId(null); setReturnRating(0); setReturnReviewText('') }}
                              className="px-3 py-1.5 text-xs text-earth-600 dark:text-earth-400 hover:underline"
                            >
                              Cancel
                            </button>
                            <button
                              onClick={() => returnMutation.mutate({
                                borrowId: b.id,
                                rating: returnRating || undefined,
                                reviewText: returnReviewText.trim() || undefined,
                              })}
                              disabled={returnMutation.isPending}
                              className="flex items-center gap-1 px-4 py-1.5 text-xs bg-lsc-blue text-white rounded-lg hover:bg-lsc-blue/90 disabled:opacity-50"
                            >
                              {returnMutation.isPending ? (
                                <Loader2 className="h-3 w-3 motion-safe:animate-spin" />
                              ) : (
                                <RotateCcw className="h-3 w-3" />
                              )} Return Book
                            </button>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          )}
        </>
      ) : (
        /* History tab */
        <>
          {historyLoading ? (
            <div className="text-center py-16" role="status">
              <Loader2 className="h-8 w-8 motion-safe:animate-spin mx-auto text-lsc-dark/70 dark:text-lsc-cream/50" aria-hidden="true" />
              <span className="sr-only">Loading borrow history...</span>
            </div>
          ) : !history?.items?.length ? (
            <div className="text-center py-16 bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700">
              <History className="h-12 w-12 mx-auto text-earth-300 dark:text-earth-600 mb-4" aria-hidden="true" />
              <p className="text-earth-600 dark:text-earth-400">No borrow history yet</p>
            </div>
          ) : (
            <>
              <div className="space-y-4">
                {history.items.map((b: HistoryBorrow) => (
                  <div key={b.id} className="flex gap-4 bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-4">
                    {b.ebook_cover_url ? (
                      <img
                        src={b.ebook_cover_url}
                        alt={`Cover of ${b.ebook_title}`}
                        className="w-16 h-24 object-cover rounded-lg shrink-0"
                      />
                    ) : (
                      <div className="w-16 h-24 bg-earth-100 dark:bg-earth-700 rounded-lg shrink-0 flex items-center justify-center">
                        <BookOpen className="h-6 w-6 text-earth-600" aria-hidden="true" />
                      </div>
                    )}

                    <div className="flex-1 min-w-0">
                      <Link
                        to={`/indie/book/${generateSlug(b.ebook_title, b.ebook_id)}`}
                        className="font-medium text-lsc-dark dark:text-lsc-cream hover:text-lsc-blue truncate block"
                        title={b.ebook_title}
                      >
                        {b.ebook_title}
                      </Link>
                      <p className="text-sm text-earth-600 dark:text-earth-400">{b.author_pen_name}</p>

                      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 mt-2 text-xs text-earth-600 dark:text-earth-400">
                        <span>Borrowed {formatDate(b.borrowed_at)}</span>
                        <span>
                          {b.status === 'returned'
                            ? `Returned ${b.returned_at ? formatDate(b.returned_at) : ''}`
                            : 'Expired'}
                        </span>
                        {b.rating != null && (
                          <span className="flex items-center gap-0.5">
                            {Array.from({ length: 5 }, (_, i) => (
                              <Star
                                key={i}
                                className={`h-3 w-3 ${i < b.rating! ? 'text-status-warning-500 fill-status-warning-500' : 'text-earth-300 dark:text-earth-600'}`}
                              />
                            ))}
                          </span>
                        )}
                      </div>
                    </div>

                    <div className="shrink-0 self-center">
                      <StatusBadge variant={b.status === 'returned' ? 'success' : 'neutral'}>
                        {b.status === 'returned' ? 'Returned' : 'Expired'}
                      </StatusBadge>
                    </div>
                  </div>
                ))}
              </div>

              {/* Pagination */}
              {history.total > history.per_page && (
                <div className="flex justify-center gap-2 mt-6">
                  <button
                    onClick={() => setHistoryPage(p => Math.max(1, p - 1))}
                    disabled={historyPage <= 1}
                    className="px-3 py-1.5 text-sm border border-lsc-border dark:border-earth-600 rounded-lg hover:bg-earth-50 dark:hover:bg-earth-750 disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    Previous
                  </button>
                  <span className="px-3 py-1.5 text-sm text-earth-600 dark:text-earth-400">
                    Page {historyPage} of {Math.ceil(history.total / history.per_page)}
                  </span>
                  <button
                    onClick={() => setHistoryPage(p => p + 1)}
                    disabled={historyPage >= Math.ceil(history.total / history.per_page)}
                    className="px-3 py-1.5 text-sm border border-lsc-border dark:border-earth-600 rounded-lg hover:bg-earth-50 dark:hover:bg-earth-750 disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    Next
                  </button>
                </div>
              )}
            </>
          )}
        </>
      )}
    </PageContainer>
  )
}

// Embeddable version for Account page tab
export function IndieBorrowsTab() {
  const { t } = useTranslation();
  const [now] = useState(() => Date.now())
  const queryClient = useQueryClient()

  const { data: borrows, isLoading } = useQuery<ActiveBorrow[]>({
    queryKey: ['indie-my-borrows'],
    queryFn: () => api.get(`${API_BASE}/indie/lending/borrows/active`),
    staleTime: 30_000,
  })


  const returnMutation = useMutation({
    mutationFn: ({ borrowId, rating, reviewText }: { borrowId: number; rating?: number; reviewText?: string }) =>
      api.post(`${API_BASE}/indie/lending/borrows/${borrowId}/return`, {
        ...(rating ? { rating } : {}),
        ...(reviewText ? { review_text: reviewText } : {}),
      }),
    onSuccess: () => {
      toast.success(t('toast.indieMyBorrows.bookReturned'))
      queryClient.invalidateQueries({ queryKey: ['indie-my-borrows'] })
    },
    onError: (err: unknown) => {
      toast.error(err instanceof Error ? err.message : t('toast.indieMyBorrows.failedToReturnBook'))
    },
  })

  const renewMutation = useMutation({
    mutationFn: (borrowId: number) =>
      api.post(`${API_BASE}/indie/lending/borrows/${borrowId}/renew`, {}),
    onSuccess: () => {
      toast.success('Borrow renewed for 21 more days')
      queryClient.invalidateQueries({ queryKey: ['indie-my-borrows'] })
    },
    onError: (err: unknown) => {
      toast.error(err instanceof Error ? err.message : 'Failed to renew borrow')
    },
  })

  const daysLeft = (due: string) => {
    const d = Math.ceil((new Date(due).getTime() - now) / (1000 * 60 * 60 * 24))
    return d
  }

  if (isLoading) {
    return <div className="flex justify-center py-12" role="status"><Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-dark/70 dark:text-lsc-cream/70" aria-hidden="true" /><span className="sr-only">Loading indie borrows...</span></div>
  }

  if (!borrows?.length) {
    return (
      <div className="text-center py-12">
        <BookOpen className="h-10 w-10 mx-auto text-earth-300 dark:text-earth-600 mb-3" aria-hidden="true" />
        <p className="text-earth-600 dark:text-earth-400 mb-2">{t('indieMyBorrows.noBorrowedIndieBooks2')}</p>
        <Link to="/indie" className="text-lsc-blue hover:underline text-sm">Browse indie catalog</Link>
      </div>
    )
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="font-serif text-xl font-bold text-lsc-dark dark:text-lsc-cream">Indie Books</h2>
        <Link to="/indie/my-borrows" className="text-sm text-lsc-blue hover:underline">View all</Link>
      </div>
      <div className="space-y-3">
        {borrows.map((b) => {
          const days = daysLeft(b.due_at)
          const overdue = days < 0
          return (

            <div key={b.id} className="flex items-center gap-3 bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700 p-3">
              {b.ebook_cover_url ? (
                <img src={b.ebook_cover_url} alt={`Cover of ${b.ebook_title}`} className="w-10 h-14 object-cover rounded shrink-0" />
              ) : (
                <div className="w-10 h-14 bg-earth-100 dark:bg-earth-700 rounded shrink-0 flex items-center justify-center">
                  <BookOpen className="h-4 w-4 text-earth-600" aria-hidden="true" />
                </div>
              )}
              <div className="flex-1 min-w-0">
                <Link to={`/indie/book/${generateSlug(b.ebook_title, b.ebook_id)}`} className="text-sm font-medium text-lsc-dark dark:text-lsc-cream hover:text-lsc-blue truncate block" title={b.ebook_title}>
                  {b.ebook_title}
                </Link>
                <p className="text-xs text-earth-600">{b.author_pen_name}</p>
                <p className={`text-xs mt-0.5 ${overdue ? 'text-status-danger-600 dark:text-status-danger-400' : 'text-earth-600'}`}>
                  {overdue ? `Overdue by ${Math.abs(days)}d` : `${days}d left`}
                </p>
              </div>
              <div className="flex flex-col gap-1 shrink-0">
                {b.can_renew && (
                  <button
                    onClick={() => renewMutation.mutate(b.id)}
                    disabled={renewMutation.isPending}
                    aria-label={`Renew ${b.ebook_title}`}
                    className="text-xs px-2 py-1 border border-lsc-border dark:border-earth-600 rounded hover:bg-earth-50 dark:hover:bg-earth-750 flex items-center gap-1"
                  >
                    {renewMutation.isPending && renewMutation.variables === b.id ? (
                      <Loader2 className="h-3 w-3 motion-safe:animate-spin" />
                    ) : (
                      <RefreshCw className="h-3 w-3" />
                    )} Renew
                  </button>
                )}
                <button
                  onClick={() => returnMutation.mutate({ borrowId: b.id })}
                  disabled={returnMutation.isPending}
                  aria-label={`Return ${b.ebook_title}`}
                  className="text-xs px-2 py-1 border border-lsc-border dark:border-earth-600 rounded hover:bg-earth-50 dark:hover:bg-earth-750 flex items-center gap-1"
                >
                  {returnMutation.isPending && returnMutation.variables?.borrowId === b.id ? (
                    <Loader2 className="h-3 w-3 motion-safe:animate-spin" />
                  ) : (
                    <RotateCcw className="h-3 w-3" />
                  )} Return
                </button>
              </div>
            </div>

  )
        })}
      </div>
    </div>
  )
}
