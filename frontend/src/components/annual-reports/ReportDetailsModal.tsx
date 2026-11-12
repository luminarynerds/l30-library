/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import { useState } from 'react'
import { X, Download, AlertCircle, CheckCircle, Loader2, ShieldCheck } from 'lucide-react'
import toast from 'react-hot-toast'
import {
  AnnualReport,
  AnnualReportValidationError,
  WebsiteTrafficSection,
  validateAnnualReport,
  certifyAnnualReport,
  getReconciliation,
  getYoYComparison,
  exportAsExcel,
  exportAsPdf,
  downloadFile,
  formatCurrency,
  formatNumber,
  formatPercent,
  YoYComparison,
  ValidationResponse,
  ReconciliationResponse,
} from '@/api/annual-reports-api'
import { useAuth } from '@/contexts/AuthContext'
import { ApiError } from '@/lib/api-client'
import { useTranslation} from '@/i18n'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

// A reconciliation field is "stale" only when there's a real, non-zero drift.
// drift === null means the live source could not be compared (not a drift), and
// `null !== 0` is true in JS, so we must guard against null explicitly.
function isStaleField(drift: number | null): boolean {
  return drift !== null && drift !== 0
}

// Extracts the inline validation errors from a 409 certify failure. The app
// reshapes HTTPException(detail=dict) into { error: { code, message: <dict> } },
// so the structured detail (with the errors array) lives at body.error.message.
function extractCertifyErrors(err: unknown): AnnualReportValidationError[] {
  if (!(err instanceof ApiError) || err.status !== 409) return []
  const body = err.body as
    | { error?: { message?: { errors?: AnnualReportValidationError[] } } }
    | undefined
  return body?.error?.message?.errors ?? []
}

// Type helper to safely access metric properties
function getMetric(report: AnnualReport, key: string): number | undefined {
  const value = report[key]
  return typeof value === 'number' ? value : undefined
}

// Helper to safely get number from YoY Record
function getYoYValue(record: Record<string, number | string | boolean | null | undefined>, key: string): number | undefined {
  const value = record[key]
  return typeof value === 'number' ? value : undefined
}

// Helper to safely get growth percentage
function getGrowthPercent(record: Record<string, number | null>, key: string): number | undefined {
  const value = record[key]
  return typeof value === 'number' ? value : undefined
}

interface ReportDetailsModalProps {
  report: AnnualReport
  onClose: () => void
  onRefresh: () => Promise<void>
}

export default function ReportDetailsModal({
  report: sourceReport,
  onClose,
  onRefresh,
}: ReportDetailsModalProps): React.ReactElement {
  const [certification, setCertification] = useState<{
    source: AnnualReport
    status: AnnualReport['status']
    is_validated: boolean
  } | null>(null)
  const report = certification?.source === sourceReport
    ? { ...sourceReport, status: certification.status, is_validated: certification.is_validated }
    : sourceReport
  const { t } = useTranslation()
  const { token } = useAuth()
  const [activeTab, setActiveTab] = useState<
    'overview' | 'statistics' | 'yoy' | 'reconciliation' | 'validation'
  >('overview')
  const [validationData, setValidationData] = useState<ValidationResponse | null>(null)
  const [yoyData, setYoYData] = useState<YoYComparison | null>(null)
  const [reconciliation, setReconciliation] = useState<ReconciliationResponse | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [isExporting, setIsExporting] = useState(false)
  const [isCertifying, setIsCertifying] = useState(false)
  // Inline blocking errors from the most recent 409 certify attempt.
  const [certifyErrors, setCertifyErrors] = useState<AnnualReportValidationError[]>([])

  // Validation errors already persisted on the report object (surfaced on open).
  const persistedErrors = Array.isArray(report.validation_errors)
    ? report.validation_errors
    : []

  const handleCertify = async () => {
    if (!token) return
    setIsCertifying(true)
    setCertifyErrors([])
    try {
      const result = await certifyAnnualReport(token, report.id)
      toast.success('Report certified')
      // Reflect the new status locally so the chip flips without a re-fetch flicker.
      setCertification({
        source: sourceReport,
        status: result.status as AnnualReport['status'],
        is_validated: result.is_validated,
      })
      await onRefresh()
    } catch (err: unknown) {
      if (err instanceof ApiError && err.status === 409) {
        const errors = extractCertifyErrors(err)
        setCertifyErrors(errors)
        toast.error(
          errors.length
            ? `Certification blocked: ${errors.length} validation error(s)`
            : 'Certification blocked'
        )
      } else if (err instanceof ApiError && err.status === 404) {
        toast.error('Report not found')
      } else {
        Sentry.captureException(err instanceof Error ? err : new Error(String(err)))
        toast.error('Failed to certify report')
      }
    } finally {
      setIsCertifying(false)
    }
  }

  const handleLoadReconciliation = async () => {
    if (!token) return
    setIsLoading(true)
    try {
      const data = await getReconciliation(token, report.id)
      setReconciliation(data)
    } catch (err: unknown) {
      Sentry.captureException(err instanceof Error ? err : new Error(String(err)))
      toast.error('Failed to load reconciliation')
    } finally {
      setIsLoading(false)
    }
  }

  const handleValidate = async () => {
    if (!token) return
    setIsLoading(true)
    try {
      const data = await validateAnnualReport(token, report.id)
      setValidationData(data)
      if (data.is_valid) {
        toast.success(t('toast.annual-reports.reportIsValid'))
      } else {
        toast.error(t('toast.annual-reports.reportHasErrorcountValidationErrors', { errorcount: data.error_count }))
      }
      await onRefresh()
    } catch (err: unknown) {
      Sentry.captureException(err instanceof Error ? err : new Error(String(err)))
      toast.error(t('components.annualReports.reportDetails.failedToValidateReport'))
    } finally {
      setIsLoading(false)
    }
  }

  const handleLoadYoY = async () => {
    if (!token) return
    setIsLoading(true)
    try {
      const data = await getYoYComparison(token, report.id)
      setYoYData(data)
    } catch (err: unknown) {
      Sentry.captureException(err instanceof Error ? err : new Error(String(err)))
      toast.error(t('components.annualReports.reportDetails.failedToLoadYearOver'))
    } finally {
      setIsLoading(false)
    }
  }

  const handleExportExcel = async () => {
    if (!token) return
    setIsExporting(true)
    try {
      const blob = await exportAsExcel(token, report.id)
      downloadFile(blob, `Annual-Report-FY${report.fiscal_year}-${report.state_code}.xlsx`)
      toast.success(t('components.annualReports.reportDetails.reportExportedAsExcel'))
      await onRefresh()
    } catch (err: unknown) {
      Sentry.captureException(err instanceof Error ? err : new Error(String(err)))
      toast.error(t('components.annualReports.reportDetails.failedToExportReport'))
    } finally {
      setIsExporting(false)
    }
  }

  const handleExportPdf = async () => {
    if (!token) return
    setIsExporting(true)
    try {
      const blob = await exportAsPdf(token, report.id)
      downloadFile(blob, `Annual-Report-FY${report.fiscal_year}-${report.state_code}.pdf`)
      toast.success(t('components.annualReports.reportDetails.reportExportedAsPdf'))
      await onRefresh()
    } catch (err: unknown) {
      Sentry.captureException(err instanceof Error ? err : new Error(String(err)))
      toast.error(t('components.annualReports.reportDetails.failedToExportReport2'))
    } finally {
      setIsExporting(false)
    }
  }

  return (
    <ModalBackdrop onClose={onClose} title={`FY${report.fiscal_year} ${report.state_code} Report`}>
      <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-lg max-w-4xl w-full mx-4 max-h-[80vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b sticky top-0 bg-lsc-white dark:bg-earth-800">
          <div className="flex items-center gap-3">
            <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
              FY{report.fiscal_year} {report.state_code} Report
            </h2>
            {reconciliation && reconciliation.fields.some((f) => isStaleField(f.drift)) && (
              <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-800 dark:text-status-warning-300">
                <AlertCircle className="w-3.5 h-3.5" />
                Stale
              </span>
            )}
          </div>
          <button onClick={onClose} className="text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-earth-700 dark:hover:text-earth-200">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b sticky top-16 bg-lsc-white dark:bg-earth-800">
          {(['overview', 'statistics', 'yoy', 'reconciliation', 'validation'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-3 font-medium text-sm transition ${
                activeTab === tab
                  ? 'border-b-2 border-lsc-rose text-lsc-rose dark:text-lsc-rose-light'
                  : 'text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-earth-900 dark:hover:text-earth-100'
              }`}
            >
              {tab.charAt(0).toUpperCase() + tab.slice(1)}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="p-6">
          {activeTab === 'overview' && (
            <div className="space-y-6">
              {/* Basic Info */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Library Name</p>
                  <p className="font-medium text-lsc-dark dark:text-lsc-cream">{report.library_name}</p>
                </div>
                <div>
                  <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Library ID</p>
                  <p className="font-medium text-lsc-dark dark:text-lsc-cream">{report.library_id || 'N/A'}</p>
                </div>
                <div>
                  <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Fiscal Year</p>
                  <p className="font-medium text-lsc-dark dark:text-lsc-cream">FY{report.fiscal_year}</p>
                </div>
                <div>
                  <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">State</p>
                  <p className="font-medium text-lsc-dark dark:text-lsc-cream">{report.state_code}</p>
                </div>
              </div>

              {/* Status */}
              <div className="bg-earth-50 dark:bg-earth-800/20 border border-lsc-border dark:border-earth-700 rounded p-4">
                <div className="flex items-start gap-3">
                  {report.is_validated ? (
                    <CheckCircle className="w-5 h-5 text-status-success-600 flex-shrink-0 mt-0.5" />
                  ) : (
                    <AlertCircle className="w-5 h-5 text-status-warning-600 flex-shrink-0 mt-0.5" />
                  )}
                  <div>
                    <p className="font-medium text-lsc-dark dark:text-lsc-cream">
                      Status: {report.status.charAt(0).toUpperCase() + report.status.slice(1)}
                    </p>
                    <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                      {report.is_validated
                        ? 'This report has been validated and is ready for submission.'
                        : 'This report needs to be validated before submission.'}
                    </p>
                  </div>
                </div>
              </div>

              {/* Blocking validation errors: persisted on the report, plus any from
                  the most recent 409 certify attempt. */}
              {(persistedErrors.length > 0 || certifyErrors.length > 0) && (
                <div className="bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-200 dark:border-status-danger-800 rounded p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <AlertCircle className="w-5 h-5 text-status-danger-600" />
                    <p className="font-medium text-status-danger-900 dark:text-status-danger-200">
                      Certification is blocked by validation errors
                    </p>
                  </div>
                  <ul className="space-y-1 ml-7 list-disc">
                    {[...persistedErrors, ...certifyErrors].map((error, idx) => (
                      <li key={`${error.field}-${idx}`} className="text-sm text-status-danger-700 dark:text-status-danger-300">
                        <span className="font-medium">{error.field}</span>
                        <span className="ml-1">{error.message}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Actions */}
              <div className="flex gap-3 flex-wrap">
                {report.status !== 'submitted' && (
                  <button
                    onClick={handleValidate}
                    disabled={isLoading}
                    className="px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 transition disabled:opacity-50 flex items-center gap-2"
                  >
                    {isLoading && <Loader2 className="w-4 h-4 motion-safe:animate-spin" />}
                    {report.is_validated ? 'Re-validate' : 'Validate Report'}
                  </button>
                )}
                {report.status !== 'submitted' && !report.is_validated && (
                  <button
                    onClick={handleCertify}
                    disabled={isCertifying}
                    className="px-4 py-2 bg-status-success-600 text-white rounded-lg hover:bg-status-success-700 transition disabled:opacity-50 flex items-center gap-2"
                  >
                    {isCertifying && <Loader2 className="w-4 h-4 motion-safe:animate-spin" />}
                    <ShieldCheck className="w-4 h-4" />
                    Certify
                  </button>
                )}
                <button
                  onClick={handleExportExcel}
                  disabled={isExporting}
                  className="px-4 py-2 bg-status-success-600 text-white rounded-lg hover:bg-status-success-700 transition disabled:opacity-50 flex items-center gap-2"
                >
                  {isExporting && <Loader2 className="w-4 h-4 motion-safe:animate-spin" />}
                  <Download className="w-4 h-4" />
                  Export Excel
                </button>
                <button
                  onClick={handleExportPdf}
                  disabled={isExporting}
                  className="px-4 py-2 bg-status-danger-600 text-white rounded-lg hover:bg-status-danger-700 transition disabled:opacity-50 flex items-center gap-2"
                >
                  {isExporting && <Loader2 className="w-4 h-4 motion-safe:animate-spin" />}
                  <Download className="w-4 h-4" />
                  Export PDF
                </button>
              </div>
            </div>
          )}

          {activeTab === 'statistics' && (
            <div className="space-y-6">
              {/* Key Metrics */}
              <div>
                <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4">Key Performance Indicators</h3>
                <div className="grid grid-cols-2 gap-4">
                  <MetricCard
                    label="Total Checkouts"
                    value={formatNumber(getMetric(report, 'total_checkouts'))}
                  />
                  <MetricCard
                    label="Total Patrons"
                    value={formatNumber(getMetric(report, 'total_registered_patrons'))}
                  />
                  <MetricCard
                    label="Active Patrons"
                    value={formatNumber(getMetric(report, 'active_patrons'))}
                  />
                  <MetricCard
                    label="Programs Offered"
                    value={formatNumber(getMetric(report, 'total_programs_offered'))}
                  />
                  <MetricCard
                    label="Program Attendance"
                    value={formatNumber(getMetric(report, 'total_program_attendance'))}
                  />
                  <MetricCard label="Library Visits" value={formatNumber(getMetric(report, 'total_library_visits'))} />
                  <MetricCard
                    label="Items Owned"
                    value={formatNumber(getMetric(report, 'total_items_owned'))}
                  />
                  <MetricCard
                    label="Items Added"
                    value={formatNumber(getMetric(report, 'items_added_during_year'))}
                  />
                </div>
              </div>

              {/* Financial */}
              <div>
                <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4">Financial Metrics</h3>
                <div className="grid grid-cols-2 gap-4">
                  <MetricCard
                    label="Total Revenue"
                    value={formatCurrency(getMetric(report, 'total_operating_revenue'))}
                  />
                  <MetricCard
                    label="Total Expenditure"
                    value={formatCurrency(getMetric(report, 'total_operating_expenditure'))}
                  />
                  <MetricCard
                    label="Personnel Costs"
                    value={formatCurrency(getMetric(report, 'personnel_expenditure'))}
                  />
                  <MetricCard
                    label="Collection Costs"
                    value={formatCurrency(getMetric(report, 'collection_expenditure'))}
                  />
                </div>
              </div>

              {/* Operational */}
              <div>
                <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4">Operational Metrics</h3>
                <div className="grid grid-cols-2 gap-4">
                  <MetricCard
                    label="Total Staff FTE"
                    value={(() => {
                      const fte = getMetric(report, 'total_staff_fte')
                      return fte !== undefined ? fte.toFixed(2) : 'N/A'
                    })()}
                  />
                  <MetricCard
                    label="Hours Open/Year"
                    value={formatNumber(getMetric(report, 'total_hours_open_per_year'))}
                  />
                  <MetricCard
                    label="Building Sq Ft"
                    value={formatNumber(getMetric(report, 'building_square_footage'))}
                  />
                  <MetricCard
                    label="Public Computers"
                    value={formatNumber(getMetric(report, 'public_computer_stations'))}
                  />
                </div>
              </div>

              {/* Website Traffic */}
              <WebsiteTrafficBlock traffic={report.website_traffic ?? null} />
            </div>
          )}

          {activeTab === 'yoy' && (
            <div className="space-y-6">
              {!yoyData ? (
                <button
                  onClick={handleLoadYoY}
                  disabled={isLoading}
                  className="w-full px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 transition disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  {isLoading && <Loader2 className="w-4 h-4 motion-safe:animate-spin" />}
                  Load Year-over-Year Comparison
                </button>
              ) : (
                <>
                  <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">Growth Metrics</h3>
                  <div className="grid grid-cols-2 gap-4">
                    <YoYCard
                      label="Checkout Growth"
                      value={formatPercent(getGrowthPercent(yoyData.growth_percent, 'checkouts'))}
                      current={getYoYValue(yoyData.current_year, 'total_checkouts')}
                      prior={getYoYValue(yoyData.prior_year, 'total_checkouts')}
                    />
                    <YoYCard
                      label="Patron Growth"
                      value={formatPercent(getGrowthPercent(yoyData.growth_percent, 'patrons'))}
                      current={getYoYValue(yoyData.current_year, 'total_patrons')}
                      prior={getYoYValue(yoyData.prior_year, 'total_patrons')}
                    />
                    <YoYCard
                      label="Visit Growth"
                      value={formatPercent(getGrowthPercent(yoyData.growth_percent, 'visits'))}
                      current={getYoYValue(yoyData.current_year, 'total_visits')}
                      prior={getYoYValue(yoyData.prior_year, 'total_visits')}
                    />
                    <YoYCard
                      label="Program Growth"
                      value={formatPercent(getGrowthPercent(yoyData.growth_percent, 'programs'))}
                      current={getYoYValue(yoyData.current_year, 'total_programs')}
                      prior={getYoYValue(yoyData.prior_year, 'total_programs')}
                    />
                  </div>
                </>
              )}
            </div>
          )}

          {activeTab === 'reconciliation' && (
            <div className="space-y-6">
              {!reconciliation ? (
                <button
                  onClick={handleLoadReconciliation}
                  disabled={isLoading}
                  className="w-full px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 transition disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  {isLoading && <Loader2 className="w-4 h-4 motion-safe:animate-spin" />}
                  Load Reconciliation
                </button>
              ) : (
                <ReconciliationTable reconciliation={reconciliation} />
              )}
            </div>
          )}

          {activeTab === 'validation' && (
            <div className="space-y-6">
              {!validationData ? (
                <button
                  onClick={handleValidate}
                  disabled={isLoading}
                  className="w-full px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 transition disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  {isLoading && <Loader2 className="w-4 h-4 motion-safe:animate-spin" />}
                  Run Validation
                </button>
              ) : (
                <>
                  <div className="flex items-center gap-3 p-4 bg-earth-50 dark:bg-earth-800/20 border border-lsc-border dark:border-earth-700 rounded">
                    {validationData.is_valid ? (
                      <>
                        <CheckCircle className="w-5 h-5 text-status-success-600" />
                        <p className="text-status-success-800 dark:text-status-success-300">
                          <strong>Valid:</strong> Report passes all validation rules
                        </p>
                      </>
                    ) : (
                      <>
                        <AlertCircle className="w-5 h-5 text-status-danger-600" />
                        <p className="text-status-danger-800 dark:text-status-danger-300">
                          <strong>Invalid:</strong> {validationData.error_count} error(s) found
                        </p>
                      </>
                    )}
                  </div>

                  {validationData.errors.length > 0 && (
                    <div>
                      <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-3">Validation Errors</h3>
                      <div className="space-y-2">
                        {validationData.errors.map((error, idx) => (
                          <div key={idx} className="bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-200 dark:border-status-danger-800 rounded p-3">
                            <p className="font-medium text-status-danger-900 dark:text-status-danger-200">{error.field}</p>
                            <p className="text-sm text-status-danger-700 dark:text-status-danger-300 mt-1">{error.message}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="border-t p-4 flex justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 border border-lsc-border dark:border-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70 rounded-lg hover:bg-earth-50 dark:bg-earth-900 dark:hover:bg-earth-800 transition"
          >
            Close
          </button>
        </div>
      </div>
    </ModalBackdrop>
  )
}

// Helper component for metrics
function MetricCard({
  label,
  value,
}: {
  label: string
  value: string
}): React.ReactElement {
  return (
    <div className="bg-earth-50 dark:bg-earth-900 rounded p-3">
      <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{label}</p>
      <p className="text-lg font-semibold text-lsc-dark dark:text-lsc-cream mt-1">{value}</p>
    </div>
  )
}

// Reconciliation table: stored report value vs. live source value, with drift.
// Any field with a real non-zero drift is flagged amber.
function ReconciliationTable({
  reconciliation,
}: {
  reconciliation: ReconciliationResponse
}): React.ReactElement {
  const staleCount = reconciliation.fields.filter((f) => isStaleField(f.drift)).length
  return (
    <div className="space-y-4">
      <div
        className={`flex items-center gap-3 p-4 rounded border ${
          staleCount > 0
            ? 'bg-status-warning-50 dark:bg-status-warning-900/20 border-status-warning-200 dark:border-status-warning-800'
            : 'bg-status-success-50 dark:bg-status-success-900/20 border-status-success-200 dark:border-status-success-800'
        }`}
      >
        {staleCount > 0 ? (
          <>
            <AlertCircle className="w-5 h-5 text-status-warning-600" />
            <p className="text-status-warning-800 dark:text-status-warning-300">
              <strong>{staleCount}</strong> field(s) drifted from the live source. This report
              may be stale.
            </p>
          </>
        ) : (
          <>
            <CheckCircle className="w-5 h-5 text-status-success-600" />
            <p className="text-status-success-800 dark:text-status-success-300">
              All fields match the live source.
            </p>
          </>
        )}
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-lsc-border dark:border-earth-700 text-left text-lsc-dark/70 dark:text-lsc-cream/70">
              <th className="px-3 py-2 font-medium">Field</th>
              <th className="px-3 py-2 font-medium text-right">Stored value</th>
              <th className="px-3 py-2 font-medium text-right">Live source</th>
              <th className="px-3 py-2 font-medium text-right">Drift</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-lsc-border dark:divide-earth-700">
            {reconciliation.fields.map((f) => {
              const stale = isStaleField(f.drift)
              return (
                <tr
                  key={f.field}
                  data-testid={`recon-row-${f.field}`}
                  className={
                    stale ? 'bg-status-warning-50 dark:bg-status-warning-900/20' : undefined
                  }
                >
                  <td className="px-3 py-2 font-medium text-lsc-dark dark:text-lsc-cream">
                    {f.field}
                  </td>
                  <td className="px-3 py-2 text-right tabular-nums text-lsc-dark dark:text-lsc-cream">
                    {f.report_value ?? '—'}
                  </td>
                  <td className="px-3 py-2 text-right tabular-nums text-lsc-dark dark:text-lsc-cream">
                    {f.live_source_value ?? '—'}
                  </td>
                  <td
                    className={`px-3 py-2 text-right tabular-nums font-medium ${
                      stale
                        ? 'text-status-warning-700 dark:text-status-warning-300'
                        : 'text-lsc-dark/70 dark:text-lsc-cream/70'
                    }`}
                  >
                    {f.drift ?? '—'}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// Helper component for YoY metrics
function YoYCard({
  label,
  value,
  current,
  prior,
}: {
  label: string
  value: string
  current: number | undefined
  prior: number | undefined
}): React.ReactElement {
  const isPositive = value !== 'N/A' && !value.includes('-')

  return (
    <div className={`rounded p-3 ${isPositive ? 'bg-status-success-50 dark:bg-status-success-900/20 border border-status-success-200 dark:border-status-success-800' : 'bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-200 dark:border-status-danger-800'}`}>
      <p className={`text-xs font-medium ${isPositive ? 'text-status-success-700 dark:text-status-success-300' : 'text-status-danger-700 dark:text-status-danger-300'}`}>
        {label}
      </p>
      <p className={`text-xl font-bold mt-1 ${isPositive ? 'text-status-success-900 dark:text-status-success-200' : 'text-status-danger-900'}`}>
        {value}
      </p>
      <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-2">
        Current: {formatNumber(current)} | Prior: {formatNumber(prior)}
      </p>
    </div>
  )
}

// Helper component for the website traffic section (Umami data)
function WebsiteTrafficBlock({
  traffic,
}: {
  traffic: WebsiteTrafficSection | null
}): React.ReactElement {
  return (
    <div>
      <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4">
        Website Traffic
      </h3>

      {!traffic || !traffic.available ? (
        <div className="bg-earth-50 dark:bg-earth-800/20 border border-lsc-border dark:border-earth-700 rounded p-4 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
          Website analytics were unavailable for this fiscal year. Configure
          Umami and regenerate this report to populate digital-reach numbers.
        </div>
      ) : (
        <div className="space-y-4">
          <div className="grid grid-cols-3 gap-4">
            <MetricCard label="Pageviews" value={formatNumber(traffic.pageviews ?? undefined)} />
            <MetricCard label="Unique Visitors" value={formatNumber(traffic.visitors ?? undefined)} />
            <MetricCard label="Visits" value={formatNumber(traffic.visits ?? undefined)} />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <TrafficList title="Top Pages" rows={traffic.top_pages} />
            <TrafficList title="Top Referrers" rows={traffic.top_referrers} />
            <TrafficList title="Top Countries" rows={traffic.top_countries} />
          </div>
        </div>
      )}
    </div>
  )
}

function TrafficList({
  title,
  rows,
}: {
  title: string
  rows: WebsiteTrafficSection['top_pages']
}): React.ReactElement {
  return (
    <div className="bg-earth-50 dark:bg-earth-900 rounded p-3">
      <p className="text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">
        {title}
      </p>
      {rows.length === 0 ? (
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">No data</p>
      ) : (
        <ol className="space-y-1 text-sm text-lsc-dark dark:text-lsc-cream">
          {rows.map((row, idx) => (
            <li key={`${row.label}-${idx}`} className="flex justify-between gap-3">
              <span className="truncate">{row.label || '(unknown)'}</span>
              <span className="font-medium tabular-nums">{formatNumber(row.count)}</span>
            </li>
          ))}
        </ol>
      )}
    </div>
  )
}
