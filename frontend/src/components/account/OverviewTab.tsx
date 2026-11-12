/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Book, Clock, DollarSign, AlertCircle, Loader2, RefreshCw, BookMarked, BookOpen, ClipboardList, ChevronRight, MapPin, CheckCircle, CircleAlert } from 'lucide-react'
import { ContextualHelp } from '../ContextualHelp'
import { Link } from 'react-router-dom'
import { useTranslation, getCurrentLocale } from '@/i18n'
import type { Checkout, Hold } from '../../services/api'
import type { EbookBorrow } from '@/api/indie-catalog-api'
import type { MetisLibCheckout } from '@/api/domains/catalog/metislib-api'
import type { MyEventRegistration, FinesSummary } from '../../services/api'
import { PendingSurveysWidget } from '../engagement/PendingSurveysWidget'

const GENRE_LABELS: Record<string, string> = {
  fiction: 'Fiction',
  mystery: 'Mystery & Thriller',
  'sci-fi': 'Sci-Fi & Fantasy',
  romance: 'Romance',
  biography: 'Biography & Memoir',
  history: 'History',
  children: "Children's",
  art: 'Art & Design',
  travel: 'Travel & Culture',
  science: 'Science & Nature',
  adventure: 'Action & Adventure',
  music: 'Music & Film',
}

type UnifiedCheckoutItem =
  | { type: 'library'; data: Checkout }
  | { type: 'indie'; data: EbookBorrow }
  | { type: 'metislib'; data: MetisLibCheckout }

// Per-variant accessors so callers don't have to repeat narrowing logic.
// MetisLibCheckout uses `expires_at` (not due_at) and `access_id` (not id), and
// `title` (not ebook_title).
function getCheckoutDueDate(item: UnifiedCheckoutItem): string | null | undefined {
  switch (item.type) {
    case 'library': return item.data.due_date
    case 'indie':   return item.data.due_at
    case 'metislib': return item.data.expires_at
  }
}

function getCheckoutKey(item: UnifiedCheckoutItem): string {
  switch (item.type) {
    case 'library': return `lib-${item.data.id}`
    case 'indie':   return `indie-${item.data.id}`
    case 'metislib': return `metislib-${item.data.access_id}`
  }
}

function getCheckoutTitle(item: UnifiedCheckoutItem): string {
  switch (item.type) {
    case 'library': return item.data.item_title ?? ''
    case 'indie':   return item.data.ebook_title
    case 'metislib': return item.data.title
  }
}

function getDaysUntilDue(dueDate: string | null | undefined): number {
  if (!dueDate) return Infinity
  const due = new Date(dueDate)
  const now = new Date()
  return Math.ceil((due.getTime() - now.getTime()) / (1000 * 60 * 60 * 24))
}

interface OverviewTabProps {
  user: { first_name: string; onboarding_completed_at?: string | null; is_active?: boolean; patron_status?: string; card_expires_at?: string | null }
  checkouts: Checkout[]
  indieBorrows: EbookBorrow[]
  holds: Hold[]
  finesSummary: FinesSummary
  myEvents: MyEventRegistration[]
  unifiedCheckouts: UnifiedCheckoutItem[]
  checkoutsLoading: boolean
  indieBorrowsLoading: boolean
  holdsLoading: boolean
  eventsLoading: boolean
  onboardingStatus?: { preferred_genres?: string[] | null }
  onSetTab: (tab: string) => void
  onRenew: (id: number) => void
  renewingId: number | null
  formatDate: (dateStr: string) => string
  isOverdue: (dueDate: string) => boolean
}

export function OverviewTab({
  user,
  checkouts: _checkouts,
  indieBorrows: _indieBorrows,
  holds,
  finesSummary,
  myEvents,
  unifiedCheckouts,
  checkoutsLoading,
  indieBorrowsLoading,
  holdsLoading,
  eventsLoading,
  onboardingStatus,
  onSetTab,
  onRenew,
  renewingId,
  formatDate,
  isOverdue,
}: OverviewTabProps): React.ReactElement {
  const { t } = useTranslation()

  const readyHolds = holds.filter(h => h.status === 'ready')
  const pendingHolds = holds.filter(h => h.status === 'pending')
  const outstandingFines = Number(finesSummary.total_outstanding ?? 0)
  const totalPaid = Number(finesSummary.total_paid ?? 0)
  const paidCount = Number(finesSummary.paid_count ?? 0)
  const cardExpired = user.card_expires_at ? new Date(user.card_expires_at) < new Date() : false
  const accountRestricted = !user.is_active || ['suspended', 'blocked'].includes(user.patron_status?.toLowerCase() ?? '')
  const needsEligibilityHelp = accountRestricted || cardExpired || outstandingFines > 0

  // Items due in the next 7 days (and overdue), sorted by urgency
  const dueSoonItems = unifiedCheckouts
    .filter(item => {
      const days = getDaysUntilDue(getCheckoutDueDate(item))
      return days <= 7
    })
    .sort((a, b) => {
      const dateA = getCheckoutDueDate(a)
      const dateB = getCheckoutDueDate(b)
      return new Date(dateA ?? 0).getTime() - new Date(dateB ?? 0).getTime()
    })

  return (
    <div>
      {user?.onboarding_completed_at && (
        <section className="bg-lsc-cream/50 dark:bg-lsc-brown/20 rounded-xl p-4 md:p-6 border border-lsc-rose/20 dark:border-lsc-rose/10 mb-6">
          <div className="flex items-baseline justify-between mb-4">
            <h2 className="font-serif font-bold text-base md:text-lg text-lsc-dark dark:text-lsc-cream">
              {t('home.welcome.greeting', { name: user.first_name })}
            </h2>
            <Link
              to="/account/preferences"
              className="text-xs text-sage-800 dark:text-lsc-rose-light font-medium hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose rounded px-2 py-1"
            >
              {t('home.welcome.customize')} →
            </Link>
          </div>

          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
            <button
              onClick={() => onSetTab('holds')}
              className="flex items-center gap-2 p-3 rounded-lg bg-lsc-white dark:bg-earth-800 border border-transparent hover:border-lsc-rose dark:hover:border-lsc-rose motion-safe:transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose focus-visible:ring-offset-2"
            >
              <ClipboardList className="w-4 h-4 text-sage-700 dark:text-lsc-rose flex-shrink-0" aria-hidden="true" />
              <span className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
                {t('home.welcome.myHolds')}
              </span>
            </button>

            <button
              onClick={() => onSetTab('checkouts')}
              className="flex items-center gap-2 p-3 rounded-lg bg-lsc-white dark:bg-earth-800 border border-transparent hover:border-lsc-rose dark:hover:border-lsc-rose motion-safe:transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose focus-visible:ring-offset-2"
            >
              <RefreshCw className="w-4 h-4 text-sage-700 dark:text-lsc-rose flex-shrink-0" aria-hidden="true" />
              <span className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
                {t('home.welcome.renewItems')}
              </span>
            </button>

            {onboardingStatus?.preferred_genres?.slice(0, 2).map((genre) => (
              <Link
                key={genre}
                to={`/catalog?genre=${encodeURIComponent(genre)}`}
                className="flex items-center gap-2 p-3 rounded-lg bg-lsc-white dark:bg-earth-800 border border-transparent hover:border-lsc-rose dark:hover:border-lsc-rose motion-safe:transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose focus-visible:ring-offset-2"
              >
                <BookOpen className="w-4 h-4 text-sage-700 dark:text-lsc-rose flex-shrink-0" aria-hidden="true" />
                <span className="text-sm font-medium text-lsc-dark dark:text-lsc-cream truncate" title={GENRE_LABELS[genre] || genre}>
                  {GENRE_LABELS[genre] || genre}
                </span>
              </Link>
            ))}
          </div>
        </section>
      )}

      <PendingSurveysWidget />

      <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-6">{t('account.accountOverview')}</h2>

      <section
        aria-labelledby="hold-eligibility-heading"
        className={`mb-6 rounded-xl border p-4 ${
          needsEligibilityHelp
            ? 'border-status-warning-300 bg-status-warning-50/60 dark:border-status-warning-700 dark:bg-status-warning-900/10'
            : 'border-status-success-300 bg-status-success-50/60 dark:border-status-success-700 dark:bg-status-success-900/10'
        }`}
      >
        <div className="flex items-start gap-3">
          {needsEligibilityHelp ? (
            <CircleAlert className="mt-0.5 h-5 w-5 shrink-0 text-status-warning-700 dark:text-status-warning-300" aria-hidden="true" />
          ) : (
            <CheckCircle className="mt-0.5 h-5 w-5 shrink-0 text-status-success-700 dark:text-status-success-300" aria-hidden="true" />
          )}
          <div className="min-w-0">
            <h3 id="hold-eligibility-heading" className="font-semibold text-lsc-dark dark:text-lsc-cream">Hold eligibility</h3>
            {accountRestricted ? (
              <p className="mt-1 text-sm text-lsc-dark/80 dark:text-lsc-cream/80">Your account needs staff assistance before you can place holds. Please contact the library.</p>
            ) : cardExpired ? (
              <p className="mt-1 text-sm text-lsc-dark/80 dark:text-lsc-cream/80">Your library card has expired. Please contact the library to renew it before placing holds.</p>
            ) : outstandingFines > 0 ? (
              <p className="mt-1 text-sm text-lsc-dark/80 dark:text-lsc-cream/80">You have an outstanding balance that may affect borrowing or holds. Review it before placing a hold.</p>
            ) : (
              <p className="mt-1 text-sm text-lsc-dark/80 dark:text-lsc-cream/80">Your account is ready to place holds.</p>
            )}
            {outstandingFines > 0 && !accountRestricted && !cardExpired && (
              <button onClick={() => onSetTab('my-data')} className="mt-3 text-sm font-semibold text-lsc-rose hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose rounded">Review fines</button>
            )}
          </div>
        </div>
      </section>

      {/* === ACTION DASHBOARD: 3 glanceable cards === */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">

        {/* -- Items Due Soon Card -- */}
        <div className={`rounded-xl border-2 p-4 ${
          dueSoonItems.some(item => {
            const d = getCheckoutDueDate(item)
            return d ? isOverdue(d) : false
          })
            ? 'border-status-danger-300 dark:border-status-danger-700 bg-status-danger-50/50 dark:bg-status-danger-900/10'
            : dueSoonItems.length > 0
              ? 'border-status-warning-300 dark:border-status-warning-700 bg-status-warning-50/50 dark:bg-status-warning-900/10'
              : 'border-sage/20 dark:border-earth-700 bg-sage/5 dark:bg-sage/10'
        }`}>
          <div className="flex items-center gap-2 mb-3">
            <Book className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" aria-hidden="true" />
            <h3 className="font-semibold text-sm text-lsc-dark dark:text-lsc-cream">{t('account.itemsDueSoonCard')}</h3>
          </div>
          {(checkoutsLoading && indieBorrowsLoading) ? (
            <div role="status" className="flex items-center gap-2">
              <Loader2 className="w-4 h-4 motion-safe:animate-spin text-lsc-dark/70 dark:text-lsc-cream/60" />
              <span className="sr-only">{t('account.loadingCheckouts')}</span>
            </div>
          ) : dueSoonItems.length === 0 ? (
            <div className="flex items-center gap-2">
              <CheckCircle className="w-5 h-5 text-status-success-600 dark:text-status-success-400" aria-hidden="true" />
              <span className="text-sm text-status-success-700 dark:text-status-success-300">{t('account.nothingDueSoon')}</span>
            </div>
          ) : (
            <div className="space-y-2">
              {dueSoonItems.slice(0, 4).map(item => {
                const isLibrary = item.type === 'library'
                const key = getCheckoutKey(item)
                const title = getCheckoutTitle(item)
                const dueDate = getCheckoutDueDate(item)
                const days = getDaysUntilDue(dueDate)
                const overdue = days < 0
                const dueToday = days === 0
                const dueTomorrow = days === 1

                return (
                  <div key={key} className="flex items-center justify-between gap-2">
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-lsc-dark dark:text-lsc-cream truncate" title={title ?? undefined}>
                        {title}
                      </p>
                      <p className={`text-xs font-medium ${
                        overdue ? 'text-status-danger-600 dark:text-status-danger-400' :
                        (dueToday || dueTomorrow) ? 'text-status-warning-600 dark:text-status-warning-400' :
                        'text-lsc-dark/70 dark:text-lsc-cream/60'
                      }`}>
                        {overdue ? t('account.overdue') : dueToday ? t('account.dueToday') : dueTomorrow ? t('account.dueTomorrow') : dueDate ? t('account.dueDate', { date: formatDate(dueDate) }) : t('account.noDueDate')}
                      </p>
                    </div>
                    {isLibrary && (
                      <button
                        onClick={() => onRenew(item.data.id)}
                        disabled={renewingId === item.data.id}
                        className="flex-shrink-0 px-2.5 py-1 text-xs font-medium bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 transition-colors disabled:opacity-50 flex items-center gap-1 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose focus-visible:ring-offset-2"
                      >
                        {renewingId === item.data.id ? (
                          <Loader2 className="w-3 h-3 motion-safe:animate-spin" />
                        ) : (
                          <RefreshCw className="w-3 h-3" />
                        )}
                        {t('account.renew')}
                      </button>
                    )}
                  </div>
                )
              })}
              {dueSoonItems.length > 4 && (
                <button
                  onClick={() => onSetTab('checkouts')}
                  className="text-xs text-lsc-rose hover:text-lsc-rose/80 font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose focus-visible:ring-offset-2 rounded"
                >
                  +{dueSoonItems.length - 4} more...
                </button>
              )}
            </div>
          )}
        </div>

        {/* -- Holds Ready Card -- */}
        <div className={`rounded-xl border-2 p-4 ${
          readyHolds.length > 0
            ? 'border-status-success-300 dark:border-status-success-700 bg-status-success-50/50 dark:bg-status-success-900/10'
            : 'border-sage/20 dark:border-earth-700 bg-sage/5 dark:bg-sage/10'
        }`}>
          <div className="flex items-center gap-2 mb-3">
            <Clock className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" aria-hidden="true" />
            <h3 className="font-semibold text-sm text-lsc-dark dark:text-lsc-cream">{t('account.holdsCard')}</h3>
          </div>
          {holdsLoading ? (
            <div role="status" className="flex items-center gap-2">
              <Loader2 className="w-4 h-4 motion-safe:animate-spin text-lsc-dark/70 dark:text-lsc-cream/60" />
              <span className="sr-only">{t('account.loadingHolds')}</span>
            </div>
          ) : readyHolds.length > 0 ? (
            <div className="space-y-2">
              {readyHolds.map(hold => (
                <div key={hold.id} className="flex items-start gap-2">
                  <CheckCircle className="w-4 h-4 text-status-success-600 dark:text-status-success-400 mt-0.5 flex-shrink-0" aria-hidden="true" />
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-lsc-dark dark:text-lsc-cream truncate" title={hold.item_title ?? undefined}>
                      {hold.item_title}
                    </p>
                    <p className="text-xs text-status-success-700 dark:text-status-success-300">
                      {t('account.readyForPickup')}
                      {hold.expires_at && <span> - {t('account.pickUpBy', { date: formatDate(hold.expires_at) })}</span>}
                    </p>
                  </div>
                </div>
              ))}
              {pendingHolds.length > 0 && (
                <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60 mt-1">
                  {t('account.holdsPendingCount', { count: pendingHolds.length })}
                </p>
              )}
              <button
                onClick={() => onSetTab('holds')}
                className="text-xs text-lsc-rose hover:text-lsc-rose/80 font-medium flex items-center gap-1 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose focus-visible:ring-offset-2 rounded"
              >
                {t('account.viewAllHolds')} <ChevronRight className="w-3 h-3" />
              </button>
            </div>
          ) : pendingHolds.length > 0 ? (
            <div>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                {t('account.noHoldsReadyForPickup')}
              </p>
              <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60 mt-1">
                {t('account.holdsPendingCount', { count: pendingHolds.length })}
              </p>
              <button
                onClick={() => onSetTab('holds')}
                className="text-xs text-lsc-rose hover:text-lsc-rose/80 font-medium flex items-center gap-1 mt-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose focus-visible:ring-offset-2 rounded"
              >
                {t('account.viewAllHolds')} <ChevronRight className="w-3 h-3" />
              </button>
            </div>
          ) : (
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{t('account.noActiveHolds')}</p>
          )}
        </div>

        {/* -- Fines/Fees Card -- */}
        <div className={`rounded-xl border-2 p-4 ${
          outstandingFines > 0
            ? 'border-status-danger-300 dark:border-status-danger-700 bg-status-danger-50/50 dark:bg-status-danger-900/10'
            : 'border-sage/20 dark:border-earth-700 bg-sage/5 dark:bg-sage/10'
        }`}>
          <div className="flex items-center gap-2 mb-3">
            <DollarSign className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" aria-hidden="true" />
            <h3 className="font-semibold text-sm text-lsc-dark dark:text-lsc-cream">{t('account.finesAndFeesCard')}</h3>
          </div>
          {outstandingFines > 0 ? (
            <div>
              <p className="text-2xl font-bold text-status-danger-600 dark:text-status-danger-400">
                ${outstandingFines.toFixed(2)}
              </p>
              <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60 mt-1">
                {t('account.outstandingFinesCount', { count: finesSummary.outstanding_count })}
              </p>
              <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60 mt-1">
                {t('account.payAtBranchOrPhone')}
              </p>
            </div>
          ) : (
            <div>
              <div className="flex items-center gap-2">
                <CheckCircle className="w-5 h-5 text-status-success-600 dark:text-status-success-400" aria-hidden="true" />
                <span className="text-sm text-status-success-700 dark:text-status-success-300">{t('account.noOutstandingFees')}</span>
              </div>
              {paidCount > 0 && totalPaid > 0 && (
                <p className="text-xs text-lsc-dark/50 dark:text-lsc-cream/40 mt-2">
                  {t('account.finesPaidSummary', { amount: totalPaid.toFixed(2), count: paidCount })}
                </p>
              )}
            </div>
          )}
        </div>
      </div>

      {outstandingFines > 0 && (
        <div className="mb-8">
          <ContextualHelp
            type="stuck"
            title="Questions about fines?"
            message="Fines accrue for overdue items. You can pay at any branch, by phone, or reduce fines through our Read to Reduce program."
            actionLabel="Get help"
            actionUrl="/help"
          />
        </div>
      )}

      {/* === E-books quick link === */}
      <div className="mb-8">
        <button
          onClick={() => onSetTab('ebooks')}
          className="flex items-center gap-4 p-4 bg-lsc-rose/5 dark:bg-lsc-rose/10 rounded-xl border border-lsc-rose/20 hover:border-lsc-rose/40 transition-colors text-left w-full focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose focus-visible:ring-offset-2"
        >
          <BookMarked className="w-8 h-8 text-lsc-rose flex-shrink-0" />
          <div>
            <p className="font-semibold text-lsc-dark dark:text-lsc-cream">{t('account.myEbooks')}</p>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/60">{t('account.viewAllBorrowedEbooks')}</p>
          </div>
          <ChevronRight className="w-5 h-5 text-lsc-rose/50 ml-auto" />
        </button>
      </div>

      {/* === Recent Checkouts (full list) === */}
      <div className="space-y-6">
        <div>
          <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-3">{t('account.recentCheckouts')}</h3>
          {(checkoutsLoading && indieBorrowsLoading) ? (
            <div role="status"><Loader2 className="w-6 h-6 motion-safe:animate-spin text-lsc-dark/70 dark:text-lsc-cream/70" /><span className="sr-only">{t('account.loadingCheckouts')}</span></div>
          ) : unifiedCheckouts.length === 0 ? (
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('account.noActiveCheckouts')}</p>
          ) : (
            <div className="space-y-2">
              {unifiedCheckouts.slice(0, 3).map(item => {
                const key = item.type === 'library'
                  ? `lib-${item.data.id}`
                  : item.type === 'metislib'
                    ? `ml-${item.data.access_id}`
                    : `indie-${item.data.id}`
                const title = item.type === 'library'
                  ? item.data.item_title
                  : item.type === 'metislib'
                    ? item.data.title
                    : item.data.ebook_title
                const dueDate = item.type === 'library'
                  ? item.data.due_date
                  : item.type === 'metislib'
                    ? item.data.expires_at
                    : item.data.due_at
                return (
                  <div key={key} className="flex items-center justify-between p-3 bg-cream dark:bg-earth-800 rounded-xl">
                    <div className="flex items-center gap-2">
                      <span className={`text-[10px] font-semibold uppercase px-1.5 py-0.5 rounded-full ${
                        item.type === 'library'
                          ? 'bg-status-info-100 text-status-info-800 dark:bg-status-info-900/50 dark:text-status-info-300'
                          : 'bg-category-100 text-category-800 dark:bg-category-900/50 dark:text-category-300'
                      }`}>
                        {item.type === 'library' ? t('account.book') : t('account.ebook')}
                      </span>
                      <div>
                        <p className="font-medium text-lsc-dark dark:text-lsc-cream">{title}</p>
                        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                          {dueDate
                            ? t('account.due', { date: formatDate(dueDate) })
                            : t('account.noDueDate')}
                        </p>
                      </div>
                    </div>
                    {dueDate && isOverdue(dueDate) && (
                      <AlertCircle className="w-5 h-5 text-status-danger-600" />
                    )}
                  </div>
                )
              })}
            </div>
          )}
        </div>

        <div>
          <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-3">{t('account.activeHolds')}</h3>
          {holdsLoading ? (
            <div role="status"><Loader2 className="w-6 h-6 motion-safe:animate-spin text-lsc-dark/70 dark:text-lsc-cream/70" /><span className="sr-only">{t('account.loadingHolds')}</span></div>
          ) : holds.length === 0 ? (
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('account.noActiveHolds')}</p>
          ) : (
            <div className="space-y-2">
              {holds.slice(0, 3).map(hold => (
                <div key={hold.id} className="flex items-center justify-between p-3 bg-cream dark:bg-earth-800 rounded-xl">
                  <div>
                    <p className="font-medium text-lsc-dark dark:text-lsc-cream">{hold.item_title}</p>
                    <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                      {hold.status === 'ready' ? t('account.readyForPickup') : t('account.position', { position: hold.position })}
                    </p>
                  </div>
                  <span className={`px-2 py-1 text-xs rounded-full ${
                    hold.status === 'ready' ? 'bg-status-success-100 text-status-success-800 dark:bg-status-success-900/30 dark:text-status-success-300' : 'bg-status-warning-500/20 text-status-warning-600 dark:bg-status-warning-900/30 dark:text-status-warning-300'
                  }`}>
                    {hold.status === 'ready' ? t('account.holdStatusReady') : t('account.holdStatusPending')}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        {myEvents.length > 0 && (
          <div>
            <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-3">{t('account.myUpcomingEvents')}</h3>
            {eventsLoading ? (
              <div role="status"><Loader2 className="w-6 h-6 motion-safe:animate-spin text-lsc-dark/70 dark:text-lsc-cream/70" /><span className="sr-only">{t('account.loadingEvents')}</span></div>
            ) : (
              <div className="space-y-2">
                {myEvents.slice(0, 4).map((reg) => {
                  const eventDate = new Date(reg.event_start_time ?? '')
                  const now = new Date()
                  const diffDays = Math.ceil((eventDate.getTime() - now.getTime()) / (1000 * 60 * 60 * 24))
                  const isToday = diffDays === 0
                  const isTomorrow = diffDays === 1

                  return (
                    <a
                      key={reg.id}
                      href={`/events/${reg.event_id}`}
                      className={`flex items-center gap-4 p-3 rounded-xl bg-lsc-cream/50 dark:bg-earth-700/50 hover:bg-lsc-cream dark:hover:bg-earth-700 transition-colors ${
                        isToday ? 'ring-2 ring-lsc-rose' : ''
                      }`}
                    >
                      <div className={`text-center flex-shrink-0 rounded-xl p-2 min-w-[48px] ${
                        isToday ? 'bg-lsc-rose text-white' : 'bg-lsc-cream dark:bg-earth-700'
                      }`}>
                        <span className={`text-xs font-medium ${isToday ? 'text-white/90' : 'text-lsc-rose'}`}>
                          {eventDate.toLocaleDateString(getCurrentLocale(), { month: 'short' })}
                        </span>
                        <span className={`block text-lg font-bold ${isToday ? 'text-white' : 'text-lsc-dark dark:text-lsc-cream'}`}>
                          {eventDate.getDate()}
                        </span>
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-lsc-dark dark:text-lsc-cream truncate" title={reg.event_title}>
                          {reg.event_title}
                        </p>
                        <div className="flex items-center gap-3 text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                          <span className="flex items-center gap-1">
                            <Clock className="w-3 h-3" />
                            {eventDate.toLocaleTimeString(getCurrentLocale(), { hour: 'numeric', minute: '2-digit' })}
                          </span>
                          {reg.event_location && (
                            <span className="flex items-center gap-1 truncate" title={reg.event_location}>
                              <MapPin className="w-3 h-3 flex-shrink-0" />
                              <span className="truncate">{reg.event_location}</span>
                            </span>
                          )}
                          <span className={`px-2 py-0.5 rounded-full font-medium ${
                            isToday ? 'bg-lsc-rose/20 text-lsc-rose' :
                            isTomorrow ? 'bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-700 dark:text-status-warning-300' :
                            'bg-lsc-cream dark:bg-earth-600 text-lsc-dark/70 dark:text-lsc-cream/60'
                          }`}>
                            {isToday ? t('account.today') : isTomorrow ? t('account.tomorrow') : t('account.inDays', { count: diffDays })}
                          </span>
                        </div>
                      </div>
                      <ChevronRight className="w-4 h-4 text-lsc-dark/30 flex-shrink-0" />
                    </a>
                  )
                })}
              </div>
            )}
            {myEvents.length > 4 && (
              <a
                href="/events"
                className="block text-center text-sm text-lsc-rose hover:text-lsc-rose/80 py-2"
              >
                {t('account.viewAllRegisteredEvents', { count: myEvents.length })}
              </a>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
