/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Smart CTA panel for indie ebook detail page.
 * Renders different actions based on patron type, borrow state, and buy-now status.
 */
import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import {
  BookMarked,
  BookOpen,
  CheckCircle,
  Clock,
  Heart,
  Loader2,
  RotateCcw,
  ShoppingCart,
  TrendingUp,
} from 'lucide-react'
import { clsx } from '@/utils/helpers'
import { useTranslation} from '@/i18n'
import { useAuth } from '@/contexts/AuthContext'
import {
  borrowEbook,
  getActiveBorrows,
  returnEbook,
  joinWaitlist,
  placeIndieHold,
  getPatronType,
  getBuyNowStatus,
  purchaseDigitalAccess,
  type IndieEbookPublic,
} from '@/api/indie-catalog-api'
import toast from 'react-hot-toast'
import BookPreviewModal from './BookPreviewModal'

interface EbookActionPanelProps {
  book: IndieEbookPublic
  readingPercent?: number
}

// eslint-disable-next-line complexity
export default function EbookActionPanel({ book, readingPercent }: EbookActionPanelProps) {
  const { t } = useTranslation()
  const { user } = useAuth()
  const queryClient = useQueryClient()

  const isAvailable = (book.available_copies ?? 0) > 0
  const [showPreview, setShowPreview] = useState(false)

  // The L30 IndieEbook PK is the universal lending key (borrow/reader/return all
  // use it). available on the public book as indie_ebook_id; fall back to id.
  const pk = book.indie_ebook_id ?? book.id

  // Get UTM params from URL
  const searchParams = new URLSearchParams(window.location.search)
  const utmSource = searchParams.get('utm_source') || 'direct'
  const utmMedium = searchParams.get('utm_medium') || 'web'
  const utmCampaign = searchParams.get('utm_campaign') || ''

  const patronQuery = useQuery({
    queryKey: ['indie', 'patron-type'],
    queryFn: getPatronType,
    enabled: !!user,
  })

  const buyNowQuery = useQuery({
    queryKey: ['indie', 'buy-now-status', book.id],
    queryFn: () => getBuyNowStatus(book.id),
  })

  // Does this patron already have THIS title out? Drives the borrowed-state CTA
  // (Read now + Return + due date) instead of an inert Borrow button.
  const activeBorrowsQuery = useQuery({
    queryKey: ['indie-active-borrows'],
    queryFn: getActiveBorrows,
    enabled: !!user,
  })
  const activeBorrow = activeBorrowsQuery.data?.find(
    (b) => (b.indie_ebook_id ?? b.ebook_id) === pk && b.status === 'active',
  )

  const borrowMutation = useMutation({
    mutationFn: borrowEbook,
    onSuccess: () => {
      toast.success(t('indieBookDetail.borrowSuccess'))
      // Refresh the detail (available_copies) and borrow-state queries so the
      // panel reflects the borrow instead of staying on the Borrow CTA.
      queryClient.invalidateQueries({ queryKey: ['indie-book'] })
      queryClient.invalidateQueries({ queryKey: ['indie-active-borrows'] })
      queryClient.invalidateQueries({ queryKey: ['user-borrow-status'] })
      queryClient.invalidateQueries({ queryKey: ['indie-reading-progress'] })
    },
    onError: (error: Error) => toast.error(error.message || t('toast.indie.failedToBorrowEbook')),
  })

  const returnMutation = useMutation({
    mutationFn: (borrowId: number) => returnEbook(borrowId),
    onSuccess: () => {
      toast.success(t('toast.indieMyBorrows.bookReturned'))
      queryClient.invalidateQueries({ queryKey: ['indie-book'] })
      queryClient.invalidateQueries({ queryKey: ['indie-active-borrows'] })
      queryClient.invalidateQueries({ queryKey: ['indie-my-borrows'] })
      queryClient.invalidateQueries({ queryKey: ['user-borrow-status'] })
    },
    onError: (error: Error) => toast.error(error.message || t('toast.indieMyBorrows.failedToReturnBook')),
  })

  const waitlistMutation = useMutation({
    mutationFn: joinWaitlist,
    onSuccess: () => toast.success(t('indieBookDetail.holdSuccess')),
    onError: (error: Error) => toast.error(error.message || t('toast.indie.failedToJoinWaitlist')),
  })

  const holdMutation = useMutation({
    mutationFn: (catalogItemId: number) => placeIndieHold(catalogItemId),
    onSuccess: () => {
      toast.success(t('toast.indie.holdPlacedSuccessfully'))
      queryClient.invalidateQueries({ queryKey: ['indie-ebook'] })
    },
    onError: (err: Error) => {
      toast.error(err.message || t('toast.holdFailed'))
    },
  })

  const purchaseMutation = useMutation({
    mutationFn: () => purchaseDigitalAccess(book.id, utmSource, utmMedium, utmCampaign),
    onSuccess: (data) => {
      const serial = data.collectible_card_serial ? ` Collectible card: ${data.collectible_card_serial}` : ''
      toast.success(t('toast.indie.purchaseCompleteserial', { serial: serial }))
    },
    onError: (error: Error) => toast.error(error.message || t('toast.indie.purchaseFailed')),
  })

  const isLoading =
    patronQuery.isLoading || buyNowQuery.isLoading || (!!user && activeBorrowsQuery.isLoading)
  const rawPatronType = user ? (patronQuery.data?.patron_type ?? 'resident_cardholder') : 'anonymous'
  // getPatronType() is a stub that returns 'anonymous' for everyone (indie patron
  // tiering was removed 2026-04-21), so the `?? 'resident_cardholder'` fallback
  // above never fires for a logged-in patron. A logged-in patron IS a borrowing
  // cardholder: collapse any authenticated value to resident_cardholder so they
  // get the Borrow button. Only a true anonymous visitor gets the sign-in CTA.
  // Without this, every logged-in patron saw 'Sign in to Borrow' -> /login -> /account.
  const patronType =
    !user
      ? 'anonymous'
      : rawPatronType === 'out_of_county_subscriber'
        ? 'out_of_county_subscriber'
        : 'resident_cardholder'
  const showBuyNow = buyNowQuery.data?.show_buy_now ?? false
  const price = buyNowQuery.data?.price ?? 20
  const demandLevel = buyNowQuery.data?.demand_level ?? 'none'
  const demandProgress = buyNowQuery.data?.demand_progress ?? 0

  const dueInDays = activeBorrow
    ? Math.ceil((new Date(activeBorrow.due_at).getTime() - Date.now()) / 86_400_000)
    : 0

  if (isLoading) {
    return (
      <div className="bg-lsc-cream dark:bg-earth-800 rounded-xl p-4 flex items-center justify-center py-8">
        <Loader2 className="w-6 h-6 motion-safe:animate-spin text-lsc-rose" />
      </div>
    )
  }

  return (
    <div className="bg-lsc-cream dark:bg-earth-800 rounded-xl p-4">
      {/* Availability status */}
      <div className="flex items-center justify-between mb-3">
        {isAvailable ? (
          <span className="flex items-center gap-2 text-status-success-600 dark:text-status-success-400 font-medium">
            <CheckCircle className="w-5 h-5" aria-hidden="true" />
            {t('indieBookDetail.availableNow')}
          </span>
        ) : (
          <span className="flex items-center gap-2 text-status-warning-600 dark:text-status-warning-400 font-medium">
            <Clock className="w-5 h-5" aria-hidden="true" />
            {t('indieBookDetail.allCopiesOut')}
          </span>
        )}
        <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
          {book.available_copies}/{book.total_copies} {t('indieBookDetail.copies')}
        </span>
      </div>

      {/* Demand momentum indicator (only when not already borrowed) */}
      {!activeBorrow && demandLevel !== 'none' && (
        <div className="mb-3">
          <div className="flex items-center justify-between mb-1">
            <span className={clsx(
              'text-xs font-medium flex items-center gap-1',
              demandLevel === 'card_available'
                ? 'text-status-success-600 dark:text-status-success-400'
                : demandLevel === 'high'
                  ? 'text-status-warning-600 dark:text-status-warning-400'
                  : 'text-lsc-dark/70 dark:text-lsc-cream/60'
            )}>
              <TrendingUp className="w-3 h-3" aria-hidden="true" />
              {demandLevel === 'card_available'
                ? 'Card available'
                : demandLevel === 'high'
                  ? 'High demand'
                  : 'Growing interest'}
            </span>
          </div>
          <div className="w-full h-1.5 bg-lsc-dark/10 dark:bg-lsc-cream/10 rounded-full overflow-hidden">
            <div
              className={clsx(
                'h-full rounded-full transition-all duration-500',
                demandLevel === 'card_available'
                  ? 'bg-status-success-500'
                  : demandLevel === 'high'
                    ? 'bg-status-warning-500'
                    : 'bg-slate-400'
              )}
              style={{ width: `${Math.round(demandProgress * 100)}%` }}
              role="progressbar"
              aria-valuenow={Math.round(demandProgress * 100)}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-label={`Demand progress: ${Math.round(demandProgress * 100)}%`}
            />
          </div>
        </div>
      )}

      {activeBorrow ? (
        /* Borrowed state — patron already has this title out */
        <div className="space-y-3">
          <p className="flex items-center gap-1.5 text-sm">
            <Clock className="w-4 h-4 text-lsc-dark/60 dark:text-lsc-cream/60" aria-hidden="true" />
            {dueInDays < 0 ? (
              <span className="text-status-danger-600 dark:text-status-danger-400 font-medium">
                Overdue by {Math.abs(dueInDays)} day{Math.abs(dueInDays) !== 1 ? 's' : ''}
              </span>
            ) : dueInDays === 0 ? (
              <span className="text-status-warning-600 dark:text-status-warning-400 font-medium">Due today</span>
            ) : (
              <span className="text-lsc-dark/70 dark:text-lsc-cream/70">
                Due in {dueInDays} day{dueInDays !== 1 ? 's' : ''}
              </span>
            )}
          </p>
          <Link
            to={`/indie/read/${pk}`}
            state={{ title: book.title }}
            aria-label={`Read ${book.title} in your browser`}
            className="w-full py-3 bg-lsc-rose text-white rounded-xl font-medium hover:bg-lsc-rose/90 flex items-center justify-center gap-2"
          >
            <BookOpen className="w-5 h-5" aria-hidden="true" />
            {readingPercent && readingPercent > 0 ? `Continue reading (${readingPercent}%)` : 'Read now'}
          </Link>
          <button
            onClick={() => returnMutation.mutate(activeBorrow.id)}
            disabled={returnMutation.isPending}
            aria-label={`Return ${book.title}`}
            className="w-full py-2.5 text-sm border border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream rounded-xl font-medium hover:bg-lsc-white dark:hover:bg-earth-700 disabled:opacity-50 flex items-center justify-center gap-2"
          >
            {returnMutation.isPending ? (
              <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
            ) : (
              <RotateCcw className="w-4 h-4" aria-hidden="true" />
            )}
            Return
          </button>
        </div>
      ) : (
        <>
          {/* CTA buttons — vary by patron type */}
          {patronType === 'resident_cardholder' && (
            <>
              {isAvailable ? (
                <button
                  onClick={() => borrowMutation.mutate(pk)}
                  disabled={borrowMutation.isPending}
                  className="w-full py-3 bg-lsc-rose text-white rounded-xl font-medium hover:bg-lsc-rose/90 disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  {borrowMutation.isPending ? (
                    <Loader2 className="w-5 h-5 motion-safe:animate-spin" />
                  ) : (
                    <BookMarked className="w-5 h-5" aria-hidden="true" />
                  )}
                  {t('indieBookDetail.borrowFor', { days: String(book.borrow_duration_days) })}
                </button>
              ) : book.catalog_item_id ? (
                <button
                  onClick={() => holdMutation.mutate(book.catalog_item_id!)}
                  disabled={holdMutation.isPending}
                  className="w-full py-3 bg-lsc-rose text-white rounded-xl font-medium hover:bg-lsc-rose/90 disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  {holdMutation.isPending ? (
                    <Loader2 className="w-5 h-5 motion-safe:animate-spin" />
                  ) : (
                    <Clock className="w-5 h-5" aria-hidden="true" />
                  )}
                  {t('indieBookDetail.placeHold')}
                </button>
              ) : (
                <button
                  onClick={() => waitlistMutation.mutate(book.id)}
                  disabled={waitlistMutation.isPending}
                  className="w-full py-3 border-2 border-lsc-rose text-lsc-rose rounded-xl font-medium hover:bg-lsc-rose/10 disabled:opacity-50"
                >
                  {t('indieBookDetail.placeHold')}
                </button>
              )}

              {/* Secondary: Support the Author (only when Buy Now triggered and not available) */}
              {showBuyNow && !isAvailable && (
                <button
                  onClick={() => purchaseMutation.mutate()}
                  disabled={purchaseMutation.isPending}
                  className="w-full mt-3 py-2.5 text-sm border border-status-success-600/30 text-status-success-700 dark:text-status-success-400 rounded-xl hover:bg-status-success-50 dark:hover:bg-status-success-900/10 flex items-center justify-center gap-2"
                >
                  <Heart className="w-4 h-4" aria-hidden="true" />
                  {t('indieBookDetail.supportTheAuthor', { price: String(price) })}
                </button>
              )}
            </>
          )}

          {patronType === 'out_of_county_subscriber' && (
            <>
              {isAvailable ? (
                <button
                  onClick={() => borrowMutation.mutate(pk)}
                  disabled={borrowMutation.isPending}
                  className="w-full py-3 bg-lsc-rose text-white rounded-xl font-medium hover:bg-lsc-rose/90 disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  {borrowMutation.isPending ? (
                    <Loader2 className="w-5 h-5 motion-safe:animate-spin" />
                  ) : (
                    <BookMarked className="w-5 h-5" aria-hidden="true" />
                  )}
                  {t('indieBookDetail.borrowFor', { days: String(book.borrow_duration_days) })}
                </button>
              ) : (
                <>
                  {book.catalog_item_id ? (
                    <button
                      onClick={() => holdMutation.mutate(book.catalog_item_id!)}
                      disabled={holdMutation.isPending}
                      className="w-full py-3 bg-lsc-rose text-white rounded-xl font-medium hover:bg-lsc-rose/90 disabled:opacity-50 flex items-center justify-center gap-2"
                    >
                      {holdMutation.isPending ? (
                        <Loader2 className="w-5 h-5 motion-safe:animate-spin" />
                      ) : (
                        <Clock className="w-5 h-5" aria-hidden="true" />
                      )}
                      {t('indieBookDetail.placeHold')}
                    </button>
                  ) : (
                    <button
                      onClick={() => waitlistMutation.mutate(book.id)}
                      disabled={waitlistMutation.isPending}
                      className="w-full py-3 border-2 border-lsc-rose text-lsc-rose rounded-xl font-medium hover:bg-lsc-rose/10 disabled:opacity-50"
                    >
                      {t('indieBookDetail.placeHold')}
                    </button>
                  )}
                  {showBuyNow && (
                    <button
                      onClick={() => purchaseMutation.mutate()}
                      disabled={purchaseMutation.isPending}
                      className="w-full mt-3 py-3 bg-status-success-600 text-white rounded-xl font-medium hover:bg-status-success-700 disabled:opacity-50 flex items-center justify-center gap-2"
                    >
                      <ShoppingCart className="w-5 h-5" aria-hidden="true" />
                      {t('indieBookDetail.buyNow', { price: String(price) })}
                    </button>
                  )}
                </>
              )}
            </>
          )}

          {(patronType === 'anonymous') && (
            <>
              {showBuyNow ? (
                <>
                  <button
                    onClick={() => {
                      if (!user) {
                        toast.error(t('toast.indie.pleaseSignInToPurchase'))
                        return
                      }
                      purchaseMutation.mutate()
                    }}
                    disabled={purchaseMutation.isPending}
                    className="w-full py-3 bg-status-success-600 text-white rounded-xl font-medium hover:bg-status-success-700 disabled:opacity-50 flex items-center justify-center gap-2"
                  >
                    {purchaseMutation.isPending ? (
                      <Loader2 className="w-5 h-5 motion-safe:animate-spin" />
                    ) : (
                      <ShoppingCart className="w-5 h-5" aria-hidden="true" />
                    )}
                    {t('indieBookDetail.buyNow', { price: String(price) })}
                  </button>
                  <Link
                    to="/indie/vault/subscribe"
                    className="w-full mt-3 py-2.5 text-sm border border-lsc-rose text-lsc-rose rounded-xl font-medium text-center hover:bg-lsc-rose/10 block"
                  >
                    {t('indieBookDetail.subscribeForAccess')}
                  </Link>
                </>
              ) : (
                <Link
                  to="/login"
                  className="block w-full py-3 bg-lsc-rose text-white rounded-xl font-medium text-center hover:bg-lsc-rose/90"
                >
                  {t('indieBookDetail.signInToBorrow')}
                </Link>
              )}
            </>
          )}

          {/* Continue reading opens the in-browser reader (needs an active borrow);
              otherwise offer a sample. Read Sample is always available. */}
          {readingPercent && readingPercent > 0 ? (
            <Link
              to={`/indie/read/${pk}`}
              state={{ title: book.title }}
              className="w-full mt-3 py-2.5 text-sm bg-lsc-rose text-white rounded-xl font-medium hover:bg-lsc-rose/90 flex items-center justify-center gap-2"
            >
              <BookOpen className="w-4 h-4" aria-hidden="true" />
              Continue Reading ({readingPercent}%)
            </Link>
          ) : (
            <button
              onClick={() => setShowPreview(true)}
              className="w-full mt-3 py-2.5 text-sm border border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream rounded-xl font-medium hover:bg-lsc-cream dark:hover:bg-earth-700 flex items-center justify-center gap-2"
            >
              <BookOpen className="w-4 h-4" aria-hidden="true" />
              {t('indieBookDetail.readSample')}
            </button>
          )}
        </>
      )}

      {showPreview && (
        <BookPreviewModal ebookId={book.id} onClose={() => setShowPreview(false)} />
      )}
    </div>
  )
}
