/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import { useState, useEffect, useCallback, useMemo, useRef } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { useAuth } from '../contexts/AuthContext'
import {
  BarChart3, Download, FileText, Loader2, RefreshCw, ClipboardList,
  TrendingUp, DollarSign, Users, BookOpen, Shield,
  AlertCircle, Copy, Clock, Sparkles,
} from 'lucide-react'
import toast from 'react-hot-toast'
import { useTranslation } from '@/i18n'
import { listBranches } from '@/api/branch-api'
import {
  getReportTypes,
  generateJsonReport,
  generateReportAsync,
  getReportProgress,
  getReportResult,
  downloadReport,
  invalidateReportCache,
  type ReportType,
  type OutputFormat,
} from '@/api/unified-reports-api'
import { AdminShell } from '../components/shells'
import PageContainer from '@/components/layout/PageContainer'

const REPORT_TYPE_CONFIG: Record<ReportType, { label: string; icon: React.ElementType; description: string }> = {
  circulation: { label: 'Circulation', icon: BookOpen, description: 'Checkouts, returns, holds, and overdue items' },
  financial: { label: 'Financial', icon: DollarSign, description: 'Revenue, fines, payments, and budgets' },
  patron_activity: { label: 'Patron Activity', icon: Users, description: 'Registration, engagement, and demographics' },
  collection: { label: 'Collection', icon: BarChart3, description: 'Inventory, acquisitions, and collection health' },
  compliance: { label: 'Compliance', icon: Shield, description: 'State-mandated and regulatory reports' },
  community_outcomes: { label: 'Community Activity', icon: TrendingUp, description: 'Cross-cutting program reach, partnerships, and activity metrics' },
}

const FORMAT_OPTIONS: { value: OutputFormat; labelKey: string; fallback: string }[] = [
  { value: 'json', labelKey: 'unifiedReports.viewJson', fallback: 'View (JSON)' },
  { value: 'csv', labelKey: '', fallback: 'CSV' },
  { value: 'excel', labelKey: '', fallback: 'Excel' },
  { value: 'pdf', labelKey: '', fallback: 'PDF' },
]

// Render the inline JSON viewer only when the payload is small enough to be
// readable without virtualization. Anything larger gets a "Download JSON"
// fallback to avoid locking the browser tab.
const INLINE_JSON_BYTES_LIMIT = 500_000 // 500 KB

// Switch to async/background generation above this date-range threshold.
// The sync endpoint is rate-limited at 10/min and can time out for large windows.
const ASYNC_SUGGESTION_DAYS = 90
const ASYNC_PROGRESS_POLL_MS = 1500

function estimateTime(days: number): string {
  if (days <= 30) return '~5s'
  if (days <= 90) return '~15s'
  if (days <= 365) return '~30s'
  return '~60s'
}

type PresetKey = 'last7' | 'mtd' | 'qtd' | 'ytd' | 'lastFy'

function isoDate(d: Date): string {
  return d.toISOString().slice(0, 10)
}

function presetRange(key: PresetKey): { start: string; end: string } {
  const now = new Date()
  const end = isoDate(now)
  switch (key) {
    case 'last7': {
      const d = new Date(now); d.setDate(d.getDate() - 6)
      return { start: isoDate(d), end }
    }
    case 'mtd': {
      const d = new Date(now.getFullYear(), now.getMonth(), 1)
      return { start: isoDate(d), end }
    }
    case 'qtd': {
      const q = Math.floor(now.getMonth() / 3)
      const d = new Date(now.getFullYear(), q * 3, 1)
      return { start: isoDate(d), end }
    }
    case 'ytd': {
      const d = new Date(now.getFullYear(), 0, 1)
      return { start: isoDate(d), end }
    }
    case 'lastFy': {
      // Fiscal year assumed to be calendar year for now.
      const y = now.getFullYear() - 1
      return { start: `${y}-01-01`, end: `${y}-12-31` }
    }
  }
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

function daysBetween(startIso: string, endIso: string): number {
  if (!startIso || !endIso) return 0
  const s = Date.parse(startIso); const e = Date.parse(endIso)
  if (Number.isNaN(s) || Number.isNaN(e)) return 0
  return Math.max(0, Math.round((e - s) / (1000 * 60 * 60 * 24)))
}

export default function UnifiedReportsPage(): React.ReactElement {
  const { t } = useTranslation()
  const { user } = useAuth()
  const [searchParams, setSearchParams] = useSearchParams()

  // Filters are driven by URL query params so they survive reload + sharing.
  const selectedType = (searchParams.get('type') as ReportType) || 'circulation'
  const selectedFormat = (searchParams.get('format') as OutputFormat) || 'json'
  const startDate = searchParams.get('start') || ''
  const endDate = searchParams.get('end') || ''
  const branchId = searchParams.get('branch') || ''

  const setParam = useCallback((next: Record<string, string | null>) => {
    const params = new URLSearchParams(searchParams)
    for (const [k, v] of Object.entries(next)) {
      if (v === null || v === '') params.delete(k)
      else params.set(k, v)
    }
    setSearchParams(params, { replace: true })
  }, [searchParams, setSearchParams])

  const [availableTypes, setAvailableTypes] = useState<ReportType[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [reportData, setReportData] = useState<unknown>(null)
  const [reportMeta, setReportMeta] = useState<{ cacheHit: boolean; bytes: number; at: number } | null>(null)
  const [errorDetail, setErrorDetail] = useState<string | null>(null)

  // Async/background generation state.
  const [asyncState, setAsyncState] = useState<
    | { kind: 'idle' }
    | { kind: 'running'; reportId: string; progress: number; message?: string }
  >({ kind: 'idle' })
  const asyncPollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // Radio-card group ref set, for arrow-key navigation (a11y).
  const radioRefs = useRef<(HTMLButtonElement | null)[]>([])

  const { data: branchOptions = [] } = useQuery({
    queryKey: ['unified-reports:branches'],
    queryFn: () => listBranches({ active_only: true }),
    staleTime: 300_000,
  })

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const result = await getReportTypes()
        if (!cancelled) setAvailableTypes(result.report_types)
      } catch (error) {
        Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
        if (!cancelled) setAvailableTypes(['circulation', 'financial', 'patron_activity', 'collection', 'compliance'])
      }
    })()
    return () => { cancelled = true }
  }, [])

  // Stop polling on unmount.
  useEffect(() => () => {
    if (asyncPollRef.current) clearInterval(asyncPollRef.current)
  }, [])

  const commonParams = useMemo(() => ({
    report_type: selectedType,
    format: selectedFormat,
    ...(startDate ? { start_date: startDate } : {}),
    ...(endDate ? { end_date: endDate } : {}),
    ...(branchId ? { branch_id: parseInt(branchId, 10) } : {}),
  }), [selectedType, selectedFormat, startDate, endDate, branchId])

  const runSyncGenerate = useCallback(async (opts: { useCache?: boolean } = {}) => {
    setIsLoading(true)
    setErrorDetail(null)
    setReportData(null)
    setReportMeta(null)
    try {
      if (selectedFormat === 'json') {
        const result = await generateJsonReport({
          ...commonParams,
          ...(opts.useCache === false ? { use_cache: false } : {}),
        })
        setReportData(result.data)
        setReportMeta({ cacheHit: result.cacheHit, bytes: result.bytes, at: Date.now() })
        toast.success(t('toast.unifiedReports.reportGenerated'))
      } else {
        await downloadReport(commonParams)
        toast.success(t('toast.unifiedReports.touppercaseDownloadStarted', { toUpperCase: selectedFormat.toUpperCase() }))
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error)
      Sentry.captureException(error instanceof Error ? error : new Error(message))
      setErrorDetail(message)
      toast.error(message || t('toast.unifiedReports.failedToGenerateReport'))
    } finally {
      setIsLoading(false)
    }
  }, [commonParams, selectedFormat, t])

  const runAsyncGenerate = useCallback(async () => {
    setIsLoading(true)
    setErrorDetail(null)
    setReportData(null)
    setReportMeta(null)
    try {
      const job = await generateReportAsync(commonParams)
      setAsyncState({ kind: 'running', reportId: job.report_id, progress: 0 })
      toast.success(t('unifiedReports.asyncProgress'))

      if (asyncPollRef.current) clearInterval(asyncPollRef.current)
      asyncPollRef.current = setInterval(async () => {
        try {
          const progress = await getReportProgress(job.report_id)
          setAsyncState((prev) => prev.kind === 'running'
            ? { ...prev, progress: progress.progress ?? 0, ...(progress.message !== undefined && { message: progress.message }) }
            : prev)

          if (progress.status === 'completed') {
            if (asyncPollRef.current) { clearInterval(asyncPollRef.current); asyncPollRef.current = null }
            // Completion: download the resulting blob.
            try {
              const blob = await getReportResult(job.report_id)
              const url = URL.createObjectURL(blob)
              const a = document.createElement('a')
              a.href = url
              a.download = `${selectedType}_report.${selectedFormat === 'excel' ? 'xlsx' : selectedFormat}`
              document.body.appendChild(a)
              a.click()
              document.body.removeChild(a)
              URL.revokeObjectURL(url)
              toast.success(t('unifiedReports.asyncComplete'))
            } catch (dlErr) {
              Sentry.captureException(dlErr instanceof Error ? dlErr : new Error(String(dlErr)))
              toast.error(t('unifiedReports.asyncFailed'))
            }
            setAsyncState({ kind: 'idle' })
            setIsLoading(false)
          } else if (progress.status === 'failed') {
            if (asyncPollRef.current) { clearInterval(asyncPollRef.current); asyncPollRef.current = null }
            setErrorDetail(progress.error || 'Background job failed')
            toast.error(t('unifiedReports.asyncFailed'))
            setAsyncState({ kind: 'idle' })
            setIsLoading(false)
          }
        } catch (pollErr) {
          Sentry.captureException(pollErr instanceof Error ? pollErr : new Error(String(pollErr)))
        }
      }, ASYNC_PROGRESS_POLL_MS)
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error)
      Sentry.captureException(error instanceof Error ? error : new Error(message))
      setErrorDetail(message)
      toast.error(message || t('toast.unifiedReports.failedToGenerateReport'))
      setIsLoading(false)
    }
  }, [commonParams, selectedFormat, selectedType, t])

  const handleClearCache = useCallback(async () => {
    try {
      const result = await invalidateReportCache(selectedType)
      toast.success(t('toast.unifiedReports.clearedInvalidatedCachedEntries', { invalidated: result.invalidated }))
    } catch (error) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
      toast.error(t('toast.unifiedReports.failedToClearCache'))
    }
  }, [selectedType, t])

  const handleCopyError = useCallback(async () => {
    if (!errorDetail) return
    try {
      await navigator.clipboard.writeText(errorDetail)
      toast.success(t('unifiedReports.copiedError'))
    } catch (err) {
      Sentry.captureException(err instanceof Error ? err : new Error(String(err)))
    }
  }, [errorDetail, t])

  // Arrow-key navigation across the 5 report-type radio cards.
  const handleRadioKeyDown = useCallback((e: React.KeyboardEvent, idx: number, types: ReportType[]) => {
    let nextIdx = -1
    if (e.key === 'ArrowRight' || e.key === 'ArrowDown') nextIdx = (idx + 1) % types.length
    else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') nextIdx = (idx - 1 + types.length) % types.length
    else if (e.key === 'Home') nextIdx = 0
    else if (e.key === 'End') nextIdx = types.length - 1
    if (nextIdx >= 0) {
      e.preventDefault()
      setParam({ type: types[nextIdx] ?? null })
      radioRefs.current[nextIdx]?.focus()
    }
  }, [setParam])

  if (!user || !['staff', 'admin', 'super_admin', 'director'].includes(user.role)) {
    return (
      <AdminShell title="Unified Reports">
        <div className="p-8 text-center">
          <p className="text-earth-600 dark:text-earth-400">{t('unifiedReports.staffRequired')}</p>
        </div>
      </AdminShell>
    )
  }

  const rangeDays = daysBetween(startDate, endDate)
  const largeRange = rangeDays > ASYNC_SUGGESTION_DAYS
  const visibleTypes = availableTypes.length ? availableTypes : Object.keys(REPORT_TYPE_CONFIG) as ReportType[]

  return (
      <AdminShell title="Unified Reports">
    <PageContainer width="wide" className="py-8">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-8">
        <div>
          <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream flex items-center gap-3">
            <FileText className="w-8 h-8 text-library-600" aria-hidden="true" />
            {t('unifiedReports.title')}
          </h1>
          <p className="text-earth-600 dark:text-earth-400 mt-1">{t('unifiedReports.subtitle')}</p>
        </div>
        <div className="flex items-center gap-2 self-start">
          <a
            href="/staff/reports/audit-log"
            className="flex items-center gap-2 px-3 py-2 text-sm rounded-lg border border-lsc-border dark:border-earth-600 text-earth-600 dark:text-earth-400 hover:bg-earth-100 dark:hover:bg-earth-800 transition-colors"
          >
            <ClipboardList className="w-4 h-4" aria-hidden="true" />
            Audit Log
          </a>
          <button
            onClick={handleClearCache}
            className="flex items-center gap-2 px-3 py-2 text-sm rounded-lg border border-lsc-border dark:border-earth-600 text-earth-600 dark:text-earth-400 hover:bg-earth-100 dark:hover:bg-earth-800 transition-colors"
            title={t('unifiedReports.clearCacheTitle')}
          >
            <RefreshCw className="w-4 h-4" aria-hidden="true" />
            {t('unifiedReports.clearCache')}
          </button>
        </div>
      </div>

      {/* Report Type Selection */}
      <div
        role="radiogroup"
        aria-label={t('aria.unifiedReports.reportType')}
        className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4 mb-8"
      >
        {visibleTypes.map((type, idx) => {
          const config = REPORT_TYPE_CONFIG[type]
          if (!config) return null
          const Icon = config.icon
          const isSelected = type === selectedType

          return (
            <button
              key={type}
              ref={(el) => { radioRefs.current[idx] = el }}
              role="radio"
              aria-checked={isSelected}
              tabIndex={isSelected ? 0 : -1}
              onClick={() => setParam({ type })}
              onKeyDown={(e) => handleRadioKeyDown(e, idx, visibleTypes)}
              className={`p-4 rounded-xl border-2 transition-all text-left focus:outline-none focus:ring-2 focus:ring-library-500 ${
                isSelected
                  ? 'border-library-500 bg-library-50 dark:bg-library-900/20'
                  : 'border-lsc-border dark:border-earth-700 hover:border-library-300'
              }`}
            >
              <Icon className={`w-6 h-6 mb-2 ${isSelected ? 'text-library-600' : 'text-earth-600'}`} aria-hidden="true" />
              <h2 className={`font-semibold text-sm ${isSelected ? 'text-library-700 dark:text-library-300' : 'text-lsc-dark/70 dark:text-lsc-cream/70'}`}>
                {config.label}
              </h2>
              <p className="text-xs text-earth-600 dark:text-earth-400 mt-1">{config.description}</p>
            </button>
          )
        })}
      </div>

      {/* Date-range presets */}
      <div className="flex flex-wrap gap-2 mb-4">
        {([
          ['last7', t('unifiedReports.presetLast7')],
          ['mtd', t('unifiedReports.presetMtd')],
          ['qtd', t('unifiedReports.presetQtd')],
          ['ytd', t('unifiedReports.presetYtd')],
          ['lastFy', t('unifiedReports.presetLastFy')],
        ] as [PresetKey, string][]).map(([key, label]) => (
          <button
            key={key}
            type="button"
            onClick={() => {
              const { start, end } = presetRange(key)
              setParam({ start, end })
            }}
            className="px-3 py-1 text-xs rounded-full border border-lsc-border dark:border-earth-600 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-earth-100 dark:hover:bg-earth-800"
          >
            {label}
          </button>
        ))}
      </div>

      {/* Filters & Format */}
      <form
        onSubmit={(e) => {
          e.preventDefault()
          if (largeRange && selectedFormat !== 'json') runAsyncGenerate()
          else runSyncGenerate()
        }}
        className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-6 mb-8"
        aria-label={t('aria.unifiedReports.reportFilters')}
      >
        <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4">
          {t('unifiedReports.filters')}
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
          <div>
            <label htmlFor="report-start-date" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
              {t('unifiedReports.startDate')}
            </label>
            <input
              id="report-start-date"
              type="date"
              value={startDate}
              max={endDate || undefined}
              onChange={(e) => setParam({ start: e.target.value })}
              aria-label={t('unifiedReports.startDate')}
              className="w-full rounded-lg border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-900 px-3 py-2 text-sm text-lsc-dark dark:text-lsc-cream"
            />
          </div>
          <div>
            <label htmlFor="report-end-date" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
              {t('unifiedReports.endDate')}
            </label>
            <input
              id="report-end-date"
              type="date"
              value={endDate}
              min={startDate || undefined}
              onChange={(e) => setParam({ end: e.target.value })}
              aria-label={t('unifiedReports.endDate')}
              className="w-full rounded-lg border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-900 px-3 py-2 text-sm text-lsc-dark dark:text-lsc-cream"
            />
          </div>
          <div>
            <label htmlFor="report-branch" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
              {t('unifiedReports.branch')}
            </label>
            <select
              id="report-branch"
              value={branchId}
              onChange={(e) => setParam({ branch: e.target.value })}
              aria-label={t('unifiedReports.branch')}
              className="w-full rounded-lg border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-900 px-3 py-2 text-sm text-lsc-dark dark:text-lsc-cream"
            >
              <option value="">{t('placeholder.unifiedReports.allBranches')}</option>
              {branchOptions.map((b) => (
                <option key={b.id} value={b.id}>{b.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="report-format" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
              {t('unifiedReports.format')}
            </label>
            <select
              id="report-format"
              value={selectedFormat}
              onChange={(e) => setParam({ format: e.target.value })}
              aria-label={t('unifiedReports.format')}
              className="w-full rounded-lg border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-900 px-3 py-2 text-sm text-lsc-dark dark:text-lsc-cream"
            >
              {FORMAT_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.labelKey ? t(opt.labelKey) : opt.fallback}
                </option>
              ))}
            </select>
          </div>
          <div className="flex items-end">
            <button
              type="submit"
              disabled={isLoading}
              className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-library-600 hover:bg-library-700 text-white rounded-lg transition-colors disabled:opacity-50"
            >
              {isLoading
                ? <Loader2 className="w-4 h-4 motion-safe:animate-spin" aria-hidden="true" />
                : <Download className="w-4 h-4" aria-hidden="true" />}
              {isLoading ? t('unifiedReports.generating') : t('unifiedReports.generate')}
            </button>
          </div>
        </div>

        {largeRange && (
          <div className="mt-4 text-sm text-earth-600 dark:text-earth-400 flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-library-600" aria-hidden="true" />
            <span>{t('unifiedReports.asyncSuggestion')}</span>
            <button
              type="button"
              onClick={runAsyncGenerate}
              disabled={isLoading}
              className="ml-auto text-library-600 hover:text-library-700 font-medium disabled:opacity-50"
            >
              {t('unifiedReports.runAsync')}
            </button>
          </div>
        )}
      </form>

      {/* Quick Export Bar */}
      <div className="bg-earth-50 dark:bg-earth-900 rounded-xl border border-lsc-border dark:border-earth-700 p-4 mb-8">
        <div className="flex items-center justify-between flex-wrap gap-3">
          <span className="text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">
            {t('unifiedReports.quickExport')}: {REPORT_TYPE_CONFIG[selectedType]?.label}
          </span>
          <div className="flex gap-2">
            {(['csv', 'excel', 'pdf'] as OutputFormat[]).map((fmt) => (
              <button
                key={fmt}
                aria-label={`${t('unifiedReports.quickExport')} ${fmt.toUpperCase()}`}
                onClick={() => {
                  downloadReport({
                    report_type: selectedType,
                    format: fmt,
                    ...(startDate ? { start_date: startDate } : {}),
                    ...(endDate ? { end_date: endDate } : {}),
                    ...(branchId ? { branch_id: parseInt(branchId, 10) } : {}),
                  })
                    .then(() => toast.success(t('toast.unifiedReports.touppercaseDownloadStarted', { toUpperCase: fmt.toUpperCase() })))
                    .catch((err) => {
                      Sentry.captureException(err instanceof Error ? err : new Error(String(err)))
                      toast.error(t('toast.unifiedReports.failedToExportTouppercase', { toUpperCase: fmt.toUpperCase() }))
                    })
                }}
                className="flex items-center gap-1 px-3 py-1.5 text-xs font-medium rounded-lg bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-600 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-earth-100 dark:hover:bg-earth-700 transition-colors"
              >
                <Download className="w-3 h-3" aria-hidden="true" />
                {fmt.toUpperCase()}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Large range suggestion */}
      {largeRange && asyncState.kind === 'idle' && (
        <div className="bg-status-warning-50 dark:bg-status-warning-900/20 border border-status-warning-200 dark:border-status-warning-800 rounded-xl p-3 mb-4 flex items-center gap-2 text-sm">
          <Clock className="w-4 h-4 text-status-warning-600 flex-shrink-0" />
          <span className="text-status-warning-800 dark:text-status-warning-300">
            Large date range ({rangeDays} days). Estimated: {estimateTime(rangeDays)}. Background generation recommended.
          </span>
        </div>
      )}

      {/* Async progress banner */}
      {asyncState.kind === 'running' && (
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-library-200 dark:border-library-700 p-4 mb-6" aria-live="polite">
          <div className="flex items-center gap-3">
            <Loader2 className="w-5 h-5 motion-safe:animate-spin text-library-600" aria-hidden="true" />
            <div className="flex-1">
              <p className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
                Generating in background... Estimated: {estimateTime(rangeDays)}
              </p>
              {asyncState.message && (
                <p className="text-xs text-earth-600 dark:text-earth-400">{asyncState.message}</p>
              )}
              <div className="mt-2 h-1.5 bg-earth-200 dark:bg-earth-700 rounded">
                <div
                  className="h-1.5 bg-library-600 rounded transition-all"
                  style={{ width: `${Math.min(100, Math.max(5, asyncState.progress))}%` }}
                />
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Persistent error panel */}
      {errorDetail && (
        <div
          role="alert"
          className="bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-200 dark:border-status-danger-800 rounded-xl p-4 mb-6"
        >
          <div className="flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-status-danger-600 dark:text-status-danger-400 flex-shrink-0 mt-0.5" aria-hidden="true" />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold text-status-danger-800 dark:text-status-danger-200">
                {t('unifiedReports.errorTitle')}
              </p>
              <p className="text-sm text-status-danger-700 dark:text-status-danger-300 mt-1 break-words font-mono">
                {errorDetail}
              </p>
            </div>
            <button
              type="button"
              onClick={handleCopyError}
              className="flex items-center gap-1 px-2 py-1 text-xs rounded border border-status-danger-300 dark:border-status-danger-700 text-status-danger-700 dark:text-status-danger-300 hover:bg-status-danger-100 dark:hover:bg-status-danger-900/40"
            >
              <Copy className="w-3 h-3" aria-hidden="true" />
              {t('unifiedReports.copyError')}
            </button>
          </div>
        </div>
      )}

      {/* Report Data Display */}
      <div aria-live="polite">
        {reportData != null && reportMeta && (
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-6">
            <div className="flex items-center justify-between flex-wrap gap-3 mb-4">
              <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream flex items-center gap-2">
                <TrendingUp className="w-5 h-5 text-library-600" aria-hidden="true" />
                {t('unifiedReports.results')}
              </h2>
              <div className="flex items-center gap-3">
                <span className="inline-flex items-center gap-1 text-xs text-earth-600 dark:text-earth-400">
                  <Clock className="w-3 h-3" aria-hidden="true" />
                  {reportMeta.cacheHit ? t('unifiedReports.cached') : t('unifiedReports.fresh')}
                  {' · '}{formatBytes(reportMeta.bytes)}
                </span>
                {reportMeta.cacheHit && (
                  <button
                    type="button"
                    onClick={() => runSyncGenerate({ useCache: false })}
                    disabled={isLoading}
                    className="inline-flex items-center gap-1 px-2 py-1 text-xs rounded border border-lsc-border dark:border-earth-600 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-earth-100 dark:hover:bg-earth-800 disabled:opacity-50"
                  >
                    <RefreshCw className="w-3 h-3" aria-hidden="true" />
                    {t('unifiedReports.regenerateFresh')}
                  </button>
                )}
              </div>
            </div>

            {reportMeta.bytes > INLINE_JSON_BYTES_LIMIT ? (
              <div className="bg-earth-50 dark:bg-earth-900 rounded-lg p-6 text-center">
                <p className="text-sm text-earth-600 dark:text-earth-400 mb-3">
                  {t('unifiedReports.downloadLargeJson', { size: formatBytes(reportMeta.bytes) })}
                </p>
                <button
                  type="button"
                  onClick={() => {
                    const blob = new Blob([JSON.stringify(reportData, null, 2)], { type: 'application/json' })
                    const url = URL.createObjectURL(blob)
                    const a = document.createElement('a')
                    a.href = url
                    a.download = `${selectedType}_report.json`
                    document.body.appendChild(a)
                    a.click()
                    document.body.removeChild(a)
                    URL.revokeObjectURL(url)
                  }}
                  className="inline-flex items-center gap-2 px-4 py-2 bg-library-600 hover:bg-library-700 text-white rounded-lg text-sm"
                >
                  <Download className="w-4 h-4" aria-hidden="true" />
                  {t('unifiedReports.downloadJson')}
                </button>
              </div>
            ) : (
              <pre className="bg-earth-50 dark:bg-earth-900 rounded-lg p-4 overflow-auto max-h-[600px] text-sm text-earth-800 dark:text-earth-200 font-mono">
                {JSON.stringify(reportData, null, 2)}
              </pre>
            )}
          </div>
        )}

        {!reportData && !errorDetail && !isLoading && asyncState.kind === 'idle' && (
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-dashed border-lsc-border dark:border-earth-600 p-10 text-center">
            <FileText className="w-10 h-10 mx-auto text-earth-600 mb-3" aria-hidden="true" />
            <p className="text-sm text-earth-600 dark:text-earth-400">
              {t('unifiedReports.emptyState')}
            </p>
          </div>
        )}
      </div>
    </PageContainer>
  
      </AdminShell>
    )
}
