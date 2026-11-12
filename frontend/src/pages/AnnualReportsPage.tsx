/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import { useState, useEffect } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { FileText, Plus, RotateCcw, CheckCircle, AlertCircle, Loader2 } from 'lucide-react'
import toast from 'react-hot-toast'
import {
  listAnnualReports,
  generateAnnualReport,
  AnnualReport,
} from '../api/annual-reports-api'
import GenerateReportModal from '../components/annual-reports/GenerateReportModal'
import ReportsList from '../components/annual-reports/ReportsList'
import { useTranslation} from '@/i18n'
import { AdminShell } from '../components/shells/AdminShell'

const STATES = [
  { code: 'OH', name: 'Ohio' },
]

const currentYear = new Date().getFullYear()
const FISCAL_YEARS = Array.from({ length: 10 }, (_, i) => currentYear - i)

export default function AnnualReportsPage(): React.ReactElement {
  const { t } = useTranslation()
  const { user, token } = useAuth()
  const [reports, setReports] = useState<AnnualReport[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [showGenerateModal, setShowGenerateModal] = useState(false)
  const [filterFiscalYear, setFilterFiscalYear] = useState<number | undefined>()
  const [filterStateCode, setFilterStateCode] = useState<string | undefined>()
  const [refreshing, setRefreshing] = useState(false)

  const loadReports = async (fiscalYear?: number, stateCode?: string) => {
    if (!token) return

    setIsLoading(true)
    try {
      const data = await listAnnualReports(token, fiscalYear ?? filterFiscalYear, stateCode ?? filterStateCode)
      setReports(data.reports || [])
    } catch (err: unknown) {
      Sentry.captureException(err instanceof Error ? err : new Error(String(err)))
      toast.error(t('annualReports.failedToLoadAnnualReports'))
      setReports([])
    } finally {
      setIsLoading(false)
    }
  }


  // Check authentication
  useEffect(() => {
    if (!user) {
      toast.error(t('toast.authenticationRequired'))
      return
    }

    if (!['admin', 'super_admin', 'staff', 'director'].includes(user.role)) {
      toast.error(t('toast.acquisitionManagement.staffAccessRequired'))
      return
    }

    loadReports()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user])

  const handleGenerateReport = async (
    fiscalYear: number,
    stateCode: string,
    libraryName: string
  ) => {
    if (!token) {
      toast.error(t('toast.authenticationRequired'))
      return
    }

    setRefreshing(true)
    try {
      await generateAnnualReport(token, {
        fiscal_year: fiscalYear,
        state_code: stateCode,
        library_name: libraryName,
      })

      toast.success(t('toast.annualReports.annualReportGeneratedForFyfiscalyear', { fiscalYear: fiscalYear }))
      setShowGenerateModal(false)

      // Refresh the list
      await loadReports()
    } catch (err: unknown) {
      Sentry.captureException(err instanceof Error ? err : new Error(String(err)))
      toast.error(t('annualReports.failedToGenerateAnnualReport'))
    } finally {
      setRefreshing(false)
    }
  }

  const handleFilterChange = () => {
    loadReports(filterFiscalYear, filterStateCode)
  }

  return (

    <AdminShell
      title="State Annual Reports"
      subtitle="Automated state annual report generation with pre-populated statistical data"
      icon={<FileText className="w-8 h-8 text-lsc-rose dark:text-lsc-rose-light" />}
      actions={
        <button
          onClick={() => setShowGenerateModal(true)}
          className="flex items-center gap-2 bg-lsc-rose text-white px-4 py-2 rounded-lg hover:bg-lsc-rose/90 transition"
        >
          <Plus className="w-5 h-5" />
          Generate Report
        </button>
      }
    >

        {/* Quick Stats */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
          <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Total Reports</p>
                <p className="text-3xl font-bold text-lsc-dark dark:text-lsc-cream">{reports.length}</p>
              </div>
              <FileText className="w-8 h-8 text-lsc-rose dark:text-lsc-rose-light" />
            </div>
          </div>
          <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Validated</p>
                <p className="text-3xl font-bold text-status-success-600">
                  {reports.filter((r) => r.is_validated).length}
                </p>
              </div>
              <CheckCircle className="w-8 h-8 text-status-success-600" />
            </div>
          </div>
          <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Needs Review</p>
                <p className="text-3xl font-bold text-status-warning-600">
                  {reports.filter((r) => !r.is_validated).length}
                </p>
              </div>
              <AlertCircle className="w-8 h-8 text-status-warning-600" />
            </div>
          </div>
        </div>

        {/* Filters */}
        <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow p-4 mb-6">
          <div className="flex flex-col md:flex-row gap-4">
            <div className="flex-1">
              <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">
                Fiscal Year
              </label>
              <select
                value={filterFiscalYear || ''}
                onChange={(e) => {
                  setFilterFiscalYear(e.target.value ? parseInt(e.target.value) : undefined)
                }}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-lsc-rose"
              >
                <option value="">All Years</option>
                {FISCAL_YEARS.map((year) => (
                  <option key={year} value={year}>
                    FY{year}
                  </option>
                ))}
              </select>
            </div>
            <div className="flex-1">
              <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">State</label>
              <select
                value={filterStateCode || ''}
                onChange={(e) => setFilterStateCode(e.target.value || undefined)}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-lsc-rose"
              >
                <option value="">All States</option>
                {STATES.map((state) => (
                  <option key={state.code} value={state.code}>
                    {state.name}
                  </option>
                ))}
              </select>
            </div>
            <div className="flex items-end gap-2">
              <button
                onClick={handleFilterChange}
                className="flex items-center gap-2 bg-earth-600 text-white px-4 py-2 rounded-lg hover:bg-earth-700 transition"
              >
                <RotateCcw className="w-4 h-4" />
                Apply Filters
              </button>
            </div>
          </div>
        </div>

        {/* Reports List */}
        {isLoading ? (
          <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow p-8 text-center">
            <Loader2 className="w-8 h-8 text-lsc-rose dark:text-lsc-rose-light motion-safe:animate-spin mx-auto mb-4" />
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70">Loading reports...</p>
          </div>
        ) : reports.length > 0 ? (
          <ReportsList reports={reports} onRefresh={loadReports} />
        ) : (
          <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow p-8 text-center">
            <FileText className="w-12 h-12 text-lsc-dark/70 dark:text-lsc-cream/70 mx-auto mb-4" />
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">{t('annualReports.noAnnualReportsFound')}</p>
            <button
              onClick={() => setShowGenerateModal(true)}
              className="inline-flex items-center gap-2 bg-lsc-rose text-white px-4 py-2 rounded-lg hover:bg-lsc-rose/90 transition"
            >
              <Plus className="w-4 h-4" />
              Create First Report
            </button>
          </div>
        )}
        {/* Generate Report Modal */}
      {showGenerateModal && (
        <GenerateReportModal
          onClose={() => setShowGenerateModal(false)}
          onGenerate={handleGenerateReport}
          isLoading={refreshing}
          states={STATES}
          fiscalYears={FISCAL_YEARS}
        />
      )}
    </AdminShell>
  )
}
