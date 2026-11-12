/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { BookKey, BookOpen, CalendarClock, CheckCircle2, Loader2, LogIn, RefreshCw, XCircle } from 'lucide-react'
import toast from 'react-hot-toast'
import api from '@/lib/api-client'
import { ApiError } from '@/lib/api-client'
import { API_BASE } from '@/api/types'
import { friendlyErrorMessage } from '@/utils/friendlyError'
import { useAuth } from '@/contexts/AuthContext'
import { StatusBadge } from '@/components/ui/StatusBadge'
import type { StatusVariant } from '@/components/ui/StatusBadge'
import { useBranding } from '@/contexts/BrandingContext'
import PageContainer from '@/components/layout/PageContainer'

interface EbookCardTierInfo {
  tier: string
  display_name: string
  description?: string | null
  annual_fee: number
  max_concurrent_borrows: number
  max_monthly_borrows: number
  is_available: boolean
}

interface EbookCardResponse {
  id: number
  card_number: string
  tier: string
  status: string
  annual_fee: number
  starts_at?: string | null
  expires_at?: string | null
  max_concurrent_borrows: number
  max_monthly_borrows: number
  borrows_this_month: number
  total_borrows: number
  auto_renew: boolean
  can_borrow: boolean
  created_at?: string | null
}

const TIERS_KEY = ['ebook-card-tiers']
const MY_CARD_KEY = ['my-ebook-card']

function formatFee(fee: number): string {
  return `$${fee % 1 === 0 ? fee.toFixed(0) : fee.toFixed(2)}/year`
}

function formatDate(iso?: string | null): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
}

function statusVariant(status: string): StatusVariant {
  switch (status) {
    case 'active':
      return 'success'
    case 'expired':
    case 'cancelled':
    case 'canceled':
      return 'danger'
    case 'pending':
      return 'warning'
    default:
      return 'neutral'
  }
}

export default function IndieVaultSubscribePage() {
  const branding = useBranding()
  const { user } = useAuth()
  const queryClient = useQueryClient()

  useEffect(() => {
    document.title = 'Indie Vault Access Card'
    return () => { document.title = branding.library_name }
  }, [branding.library_name])

  const [autoRenew, setAutoRenew] = useState(false)
  const [confirmCancel, setConfirmCancel] = useState(false)

  const {
    data: tiers,
    isLoading: tiersLoading,
    isError: tiersError,
  } = useQuery<EbookCardTierInfo[]>({
    queryKey: TIERS_KEY,
    queryFn: () => api.get(`${API_BASE}/ebook-access-cards/tiers`),
    staleTime: 5 * 60_000,
  })

  const {
    data: card,
    isLoading: cardLoading,
    isError: cardError,
  } = useQuery<EbookCardResponse | null>({
    queryKey: MY_CARD_KEY,
    queryFn: () => api.get(`${API_BASE}/ebook-access-cards/my-card`),
    enabled: !!user,
    staleTime: 30_000,
  })

  const hasActiveCard = card?.status === 'active'

  const purchaseMutation = useMutation({
    mutationFn: (tier: string) =>
      api.post<EbookCardResponse>(`${API_BASE}/ebook-access-cards/purchase`, {
        tier,
        auto_renew: autoRenew,
      }),
    onSuccess: () => {
      toast.success('Your Indie Vault access card is active.')
      queryClient.invalidateQueries({ queryKey: MY_CARD_KEY })
    },
    onError: (err: unknown) => {
      if (err instanceof ApiError && err.status === 409) {
        toast('You already have an active card.')
        queryClient.invalidateQueries({ queryKey: MY_CARD_KEY })
        return
      }
      toast.error(friendlyErrorMessage(err))
    },
  })

  const cancelMutation = useMutation({
    mutationFn: () =>
      api.post<{ message: string; expires_at: string }>(`${API_BASE}/ebook-access-cards/my-card/cancel`),
    onSuccess: () => {
      toast.success('Auto-renew turned off. Your card stays active until it expires.')
      queryClient.invalidateQueries({ queryKey: MY_CARD_KEY })
      setConfirmCancel(false)
    },
    onError: (err: unknown) => {
      toast.error(friendlyErrorMessage(err))
    },
  })

  const renewMutation = useMutation({
    mutationFn: (tier?: string) =>
      api.post<EbookCardResponse>(`${API_BASE}/ebook-access-cards/my-card/renew`, tier ? { tier } : {}),
    onSuccess: () => {
      toast.success('Your card has been renewed.')
      queryClient.invalidateQueries({ queryKey: MY_CARD_KEY })
    },
    onError: (err: unknown) => {
      toast.error(friendlyErrorMessage(err))
    },
  })

  const availableTiers = tiers?.filter(t => t.is_available) ?? []

  return (
    <PageContainer width="form" className="py-8">
      <div className="mb-6">
        <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream flex items-center gap-2">
          <BookKey className="h-6 w-6" aria-hidden="true" /> Indie Vault Access Card
        </h1>
        <p className="mt-2 text-earth-600 dark:text-earth-400">
          Borrow indie ebooks from authors who publish directly to the library. One card, the whole vault.
        </p>
      </div>

      {/* Loading state */}
      {(tiersLoading || (!!user && cardLoading)) ? (
        <div className="text-center py-16" role="status">
          <Loader2 className="h-8 w-8 motion-safe:animate-spin mx-auto text-lsc-dark/70 dark:text-lsc-cream/50" aria-hidden="true" />
          <span className="sr-only">Loading access card options...</span>
        </div>
      ) : tiersError ? (
        <div className="text-center py-16 bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700">
          <XCircle className="h-12 w-12 mx-auto text-status-danger-500 mb-4" aria-hidden="true" />
          <p className="text-earth-600 dark:text-earth-400">We could not load access card options right now. Please try again in a moment.</p>
        </div>
      ) : !availableTiers.length ? (
        <div className="text-center py-16 bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700">
          <BookOpen className="h-12 w-12 mx-auto text-earth-300 dark:text-earth-600 mb-4" aria-hidden="true" />
          <p className="text-earth-600 dark:text-earth-400">Indie Vault access cards are not available right now. Please check back soon.</p>
        </div>
      ) : (
        <>
          {/* Manage view: active card */}
          {!!user && hasActiveCard && card ? (
            <section
              aria-labelledby="manage-card-heading"
              className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-6"
            >
              <div className="flex items-start justify-between gap-4 flex-wrap">
                <div>
                  <h2 id="manage-card-heading" className="font-serif text-xl font-bold text-lsc-dark dark:text-lsc-cream">
                    Your access card
                  </h2>
                  <p className="text-sm text-earth-600 dark:text-earth-400 mt-1">
                    Card <span className="font-mono">{card.card_number}</span> &middot; {card.tier}
                  </p>
                </div>
                <StatusBadge variant={statusVariant(card.status)}>{card.status}</StatusBadge>
              </div>

              <dl className="grid grid-cols-2 sm:grid-cols-3 gap-4 mt-6 text-sm">
                <div>
                  <dt className="text-earth-600 dark:text-earth-400 flex items-center gap-1">
                    <CalendarClock className="h-4 w-4" aria-hidden="true" /> Expires
                  </dt>
                  <dd className="text-lsc-dark dark:text-lsc-cream font-medium mt-0.5">{formatDate(card.expires_at)}</dd>
                </div>
                <div>
                  <dt className="text-earth-600 dark:text-earth-400">Borrows this month</dt>
                  <dd className="text-lsc-dark dark:text-lsc-cream font-medium mt-0.5">{card.borrows_this_month}</dd>
                </div>
                <div>
                  <dt className="text-earth-600 dark:text-earth-400">Total borrows</dt>
                  <dd className="text-lsc-dark dark:text-lsc-cream font-medium mt-0.5">{card.total_borrows}</dd>
                </div>
                <div>
                  <dt className="text-earth-600 dark:text-earth-400">Concurrent limit</dt>
                  <dd className="text-lsc-dark dark:text-lsc-cream font-medium mt-0.5">{card.max_concurrent_borrows}</dd>
                </div>
                <div>
                  <dt className="text-earth-600 dark:text-earth-400">Borrowing</dt>
                  <dd className="mt-0.5">
                    {card.can_borrow ? (
                      <span className="text-status-success-600 dark:text-status-success-400 font-medium flex items-center gap-1">
                        <CheckCircle2 className="h-4 w-4" aria-hidden="true" /> Available
                      </span>
                    ) : (
                      <span className="text-status-danger-600 dark:text-status-danger-400 font-medium flex items-center gap-1">
                        <XCircle className="h-4 w-4" aria-hidden="true" /> Limit reached
                      </span>
                    )}
                  </dd>
                </div>
                <div>
                  <dt className="text-earth-600 dark:text-earth-400">Auto-renew</dt>
                  <dd className="text-lsc-dark dark:text-lsc-cream font-medium mt-0.5">{card.auto_renew ? 'On' : 'Off'}</dd>
                </div>
              </dl>

              <div className="flex flex-wrap gap-3 mt-6 pt-6 border-t border-lsc-border dark:border-earth-700">
                <Link
                  to="/indie/my-borrows"
                  className="inline-flex items-center gap-1.5 px-4 py-2 text-sm bg-lsc-rose text-white rounded-xl hover:bg-lsc-rose/90"
                >
                  <BookOpen className="h-4 w-4" aria-hidden="true" /> Browse the vault
                </Link>
                <button
                  type="button"
                  onClick={() => renewMutation.mutate(card.tier)}
                  disabled={renewMutation.isPending}
                  className="inline-flex items-center gap-1.5 px-4 py-2 text-sm border border-lsc-border dark:border-earth-600 rounded-xl hover:bg-earth-50 dark:hover:bg-earth-750 text-earth-600 dark:text-earth-400 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {renewMutation.isPending ? (
                    <Loader2 className="h-4 w-4 motion-safe:animate-spin" aria-hidden="true" />
                  ) : (
                    <RefreshCw className="h-4 w-4" aria-hidden="true" />
                  )} Renew
                </button>
                {confirmCancel ? (
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => cancelMutation.mutate()}
                      disabled={cancelMutation.isPending}
                      className="inline-flex items-center gap-1.5 px-4 py-2 text-sm bg-status-danger-600 text-white rounded-xl hover:bg-status-danger-700 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {cancelMutation.isPending ? (
                        <Loader2 className="h-4 w-4 motion-safe:animate-spin" aria-hidden="true" />
                      ) : (
                        <XCircle className="h-4 w-4" aria-hidden="true" />
                      )} Confirm cancel
                    </button>
                    <button
                      type="button"
                      onClick={() => setConfirmCancel(false)}
                      className="px-3 py-2 text-sm text-earth-600 dark:text-earth-400 hover:underline"
                    >
                      Keep card
                    </button>
                  </div>
                ) : (
                  <button
                    type="button"
                    onClick={() => setConfirmCancel(true)}
                    className="inline-flex items-center gap-1.5 px-4 py-2 text-sm border border-lsc-border dark:border-earth-600 rounded-xl hover:bg-earth-50 dark:hover:bg-earth-750 text-earth-600 dark:text-earth-400"
                  >
                    Cancel auto-renew
                  </button>
                )}
              </div>
              {confirmCancel && (
                <p className="text-xs text-earth-600 dark:text-earth-400 mt-3">
                  Cancelling turns off auto-renew. Your card stays usable until it expires.
                </p>
              )}
            </section>
          ) : (
            /* Subscribe view: tiers */
            <div className="space-y-4">
              {cardError && !!user && (
                <p className="text-sm text-status-warning-600 dark:text-status-warning-400">
                  We could not check your current card. You can still review the options below.
                </p>
              )}
              {availableTiers.map((tier) => (
                <section
                  key={tier.tier}
                  aria-labelledby={`tier-${tier.tier}-heading`}
                  className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-6"
                >
                  <div className="flex items-start justify-between gap-4 flex-wrap">
                    <div>
                      <h2 id={`tier-${tier.tier}-heading`} className="font-serif text-xl font-bold text-lsc-dark dark:text-lsc-cream">
                        {tier.display_name}
                      </h2>
                      {tier.description && (
                        <p className="text-sm text-earth-600 dark:text-earth-400 mt-1">{tier.description}</p>
                      )}
                    </div>
                    <p className="text-lg font-semibold text-lsc-rose whitespace-nowrap">{formatFee(tier.annual_fee)}</p>
                  </div>

                  <ul className="mt-4 space-y-1.5 text-sm text-earth-600 dark:text-earth-400">
                    <li className="flex items-center gap-2">
                      <CheckCircle2 className="h-4 w-4 text-lsc-rose shrink-0" aria-hidden="true" />
                      {tier.max_concurrent_borrows} books out at once
                    </li>
                    <li className="flex items-center gap-2">
                      <CheckCircle2 className="h-4 w-4 text-lsc-rose shrink-0" aria-hidden="true" />
                      {tier.max_monthly_borrows} borrows per month
                    </li>
                  </ul>

                  <div className="mt-6 pt-6 border-t border-lsc-border dark:border-earth-700">
                    {!user ? (
                      <Link
                        to="/login"
                        state={{ from: '/indie/vault/subscribe' }}
                        className="inline-flex items-center gap-1.5 px-5 py-2.5 text-sm bg-lsc-rose text-white rounded-xl hover:bg-lsc-rose/90"
                      >
                        <LogIn className="h-4 w-4" aria-hidden="true" /> Log in to subscribe
                      </Link>
                    ) : (
                      <>
                        <label className="flex items-center gap-2 text-sm text-earth-600 dark:text-earth-400 mb-4 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={autoRenew}
                            onChange={(e) => setAutoRenew(e.target.checked)}
                            className="rounded border-lsc-border dark:border-earth-600 text-lsc-rose focus:ring-lsc-rose"
                          />
                          Renew this card automatically each year
                        </label>
                        <button
                          type="button"
                          onClick={() => purchaseMutation.mutate(tier.tier)}
                          disabled={purchaseMutation.isPending}
                          className="inline-flex items-center gap-1.5 px-5 py-2.5 text-sm bg-lsc-rose text-white rounded-xl hover:bg-lsc-rose/90 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          {purchaseMutation.isPending && purchaseMutation.variables === tier.tier ? (
                            <Loader2 className="h-4 w-4 motion-safe:animate-spin" aria-hidden="true" />
                          ) : (
                            <BookKey className="h-4 w-4" aria-hidden="true" />
                          )} Get your card
                        </button>
                      </>
                    )}
                  </div>
                </section>
              ))}
            </div>
          )}
        </>
      )}
    </PageContainer>
  )
}
