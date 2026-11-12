/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import { useState, useEffect } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { Link } from 'react-router-dom'
import {
  BookOpen, BarChart3, Clock, TrendingUp, Library,
  Star, Award, Loader2, ArrowRight,
} from 'lucide-react'
import { useTranslation } from '@/i18n'
import { fetchApi } from '@/api/fetchApi'
import PageContainer from '@/components/layout/PageContainer'

interface PatronStats {
  total_checkouts: number
  active_checkouts: number
  total_holds: number
  overdue_count: number
  fines_balance: number
}

interface ReadingSummary {
  books_read_this_year: number
  books_read_all_time: number
  favorite_genre: string | null
  reading_streak_days: number
  avg_books_per_month: number | null
}

export default function PatronReportsDashboardPage(): React.ReactElement {
  const { t } = useTranslation()
  const { user, token } = useAuth()
  const [isLoading, setIsLoading] = useState(true)
  const [stats, setStats] = useState<PatronStats | null>(null)
  const [readingSummary, setReadingSummary] = useState<ReadingSummary | null>(null)
  const [loadError, setLoadError] = useState(false)

  const loadData = async () => {
    setIsLoading(true)
    setLoadError(false)

    try {
      const [accountRes, checkoutsRes, holdsRes, insightsRes] = await Promise.allSettled([
        fetchApi('/patron/account'),
        fetchApi('/circulation/checkouts'),
        fetchApi('/circulation/holds'),
        fetchApi('/reading/insights/summary'),
      ])

      let accountOk = false
      let insightsOk = false

      // Build stats from account balance + checkout/hold counts
      // /patron/account serializes balance as a string (Decimal). Coerce to a
      // number so the `fines_balance > 0` guard and `.toFixed(2)` below don't
      // crash the page for any patron with a non-zero balance.
      const finesBalance = accountRes.status === 'fulfilled'
        ? Number(accountRes.value?.balance ?? 0) || 0
        : 0
      // /circulation/checkouts and /holds return { data: [...] }, not a bare
      // array — Array.isArray() on the envelope was false, so every count fell
      // to 0 even when the patron had checkouts/holds. Unwrap .data.
      const unwrap = (v: unknown): unknown[] => {
        if (Array.isArray(v)) return v
        const d = (v as { data?: unknown } | null)?.data
        return Array.isArray(d) ? d : []
      }
      const activeCheckouts = (checkoutsRes.status === 'fulfilled' ? unwrap(checkoutsRes.value) : []) as Array<{ is_overdue?: boolean; status?: string }>
      const activeHolds = holdsRes.status === 'fulfilled' ? unwrap(holdsRes.value) : []

      setStats({
        total_checkouts: activeCheckouts.length,
        active_checkouts: activeCheckouts.length,
        total_holds: activeHolds.length,
        // checkout objects carry status:'overdue', not an is_overdue flag
        overdue_count: activeCheckouts.filter((c) => c.is_overdue || c.status === 'overdue').length,
        fines_balance: finesBalance,
      })
      accountOk = activeCheckouts.length > 0 || finesBalance > 0 || true

      if (insightsRes.status === 'fulfilled') {
        try {
          const data = insightsRes.value
          setReadingSummary({
            books_read_this_year: data.total_books_this_year ?? 0,
            books_read_all_time: data.total_books_all_time ?? 0,
            favorite_genre: data.favorite_genre ?? null,
            reading_streak_days: data.current_streak_days ?? 0,
            avg_books_per_month: data.avg_books_per_month ?? null,
          })
          insightsOk = true
        } catch (e) {
          Sentry.captureException(e instanceof Error ? e : new Error(String(e)))
        }
      }

      if (!accountOk && !insightsOk) {
        setLoadError(true)
      }
    } catch (error) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
      setLoadError(true)
    } finally {
      setIsLoading(false)
    }
  }


  useEffect(() => {
    if (!user || !token) return
    loadData()

  }, [user, token])

  if (!user) {
    return (
      <div className="p-8 text-center">
        <p className="text-earth-600 dark:text-earth-400">
          {t('patronReports.loginRequired', 'Please log in to view your reports.')}
        </p>
        <Link to="/login" className="text-library-600 hover:underline mt-2 inline-block">Log in</Link>
      </div>
    )
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <Loader2 className="w-8 h-8 motion-safe:animate-spin text-library-600" />
      </div>
    )
  }

  const statCards = [
    { label: t('patronReports.activeCheckouts', 'Active Checkouts'), value: stats?.active_checkouts ?? 0, icon: BookOpen, color: 'text-status-info-600' },
    { label: t('patronReports.totalHolds', 'Holds'), value: stats?.total_holds ?? 0, icon: Clock, color: 'text-status-warning-600' },
    { label: t('patronReports.overdue', 'Overdue'), value: stats?.overdue_count ?? 0, icon: Clock, color: 'text-status-danger-600' },
    { label: t('patronReports.booksThisYear', 'Books This Year'), value: readingSummary?.books_read_this_year ?? 0, icon: TrendingUp, color: 'text-status-success-600' },
  ]

  const quickLinks = [
    { label: t('patronReports.readingInsights', 'Reading Insights'), path: '/my-reading-insights', icon: BarChart3, description: 'Genre trends, velocity, and heatmap' },
    { label: t('patronReports.readingChallenge', 'Reading Challenge'), path: '/reading-challenge', icon: Award, description: 'Achievements and leaderboards' },
    { label: 'Reading Leaderboards', path: '/reading-leaderboards', icon: TrendingUp, description: 'Top readers and competitions' },
    { label: t('patronReports.checkoutHistory', 'Checkout History'), path: '/account?tab=history', icon: Library, description: 'Full borrowing history' },
    { label: t('patronReports.favorites', 'My Favorites'), path: '/account?tab=favorites', icon: Star, description: 'Saved items and lists' },
  ]

  return (
    <PageContainer className="py-8">
      <div className="mb-8">
        <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream flex items-center gap-3">
          <BarChart3 className="w-8 h-8 text-library-600" />
          {t('patronReports.title', 'My Library Reports')}
        </h1>
        <p className="text-earth-600 dark:text-earth-400 mt-1">
          {t('patronReports.subtitle', 'Your reading activity, stats, and library usage at a glance')}
        </p>
      </div>

      {/* Data load error banner */}
      {loadError && (
        <div className="bg-status-warning-50 dark:bg-status-warning-900/20 border border-status-warning-200 dark:border-status-warning-800 rounded-xl p-4 mb-6">
          <p className="text-status-warning-800 dark:text-status-warning-200 text-sm">
            {t('patronReports.loadError', 'Unable to load your statistics right now. Some data may be unavailable.')}{' '}
            <button onClick={loadData} className="underline hover:no-underline font-medium">
              {t('patronReports.retry', 'Try again')}
            </button>
          </p>
        </div>
      )}

      {/* Stats Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        {statCards.map((card) => {
          const Icon = card.icon
          return (
            <div key={card.label} className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-4">
              <div className="flex items-center gap-2 mb-2">
                <Icon className={`w-5 h-5 ${card.color}`} />
                <span className="text-xs font-medium text-earth-600 dark:text-earth-400">{card.label}</span>
              </div>
              <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">{card.value}</p>
            </div>
          )
        })}
      </div>

      {/* Reading Summary */}
      {readingSummary && (
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-6 mb-8">
          <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4">
            {t('patronReports.readingSummary', 'Reading Summary')}
          </h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
            <div>
              <p className="text-sm text-earth-600 dark:text-earth-400">All-Time Books</p>
              <p className="text-xl font-bold text-lsc-dark dark:text-lsc-cream">{readingSummary.books_read_all_time}</p>
            </div>
            <div>
              <p className="text-sm text-earth-600 dark:text-earth-400">Favorite Genre</p>
              <p className="text-xl font-bold text-lsc-dark dark:text-lsc-cream">{readingSummary.favorite_genre || 'Exploring...'}</p>
            </div>
            <div>
              <p className="text-sm text-earth-600 dark:text-earth-400">Reading Streak</p>
              <p className="text-xl font-bold text-lsc-dark dark:text-lsc-cream">{readingSummary.reading_streak_days} days</p>
            </div>
            <div>
              <p className="text-sm text-earth-600 dark:text-earth-400">Avg Books/Month</p>
              <p className="text-xl font-bold text-lsc-dark dark:text-lsc-cream">{readingSummary.avg_books_per_month != null ? readingSummary.avg_books_per_month.toFixed(1) : '—'}</p>
            </div>
          </div>
        </div>
      )}

      {/* Account Balance */}
      {stats && stats.fines_balance > 0 && (
        <div className="bg-status-warning-50 dark:bg-status-warning-900/20 border border-status-warning-200 dark:border-status-warning-800 rounded-xl p-4 mb-8">
          <p className="text-status-warning-800 dark:text-status-warning-200 text-sm">
            You have an outstanding balance of <strong>${stats.fines_balance.toFixed(2)}</strong>.{' '}
            <Link to="/account?tab=overview" className="underline hover:no-underline">View details</Link>
          </p>
        </div>
      )}

      {/* Quick Links */}
      <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4">
        {t('patronReports.exploreMore', 'Explore Your Data')}
      </h2>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {quickLinks.map((link) => {
          const Icon = link.icon
          return (
            <Link
              key={link.path}
              to={link.path}
              className="flex items-center justify-between bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-4 hover:border-library-400 transition-colors group"
            >
              <div className="flex items-center gap-3">
                <Icon className="w-5 h-5 text-library-600" />
                <div>
                  <p className="font-medium text-lsc-dark dark:text-lsc-cream">{link.label}</p>
                  <p className="text-xs text-earth-600 dark:text-earth-400">{link.description}</p>
                </div>
              </div>
              <ArrowRight className="w-4 h-4 text-earth-600 group-hover:text-library-600 transition-colors" />
            </Link>
          )
        })}
      </div>
    </PageContainer>
  )
}
