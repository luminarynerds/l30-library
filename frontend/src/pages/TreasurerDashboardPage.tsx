/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React, { useState, useEffect } from 'react'
import { useAuth } from '../contexts/AuthContext'
import {
  DollarSign,
  Download,
  AlertCircle,
  CheckCircle,
  Clock,
  FileText,
  Loader2,
  Search,
  Eye,
  Save,
  X,
  Lock,
  FileDown,
} from 'lucide-react'
import toast from 'react-hot-toast'
import { listBillingRecords, recordPayment, type ConsortiumBilling, type BillingStatus } from '../api/consortium-api'
import { useTranslation, getCurrentLocale } from '@/i18n'
import { AdminShell } from '../components/shells/AdminShell'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'
import PageContainer from '@/components/layout/PageContainer'

type StatusFilter = 'all' | BillingStatus

interface FilterOptions {
  status: StatusFilter
  dateFrom: string
  dateTo: string
  consortiumId: string | null
}

interface PaymentModalState {
  isOpen: boolean
  billingId: number | null
  paymentReference: string
  isProcessing: boolean
}

// Status badge styles
const STATUS_STYLES: Record<BillingStatus, { bg: string; text: string; icon: React.ReactNode }> = {
  pending: {
    bg: 'bg-status-warning-100 dark:bg-status-warning-900/30',
    text: 'text-status-warning-700 dark:text-status-warning-400',
    icon: <Clock className="w-4 h-4" />,
  },
  invoiced: {
    bg: 'bg-earth-100 dark:bg-earth-800/30',
    text: 'text-lsc-rose dark:text-lsc-rose-light',
    icon: <FileText className="w-4 h-4" />,
  },
  paid: {
    bg: 'bg-status-success-100 dark:bg-status-success-900/30',
    text: 'text-status-success-700 dark:text-status-success-400',
    icon: <CheckCircle className="w-4 h-4" />,
  },
  overdue: {
    bg: 'bg-status-danger-100 dark:bg-status-danger-900/30',
    text: 'text-status-danger-700 dark:text-status-danger-400',
    icon: <AlertCircle className="w-4 h-4" />,
  },
  disputed: {
    bg: 'bg-status-warning-100 dark:bg-status-warning-900/30',
    text: 'text-status-warning-700 dark:text-status-warning-400',
    icon: <AlertCircle className="w-4 h-4" />,
  },
  cancelled: {
    bg: 'bg-earth-100 dark:bg-earth-900/30',
    text: 'text-lsc-dark/70 dark:text-lsc-cream/70',
    icon: <CheckCircle className="w-4 h-4" />,
  },
}

export default function TreasurerDashboardPage() {
  const { t } = useTranslation()
  const { token, user } = useAuth()
  const [billingRecords, setBillingRecords] = useState<ConsortiumBilling[]>([])
  const [loading, setLoading] = useState(false)
  const [searchTerm, setSearchTerm] = useState('')
  const [filters, setFilters] = useState<FilterOptions>({
    status: 'all',
    dateFrom: '',
    dateTo: '',
    consortiumId: null,
  })
  const [expandedRows, setExpandedRows] = useState<Set<number>>(new Set())
  const [downloadingId, setDownloadingId] = useState<number | null>(null)
  const [paymentModal, setPaymentModal] = useState<PaymentModalState>({
    isOpen: false,
    billingId: null,
    paymentReference: '',
    isProcessing: false,
  })

  // Check if user has permission to manage payments
  const canManagePayments = user && ['admin', 'super_admin'].includes(user.role)
  const canDownload = user && ['admin', 'staff', 'super_admin'].includes(user.role)

  // Load billing records
  useEffect(() => {
    if (!token) return

    const loadBillingData = async () => {
      try {
        setLoading(true)

        // Get billing records - use consortiumId 1 as default
        const consortiumId = filters.consortiumId ? parseInt(filters.consortiumId) : 1
        const records = await listBillingRecords(consortiumId, {
          ...(filters.status !== 'all' && { status: filters.status }),
          ...(filters.dateFrom && { from_date: filters.dateFrom }),
          ...(filters.dateTo && { to_date: filters.dateTo }),
        })

        setBillingRecords(records)

      } catch (err: unknown) {
        toast.error(err instanceof Error ? err.message : t('toast.admin.failedToLoadBillingData'))
      } finally {
        setLoading(false)
      }
    }

    loadBillingData()
  }, [token, filters, t])

  // Check if user has permission to access this page
  if (!user || !['admin', 'staff', 'super_admin'].includes(user.role)) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-lsc-cream to-lsc-cream/50 dark:from-earth-900 dark:to-earth-900/50 flex items-center justify-center">
        <div className="text-center">
          <Lock className="w-16 h-16 text-status-danger-600 dark:text-status-danger-400 mx-auto mb-4" />
          <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-2">Staff-Only Area</h1>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('treasurerDashboard.youDonTHavePermission')}</p>
        </div>
      </div>
    )
  }

  // Download invoice
  const handleDownload = async (billingId: number, format: 'pdf' | 'csv') => {
    if (!token || !canDownload) {
      toast.error(t('treasurerDashboard.youDoNotHavePermission'))
      return
    }

    try {
      setDownloadingId(billingId)
      const endpoint = `/consortiums/billing/${billingId}/export/${format}`

      // eslint-disable-next-line no-restricted-syntax -- CSV/PDF invoice export, blob response
      const response = await fetch(`${import.meta.env.VITE_API_URL}${endpoint}`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      })

      if (!response.ok) {
        throw new Error('Failed to download invoice')
      }

      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url

      const record = billingRecords.find((r) => r.id === billingId)
      a.download = `invoice_${record?.invoice_number || billingId}.${format}`

      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)

      toast.success(t('toast.treasurerDashboard.invoiceDownloadedAsTouppercase', { toUpperCase: format.toUpperCase() }))
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : t('toast.treasurerDashboard.failedToDownloadInvoice'))
    } finally {
      setDownloadingId(null)
    }
  }

  // Bulk export all invoices as CSV
  const handleBulkExportCSV = async () => {
    if (!token || !canDownload) {
      toast.error(t('treasurerDashboard.youDoNotHavePermission2'))
      return
    }

    try {
      setDownloadingId(-1) // Use -1 for bulk export loading state
      const endpoint = `/consortiums/${filters.consortiumId || 1}/billing/export/csv-summary`

      const params = new URLSearchParams()
      if (filters.status !== 'all') params.append('status', filters.status)
      if (filters.dateFrom) params.append('from_date', filters.dateFrom)
      if (filters.dateTo) params.append('to_date', filters.dateTo)

      // eslint-disable-next-line no-restricted-syntax -- CSV bulk export, blob response
      const response = await fetch(`${import.meta.env.VITE_API_URL}${endpoint}?${params.toString()}`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      })

      if (!response.ok) {
        throw new Error('Failed to export invoices')
      }

      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `invoices-export-${new Date().toISOString().split('T')[0]}.csv`

      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)

      toast.success(t('toast.treasurerDashboard.exportedLengthInvoices', { length: filteredRecords.length }))
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : t('toast.treasurerDashboard.failedToExportInvoices'))
    } finally {
      setDownloadingId(null)
    }
  }

  // Record payment
  const handleRecordPayment = async () => {
    if (!token || !canManagePayments) {
      toast.error(t('treasurerDashboard.youDoNotHavePermission3'))
      return
    }

    if (!paymentModal.billingId) return

    try {
      setPaymentModal((prev) => ({ ...prev, isProcessing: true }))

      await recordPayment(token, paymentModal.billingId, paymentModal.paymentReference || undefined)

      toast.success(t('toast.treasurerDashboard.paymentRecordedSuccessfully'))
      setPaymentModal({ isOpen: false, billingId: null, paymentReference: '', isProcessing: false })

      // Reload billing records
      const consortiumId = filters.consortiumId ? parseInt(filters.consortiumId) : 1
      const records = await listBillingRecords(consortiumId, {
        ...(filters.status !== 'all' && { status: filters.status }),
        ...(filters.dateFrom && { from_date: filters.dateFrom }),
        ...(filters.dateTo && { to_date: filters.dateTo }),
      })

      setBillingRecords(records)
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : t('toast.admin.failedToRecordPayment'))
    } finally {
      setPaymentModal((prev) => ({ ...prev, isProcessing: false }))
    }
  }

  // Open payment modal
  const openPaymentModal = (billingId: number) => {
    if (!canManagePayments) {
      toast.error(t('treasurerDashboard.youDoNotHavePermission4'))
      return
    }
    setPaymentModal({ isOpen: true, billingId, paymentReference: '', isProcessing: false })
  }

  // Toggle row expansion
  const toggleRow = (billingId: number) => {
    const newExpanded = new Set(expandedRows)
    if (newExpanded.has(billingId)) {
      newExpanded.delete(billingId)
    } else {
      newExpanded.add(billingId)
    }
    setExpandedRows(newExpanded)
  }

  // Filter and search records
  const filteredRecords = billingRecords.filter((record) => {
    const searchLower = searchTerm.toLowerCase()
    return (
      record.invoice_number?.toLowerCase().includes(searchLower) ||
      record.description?.toLowerCase().includes(searchLower)
    )
  })

  // Calculate statistics
  const stats = {
    total: filteredRecords.length,
    pending: filteredRecords.filter((r) => r.status === 'pending').length,
    invoiced: filteredRecords.filter((r) => r.status === 'invoiced').length,
    paid: filteredRecords.filter((r) => r.status === 'paid').length,
    overdue: filteredRecords.filter((r) => r.status === 'overdue').length,
    totalAmount: filteredRecords.reduce((sum, r) => sum + parseFloat(r.total_amount), 0),
    paidAmount: filteredRecords
      .filter((r) => r.status === 'paid')
      .reduce((sum, r) => sum + parseFloat(r.total_amount), 0),
    outstandingAmount: filteredRecords
      .filter((r) => r.status === 'invoiced' || r.status === 'overdue')
      .reduce((sum, r) => sum + parseFloat(r.total_amount), 0),
  }

  return (

    <AdminShell title="Treasurer Dashboard">    <div className="min-h-screen bg-gradient-to-br from-lsc-cream to-lsc-cream/50 dark:from-earth-900 dark:to-earth-900/50">
      <PageContainer width="wide" className="py-8">
        {/* Header */}
        <div className="mb-8 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-2">
              Treasurer Dashboard
            </h1>
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
              Manage consortium billing, invoices, and payments
            </p>
          </div>
          {canDownload && (
            <button
              onClick={handleBulkExportCSV}
              disabled={loading || downloadingId !== null}
              className="flex items-center gap-2 px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-xl font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {downloadingId === -1 ? (
                <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
              ) : (
                <FileDown className="w-4 h-4" />
              )}
              Export All
            </button>
          )}
        </div>

        {/* Statistics Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-6">
            <div className="flex items-center justify-between mb-4">
              <p className="text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Total Invoiced</p>
              <DollarSign className="w-5 h-5 text-lsc-rose" />
            </div>
            <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">
              ${stats.totalAmount.toLocaleString(getCurrentLocale(), { maximumFractionDigits: 2 })}
            </p>
            <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-2">{stats.total} invoices</p>
          </div>

          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-6">
            <div className="flex items-center justify-between mb-4">
              <p className="text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Paid</p>
              <CheckCircle className="w-5 h-5 text-status-success-600" />
            </div>
            <p className="text-2xl font-bold text-status-success-600 dark:text-status-success-400">
              ${stats.paidAmount.toLocaleString(getCurrentLocale(), { maximumFractionDigits: 2 })}
            </p>
            <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-2">{stats.paid} paid invoices</p>
          </div>

          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-6">
            <div className="flex items-center justify-between mb-4">
              <p className="text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Outstanding</p>
              <Clock className="w-5 h-5 text-status-warning-600" />
            </div>
            <p className="text-2xl font-bold text-status-warning-600 dark:text-status-warning-400">
              ${stats.outstandingAmount.toLocaleString(getCurrentLocale(), { maximumFractionDigits: 2 })}
            </p>
            <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-2">
              {stats.invoiced + stats.overdue} pending
            </p>
          </div>

          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-6">
            <div className="flex items-center justify-between mb-4">
              <p className="text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Overdue</p>
              <AlertCircle className="w-5 h-5 text-status-danger-600" />
            </div>
            <p className="text-2xl font-bold text-status-danger-600 dark:text-status-danger-400">{stats.overdue}</p>
            <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-2">Requires action</p>
          </div>
        </div>

        {/* Filters and Search */}
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-6 mb-8">
          <div className="flex flex-col gap-4">
            {/* Search */}
            <div className="relative">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
              <input
                type="text"
                placeholder={t('placeholder.treasurerDashboard.searchInvoicesMembers')}
                aria-label={t('aria.treasurerDashboard.searchInvoicesMembers')}
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-12 pr-4 py-2 bg-lsc-cream/50 dark:bg-earth-700 border border-lsc-border dark:border-earth-700 rounded-xl text-lsc-dark dark:text-lsc-cream placeholder-earth-500 dark:placeholder-earth-500 focus:outline-none focus:ring-2 focus:ring-lsc-rose"
              />
            </div>

            {/* Filter Controls */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div>
                <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
                  Status
                </label>
                <select
                  value={filters.status}
                  onChange={(e) => setFilters({ ...filters, status: e.target.value as StatusFilter })}
                  className="w-full px-4 py-2 bg-lsc-cream/50 dark:bg-earth-700 border border-lsc-border dark:border-earth-700 rounded-xl text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose"
                >
                  <option value="all">All Statuses</option>
                  <option value="pending">Pending</option>
                  <option value="invoiced">Invoiced</option>
                  <option value="paid">Paid</option>
                  <option value="overdue">Overdue</option>
                  <option value="disputed">Disputed</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
                  From Date
                </label>
                <input
                  type="date"
                  value={filters.dateFrom}
                  onChange={(e) => setFilters({ ...filters, dateFrom: e.target.value })}
                  className="w-full px-4 py-2 bg-lsc-cream/50 dark:bg-earth-700 border border-lsc-border dark:border-earth-700 rounded-xl text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
                  To Date
                </label>
                <input
                  type="date"
                  value={filters.dateTo}
                  onChange={(e) => setFilters({ ...filters, dateTo: e.target.value })}
                  className="w-full px-4 py-2 bg-lsc-cream/50 dark:bg-earth-700 border border-lsc-border dark:border-earth-700 rounded-xl text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose"
                />
              </div>

              <div className="flex items-end">
                <button
                  onClick={() =>
                    setFilters({
                      status: 'all',
                      dateFrom: '',
                      dateTo: '',
                      consortiumId: null,
                    })
                  }
                  className="w-full px-4 py-2 bg-lsc-cream/50 dark:bg-earth-700 border border-lsc-border dark:border-earth-700 rounded-xl text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-earth-600 transition-colors font-medium"
                >
                  Reset Filters
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Invoices Table */}
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 overflow-hidden">
          {loading ? (
            <div className="flex justify-center py-12">
              <Loader2 className="w-8 h-8 text-lsc-rose motion-safe:animate-spin" />
            </div>
          ) : filteredRecords.length === 0 ? (
            <div className="p-12 text-center">
              <FileText className="w-16 h-16 text-lsc-dark/30 dark:text-lsc-cream/60 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-lsc-dark dark:text-lsc-cream mb-2">No invoices found</h3>
              <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
                Adjust your filters or check back when invoices are generated.
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="bg-lsc-cream/50 dark:bg-earth-700/50 border-b border-lsc-border dark:border-earth-700">
                    <th className="px-6 py-4 text-left text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
                      Invoice
                    </th>
                    <th className="px-6 py-4 text-left text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
                      Billing Period
                    </th>
                    <th className="px-6 py-4 text-left text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
                      Member
                    </th>
                    <th className="px-6 py-4 text-left text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
                      Amount
                    </th>
                    <th className="px-6 py-4 text-left text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
                      Status
                    </th>
                    <th className="px-6 py-4 text-left text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
                      Due Date
                    </th>
                    <th className="px-6 py-4 text-right text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {filteredRecords.map((record) => (
                    <React.Fragment key={record.id}>
                      <tr className="border-b border-lsc-border dark:border-earth-700 hover:bg-lsc-cream/30 dark:hover:bg-earth-700/30 transition-colors">
                        <td className="px-6 py-4">
                          <div className="flex items-center gap-2">
                            <span className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
                              {record.invoice_number || `INV-${record.id}`}
                            </span>
                          </div>
                        </td>
                        <td className="px-6 py-4 text-sm text-lsc-dark dark:text-lsc-cream">
                          {new Date(record.billing_period_start).toLocaleDateString()} -{' '}
                          {new Date(record.billing_period_end).toLocaleDateString()}
                        </td>
                        <td className="px-6 py-4 text-sm text-lsc-dark dark:text-lsc-cream">
                          <div>
                            <p className="font-medium">
                              Member #{record.billed_member_id}
                            </p>
                            <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                              Billed by Member #{record.billing_member_id}
                            </p>
                          </div>
                        </td>
                        <td className="px-6 py-4 text-sm font-medium text-lsc-dark dark:text-lsc-cream">
                          ${parseFloat(record.total_amount).toFixed(2)}
                        </td>
                        <td className="px-6 py-4">
                          <div className="flex items-center gap-2">
                            {STATUS_STYLES[record.status].icon}
                            <span
                              className={`inline-flex px-2 py-1 rounded-full text-xs font-medium ${STATUS_STYLES[record.status].bg} ${STATUS_STYLES[record.status].text}`}
                            >
                              {record.status}
                            </span>
                          </div>
                        </td>
                        <td className="px-6 py-4 text-sm text-lsc-dark dark:text-lsc-cream">
                          {record.due_date ? new Date(record.due_date).toLocaleDateString() : '-'}
                        </td>
                        <td className="px-6 py-4">
                          <div className="flex items-center justify-end gap-2">
                            <button
                              onClick={() => toggleRow(record.id)}
                              className="p-2 hover:bg-lsc-cream/50 dark:hover:bg-earth-700 rounded-lg transition-colors"
                              title="View details"
                            >
                              <Eye className="w-4 h-4 text-lsc-dark dark:text-lsc-cream" />
                            </button>
                            {canDownload && (
                              <>
                                <button
                                  onClick={() => handleDownload(record.id, 'pdf')}
                                  disabled={downloadingId === record.id}
                                  className="p-2 hover:bg-lsc-cream/50 dark:hover:bg-earth-700 rounded-lg transition-colors disabled:opacity-50"
                                  title="Download PDF"
                                >
                                  {downloadingId === record.id ? (
                                    <Loader2 className="w-4 h-4 text-lsc-rose motion-safe:animate-spin" />
                                  ) : (
                                    <Download className="w-4 h-4 text-lsc-dark dark:text-lsc-cream" />
                                  )}
                                </button>
                                <button
                                  onClick={() => handleDownload(record.id, 'csv')}
                                  disabled={downloadingId === record.id}
                                  className="p-2 hover:bg-lsc-cream/50 dark:hover:bg-earth-700 rounded-lg transition-colors disabled:opacity-50 text-xs font-medium text-lsc-dark dark:text-lsc-cream"
                                  title="Download CSV"
                                >
                                  CSV
                                </button>
                              </>
                            )}
                            {canManagePayments && record.status === 'invoiced' && (
                              <button
                                onClick={() => openPaymentModal(record.id)}
                                className="px-3 py-1 text-xs font-medium bg-status-success-100 dark:bg-status-success-900/30 text-status-success-700 dark:text-status-success-400 hover:bg-status-success-200 dark:hover:bg-status-success-900/50 rounded-lg transition-colors"
                                title="Record payment"
                              >
                                <CheckCircle className="w-4 h-4" />
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>

                      {/* Expanded Row Details */}
                      {expandedRows.has(record.id) && (
                        <tr className="bg-lsc-cream/30 dark:bg-earth-700/30 border-b border-lsc-border dark:border-earth-700">
                          <td colSpan={7} className="px-6 py-4">
                            <div className="space-y-3">
                              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                                <div>
                                  <p className="text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                                    Item Type
                                  </p>
                                  <p className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
                                    {record.item_type.replace(/_/g, ' ')}
                                  </p>
                                </div>
                                <div>
                                  <p className="text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                                    Quantity
                                  </p>
                                  <p className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
                                    {record.quantity}
                                  </p>
                                </div>
                                <div>
                                  <p className="text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                                    Unit Amount
                                  </p>
                                  <p className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
                                    ${parseFloat(record.unit_amount).toFixed(2)}
                                  </p>
                                </div>
                                <div>
                                  <p className="text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                                    Invoiced At
                                  </p>
                                  <p className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
                                    {record.invoiced_at ? new Date(record.invoiced_at).toLocaleDateString() : '-'}
                                  </p>
                                </div>
                              </div>
                              {record.description && (
                                <div>
                                  <p className="text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                                    Description
                                  </p>
                                  <p className="text-sm text-lsc-dark dark:text-lsc-cream">{record.description}</p>
                                </div>
                              )}
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Payment Recording Modal */}
        {paymentModal.isOpen && (
          <ModalBackdrop onClose={() => setPaymentModal({ isOpen: false, billingId: null, paymentReference: '', isProcessing: false })} title="Record Payment">
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg max-w-md w-full border border-lsc-border dark:border-earth-700">
              <div className="flex items-center justify-between p-6 border-b border-lsc-border dark:border-earth-700">
                <h2 className="font-serif text-xl font-bold text-lsc-dark dark:text-lsc-cream">Record Payment</h2>
                <button
                  onClick={() => setPaymentModal({ isOpen: false, billingId: null, paymentReference: '', isProcessing: false })}
                  className="p-1 hover:bg-lsc-cream/50 dark:hover:bg-earth-700 rounded-lg transition-colors"
                >
                  <X className="w-5 h-5 text-lsc-dark dark:text-lsc-cream" />
                </button>
              </div>

              <div className="p-6 space-y-4">
                {paymentModal.billingId && (
                  <div className="bg-earth-100 dark:bg-earth-800/30 border border-lsc-border dark:border-earth-600 rounded-lg p-4">
                    <p className="text-sm text-lsc-rose dark:text-lsc-rose-light">
                      Invoice #{billingRecords.find((r) => r.id === paymentModal.billingId)?.invoice_number || paymentModal.billingId}
                    </p>
                    <p className="text-lg font-bold text-lsc-dark dark:text-lsc-cream mt-2">
                      ${parseFloat(billingRecords.find((r) => r.id === paymentModal.billingId)?.total_amount || '0').toFixed(2)}
                    </p>
                  </div>
                )}

                <div>
                  <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
                    Payment Reference
                  </label>
                  <input
                    type="text"
                    placeholder={t('placeholder.treasurerDashboard.egCheck12345Wire')}
                    value={paymentModal.paymentReference}
                    onChange={(e) => setPaymentModal((prev) => ({ ...prev, paymentReference: e.target.value }))}
                    className="w-full px-4 py-2 bg-lsc-cream/50 dark:bg-earth-700 border border-lsc-border dark:border-earth-700 rounded-xl text-lsc-dark dark:text-lsc-cream placeholder-earth-500 dark:placeholder-earth-500 focus:outline-none focus:ring-2 focus:ring-lsc-rose"
                  />
                </div>

                <div className="flex gap-3">
                  <button
                    onClick={() => setPaymentModal({ isOpen: false, billingId: null, paymentReference: '', isProcessing: false })}
                    disabled={paymentModal.isProcessing}
                    className="flex-1 px-4 py-2 bg-lsc-cream/50 dark:bg-earth-700 border border-lsc-border dark:border-earth-700 rounded-xl text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-earth-600 transition-colors font-medium disabled:opacity-50"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleRecordPayment}
                    disabled={paymentModal.isProcessing}
                    className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-status-success-600 hover:bg-status-success-700 text-white rounded-xl font-medium transition-colors disabled:opacity-50"
                  >
                    {paymentModal.isProcessing ? (
                      <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
                    ) : (
                      <Save className="w-4 h-4" />
                    )}
                    Record Payment
                  </button>
                </div>
              </div>
            </div>
          </ModalBackdrop>
        )}
      </PageContainer>
    </div>
  </AdminShell>
  )
}
