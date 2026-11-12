/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { Eye, Download, CheckCircle, AlertCircle, DollarSign, ShieldCheck } from 'lucide-react'
import toast from 'react-hot-toast'
import { AnnualReport, exportAsExcel, downloadFile } from '../../api/annual-reports-api'
import { useAuth } from '../../contexts/AuthContext'
import ReportDetailsModal from './ReportDetailsModal'
import FinanceEntryModal from './FinanceEntryModal'
import { getCurrentLocale } from '@/i18n'

interface ReportsListProps {
  reports: AnnualReport[]
  onRefresh: () => Promise<void>
}

const STATUS_COLORS = {
  draft: { bg: 'bg-earth-100 dark:bg-earth-700', text: 'text-earth-800 dark:text-earth-100', icon: 'text-earth-600' },
  generated: { bg: 'bg-earth-100 dark:bg-earth-800/30', text: 'text-earth-800 dark:text-lsc-rose-light', icon: 'text-earth-600' },
  validated: { bg: 'bg-status-success-100 dark:bg-status-success-900/30', text: 'text-status-success-800 dark:text-status-success-300', icon: 'text-status-success-500' },
  submitted: { bg: 'bg-category-100 dark:bg-category-900/30', text: 'text-category-800 dark:text-category-300', icon: 'text-category-500' },
  rejected: { bg: 'bg-status-danger-100 dark:bg-status-danger-900/30', text: 'text-status-danger-800 dark:text-status-danger-300', icon: 'text-status-danger-500' },
}

export default function ReportsList({
  reports,
  onRefresh,
}: ReportsListProps): React.ReactElement {
  const { token } = useAuth()
  const [selectedReport, setSelectedReport] = useState<AnnualReport | null>(null)
  const [showDetailsModal, setShowDetailsModal] = useState(false)
  const [financeReport, setFinanceReport] = useState<AnnualReport | null>(null)

  const handleExport = async (report: AnnualReport) => {
    if (!token) return
    try {
      const blob = await exportAsExcel(token, report.id)
      downloadFile(blob, `Annual-Report-FY${report.fiscal_year}-${report.state_code}.xlsx`)
      toast.success('Report exported')
    } catch {
      toast.error('Failed to export report')
    }
  }

  const handleViewDetails = (report: AnnualReport) => {
    setSelectedReport(report)
    setShowDetailsModal(true)
  }

  const formatDate = (dateString: string) => {
    if (!dateString) return "N/A"
    const date = new Date(dateString)
    if (isNaN(date.getTime())) return "N/A"
    return date.toLocaleDateString(getCurrentLocale(), {
      year: "numeric",
      month: "short",
      day: "numeric",
    })
  }

  return (
    <>
      <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow overflow-hidden">
        <table className="w-full">
          <thead className="bg-earth-50 dark:bg-earth-900 border-b">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 uppercase">
                Fiscal Year
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 uppercase">
                State
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 uppercase">
                Library
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 uppercase">
                Status
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 uppercase">
                Created
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 uppercase">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {reports.map((report) => {
              const statusConfig = STATUS_COLORS[report.status as keyof typeof STATUS_COLORS] || STATUS_COLORS.draft
              return (
                <tr key={report.id} className="hover:bg-earth-50 dark:bg-earth-900 dark:hover:bg-earth-800">
                  <td className="px-6 py-4 text-sm font-medium text-lsc-dark dark:text-lsc-cream">
                    FY{report.fiscal_year}
                  </td>
                  <td className="px-6 py-4 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{report.state_code}</td>
                  <td className="px-6 py-4 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{report.library_name}</td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-2">
                      {report.is_validated ? (
                        <CheckCircle className="w-4 h-4 text-status-success-600" />
                      ) : (
                        <AlertCircle className="w-4 h-4 text-status-warning-600" />
                      )}
                      <span
                        className={`inline-block px-3 py-1 rounded-full text-xs font-medium ${statusConfig.bg} ${statusConfig.text}`}
                      >
                        {report.status.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')}
                      </span>
                    </div>
                  </td>
                  <td className="px-6 py-4 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                    {formatDate(String(report.generated_at ?? ''))}
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => handleViewDetails(report)}
                        className="inline-flex items-center gap-1 text-lsc-rose dark:text-lsc-rose-light hover:text-lsc-rose dark:text-lsc-rose-light text-sm"
                        title="View details"
                      >
                        <Eye className="w-4 h-4" />
                        View
                      </button>
                      <button
                        onClick={() => setFinanceReport(report)}
                        className="inline-flex items-center gap-1 text-earth-700 dark:text-earth-200 hover:text-lsc-rose dark:hover:text-lsc-rose-light text-sm"
                        title="Enter director finance"
                      >
                        <DollarSign className="w-4 h-4" />
                        Finance
                      </button>
                      {report.status !== 'submitted' && !report.is_validated && (
                        <button
                          onClick={() => handleViewDetails(report)}
                          className="inline-flex items-center gap-1 text-earth-700 dark:text-earth-200 hover:text-lsc-rose dark:hover:text-lsc-rose-light text-sm"
                          title="Certify report"
                        >
                          <ShieldCheck className="w-4 h-4" />
                          Certify
                        </button>
                      )}
                      {report.status !== 'draft' && (
                        <button
                          onClick={() => handleExport(report)}
                          className="inline-flex items-center gap-1 text-status-success-600 hover:text-status-success-800 dark:text-status-success-300 text-sm"
                          title="Download report"
                        >
                          <Download className="w-4 h-4" />
                          Export
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {/* Details Modal */}
      {showDetailsModal && selectedReport && (
        <ReportDetailsModal
          report={selectedReport}
          onClose={() => setShowDetailsModal(false)}
          onRefresh={onRefresh}
        />
      )}

      {/* Finance Entry Modal */}
      {financeReport && (
        <FinanceEntryModal
          report={financeReport}
          onClose={() => setFinanceReport(null)}
          onSaved={onRefresh}
        />
      )}
    </>
  )
}
