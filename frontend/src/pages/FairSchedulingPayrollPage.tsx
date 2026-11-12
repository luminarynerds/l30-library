/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import {
  DollarSign,
  Download,
  CheckCircle,
  Clock,
  FileText,
  Loader2,
  AlertTriangle,
} from 'lucide-react'
import toast from 'react-hot-toast'
import { useAuth } from '../contexts/AuthContext'
import { AdminShell } from '../components/shells/AdminShell'
import { fairSchedulingApi } from '../api/fair-scheduling-api'

interface PayrollSummary {
  pay_period_start: string
  pay_period_end: string
  total_records: number
  total_regular_hours: number
  total_overtime_hours: number
  total_holiday_hours: number
  staff_details: Record<string, unknown>[]
  records_with_discrepancy: number
  pending_approval: number
}

interface PayrollExport {
  batch_id: string
  export_status: 'pending' | 'exported' | 'confirmed' | 'error'
  total_records: number
  total_regular_hours: number
  total_overtime_hours: number
  total_holiday_hours: number
  export_format: string
  exported_at: string | null
  error_message: string | null
}

const statusBadgeClass: Record<string, string> = {
  exported: 'bg-lsc-green text-white',
  confirmed: 'bg-status-info-500 text-white',
  pending: 'bg-status-warning-500 text-white',
  error: 'bg-status-danger-600 text-white',
}

export default function FairSchedulingPayrollPage(): React.ReactElement {
  useAuth()

  const [periodStart, setPeriodStart] = useState('')
  const [periodEnd, setPeriodEnd] = useState('')
  const [branchId, setBranchId] = useState<string>('')
  const [exportFormat, setExportFormat] = useState('csv')

  const [summary, setSummary] = useState<PayrollSummary | null>(null)
  const [exportResult, setExportResult] = useState<PayrollExport | null>(null)

  const [generating, setGenerating] = useState(false)
  const [loadingSummary, setLoadingSummary] = useState(false)
  const [exporting, setExporting] = useState(false)
  const [approving, setApproving] = useState(false)
  const [showApproveConfirm, setShowApproveConfirm] = useState(false)

  const buildParams = () => ({
    pay_period_start: periodStart,
    pay_period_end: periodEnd,
    ...(branchId ? { branch_id: Number(branchId) } : {}),
  })

  const validatePeriod = (): boolean => {
    if (!periodStart || !periodEnd) {
      toast.error('Please select both start and end dates')
      return false
    }
    if (periodStart > periodEnd) {
      toast.error('Start date must be before end date')
      return false
    }
    return true
  }

  const handleGenerate = async () => {
    if (!validatePeriod()) return
    setGenerating(true)
    try {
      await fairSchedulingApi.generatePayroll(buildParams())
      toast.success('Payroll generated successfully')
    } catch {
      toast.error('Failed to generate payroll')
    } finally {
      setGenerating(false)
    }
  }

  const handleViewSummary = async () => {
    if (!validatePeriod()) return
    setLoadingSummary(true)
    try {
      const res = await fairSchedulingApi.getPayrollSummary({
        pay_period_start: periodStart,
        pay_period_end: periodEnd,
        ...(branchId ? { branch_id: Number(branchId) } : {}),
      })
      setSummary(res as PayrollSummary)
    } catch {
      toast.error('Failed to load payroll summary')
    } finally {
      setLoadingSummary(false)
    }
  }

  const handleExport = async () => {
    if (!validatePeriod()) return
    setExporting(true)
    try {
      const res = await fairSchedulingApi.exportPayroll({
        ...buildParams(),
        export_format: exportFormat,
      })
      setExportResult(res as PayrollExport)
      toast.success('Payroll export initiated')
    } catch {
      toast.error('Failed to export payroll')
    } finally {
      setExporting(false)
    }
  }

  const handleApprove = async () => {
    setShowApproveConfirm(false)
    setApproving(true)
    try {
      const res = (await fairSchedulingApi.approvePayroll({
        pay_period_start: periodStart,
        pay_period_end: periodEnd,
      })) as { approved_count?: number }
      toast.success(`Approved ${res.approved_count ?? 0} payroll records`)
    } catch {
      toast.error('Failed to approve payroll')
    } finally {
      setApproving(false)
    }
  }

  const statCards = summary
    ? [
        { label: 'Total Records', value: summary.total_records, icon: FileText },
        { label: 'Regular Hours', value: summary.total_regular_hours, icon: Clock },
        { label: 'Overtime Hours', value: summary.total_overtime_hours, icon: DollarSign },
        { label: 'Holiday Hours', value: summary.total_holiday_hours, icon: CheckCircle },
        { label: 'Discrepancies', value: summary.records_with_discrepancy, icon: AlertTriangle },
        { label: 'Pending Approval', value: summary.pending_approval, icon: Clock },
      ]
    : []

  const staffDetailKeys =
    summary?.staff_details?.length
      ? Object.keys(summary.staff_details[0] ?? {})
      : []

  return (
    <AdminShell
      title="Payroll Integration"
      subtitle="Generate and manage payroll from scheduled hours"
    >
      <div className="space-y-6">
        {/* Period Selector */}
        <div className="rounded-xl p-6 bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700">
          <h2 className="text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4">
            Pay Period
          </h2>
          <div className="flex flex-wrap gap-4 items-end">
            <div>
              <label className="block text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                Start Date
              </label>
              <input
                type="date"
                value={periodStart}
                onChange={(e) => setPeriodStart(e.target.value)}
                className="rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream px-3 py-2"
              />
            </div>
            <div>
              <label className="block text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                End Date
              </label>
              <input
                type="date"
                value={periodEnd}
                onChange={(e) => setPeriodEnd(e.target.value)}
                className="rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream px-3 py-2"
              />
            </div>
            <div>
              <label className="block text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                Branch ID (optional)
              </label>
              <input
                type="number"
                value={branchId}
                onChange={(e) => setBranchId(e.target.value)}
                placeholder="All branches"
                className="rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream px-3 py-2 w-40"
              />
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-wrap gap-3">
          <button
            onClick={handleGenerate}
            disabled={generating}
            className="bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-lg px-4 py-2 inline-flex items-center gap-2 disabled:opacity-50"
          >
            {generating ? (
              <Loader2 className="h-4 w-4 motion-safe:animate-spin" />
            ) : (
              <DollarSign className="h-4 w-4" />
            )}
            Generate Payroll
          </button>
          <button
            onClick={handleViewSummary}
            disabled={loadingSummary}
            className="bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-lg px-4 py-2 inline-flex items-center gap-2 disabled:opacity-50"
          >
            {loadingSummary ? (
              <Loader2 className="h-4 w-4 motion-safe:animate-spin" />
            ) : (
              <FileText className="h-4 w-4" />
            )}
            View Summary
          </button>
          <button
            onClick={handleExport}
            disabled={exporting}
            className="bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-lg px-4 py-2 inline-flex items-center gap-2 disabled:opacity-50"
          >
            {exporting ? (
              <Loader2 className="h-4 w-4 motion-safe:animate-spin" />
            ) : (
              <Download className="h-4 w-4" />
            )}
            Export
          </button>
          <button
            onClick={() => {
              if (!validatePeriod()) return
              setShowApproveConfirm(true)
            }}
            disabled={approving}
            className="bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-lg px-4 py-2 inline-flex items-center gap-2 disabled:opacity-50"
          >
            {approving ? (
              <Loader2 className="h-4 w-4 motion-safe:animate-spin" />
            ) : (
              <CheckCircle className="h-4 w-4" />
            )}
            Approve
          </button>
        </div>

        {/* Approve Confirmation Dialog */}
        {showApproveConfirm && (
          <div className="rounded-xl p-6 bg-lsc-white dark:bg-earth-800 border-2 border-status-danger-400 dark:border-status-danger-600">
            <div className="flex items-start gap-3">
              <AlertTriangle className="h-5 w-5 text-status-danger-600 shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold text-lsc-dark dark:text-lsc-cream">
                  Confirm Payroll Approval
                </p>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                  This will approve all pending payroll records for{' '}
                  {periodStart} to {periodEnd}. This action cannot be undone.
                </p>
                <div className="flex gap-3 mt-4">
                  <button
                    onClick={handleApprove}
                    className="bg-status-danger-600 hover:bg-status-danger-700 text-white rounded-lg px-4 py-2 text-sm"
                  >
                    Yes, Approve
                  </button>
                  <button
                    onClick={() => setShowApproveConfirm(false)}
                    className="border border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream rounded-lg px-4 py-2 text-sm"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Summary Stats */}
        {summary && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {statCards.map((stat) => (
                <div
                  key={stat.label}
                  className="rounded-xl p-6 bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700"
                >
                  <div className="flex items-center gap-3 mb-2">
                    <stat.icon className="h-5 w-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
                    <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                      {stat.label}
                    </span>
                  </div>
                  <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">
                    {stat.value}
                  </p>
                </div>
              ))}
            </div>

            {/* Staff Details Table */}
            {summary.staff_details?.length > 0 && (
              <div className="rounded-xl bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 overflow-hidden">
                <h3 className="text-lg font-semibold text-lsc-dark dark:text-lsc-cream p-6 pb-0">
                  Staff Details
                </h3>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm text-left">
                    <thead>
                      <tr className="border-b border-lsc-border dark:border-earth-700">
                        {staffDetailKeys.map((key) => (
                          <th
                            key={key}
                            className="px-6 py-3 text-lsc-dark/70 dark:text-lsc-cream/70 font-medium"
                          >
                            {key.replace(/_/g, ' ')}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {summary.staff_details.map((row, idx) => (
                        <tr
                          key={idx}
                          className="border-b border-lsc-border dark:border-earth-700 last:border-0"
                        >
                          {staffDetailKeys.map((key) => (
                            <td
                              key={key}
                              className="px-6 py-3 text-lsc-dark dark:text-lsc-cream"
                            >
                              {String(row[key] ?? '')}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Export Section */}
        <div className="rounded-xl p-6 bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700">
          <h2 className="text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4">
            Export Options
          </h2>
          <div className="flex flex-wrap items-end gap-4">
            <div>
              <label className="block text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                Format
              </label>
              <select
                value={exportFormat}
                onChange={(e) => setExportFormat(e.target.value)}
                className="rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream px-3 py-2"
              >
                <option value="csv">CSV</option>
                <option value="xlsx">XLSX</option>
                <option value="json">JSON</option>
              </select>
            </div>
            <button
              onClick={handleExport}
              disabled={exporting}
              className="bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-lg px-4 py-2 inline-flex items-center gap-2 disabled:opacity-50"
            >
              {exporting ? (
                <Loader2 className="h-4 w-4 motion-safe:animate-spin" />
              ) : (
                <Download className="h-4 w-4" />
              )}
              Export Payroll
            </button>
          </div>

          {exportResult && (
            <div className="mt-4 p-4 rounded-lg border border-lsc-border dark:border-earth-700">
              <div className="flex items-center gap-3 mb-2">
                <span className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
                  Batch: {exportResult.batch_id}
                </span>
                <span
                  className={`text-xs px-2 py-0.5 rounded-full font-medium ${statusBadgeClass[exportResult.export_status] ?? 'bg-earth-400 dark:bg-earth-500 text-white'}`}
                >
                  {exportResult.export_status}
                </span>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                <span>Records: {exportResult.total_records}</span>
                <span>Regular: {exportResult.total_regular_hours}h</span>
                <span>Overtime: {exportResult.total_overtime_hours}h</span>
                <span>Holiday: {exportResult.total_holiday_hours}h</span>
              </div>
              {exportResult.exported_at && (
                <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-2">
                  Exported: {new Date(exportResult.exported_at).toLocaleString()}
                </p>
              )}
              {exportResult.error_message && (
                <p className="text-xs text-status-danger-600 mt-2 flex items-center gap-1">
                  <AlertTriangle className="h-3 w-3" />
                  {exportResult.error_message}
                </p>
              )}
            </div>
          )}
        </div>
      </div>
    </AdminShell>
  )
}
