/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { Link } from 'react-router-dom'
import {
  ShieldAlert,
  BookOpen,
  MapPin,
  Ban,
  Library,
  TrendingUp,
  Megaphone,
  ChevronRight,
  Loader2,
  AlertTriangle,
  FileQuestion,
  Info,
  Globe,
  Scale,
  Users,
  ChevronLeft,
} from 'lucide-react'
import StandardPageLayout from '@/components/StandardPageLayout'
import { useTranslation } from '@/i18n'
import { t } from '@/i18n'
import {
  getBanTypeBadge,
  getBanTypeIcon,
  formatNumber,
  US_STATES_MAP,
  REASON_LABELS,
} from '@/components/ban-tracker/ban-tracker-data'
import { StateMap } from '@/components/ban-tracker/StateMap'
import { FilterBar } from '@/components/ban-tracker/FilterBar'
import { ReportCard } from '@/components/ban-tracker/ReportCard'
import { CatalogMatchesSection } from '@/components/ban-tracker/CatalogMatchesSection'
import { MostChallengedSection } from '@/components/ban-tracker/MostChallengedSection'
import { SubscribeCTA } from '@/components/ban-tracker/SubscribeCTA'
import { TimelineChart } from '@/components/ban-tracker/TimelineChart'
import { useBanTracker } from '@/hooks/useBanTracker'
import { useBanTrackerTimeline } from '@/hooks/useBanTrackerTimeline'
import { useBranding } from '@/contexts/BrandingContext'
import { TurnstileWidget } from '@/components/TurnstileWidget'
import { api } from '@/lib/api-client'

const BAN_TYPE_OPTIONS = [
  { value: 'challenged', labelKey: 'publicBanTracker.challenged', label: 'Challenged' },
  { value: 'restricted', labelKey: 'publicBanTracker.restricted', label: 'Restricted' },
  { value: 'banned', labelKey: 'publicBanTracker.banned', label: 'Banned' },
] as const

type BanTypeValue = typeof BAN_TYPE_OPTIONS[number]['value']

function BanReportSubmissionForm(): React.ReactElement {
  const { t } = useTranslation()
  const [title, setTitle] = useState('')
  const [author, setAuthor] = useState('')
  const [stateCode, setStateCode] = useState('')
  const [district, setDistrict] = useState('')
  const [institution, setInstitution] = useState('')
  const [banType, setBanType] = useState<BanTypeValue | ''>('')
  const [reasonCategory, setReasonCategory] = useState('')
  const [sourceUrl, setSourceUrl] = useState('')
  const [notes, setNotes] = useState('')
  const [turnstileToken, setTurnstileToken] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [success, setSuccess] = useState(false)
  const [errorMsg, setErrorMsg] = useState('')

  const requiredOk = title.trim() && author.trim() && stateCode && banType
  const canSubmit = Boolean(requiredOk) && Boolean(turnstileToken) && !submitting

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!canSubmit) return
    setErrorMsg('')
    setSubmitting(true)
    try {
      await api.post('/api/v1/ban-tracker/public/submit', {
        title: title.trim(),
        author: author.trim(),
        state: stateCode,
        district: district.trim() || undefined,
        institution: institution.trim() || undefined,
        ban_type: banType,
        reason_category: reasonCategory || undefined,
        source_url: sourceUrl.trim() || undefined,
        notes: notes.trim() || undefined,
        turnstile_token: turnstileToken,
      })
      setSuccess(true)
      setTitle('')
      setAuthor('')
      setStateCode('')
      setDistrict('')
      setInstitution('')
      setBanType('')
      setReasonCategory('')
      setSourceUrl('')
      setNotes('')
    } catch (err) {
      const msg = err instanceof Error ? err.message : t('publicBanTracker.submissionFailedPleaseTry', 'Submission failed. Please try again.')
      setErrorMsg(msg)
    } finally {
      setSubmitting(false)
    }
  }

  const inputClass =
    'w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-900 text-sm text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose'
  const labelClass = 'block text-xs font-semibold text-lsc-dark dark:text-lsc-cream mb-1'

  if (success) {
    return (
      <div
        role="status"
        className="bg-earth-50 dark:bg-earth-700/50 rounded-xl p-5 text-center"
      >
        <p className="text-sm text-lsc-dark dark:text-lsc-cream mb-3">
          {t('publicBanTracker.thanksYourSubmissionIsQueued', 'Thanks -- your submission is queued for staff review.')}
        </p>
        <button
          type="button"
          onClick={() => setSuccess(false)}
          className="text-sm font-semibold text-lsc-rose dark:text-lsc-rose-light hover:underline"
        >
          {t('publicBanTracker.submitAnotherReport', 'Submit another report')}
        </button>
      </div>
    )
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-3" noValidate>
      <div>
        <label htmlFor="ban-form-title" className={labelClass}>
          {t('publicBanTracker.formTitle', 'Title')} <span className="text-lsc-rose">*</span>
        </label>
        <input
          id="ban-form-title"
          type="text"
          required
          maxLength={300}
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          className={inputClass}
        />
      </div>
      <div>
        <label htmlFor="ban-form-author" className={labelClass}>
          {t('publicBanTracker.formAuthor', 'Author')} <span className="text-lsc-rose">*</span>
        </label>
        <input
          id="ban-form-author"
          type="text"
          required
          maxLength={200}
          value={author}
          onChange={(e) => setAuthor(e.target.value)}
          className={inputClass}
        />
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label htmlFor="ban-form-state" className={labelClass}>
            {t('publicBanTracker.formState', 'State')} <span className="text-lsc-rose">*</span>
          </label>
          <select
            id="ban-form-state"
            required
            value={stateCode}
            onChange={(e) => setStateCode(e.target.value)}
            className={inputClass}
          >
            <option value="">{t('publicBanTracker.selectEllipsis', 'Select...')}</option>
            {Object.entries(US_STATES_MAP).map(([code, name]) => (
              <option key={code} value={code}>
                {code} -- {name}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="ban-form-bantype" className={labelClass}>
            {t('publicBanTracker.formBanType', 'Ban type')} <span className="text-lsc-rose">*</span>
          </label>
          <select
            id="ban-form-bantype"
            required
            value={banType}
            onChange={(e) => setBanType(e.target.value as BanTypeValue | '')}
            className={inputClass}
          >
            <option value="">{t('publicBanTracker.selectEllipsis', 'Select...')}</option>
            {BAN_TYPE_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {t(opt.labelKey, opt.label)}
              </option>
            ))}
          </select>
        </div>
      </div>
      <div>
        <label htmlFor="ban-form-district" className={labelClass}>
          {t('publicBanTracker.formDistrict', 'District')}
        </label>
        <input
          id="ban-form-district"
          type="text"
          maxLength={200}
          value={district}
          onChange={(e) => setDistrict(e.target.value)}
          className={inputClass}
        />
      </div>
      <div>
        <label htmlFor="ban-form-institution" className={labelClass}>
          {t('publicBanTracker.formInstitution', 'Institution')}
        </label>
        <input
          id="ban-form-institution"
          type="text"
          maxLength={200}
          value={institution}
          onChange={(e) => setInstitution(e.target.value)}
          className={inputClass}
        />
      </div>
      <div>
        <label htmlFor="ban-form-reason" className={labelClass}>
          {t('publicBanTracker.formReason', 'Reason')}
        </label>
        <select
          id="ban-form-reason"
          value={reasonCategory}
          onChange={(e) => setReasonCategory(e.target.value)}
          className={inputClass}
        >
          <option value="">{t('publicBanTracker.selectEllipsis', 'Select...')}</option>
          {Object.entries(REASON_LABELS).map(([key, label]) => (
            <option key={key} value={key}>
              {label}
            </option>
          ))}
        </select>
      </div>
      <div>
        <label htmlFor="ban-form-source" className={labelClass}>
          {t('publicBanTracker.formSourceUrl', 'Source URL')}
        </label>
        <input
          id="ban-form-source"
          type="url"
          placeholder="https://..."
          value={sourceUrl}
          onChange={(e) => setSourceUrl(e.target.value)}
          className={inputClass}
        />
      </div>
      <div>
        <label htmlFor="ban-form-notes" className={labelClass}>
          {t('publicBanTracker.formNotes', 'Notes')}
        </label>
        <textarea
          id="ban-form-notes"
          rows={3}
          maxLength={2000}
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          className={inputClass}
        />
      </div>

      <TurnstileWidget onVerify={setTurnstileToken} />

      {errorMsg && (
        <p role="alert" className="text-sm text-lsc-rose dark:text-lsc-rose-light">
          {errorMsg}
        </p>
      )}

      <button
        type="submit"
        disabled={!canSubmit}
        className="inline-flex items-center gap-2 px-5 py-2.5 bg-lsc-rose text-white font-semibold rounded-xl hover:bg-lsc-rose/90 transition-colors text-sm disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {submitting ? (
          <>
            <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" />
            {t('publicBanTracker.submittingEllipsis', 'Submitting...')}
          </>
        ) : (
          <>
            {t('publicBanTracker.submitReport', 'Submit report')}
            <ChevronRight className="w-4 h-4" aria-hidden="true" />
          </>
        )}
      </button>
    </form>
  )
}

function StatCard({
  value,
  label,
  icon: Icon,
  colorClass,
}: {
  value: number
  label: string
  icon: React.ElementType
  colorClass: string
}): React.ReactElement {
  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-6 text-center">
      <div className="flex justify-center mb-3">
        <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${colorClass}`}>
          <Icon className="w-5 h-5" aria-hidden="true" />
        </div>
      </div>
      <div className="text-3xl font-bold text-lsc-dark dark:text-lsc-cream mb-1">
        {formatNumber(value)}
      </div>
      <div className="text-sm text-lsc-dark/70 dark:text-lsc-cream/60">{label}</div>
    </div>
  )
}

function Pagination({
  page,
  totalPages,
  total,
  onPageChange,
}: {
  page: number
  totalPages: number
  total: number
  onPageChange: (p: number) => void
}): React.ReactElement | null {
  if (totalPages <= 1) return null

  const getVisiblePages = (): (number | 'ellipsis')[] => {
    const pages: (number | 'ellipsis')[] = []
    const delta = 2

    pages.push(1)

    const rangeStart = Math.max(2, page - delta)
    const rangeEnd = Math.min(totalPages - 1, page + delta)

    if (rangeStart > 2) pages.push('ellipsis')

    for (let i = rangeStart; i <= rangeEnd; i++) {
      pages.push(i)
    }

    if (rangeEnd < totalPages - 1) pages.push('ellipsis')

    if (totalPages > 1) pages.push(totalPages)

    return pages
  }

  return (
    <nav
      className="flex flex-col sm:flex-row items-center justify-between gap-4 mt-6"
      aria-label={t('aria.publicBanTracker.pagination')}
    >
      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/60">
        {t('publicBanTracker.showingPageXOfY', { page, totalPages, total: formatNumber(total) })}
      </p>

      <div className="flex items-center gap-1">
        <button
          onClick={() => onPageChange(page - 1)}
          disabled={page <= 1}
          className="p-2 rounded-lg border border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream hover:bg-earth-50 dark:hover:bg-earth-700 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
          aria-label={t('aria.account.previousPage')}
        >
          <ChevronLeft className="w-4 h-4" aria-hidden="true" />
        </button>

        {getVisiblePages().map((p, idx) =>
          p === 'ellipsis' ? (
            <span
              key={`ellipsis-${idx}`}
              className="px-2 text-lsc-dark/70 dark:text-lsc-cream/60"
              aria-hidden="true"
            >
              ...
            </span>
          ) : (
            <button
              key={p}
              onClick={() => onPageChange(p)}
              className={`w-9 h-9 rounded-lg text-sm font-medium transition-colors ${
                p === page
                  ? 'bg-lsc-rose text-white'
                  : 'border border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream hover:bg-earth-50 dark:hover:bg-earth-700'
              }`}
              aria-label={t('publicBanTracker.pageX', { page: p })}
              aria-current={p === page ? 'page' : undefined}
            >
              {p}
            </button>
          )
        )}

        <button
          onClick={() => onPageChange(page + 1)}
          disabled={page >= totalPages}
          className="p-2 rounded-lg border border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream hover:bg-earth-50 dark:hover:bg-earth-700 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
          aria-label={t('aria.account.nextPage')}
        >
          <ChevronRight className="w-4 h-4" aria-hidden="true" />
        </button>
      </div>
    </nav>
  )
}

export default function PublicBanTrackerPage(): React.ReactElement {
  const branding = useBranding()
  const { t } = useTranslation()
  const {
    stats,
    statsLoading,
    statsError,
    reports,
    reportsLoading,
    reportsError,
    loadReports,
    page,
    totalPages,
    totalReports,
    catalogMatches,
    mostBanned,
    searchQuery,
    setSearchQuery,
    selectedState,
    setSelectedState,
    selectedBanType,
    setSelectedBanType,
    selectedReason,
    setSelectedReason,
    selectedSource,
    setSelectedSource,
    hasActiveFilters,
    clearFilters,
    handlePageChange,
  } = useBanTracker()

  const { buckets: timelineBuckets } = useBanTrackerTimeline({
    state: selectedState,
    banType: selectedBanType,
    reasonCategory: selectedReason,
    source: selectedSource,
  })

  const isEmpty = !!stats && stats.total_reports === 0 && stats.by_state.length === 0

  return (
    <StandardPageLayout
      title={t('publicBanTracker.bookBanTracker', 'Book Ban Tracker')}
      subtitle={t('publicBanTracker.trackingBookBansChallengesAnd')}
      icon={ShieldAlert}
      isLoading={statsLoading && reportsLoading}
    >
      {/* Hero Section */}
      <div className="bg-gradient-to-r from-red-600/90 to-lsc-brown/70 rounded-xl p-8 text-white mb-0 -mt-4">
        <div className="flex items-start gap-4">
          <ShieldAlert className="w-10 h-10 flex-shrink-0 mt-0.5 opacity-90" aria-hidden="true" />
          <div>
            <h2 className="text-2xl font-serif font-bold mb-2">{t('publicBanTracker.theFreedomToReadIs')}</h2>
            <p className="text-white/85 text-base leading-relaxed max-w-2xl mb-4">
              {t('publicBanTracker.bookBansAreAccelerating', 'Book bans are accelerating across the country. School boards, legislatures, and library committees are removing or restricting access to books at unprecedented rates. This tracker aggregates publicly reported bans, challenges, and restrictions so communities can stay informed and take action.')}
            </p>
            <Link
              to="/advocacy"
              className="inline-flex items-center gap-2 px-5 py-2.5 bg-lsc-white/20 hover:bg-lsc-white/30 rounded-xl text-white font-semibold text-sm transition-colors"
            >
              <Megaphone className="w-4 h-4" aria-hidden="true" />
              {t('bannedBooks.takeAction')}
              <ChevronRight className="w-4 h-4" aria-hidden="true" />
            </Link>
          </div>
        </div>
      </div>

      {/* Stats Bar */}
      {statsError && (
        <div className="bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-200 dark:border-status-danger-700 rounded-xl p-4 text-status-danger-700 dark:text-status-danger-300 text-sm">
          {statsError}
        </div>
      )}

      {stats && !statsError && !isEmpty && (
        <section aria-labelledby="stats-heading">
          <h2 id="stats-heading" className="sr-only">{t('publicBanTracker.banStatistics', 'Ban Statistics')}</h2>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <StatCard
              value={stats.total_reports}
              label={t('publicBanTracker.totalBanReports', 'Total Ban Reports')}
              icon={Ban}
              colorClass="bg-status-danger-100 dark:bg-status-danger-900/30 text-status-danger-600 dark:text-status-danger-400"
            />
            <StatCard
              value={stats.total_states}
              label={t('publicBanTracker.statesAffected', 'States Affected')}
              icon={MapPin}
              colorClass="bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-600 dark:text-status-warning-400"
            />
            <StatCard
              value={stats.total_has_in_cataloges}
              label={t('publicBanTracker.bannedBooksInOurCatalog', 'Banned Books in Our Catalog')}
              icon={Library}
              colorClass="bg-status-success-100 dark:bg-status-success-900/30 text-status-success-600 dark:text-status-success-400"
            />
          </div>
        </section>
      )}

      {/* Most Challenged Books */}
      {mostBanned.length > 0 && (
        <MostChallengedSection books={mostBanned} />
      )}

      {/* State Breakdown Grid */}
      {stats && stats.by_state.length > 0 && (
        <section aria-labelledby="state-breakdown-heading">
          <h2 id="state-breakdown-heading" className="sr-only">{t('publicBanTracker.stateBreakdown', 'State Breakdown')}</h2>
          <StateMap stateData={stats.by_state} selectedState={selectedState} onStateClick={setSelectedState} />
        </section>
      )}

      {/* Monthly trend timeline. The caption is load-bearing: the bulk of the
          data is one school year of PEN America reporting, so the months
          before it are near-empty for want of coverage, not for want of bans.
          Without saying so the chart reads as "bans started in 2023". */}
      {!isEmpty && (
        <section aria-labelledby="timeline-heading">
          <h2 id="timeline-heading" className="sr-only">{t('publicBanTracker.monthlyTrend', 'Monthly Trend')}</h2>
          <TimelineChart buckets={timelineBuckets} />
          <p className="mt-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
            {t('publicBanTracker.timelineCoverage', 'Most reports here come from PEN America\'s Index of School Book Bans for the 2023-24 school year, July 2023 through June 2024. Earlier months hold only scattered individual reports, so a low bar means we lack data for that month, not that no books were banned.')}
          </p>
        </section>
      )}

      {/* Subscribe CTA — sign-in pointer or per-user subscription affordance */}
      <SubscribeCTA />

      {/* In Our Collection Highlight */}
      {catalogMatches.length > 0 && (
        <CatalogMatchesSection reports={catalogMatches} />
      )}

      {/* Empty-state explanatory panel — shown when stats load with zero data */}
      {isEmpty && !statsError && (
        <section aria-labelledby="empty-state-heading">
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-6">
            <div className="flex items-center gap-2 mb-4">
              <Info className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" aria-hidden="true" />
              <h2
                id="empty-state-heading"
                className="font-serif text-lg font-bold text-lsc-dark dark:text-lsc-cream"
              >
                {t('publicBanTracker.wereStillGatheringReports', "We're still gathering reports.")}
              </h2>
            </div>
            <div className="text-sm text-lsc-dark/80 dark:text-lsc-cream/80 leading-relaxed space-y-3 max-w-3xl">
              <p>
                {t('publicBanTracker.thisTrackerAggregatesBanAnd', "This tracker aggregates ban and challenge reports from PEN America's Index of School Book Bans, the American Library Association's Office for Intellectual Freedom, and verified entries from library staff. Each report is reviewed before it appears here.")}
              </p>
              <p>
                {t('publicBanTracker.wePublishThisPageEven', "We publish this page even when our database is empty because transparency about what we know — and don't yet know — is part of defending the freedom to read. Censorship rarely announces itself, and a quiet page is not the same as a quiet problem.")}
              </p>
              <p>
                {t('publicBanTracker.whileWeBuildOutOur', 'While we build out our data, the')}{' '}
                <Link
                  to="/advocacy"
                  className="text-lsc-rose dark:text-lsc-rose-light hover:underline font-medium"
                >
                  {t('publicBanTracker.advocacyHub', 'Advocacy Hub')}
                </Link>{' '}
                {t('publicBanTracker.hasToolsToContactYour', 'has tools to contact your representatives, and the source links further down this page lead to up-to-date national tracking from PEN America and the ALA.')}
              </p>
            </div>
          </div>
        </section>
      )}

      {/* Filterable Book List */}
      {!isEmpty && (
      <section aria-labelledby="book-list-heading">
        <div className="flex items-center gap-2 mb-4">
          <BookOpen className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" aria-hidden="true" />
          <h2
            id="book-list-heading"
            className="font-serif text-xl font-bold text-lsc-dark dark:text-lsc-cream"
          >
            {t('publicBanTracker.banReports', 'Ban Reports')}
          </h2>
          {!reportsLoading && (
            <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/50">
              {t('publicBanTracker.xTotal', { count: formatNumber(totalReports) })}
            </span>
          )}
        </div>

        {/* Filter bar */}
        {stats && (
          <FilterBar
            states={stats.by_state}
            banTypes={stats.by_type}
            reasonCategories={stats.by_reason}
            selectedState={selectedState}
            selectedBanType={selectedBanType}
            selectedReason={selectedReason}
            selectedSource={selectedSource}
            searchQuery={searchQuery}
            onStateChange={setSelectedState}
            onBanTypeChange={setSelectedBanType}
            onReasonChange={setSelectedReason}
            onSourceChange={setSelectedSource}
            onSearchChange={setSearchQuery}
            onClearFilters={clearFilters}
            hasActiveFilters={hasActiveFilters}
          />
        )}

        {/* Loading state */}
        {reportsLoading && (
          <div className="flex items-center justify-center py-16">
            <Loader2 className="w-8 h-8 text-lsc-rose motion-safe:animate-spin" aria-hidden="true" />
            <span className="ml-3 text-lsc-dark/70 dark:text-lsc-cream/60">{t('publicBanTracker.loadingReportsEllipsis', 'Loading reports...')}</span>
          </div>
        )}

        {/* Error state */}
        {reportsError && !reportsLoading && (
          <div className="bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-200 dark:border-status-danger-700 rounded-xl p-6 text-center">
            <AlertTriangle className="w-8 h-8 text-status-danger-400 mx-auto mb-2" aria-hidden="true" />
            <p className="text-status-danger-700 dark:text-status-danger-300 text-sm">{reportsError}</p>
            <button
              onClick={loadReports}
              className="mt-3 px-4 py-2 bg-status-danger-100 dark:bg-status-danger-900/30 text-status-danger-700 dark:text-status-danger-300 rounded-lg text-sm font-medium hover:bg-status-danger-200 dark:hover:bg-status-danger-900/50 transition-colors"
            >
              {t('publicBanTracker.tryAgain', 'Try again')}
            </button>
          </div>
        )}

        {/* Empty state */}
        {!reportsLoading && !reportsError && reports.length === 0 && (
          <div className="text-center py-16 text-lsc-dark/70 dark:text-lsc-cream/60">
            <BookOpen className="w-12 h-12 mx-auto mb-3 opacity-30" aria-hidden="true" />
            {hasActiveFilters ? (
              <>
                <p>{t('publicBanTracker.noReportsMatchYourCurrent')}</p>
                <button
                  onClick={clearFilters}
                  className="mt-3 text-sm text-lsc-rose dark:text-lsc-rose-light hover:underline font-medium"
                >
                  {t('publicBanTracker.clearFilters', 'Clear filters')}
                </button>
              </>
            ) : (
              <>
                <p className="text-lg font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">
                  {t('publicBanTracker.thisTrackerIsGrowing', 'This tracker is growing')}
                </p>
                <p className="text-sm max-w-md mx-auto">
                  {t('publicBanTracker.wereActivelyGatheringReportsFrom', "We're actively gathering reports from PEN America, the ALA, and community sources. Check back soon, or visit our")}{' '}
                  <Link to="/advocacy" className="text-lsc-rose dark:text-lsc-rose-light hover:underline font-medium">{t('publicBanTracker.advocacyHub', 'Advocacy Hub')}</Link>{' '}
                  {t('publicBanTracker.toGetInvolved', 'to get involved.')}
                </p>
              </>
            )}
          </div>
        )}

        {/* Report cards */}
        {!reportsLoading && !reportsError && reports.length > 0 && (
          <>
            <div className="grid sm:grid-cols-2 gap-4">
              {reports.map((report) => (
                <ReportCard key={report.id} report={report} />
              ))}
            </div>

            <Pagination
              page={page}
              totalPages={totalPages}
              total={totalReports}
              onPageChange={handlePageChange}
            />
          </>
        )}
      </section>
      )}

      {/* Type Breakdown (compact) */}
      {stats && stats.by_type.length > 0 && (
        <section aria-labelledby="type-breakdown-heading">
          <div className="flex items-center gap-2 mb-4">
            <TrendingUp className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" aria-hidden="true" />
            <h2
              id="type-breakdown-heading"
              className="font-serif text-xl font-bold text-lsc-dark dark:text-lsc-cream"
            >
              {t('publicBanTracker.byActionType', 'By Action Type')}
            </h2>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {stats.by_type.map((item) => {
              const badge = getBanTypeBadge(item.ban_type)
              const icon = getBanTypeIcon(item.ban_type)
              return (
                <button
                  key={item.ban_type}
                  onClick={() => {
                    setSelectedBanType(item.ban_type === selectedBanType ? '' : item.ban_type)
                    document.getElementById('book-list-heading')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
                  }}
                  className={`rounded-xl border p-4 text-left transition-all hover:shadow-md ${
                    selectedBanType === item.ban_type
                      ? 'border-lsc-rose ring-2 ring-lsc-rose/30 bg-lsc-rose/5 dark:bg-lsc-rose/10'
                      : 'border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800'
                  }`}
                  aria-pressed={selectedBanType === item.ban_type}
                  aria-label={t('publicBanTracker.filterByXYReports', { label: badge.label, count: item.count })}
                >
                  <div className="flex items-center gap-2 mb-2">
                    <span className={`inline-flex items-center gap-1 px-2 py-0.5 text-xs font-semibold rounded-full ${badge.className}`}>
                      {icon}
                      {badge.label}
                    </span>
                  </div>
                  <div className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">
                    {formatNumber(item.count)}
                  </div>
                </button>
              )
            })}
          </div>
        </section>
      )}

      {/* Report a Ban */}
      <section aria-labelledby="report-ban-heading">
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-6">
          <div className="flex items-center gap-2 mb-4">
            <FileQuestion className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" aria-hidden="true" />
            <h2
              id="report-ban-heading"
              className="font-serif text-lg font-bold text-lsc-dark dark:text-lsc-cream"
            >
              {t('publicBanTracker.reportABookBan', 'Report a Book Ban')}
            </h2>
          </div>
          <div className="grid md:grid-cols-2 gap-6">
            <div>
              <p className="text-sm text-lsc-dark/80 dark:text-lsc-cream/80 leading-relaxed mb-4">
                {t('publicBanTracker.knowAboutABookThats', "Know about a book that's been banned, challenged, or restricted in your community? Help us track censorship by reporting it. Staff members verify all submissions before they appear in the tracker.")}
              </p>
              <h3 className="text-sm font-semibold text-lsc-dark dark:text-lsc-cream mb-2">{t('publicBanTracker.whatToInclude', 'What to include:')}</h3>
              <ul className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 space-y-1.5">
                <li className="flex items-start gap-2">
                  <span className="text-lsc-rose mt-0.5">&#8226;</span>
                  {t('publicBanTracker.bookTitleAndAuthor', 'Book title and author')}
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-lsc-rose mt-0.5">&#8226;</span>
                  {t('publicBanTracker.locationStateDistrictOrInstitution', 'Location (state, district, or institution)')}
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-lsc-rose mt-0.5">&#8226;</span>
                  {t('publicBanTracker.typeOfActionBannedChallenged', 'Type of action (banned, challenged, restricted)')}
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-lsc-rose mt-0.5">&#8226;</span>
                  {t('publicBanTracker.reasonGivenForTheChallenge', 'Reason given for the challenge')}
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-lsc-rose mt-0.5">&#8226;</span>
                  {t('publicBanTracker.newsArticleOrSourceLink', 'News article or source link, if available')}
                </li>
              </ul>
            </div>
            <div>
              <BanReportSubmissionForm />
            </div>
          </div>
        </div>
      </section>

      {/* About This Data */}
      <section aria-labelledby="about-data-heading">
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-6">
          <div className="flex items-center gap-2 mb-4">
            <Info className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" aria-hidden="true" />
            <h2
              id="about-data-heading"
              className="font-serif text-lg font-bold text-lsc-dark dark:text-lsc-cream"
            >
              {t('publicBanTracker.aboutThisData', 'About This Data')}
            </h2>
          </div>
          <div className="grid md:grid-cols-2 gap-6 text-sm text-lsc-dark/80 dark:text-lsc-cream/80 leading-relaxed">
            <div>
              <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-2">{t('publicBanTracker.sources', 'Sources')}</h3>
              <p className="mb-3">
                {t('publicBanTracker.banReportsAreAggregatedFrom', "Ban reports are aggregated from multiple sources including PEN America's Index of School Book Bans, the American Library Association's Office for Intellectual Freedom, news reports, and verified staff entries. Each report includes its source for transparency.")}
              </p>
              <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-2">{t('publicBanTracker.definitions', 'Definitions')}</h3>
              <ul className="space-y-1.5">
                <li><span className="font-medium">{t('publicBanTracker.bannedColon', 'Banned:')}</span> {t('publicBanTracker.removedEntirelyFromALibrary', 'Removed entirely from a library or school')}</li>
                <li><span className="font-medium">{t('publicBanTracker.restrictedColon', 'Restricted:')}</span> {t('publicBanTracker.accessLimitedEgParentalPermission', 'Access limited (e.g., parental permission required, moved to a different section)')}</li>
                <li><span className="font-medium">{t('publicBanTracker.challengedColon', 'Challenged:')}</span> {t('publicBanTracker.formalComplaintFiledRequestingRemoval', 'Formal complaint filed requesting removal, regardless of outcome')}</li>
              </ul>
            </div>
            <div>
              <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-2">{t('publicBanTracker.limitations', 'Limitations')}</h3>
              <p className="mb-3">
                {t('publicBanTracker.thisTrackerReflectsPubliclyDocumented', 'This tracker reflects publicly documented cases and may not capture every ban or challenge. Many removals happen quietly without formal reporting. Data may lag behind real-time events as reports are verified before publication.')}
              </p>
              <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-2">{t('publicBanTracker.catalogMatches', 'Catalog Matches')}</h3>
              <p>
                {t('publicBanTracker.booksMarkedInOurCatalog', { libraryShortName: branding.library_short_name })}
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Learn More Resources */}
      <section aria-labelledby="resources-heading">
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-6">
          <div className="flex items-center gap-2 mb-4">
            <Globe className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" aria-hidden="true" />
            <h2
              id="resources-heading"
              className="font-serif text-lg font-bold text-lsc-dark dark:text-lsc-cream"
            >
              {t('publicBanTracker.learnMore', 'Learn More')}
            </h2>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            <a
              href="https://pen.org/report/banned-in-the-usa/"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-start gap-3 p-4 rounded-lg border border-lsc-border dark:border-earth-700 hover:border-lsc-rose dark:hover:border-lsc-rose-light hover:shadow-md transition-all group"
            >
              <Scale className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/40 group-hover:text-lsc-rose dark:group-hover:text-lsc-rose-light flex-shrink-0 mt-0.5 transition-colors" aria-hidden="true" />
              <div>
                <div className="text-sm font-semibold text-lsc-dark dark:text-lsc-cream group-hover:text-lsc-rose dark:group-hover:text-lsc-rose-light transition-colors">PEN America</div>
                <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60">{t('publicBanTracker.indexOfSchoolBookBans', 'Index of School Book Bans, research, and advocacy resources')}</div>
              </div>
            </a>
            <a
              href="https://www.ala.org/advocacy/bbooks"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-start gap-3 p-4 rounded-lg border border-lsc-border dark:border-earth-700 hover:border-lsc-rose dark:hover:border-lsc-rose-light hover:shadow-md transition-all group"
            >
              <BookOpen className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/40 group-hover:text-lsc-rose dark:group-hover:text-lsc-rose-light flex-shrink-0 mt-0.5 transition-colors" aria-hidden="true" />
              <div>
                <div className="text-sm font-semibold text-lsc-dark dark:text-lsc-cream group-hover:text-lsc-rose dark:group-hover:text-lsc-rose-light transition-colors">{t('bannedBooks.alaBannedBooks')}</div>
                <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60">{t('publicBanTracker.frequentlyChallengedBooksBannedBooks', 'Frequently challenged books, Banned Books Week, and freedom to read')}</div>
              </div>
            </a>
            <a
              href="https://www.ala.org/aboutala/offices/oif"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-start gap-3 p-4 rounded-lg border border-lsc-border dark:border-earth-700 hover:border-lsc-rose dark:hover:border-lsc-rose-light hover:shadow-md transition-all group"
            >
              <ShieldAlert className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/40 group-hover:text-lsc-rose dark:group-hover:text-lsc-rose-light flex-shrink-0 mt-0.5 transition-colors" aria-hidden="true" />
              <div>
                <div className="text-sm font-semibold text-lsc-dark dark:text-lsc-cream group-hover:text-lsc-rose dark:group-hover:text-lsc-rose-light transition-colors">{t('publicBanTracker.officeForIntellectualFreedom', 'Office for Intellectual Freedom')}</div>
                <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60">{t('publicBanTracker.reportingToolsSupportForLibrarians', 'Reporting tools, support for librarians, and intellectual freedom resources')}</div>
              </div>
            </a>
            <Link
              to="/banned-books"
              className="flex items-start gap-3 p-4 rounded-lg border border-lsc-border dark:border-earth-700 hover:border-lsc-rose dark:hover:border-lsc-rose-light hover:shadow-md transition-all group"
            >
              <Library className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/40 group-hover:text-lsc-rose dark:group-hover:text-lsc-rose-light flex-shrink-0 mt-0.5 transition-colors" aria-hidden="true" />
              <div>
                <div className="text-sm font-semibold text-lsc-dark dark:text-lsc-cream group-hover:text-lsc-rose dark:group-hover:text-lsc-rose-light transition-colors">{t('publicBanTracker.ourIntellectualFreedomPage', 'Our Intellectual Freedom Page')}</div>
                <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60">{t('publicBanTracker.localChallengeHistoryReconsiderationRequests', 'Local challenge history, reconsideration requests, and our collection policy')}</div>
              </div>
            </Link>
            <Link
              to="/advocacy"
              className="flex items-start gap-3 p-4 rounded-lg border border-lsc-border dark:border-earth-700 hover:border-lsc-rose dark:hover:border-lsc-rose-light hover:shadow-md transition-all group"
            >
              <Megaphone className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/40 group-hover:text-lsc-rose dark:group-hover:text-lsc-rose-light flex-shrink-0 mt-0.5 transition-colors" aria-hidden="true" />
              <div>
                <div className="text-sm font-semibold text-lsc-dark dark:text-lsc-cream group-hover:text-lsc-rose dark:group-hover:text-lsc-rose-light transition-colors">{t('publicBanTracker.advocacyHub', 'Advocacy Hub')}</div>
                <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60">{t('publicBanTracker.findYourRepresentativesDraftLetters', 'Find your representatives, draft letters, and take action against censorship')}</div>
              </div>
            </Link>
            <a
              href="https://ncac.org/"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-start gap-3 p-4 rounded-lg border border-lsc-border dark:border-earth-700 hover:border-lsc-rose dark:hover:border-lsc-rose-light hover:shadow-md transition-all group"
            >
              <Users className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/40 group-hover:text-lsc-rose dark:group-hover:text-lsc-rose-light flex-shrink-0 mt-0.5 transition-colors" aria-hidden="true" />
              <div>
                <div className="text-sm font-semibold text-lsc-dark dark:text-lsc-cream group-hover:text-lsc-rose dark:group-hover:text-lsc-rose-light transition-colors">{t('publicBanTracker.nationalCoalitionAgainstCensorship', 'National Coalition Against Censorship')}</div>
                <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60">{t('publicBanTracker.anticensorshipAdvocacyLegalSupport', 'Anti-censorship advocacy, legal support, and educational materials')}</div>
              </div>
            </a>
          </div>
        </div>
      </section>

      {/* Cross-link to Advocacy */}
      <div className="bg-gradient-to-r from-lsc-rose/10 to-lsc-brown/10 dark:from-lsc-rose/20 dark:to-lsc-brown/20 rounded-xl p-8 border border-lsc-rose/20">
        <div className="flex items-start gap-4">
          <Megaphone className="w-8 h-8 text-lsc-rose dark:text-lsc-rose-light flex-shrink-0 mt-0.5" aria-hidden="true" />
          <div>
            <h2 className="font-serif text-xl font-bold text-lsc-dark dark:text-lsc-cream mb-2">
              {t('publicBanTracker.makeYourVoiceHeard', 'Make Your Voice Heard')}
            </h2>
            <p className="text-lsc-dark/80 dark:text-lsc-cream/80 text-sm leading-relaxed mb-4 max-w-2xl">
              {t('publicBanTracker.theFreedomToReadDepends', 'The freedom to read depends on people willing to stand up. Find your elected officials, write a letter, and join the fight against censorship. Our Advocacy Hub gives you the tools to take action.')}
            </p>
            <Link
              to="/advocacy"
              className="inline-flex items-center gap-2 px-5 py-2.5 bg-lsc-rose text-white font-semibold rounded-xl hover:bg-lsc-rose/90 transition-colors text-sm focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-lsc-rose dark:focus:ring-offset-earth-800"
            >
              <Megaphone className="w-4 h-4" aria-hidden="true" />
              {t('publicBanTracker.visitAdvocacyHub', 'Visit Advocacy Hub')}
              <ChevronRight className="w-4 h-4" aria-hidden="true" />
            </Link>
          </div>
        </div>
      </div>
    </StandardPageLayout>
  )
}
