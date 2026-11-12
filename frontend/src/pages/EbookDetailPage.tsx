/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * MetisLib Ebook Detail Page
 * Full detail view with borrow/hold actions
 */
import { useState, useEffect } from 'react'
import { useParams, Link, useSearchParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  BookOpen,
  Loader2,
  AlertCircle,
  CheckCircle,
  Clock,
  Download,
  Share2,
  ArrowLeft,
  Globe,
  Feather,
  Star,
  BookMarked,
  ShoppingCart,
} from 'lucide-react'
import toast from 'react-hot-toast'
import { clsx } from '@/utils/helpers'
import { penNameToSlug } from '@/api/indie-catalog-api'
import { useAuth } from '@/contexts/AuthContext'
import {
  getMetisLibEbook,
  getMyMetisLibCheckouts,
  borrowMetisLibEbook,
  placeMetisLibHold,
  getMetisLibHoldStatus,
  leaveMetisLibHold,
  getMetisLibDownloadUrl,
  overflowPurchase,
} from '@/api/domains/catalog/metislib-api'
import { useTranslation} from '@/i18n'
import { clean } from '@/lib/utils'
import { useBranding } from '@/contexts/BrandingContext'
import PageContainer from '@/components/layout/PageContainer'

export default function EbookDetailPage(): React.ReactElement {
  const branding = useBranding()
  const { t } = useTranslation()
  const { id } = useParams<{ id: string }>()
  const [searchParams] = useSearchParams()
  const entryType = searchParams.get('entry_type') as 'ebook' | 'indie_ebook' | null
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const [coverFailed, setCoverFailed] = useState(false)

  const { data: ebook, isLoading, error } = useQuery({
    queryKey: ['metislib-ebook', id, entryType],
    queryFn: () => getMetisLibEbook(Number(id), entryType || undefined),
    enabled: !!id,
  })

  const { data: myCheckouts } = useQuery({
    queryKey: ['metislib-checkouts'],
    queryFn: getMyMetisLibCheckouts,
    enabled: !!user,
  })
  const activeCheckout = myCheckouts?.find((c) => c.ebook_id === Number(id))
  const alreadyBorrowed = !!activeCheckout

  const { data: holdStatus } = useQuery({
    queryKey: ['metislib-hold-status', id],
    queryFn: () => getMetisLibHoldStatus(Number(id)),
    enabled: !!user && !!id && !alreadyBorrowed,
  })
  const onHold = holdStatus?.on_hold === true
  const holdReady = onHold && holdStatus?.status === 'ready'

  const borrowMutation = useMutation({
    mutationFn: () => borrowMetisLibEbook(Number(id)),
    onSuccess: (data) => {
      toast.success(t('toast.ebookDetail.ebookBorrowedSuccessfully'))
      queryClient.invalidateQueries({ queryKey: ['metislib-ebook', id] })
      queryClient.invalidateQueries({ queryKey: ['metislib-checkouts'] })
      if (data.download_url) {
        toast.success(t('ebookDetail.yourDownloadIsReady'), { duration: 6000 })
      }
    },
    onError: (err: { userMessage?: string; message?: string }) => {
      toast.error(err.userMessage || t('toast.indie.failedToBorrowEbook'))
    },
  })

  const [downloading, setDownloading] = useState(false)

  const handleDownload = async (accessId?: number) => {
    const downloadId = accessId || borrowMutation.data?.access_id
    if (!downloadId) return
    setDownloading(true)
    try {
      const data = await getMetisLibDownloadUrl(downloadId)
      if ('provider' in data) {
        // LCP license — save as .lcpl file
        const blob = new Blob([JSON.stringify(data)], { type: 'application/vnd.readium.lcp.license.v1.0+json' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `${ebook?.title || 'ebook'}.lcpl`
        a.click()
        URL.revokeObjectURL(url)
        toast.success('License downloaded! Open with Thorium Reader or any LCP-compatible app.', { duration: 6000 })
      } else if (data.download_url) {
        window.open(data.download_url, '_blank', 'noopener,noreferrer')
      }
    } catch {
      toast.error(t('toast.ebookDetail.failedToGetDownload'))
    } finally {
      setDownloading(false)
    }
  }

  const holdMutation = useMutation({
    mutationFn: () => placeMetisLibHold(Number(id)),
    onSuccess: (data) => {
      toast.success(t('toast.ebookDetail.holdPlacedYourePositionIn', { position: data.position }))
      queryClient.invalidateQueries({ queryKey: ['metislib-ebook', id] })
      queryClient.invalidateQueries({ queryKey: ['metislib-hold-status', id] })
    },
    onError: (err: { userMessage?: string; message?: string }) => {
      toast.error(err.userMessage || t('toast.holdFailed'))
    },
  })

  const leaveHoldMutation = useMutation({
    mutationFn: () => leaveMetisLibHold(Number(id)),
    onSuccess: () => {
      toast.success(t('toast.ebookDetail.holdLeft'))
      queryClient.invalidateQueries({ queryKey: ['metislib-hold-status', id] })
      queryClient.invalidateQueries({ queryKey: ['metislib-ebook', id] })
    },
    onError: (err: { userMessage?: string; message?: string }) => {
      toast.error(err.userMessage || t('toast.ebookDetail.holdLeaveFailed'))
    },
  })

  const buyMutation = useMutation({
    mutationFn: () => overflowPurchase(Number(id)),
    onSuccess: (data) => {
      if (data.checkout_url) {
        window.location.href = data.checkout_url
      }
    },
    onError: (err: { userMessage?: string; message?: string }) => {
      toast.error(err.userMessage || t('toast.ebookDetail.purchaseUnavailableRightNow'))
    },
  })

  const handleShare = async () => {
    const url = window.location.href
    if (navigator.share) {
      try {
        await navigator.share(clean({
          title: ebook?.title,
          text: `Check out "${ebook?.title}" by ${ebook?.author_name}`,
          url,
        }))
      } catch {
        // User cancelled
      }
    } else {
      await navigator.clipboard.writeText(url)
      toast.success(t('ebookDetail.linkCopiedToClipboard'))
    }
  }

  useEffect(() => {
    if (ebook) {
      document.title = `${ebook.title} | eBooks | ${branding.library_short_name}`
    }
    return () => { document.title = branding.library_name }
  }, [ebook])

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]" role="status" aria-live="polite">
        <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" aria-hidden="true" />
        <span className="sr-only">{t('common.loading', 'Loading…')}</span>
      </div>
    )
  }

  if (error || !ebook) {
    return (
      <PageContainer className="py-16 text-center">
        <AlertCircle className="w-16 h-16 mx-auto mb-4 text-status-danger-500" />
        <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-2">
          eBook Not Found
        </h1>
        <p className="text-earth-600 dark:text-earth-400 mb-4">
          This eBook may have been removed or is temporarily unavailable.
        </p>
        <Link to="/ebooks" className="text-lsc-rose hover:underline">
          Browse eBooks
        </Link>
      </PageContainer>
    )
  }

  const isOpenAccess = ebook.source_type === 'open_access'
  // Treat unknown copy counts as available so borrowing is never wrongly hidden.
  const isAvailable = (ebook.available_copies ?? 1) > 0
  const sourceLabel = isOpenAccess ? 'Public Domain' : 'Indie Author'
  const sourceColor = isOpenAccess
    ? 'bg-earth-100 text-lsc-rose dark:bg-earth-800 dark:text-lsc-rose-light/80'
    : 'bg-category-100 text-category-700 dark:bg-category-900 dark:text-category-200'
  const SourceIcon = isOpenAccess ? Globe : Feather

  return (
    <PageContainer className="py-8 space-y-8">
      {/* Breadcrumb */}
      <nav className="flex items-center gap-2 text-sm text-earth-600 dark:text-earth-400">
        <Link to="/ebooks" className="flex items-center gap-1 hover:text-lsc-rose transition-colors">
          <ArrowLeft className="w-4 h-4" />
          eBooks
        </Link>
        <span>/</span>
        <span className="text-lsc-dark dark:text-lsc-cream truncate" title={ebook.title}>{ebook.title}</span>
      </nav>

      {/* Main Content */}
      <div className="grid md:grid-cols-3 gap-8">
        {/* Cover Column */}
        <div className="space-y-4">
          <div className="aspect-[2/3] bg-lsc-cream dark:bg-lsc-brown rounded-xl overflow-hidden shadow-lg">
            {ebook.cover_url && !coverFailed ? (
              <img
                src={ebook.cover_url}
                alt={`Cover of ${ebook.title}`}
                className="w-full h-full object-cover"
                onError={() => setCoverFailed(true)}
              />
            ) : (
              <div className="w-full h-full flex items-center justify-center">
                <BookOpen className="w-24 h-24 text-lsc-rose/30" />
              </div>
            )}
          </div>

          {/* Action Buttons */}
          <div className="space-y-2">
            {isOpenAccess ? (
              <button
                onClick={() => borrowMutation.mutate()}
                disabled={borrowMutation.isPending || !user}
                className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-lsc-rose text-white rounded-lg font-medium hover:bg-lsc-rose/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {borrowMutation.isPending ? (
                  <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
                ) : (
                  <Download className="w-4 h-4" />
                )}
                {user ? 'Read Now' : 'Sign in to read'}
              </button>
            ) : alreadyBorrowed ? (
              <button
                onClick={() => handleDownload(activeCheckout?.access_id)}
                disabled={downloading}
                className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-status-success-600 text-white rounded-lg font-medium hover:bg-status-success-700 disabled:opacity-50 transition-colors"
              >
                {downloading ? (
                  <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
                ) : (
                  <Download className="w-4 h-4" />
                )}
                Read &mdash; you have this checked out
              </button>
            ) : (
              <>
                {isAvailable ? (
                  <button
                    onClick={() => borrowMutation.mutate()}
                    disabled={borrowMutation.isPending || !user}
                    className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-lsc-rose text-white rounded-lg font-medium hover:bg-lsc-rose/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    {borrowMutation.isPending ? (
                      <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
                    ) : (
                      <BookMarked className="w-4 h-4" />
                    )}
                    {user ? 'Borrow' : 'Sign in to borrow'}
                  </button>
                ) : onHold ? (
                  <div className="space-y-2">
                    <div
                      role="status"
                      aria-live="polite"
                      className="rounded-lg border border-lsc-border dark:border-earth-600 bg-earth-50 dark:bg-earth-800 px-4 py-3 text-center"
                    >
                      {holdReady ? (
                        <p className="text-sm font-medium text-status-success-700 dark:text-status-success-400">
                          {t('ebookDetail.holdReady')}
                        </p>
                      ) : (
                        <>
                          <p className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
                            {t('ebookDetail.holdPositionInLine', { position: holdStatus?.position ?? 0 })}
                          </p>
                          {typeof holdStatus?.total_waiting === 'number' && (
                            <p className="text-xs text-earth-600 dark:text-earth-400 mt-0.5">
                              {t('ebookDetail.holdWaitingCount', { count: holdStatus.total_waiting })}
                            </p>
                          )}
                        </>
                      )}
                    </div>
                    {holdReady && (
                      <button
                        onClick={() => borrowMutation.mutate()}
                        disabled={borrowMutation.isPending || !user}
                        className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-lsc-rose text-white rounded-lg font-medium hover:bg-lsc-rose/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                      >
                        {borrowMutation.isPending ? (
                          <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
                        ) : (
                          <BookMarked className="w-4 h-4" />
                        )}
                        Borrow
                      </button>
                    )}
                    <button
                      onClick={() => leaveHoldMutation.mutate()}
                      disabled={leaveHoldMutation.isPending}
                      className="w-full flex items-center justify-center gap-2 px-4 py-2.5 border border-lsc-border dark:border-earth-600 text-lsc-dark/70 dark:text-lsc-cream/70 rounded-lg font-medium hover:bg-earth-50 dark:hover:bg-earth-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                      {leaveHoldMutation.isPending ? (
                        <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
                      ) : (
                        <Clock className="w-4 h-4" />
                      )}
                      {t('ebookDetail.leaveHold')}
                    </button>
                  </div>
                ) : (
                  <>
                    <button
                      onClick={() => holdMutation.mutate()}
                      disabled={holdMutation.isPending || !user}
                      className="w-full flex items-center justify-center gap-2 px-4 py-2.5 border border-lsc-border dark:border-earth-600 text-lsc-dark/70 dark:text-lsc-cream/70 rounded-lg font-medium hover:bg-earth-50 dark:hover:bg-earth-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                      {holdMutation.isPending ? (
                        <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
                      ) : (
                        <Clock className="w-4 h-4" />
                      )}
                      Place Hold
                    </button>
                    {user && (
                      <div className="space-y-1.5">
                        <button
                          onClick={() => buyMutation.mutate()}
                          disabled={buyMutation.isPending}
                          className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-emerald-600 text-white rounded-lg font-medium hover:bg-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                        >
                          {buyMutation.isPending ? (
                            <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
                          ) : (
                            <ShoppingCart className="w-4 h-4" />
                          )}
                          Buy Now &mdash; $15
                        </button>
                        <p className="text-xs text-earth-600 dark:text-earth-400 text-center">
                          Skip the wait &mdash; buy your own copy
                        </p>
                      </div>
                    )}
                  </>
                )}
              </>
            )}
            {borrowMutation.isSuccess && borrowMutation.data?.access_id && !alreadyBorrowed && (
              <button
                onClick={() => handleDownload()}
                disabled={downloading}
                className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-status-success-600 text-white rounded-lg font-medium hover:bg-status-success-700 disabled:opacity-50 transition-colors"
              >
                {downloading ? (
                  <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
                ) : (
                  <Download className="w-4 h-4" />
                )}
                Download Ebook
              </button>
            )}
            <button
              onClick={handleShare}
              className="w-full flex items-center justify-center gap-2 px-4 py-2.5 border border-lsc-border dark:border-earth-600 text-lsc-dark/70 dark:text-lsc-cream/70 rounded-lg font-medium hover:bg-earth-50 dark:hover:bg-earth-700 transition-colors"
            >
              <Share2 className="w-4 h-4" />
              Share
            </button>
          </div>

          {!user && (
            <p className="text-xs text-earth-600 dark:text-earth-400 text-center">
              <Link to="/login" className="text-lsc-rose hover:underline">Sign in</Link> to borrow ebooks
            </p>
          )}
        </div>

        {/* Detail Column */}
        <div className="md:col-span-2 space-y-6">
          {/* Title & Author */}
          <div>
            <h1 className="font-serif text-2xl font-bold text-lsc-dark dark:text-lsc-cream leading-tight">
              {ebook.title}
            </h1>
            <p className="text-lg text-earth-600 dark:text-earth-400 mt-1">
              by{' '}
              {ebook.entry_type === 'indie_ebook' ? (
                <Link
                  to={`/indie/author/${penNameToSlug(ebook.author_name)}`}
                  className="text-lsc-rose hover:underline"
                >
                  {ebook.author_name}
                </Link>
              ) : (
                ebook.author_name
              )}
            </p>
          </div>

          {/* Badges */}
          <div className="flex items-center gap-2 flex-wrap">
            <span className={clsx('inline-flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full font-medium', sourceColor)}>
              <SourceIcon className="w-3.5 h-3.5" />
              {sourceLabel}
            </span>
            <span className="text-xs px-2.5 py-1 rounded-full bg-earth-100 text-earth-600 dark:bg-earth-700 dark:text-earth-300 font-medium uppercase">
              {ebook.format}
            </span>
            {ebook.language && (
              <span className="text-xs px-2.5 py-1 rounded-full bg-earth-100 text-earth-600 dark:bg-earth-700 dark:text-earth-300 font-medium uppercase">
                {ebook.language}
              </span>
            )}
            {ebook.average_rating && (
              <span className="inline-flex items-center gap-1 text-xs px-2.5 py-1 rounded-full bg-status-warning-100 text-status-warning-700 dark:bg-status-warning-900 dark:text-status-warning-200 font-medium">
                <Star className="w-3.5 h-3.5 fill-current" />
                {ebook.average_rating.toFixed(1)}
                <span className="text-status-warning-600 dark:text-status-warning-300">({ebook.total_ratings})</span>
              </span>
            )}
          </div>

          {/* Description */}
          {ebook.description && (
            <div>
              <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-2">
                About this book
              </h2>
              <p className="text-lsc-dark/70 dark:text-lsc-cream/70 leading-relaxed">
                {ebook.description}
              </p>
            </div>
          )}

          {/* Details Table */}
          <div className="bg-lsc-cream/50 dark:bg-earth-800 rounded-xl p-5">
            <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-3">
              Details
            </h2>
            <dl className="grid grid-cols-2 gap-x-8 gap-y-3 text-sm">
              <div>
                <dt className="text-earth-600 dark:text-earth-400">Format</dt>
                <dd className="font-medium text-lsc-dark dark:text-lsc-cream uppercase">{ebook.format}</dd>
              </div>
              {ebook.language && (
                <div>
                  <dt className="text-earth-600 dark:text-earth-400">Language</dt>
                  <dd className="font-medium text-lsc-dark dark:text-lsc-cream uppercase">{ebook.language}</dd>
                </div>
              )}
              {ebook.isbn && (
                <div>
                  <dt className="text-earth-600 dark:text-earth-400">ISBN</dt>
                  <dd className="font-medium text-lsc-dark dark:text-lsc-cream">{ebook.isbn}</dd>
                </div>
              )}
              {ebook.page_count && (
                <div>
                  <dt className="text-earth-600 dark:text-earth-400">Pages</dt>
                  <dd className="font-medium text-lsc-dark dark:text-lsc-cream">{ebook.page_count}</dd>
                </div>
              )}
              <div>
                <dt className="text-earth-600 dark:text-earth-400">Source</dt>
                <dd className="font-medium text-lsc-dark dark:text-lsc-cream">{sourceLabel}</dd>
              </div>
              <div>
                <dt className="text-earth-600 dark:text-earth-400">Type</dt>
                <dd className="font-medium text-lsc-dark dark:text-lsc-cream capitalize">{(ebook.entry_type ?? '').replace('_', ' ')}</dd>
              </div>
            </dl>
          </div>

          {/* Availability notice for open access */}
          {isOpenAccess && (
            <div className="flex items-start gap-3 bg-earth-50 dark:bg-earth-800/20 border border-lsc-border dark:border-earth-700 rounded-xl p-4">
              <CheckCircle className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-medium text-earth-800 dark:text-lsc-rose-light/80">Free to read</p>
                <p className="text-sm text-lsc-rose dark:text-lsc-rose-light mt-0.5">
                  This is a public domain work. You can read it anytime, no limits.
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </PageContainer>
  )
}
