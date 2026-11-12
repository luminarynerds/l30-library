/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useMemo, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import * as Sentry from "@/lib/sentry-lazy"
import {
  Users,
  Calendar,
  Baby,
  UsersRound,
  ClipboardList,
  Home,
  Loader2,
  RefreshCw,
  AlertTriangle,
  Check,
  Download,
  ChevronDown,
} from 'lucide-react'
import toast from 'react-hot-toast'
import {
  getDashboard,
  triggerWeeklySummaryDownload,
  type ParentOnboardingDashboard,
} from '@/api/parent-onboarding-api'
import { useTranslation } from '@/i18n'
import { AdminShell } from '../components/shells/AdminShell'
import { useAuth } from '../contexts/AuthContext'
import { bucketUpNext, type RailItem } from './upNextRail/bucketUpNext'
import UpNextRail from './upNextRail/UpNextRail'
import {
  useParentOnboardingDashboardPrefs,
  type OverdueRiskFilter,
} from '../hooks/useParentOnboardingDashboardPrefs'

const ADMIN_TITLE = 'Parent Onboarding'

function StatCard({
  label,
  value,
  icon,
  color = 'text-lsc-dark dark:text-lsc-cream',
  urgent = false,
  urgentLabel,
}: {
  label: string
  value: string | number
  icon: React.ReactNode
  color?: string
  urgent?: boolean
  urgentLabel?: string
}) {
  // When urgent, provide a screen-reader-only prefix so the count isn't
  // communicated by colour alone (WCAG 1.4.1 Use of Color).
  const ariaLabel = urgent && urgentLabel ? urgentLabel : undefined
  return (
    <div
      className={`bg-lsc-white dark:bg-earth-800 rounded-xl p-4 border ${
        urgent
          ? 'border-status-danger-400 dark:border-status-danger-500 border-2'
          : 'border-lsc-border dark:border-earth-700'
      }`}
      {...(ariaLabel ? { 'aria-label': ariaLabel } : {})}
    >
      <div className="flex items-start justify-between mb-2">
        <div className="p-2 bg-lsc-cream dark:bg-earth-700/50 rounded-lg">{icon}</div>
        {urgent && (
          <AlertTriangle
            aria-hidden="true"
            className="w-4 h-4 text-status-danger-500"
          />
        )}
      </div>
      <p className={`text-2xl font-bold ${color}`}>{value}</p>
      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{label}</p>
    </div>
  )
}

function OverdueFilterToggle({
  value,
  totalCount,
  highCount,
  onChange,
  t,
}: {
  value: OverdueRiskFilter
  totalCount: number
  highCount: number
  onChange: (next: OverdueRiskFilter) => void
  t: (k: string, paramsOrFallback?: Record<string, unknown> | string) => string
}) {
  const baseBtn =
    'inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium border transition-colors focus:outline-none focus:ring-2 focus:ring-lsc-rose focus:ring-offset-1 dark:focus:ring-offset-earth-800'
  const inactive =
    'bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream border-lsc-border dark:border-earth-700 hover:bg-lsc-cream dark:hover:bg-earth-700/50'
  const active =
    'bg-lsc-dark dark:bg-lsc-cream text-lsc-cream dark:text-lsc-dark border-lsc-dark dark:border-lsc-cream shadow-inner'

  const isAll = value === 'all'
  const isHigh = value === 'high'

  return (
    <div className="flex items-center gap-2 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
      <span id="overdue-filter-label">{t('parentOnboarding.dashboard.overdue.filter.label', 'Show')}:</span>
      <div role="group" aria-labelledby="overdue-filter-label" className="flex items-center gap-1.5">
        <button
          type="button"
          aria-pressed={isAll}
          onClick={() => onChange('all')}
          className={`${baseBtn} ${isAll ? active : inactive}`}
        >
          {isAll && <Check aria-hidden="true" className="w-3 h-3" />}
          <span>{t('parentOnboarding.dashboard.overdue.filter.all', 'All')} ({totalCount})</span>
        </button>
        <button
          type="button"
          aria-pressed={isHigh}
          onClick={() => onChange('high')}
          className={`${baseBtn} ${isHigh ? active : inactive}`}
        >
          {isHigh && <Check aria-hidden="true" className="w-3 h-3" />}
          <span>{t('parentOnboarding.dashboard.overdue.filter.highOnly', 'High risk only')} ({highCount})</span>
        </button>
      </div>
    </div>
  )
}

function WeeklyExportMenu({
  t,
}: {
  t: (k: string, paramsOrFallback?: Record<string, unknown> | string) => string
}) {
  const [open, setOpen] = useState(false)
  const [pending, setPending] = useState(false)
  const [mineOnly, setMineOnly] = useState(false)
  const containerRef = useRef<HTMLDivElement | null>(null)
  const buttonRef = useRef<HTMLButtonElement | null>(null)

  // Close on outside click.
  useEffect(() => {
    if (!open) return
    const onDocClick = (e: MouseEvent) => {
      if (!containerRef.current) return
      if (!containerRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', onDocClick)
    return () => document.removeEventListener('mousedown', onDocClick)
  }, [open])

  // Close on Escape.
  const onKeyDownMenu = (e: React.KeyboardEvent<HTMLDivElement>) => {
    if (e.key === 'Escape') {
      e.stopPropagation()
      setOpen(false)
      buttonRef.current?.focus()
    }
  }

  const handleDownload = async (format: 'csv' | 'pdf') => {
    if (pending) return
    setOpen(false)
    setPending(true)
    const loadingId = toast.loading(
      t('parentOnboarding.dashboard.export.toast.generating', 'Generating report...'),
    )
    try {
      const { filename } = await triggerWeeklySummaryDownload({
        format,
        coordinatorId: mineOnly ? 'me' : undefined,
      })
      toast.success(
        t('parentOnboarding.dashboard.export.toast.success', { filename }),
        { id: loadingId },
      )
    } catch (err) {
      Sentry.captureException(err)
      toast.error(
        t(
          'parentOnboarding.dashboard.export.toast.error',
          'Could not generate report. Try again.',
        ),
        { id: loadingId },
      )
    } finally {
      setPending(false)
    }
  }

  return (
    <div ref={containerRef} className="relative">
      <button
        ref={buttonRef}
        type="button"
        aria-haspopup="menu"
        aria-expanded={open}
        disabled={pending}
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-2 px-3 py-2 text-sm bg-lsc-cream dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream rounded-lg hover:bg-lsc-border dark:hover:bg-earth-600 transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
      >
        {pending ? (
          <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" />
        ) : (
          <Download className="w-4 h-4" aria-hidden="true" />
        )}
        <span>{t('parentOnboarding.dashboard.export.button', 'Export weekly summary')}</span>
        <ChevronDown className="w-4 h-4" aria-hidden="true" />
      </button>
      {open && (
        <div
          role="menu"
          aria-label={t('parentOnboarding.dashboard.export.button', 'Export weekly summary')}
          onKeyDown={onKeyDownMenu}
          className="absolute right-0 mt-2 w-72 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 shadow-lg z-20 py-1"
        >
          <button
            role="menuitem"
            type="button"
            onClick={() => handleDownload('csv')}
            className="block w-full text-left px-4 py-2 text-sm text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-earth-700"
          >
            {t(
              'parentOnboarding.dashboard.export.menu.csv',
              'Download as CSV (last 7 days)',
            )}
          </button>
          <button
            role="menuitem"
            type="button"
            disabled
            aria-disabled="true"
            title={t(
              'parentOnboarding.dashboard.export.pdfDisabledHint',
              'PDF export coming soon.',
            )}
            className="block w-full text-left px-4 py-2 text-sm text-lsc-dark/50 dark:text-lsc-cream/40 cursor-not-allowed"
          >
            {t(
              'parentOnboarding.dashboard.export.menu.pdf',
              'Download as PDF (last 7 days)',
            )}
          </button>
          <div role="separator" className="my-1 border-t border-lsc-border dark:border-earth-700" />
          <label className="flex items-center gap-2 px-4 py-2 text-sm text-lsc-dark dark:text-lsc-cream cursor-pointer hover:bg-lsc-cream dark:hover:bg-earth-700">
            <input
              type="checkbox"
              checked={mineOnly}
              onChange={(e) => setMineOnly(e.target.checked)}
              className="accent-lsc-rose"
            />
            <span>
              {t(
                'parentOnboarding.dashboard.export.menu.mineOnly',
                'Only my coordinator activity',
              )}
            </span>
          </label>
        </div>
      )}
    </div>
  )
}

export default function ParentOnboardingDashboardPage() {
  const { t } = useTranslation()
  const { user } = useAuth()
  const { overdueRiskFilter, setOverdueRiskFilter } = useParentOnboardingDashboardPrefs()

  const {
    data: dashboard,
    isLoading,
    error,
    refetch,
  } = useQuery<ParentOnboardingDashboard>({
    queryKey: ['parent-onboarding-dashboard'],
    queryFn: getDashboard,
  })

  if (error) {
    Sentry.captureException(error)
  }

  // Up Next bucketing: memoised on dashboard payload + signed-in coordinator
  // id so re-renders without new data don't re-sort and steal screen-reader focus.
  // `now` is captured once per render and passed in; the rail itself does not
  // tick, so a manual Refresh re-evaluates "today".
  const buckets = useMemo(() => {
    if (!dashboard || !user) return { overdue: [], today: [], thisWeek: [] }
    return bucketUpNext(dashboard, { currentUserId: user.id, now: new Date() })
  }, [dashboard, user])

  // Risk-filter scope: the rail's overdue bucket. After bucketing, only
  // assignments whose check-in is genuinely past-due land here; items the
  // server flagged but whose date is future-this-week appear in This Week and
  // are not filtered. See PR #1219 conflict-resolution notes (PR #1218 collapsed
  // the standalone Overdue panel into the rail).
  const overdueAssignments = useMemo<RailItem[]>(
    () => buckets.overdue.filter((item) => item.entity === 'assignment'),
    [buckets.overdue],
  )
  const overdueHighAssignments = useMemo<RailItem[]>(
    () => overdueAssignments.filter((item) => item.riskLevel === 'high'),
    [overdueAssignments],
  )

  // Build the rail's buckets after risk filter is applied. We only filter the
  // Overdue bucket; non-assignment rows (sessions, visits) pass through
  // unfiltered, so the filter never hides a session just because it's overdue.
  const filteredBuckets = useMemo(() => {
    if (overdueRiskFilter !== 'high') return buckets
    const filteredOverdue = buckets.overdue.filter(
      (item) => item.entity !== 'assignment' || item.riskLevel === 'high',
    )
    return { ...buckets, overdue: filteredOverdue }
  }, [buckets, overdueRiskFilter])

  if (isLoading) {
    return (
      <AdminShell title={ADMIN_TITLE}>
        <div
          className="flex items-center justify-center min-h-[60vh]"
          role="status"
          aria-live="polite"
          aria-label={t('parentOnboarding.dashboard.loadingAriaLabel', 'Loading parent onboarding dashboard')}
        >
          <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" aria-hidden="true" />
          <span className="sr-only">{t('parentOnboarding.dashboard.loadingAriaLabel', 'Loading parent onboarding dashboard')}</span>
        </div>
      </AdminShell>
    )
  }

  if (error || !dashboard) {
    return (
      <AdminShell title={ADMIN_TITLE}>
        <div className="max-w-4xl mx-auto p-6">
          <div
            role="alert"
            className="bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-200 dark:border-status-danger-800 rounded-xl p-6 text-center"
          >
            <AlertTriangle className="w-8 h-8 text-status-danger-500 mx-auto mb-2" aria-hidden="true" />
            <p className="text-status-danger-700 dark:text-status-danger-300">{t('parentOnboarding.dashboard.failedToLoadData', 'Failed to load dashboard data')}</p>
            <button
              onClick={() => refetch()}
              className="mt-3 px-4 py-2 bg-status-danger-100 dark:bg-status-danger-900/30 text-status-danger-700 dark:text-status-danger-300 rounded-lg text-sm hover:bg-status-danger-200 dark:hover:bg-status-danger-900/50"
            >
              {t('common.retry', 'Retry')}
            </button>
          </div>
        </div>
      </AdminShell>
    )
  }

  const handleRefresh = async () => {
    try {
      const result = await refetch()
      if (result.error) {
        toast.error(t('parentOnboarding.dashboard.refreshFailed', 'Failed to refresh dashboard'))
      } else {
        toast.success(t('parentOnboarding.dashboard.refreshSuccess', 'Dashboard refreshed'))
      }
    } catch {
      toast.error(t('parentOnboarding.dashboard.refreshFailed', 'Failed to refresh dashboard'))
    }
  }

  // Filter-change announcement copy. Phrased against the rail's overdue bucket
  // (assignments only), which is what the toggle actually controls.
  const filteredOverdueCount =
    overdueRiskFilter === 'high'
      ? overdueHighAssignments.length
      : overdueAssignments.length
  const filterLevelLabel =
    overdueRiskFilter === 'high'
      ? t('parentOnboarding.dashboard.overdue.filter.highOnly', 'High risk only').toLowerCase()
      : t('parentOnboarding.dashboard.overdue.filter.all', 'All').toLowerCase()
  const filterAnnouncement = t(
    'parentOnboarding.dashboard.overdue.filter.announce',
    { count: filteredOverdueCount, level: filterLevelLabel },
  )
  const showFilterToggle = overdueAssignments.length > 0
  const showEmptyHighHint =
    overdueRiskFilter === 'high' &&
    overdueHighAssignments.length === 0 &&
    overdueAssignments.length > 0

  return (
    <AdminShell title={ADMIN_TITLE}>
      <div className="max-w-7xl mx-auto p-6 space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
              {t('parentOnboarding.dashboard.title', 'Parent Onboarding Dashboard')}
            </h1>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
              {t('parentOnboarding.dashboard.subtitle', 'Overview of parent onboarding services and activities')}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <WeeklyExportMenu t={t} />
            <button
              onClick={handleRefresh}
              className="flex items-center gap-2 px-3 py-2 text-sm bg-lsc-cream dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream rounded-lg hover:bg-lsc-border dark:hover:bg-earth-600 transition-colors"
            >
              <RefreshCw className="w-4 h-4" aria-hidden="true" />
              {t('common.refresh', 'Refresh')}
            </button>
          </div>
        </div>

        {/* Stats Grid: aria-live so screen readers hear updated counts after refresh */}
        <div
          className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-4"
          aria-live="polite"
          aria-label={t('parentOnboarding.dashboard.statisticsAriaLabel', 'Dashboard statistics')}
        >
          <StatCard
            label={t('parentOnboarding.dashboard.activeFamilies', 'Active Families')}
            value={dashboard.active_families}
            icon={<Users className="w-5 h-5 text-lsc-rose" aria-hidden="true" />}
          />
          <StatCard
            label={t('parentOnboarding.dashboard.upcomingSessions', 'Upcoming Sessions')}
            value={dashboard.upcoming_sessions}
            icon={<Calendar className="w-5 h-5 text-status-info-500" aria-hidden="true" />}
          />
          <StatCard
            label={t('parentOnboarding.dashboard.overdueCheckIns', 'Overdue Check-ins')}
            value={dashboard.overdue_check_ins}
            icon={<AlertTriangle className="w-5 h-5 text-status-danger-500" aria-hidden="true" />}
            {...(dashboard.overdue_check_ins > 0 && {
              color: 'text-status-danger-600 dark:text-status-danger-400',
              urgent: true,
              urgentLabel: `${t('parentOnboarding.dashboard.overdueCheckIns', 'Overdue Check-ins')}: ${dashboard.overdue_check_ins} - ${t('common.urgent', 'urgent')}`,
            })}
          />
          <StatCard
            label={t('parentOnboarding.dashboard.activeChildcareLabel', 'Active Childcare')}
            value={dashboard.active_childcare_sessions}
            icon={<Baby className="w-5 h-5 text-pink-500" aria-hidden="true" />}
          />
          <StatCard
            label={t('parentOnboarding.dashboard.activeGroupsLabel', 'Active Groups')}
            value={dashboard.active_connection_groups}
            icon={<UsersRound className="w-5 h-5 text-category-500" aria-hidden="true" />}
          />
          <StatCard
            label={t('parentOnboarding.dashboard.pendingEnrollments', 'Pending Enrollments')}
            value={dashboard.pending_enrollments}
            icon={<ClipboardList className="w-5 h-5 text-status-warning-500" aria-hidden="true" />}
          />
          <StatCard
            label={t('parentOnboarding.dashboard.upcomingVisitsLabel', 'Upcoming Visits')}
            value={dashboard.upcoming_home_visits}
            icon={<Home className="w-5 h-5 text-teal-500" aria-hidden="true" />}
          />
        </div>

        {/*
          Overdue filter toggle. Sits above the Up Next rail because (1) the
          rail itself is freshly defined by PR #1218 and we don't want to wire
          a filter slot into it for one consumer, and (2) the toggle visibly
          affects only the rail's Overdue bucket which is the rail's first
          bucket below it - they read top-to-bottom.

          The separate aria-live polite region narrates filter activity only,
          never the unrelated stats refresh.
        */}
        {showFilterToggle && (
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 px-5 py-3">
            <OverdueFilterToggle
              value={overdueRiskFilter}
              totalCount={overdueAssignments.length}
              highCount={overdueHighAssignments.length}
              onChange={setOverdueRiskFilter}
              t={t}
            />
            {showEmptyHighHint && (
              <div className="mt-2 flex items-center gap-2 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                <span>{t('parentOnboarding.dashboard.overdue.filter.emptyHigh', 'No high-risk overdue check-ins.')}</span>
                <button
                  type="button"
                  onClick={() => setOverdueRiskFilter('all')}
                  className="text-lsc-rose hover:underline focus:outline-none focus:ring-2 focus:ring-lsc-rose focus:ring-offset-1 dark:focus:ring-offset-earth-800 rounded"
                >
                  {t('parentOnboarding.dashboard.overdue.filter.showAll', 'Show all overdue')}
                </button>
              </div>
            )}
          </div>
        )}
        <div
          className="sr-only"
          role="status"
          aria-live="polite"
          data-testid="overdue-filter-announce"
        >
          {showFilterToggle ? filterAnnouncement : ''}
        </div>

        {/* Up Next rail: replaces the previous Recent Sessions / Overdue Check-ins /
            Upcoming Home Visits panels. Date-bucketed, coordinator-scoped. See spec
            2026-05-18-l30-parent-onboarding-dashboard-up-next-rail.md. */}
        <UpNextRail buckets={filteredBuckets} t={t} />
      </div>
    </AdminShell>
  )
}
