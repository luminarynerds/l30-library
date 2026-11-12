/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect, useCallback } from 'react'
import {
  DollarSign,
  Plus,
  X,
  Loader2,
  Check,
} from 'lucide-react'
import toast from 'react-hot-toast'
import {
  listBillingRecords,
  getFinancialSummary,
  generateBilling,
  recordPayment,
  type ConsortiumDetail,
  type ConsortiumBilling,
  type FinancialSummary,
} from '../../../api/consortium-api'
import { BILLING_STATUS_STYLES } from './StatusBadges'
import { t } from '@/i18n'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

function BillingTab({
  token,
  selectedConsortium,
}: {
  token: string | null
  selectedConsortium: ConsortiumDetail | null
}) {
  const [billingRecords, setBillingRecords] = useState<ConsortiumBilling[]>([])
  const [financialSummary, setFinancialSummary] = useState<FinancialSummary | null>(null)
  const [loading, setLoading] = useState(false)
  const [showGenerateModal, setShowGenerateModal] = useState(false)
  const [generateDates, setGenerateDates] = useState({
    start: '',
    end: '',
  })
  const [isGenerating, setIsGenerating] = useState(false)

  const loadData = useCallback(async () => {
    if (!selectedConsortium) return
    try {
      setLoading(true)
      const [records, summary] = await Promise.all([
        listBillingRecords(selectedConsortium.id, { limit: 50 }),
        getFinancialSummary(selectedConsortium.id),
      ])
      setBillingRecords(records)
      setFinancialSummary(summary)
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : t('toast.admin.failedToLoadBillingData'))
    } finally {
      setLoading(false)
    }
  }, [selectedConsortium])

  useEffect(() => {
    loadData()
  }, [loadData])

  const handleGenerateBilling = async () => {
    if (!token || !selectedConsortium || !generateDates.start || !generateDates.end) return
    setIsGenerating(true)
    try {
      const result = await generateBilling(
        token,
        selectedConsortium.id,
        generateDates.start,
        generateDates.end
      )
      toast.success(t('toast.admin.generatedRecordscreatedBillingRecords', { recordscreated: result.records_created }))
      setShowGenerateModal(false)
      loadData()
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : t('toast.admin.failedToGenerateBilling'))
    } finally {
      setIsGenerating(false)
    }
  }

  const handleRecordPayment = async (billingId: number) => {
    if (!token) return
    try {
      await recordPayment(token, billingId)
      toast.success(t('toast.admin.paymentRecorded'))
      loadData()
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : t('toast.admin.failedToRecordPayment'))
    }
  }

  if (!selectedConsortium) {
    return (
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-12 text-center">
        <DollarSign className="w-16 h-16 text-lsc-dark/30 dark:text-lsc-cream/60 mx-auto mb-4" />
        <h3 className="text-lg font-medium text-lsc-dark dark:text-lsc-cream mb-2">
          Select a consortium
        </h3>
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
          Go to the Consortiums tab and select a consortium to view billing.
        </p>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="flex justify-center py-12">
        <Loader2 className="w-8 h-8 text-lsc-rose motion-safe:animate-spin" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
            Billing & Cost Sharing
          </h2>
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
            {selectedConsortium.name} financial management
          </p>
        </div>
        <button
          onClick={() => setShowGenerateModal(true)}
          className="flex items-center gap-2 px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-xl font-medium transition-colors"
        >
          <Plus className="w-5 h-5" />
          Generate Billing
        </button>
      </div>

      {/* Financial Summary Cards */}
      {financialSummary && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-5">
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Total Billed</p>
            <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">
              ${parseFloat(financialSummary.total_billed || '0').toLocaleString()}
            </p>
          </div>
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-5">
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Total Paid</p>
            <p className="text-2xl font-bold text-status-success-600 dark:text-status-success-400">
              ${parseFloat(financialSummary.total_paid || '0').toLocaleString()}
            </p>
          </div>
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-5">
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Outstanding</p>
            <p className="text-2xl font-bold text-status-warning-600 dark:text-status-warning-400">
              ${parseFloat(financialSummary.total_outstanding || '0').toLocaleString()}
            </p>
          </div>
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-5">
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Disputed</p>
            <p className="text-2xl font-bold text-status-danger-600 dark:text-status-danger-400">
              ${parseFloat(financialSummary.total_disputed || '0').toLocaleString()}
            </p>
          </div>
        </div>
      )}

      {/* Billing Records Table */}
      {billingRecords.length === 0 ? (
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-12 text-center">
          <DollarSign className="w-16 h-16 text-lsc-dark/30 dark:text-lsc-cream/60 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-lsc-dark dark:text-lsc-cream mb-2">
            No billing records
          </h3>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
            Generate billing to create records for consortium activities.
          </p>
        </div>
      ) : (
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-lsc-cream/50 dark:bg-earth-700/50 border-b border-lsc-border dark:border-earth-700">
                  <th className="px-6 py-4 text-left text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
                    Period
                  </th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
                    Type
                  </th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
                    Amount
                  </th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
                    Status
                  </th>
                  <th className="px-6 py-4 text-right text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody>
                {billingRecords.map((record) => (
                  <tr
                    key={record.id}
                    className="border-b border-lsc-border dark:border-earth-700 hover:bg-lsc-cream/30 dark:hover:bg-earth-700/30 transition-colors"
                  >
                    <td className="px-6 py-4 text-sm text-lsc-dark dark:text-lsc-cream">
                      {new Date(record.billing_period_start).toLocaleDateString()} -{' '}
                      {new Date(record.billing_period_end).toLocaleDateString()}
                    </td>
                    <td className="px-6 py-4 text-sm text-lsc-dark dark:text-lsc-cream">
                      {record.item_type.replace('_', ' ')}
                    </td>
                    <td className="px-6 py-4 text-sm font-medium text-lsc-dark dark:text-lsc-cream">
                      ${parseFloat(record.total_amount).toFixed(2)}
                    </td>
                    <td className="px-6 py-4">
                      <span
                        className={`inline-flex px-2 py-1 rounded-full text-xs font-medium ${BILLING_STATUS_STYLES[record.status].bg} ${BILLING_STATUS_STYLES[record.status].text}`}
                      >
                        {record.status}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center justify-end gap-2">
                        {record.status === 'invoiced' && (
                          <button
                            onClick={() => handleRecordPayment(record.id)}
                            className="px-3 py-1 text-xs font-medium text-status-success-600 hover:bg-status-success-100 dark:bg-status-success-900/30 dark:hover:bg-status-success-900/30 rounded-lg transition-colors"
                          >
                            Mark Paid
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Generate Billing Modal */}
      {showGenerateModal && (
        <ModalBackdrop onClose={() => setShowGenerateModal(false)} title="Generate Billing">
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg w-full max-w-md">
            <div className="flex items-center justify-between p-6 border-b border-lsc-border dark:border-earth-700">
              <h2 className="text-lg font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
                Generate Billing
              </h2>
              <button
                onClick={() => setShowGenerateModal(false)}
                className="p-1 hover:bg-lsc-cream dark:hover:bg-earth-700 rounded-full"
              >
                <X className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
              </button>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                  Period Start *
                </label>
                <input
                  type="date"
                  value={generateDates.start}
                  onChange={(e) => setGenerateDates({ ...generateDates, start: e.target.value })}
                  className="w-full px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                  Period End *
                </label>
                <input
                  type="date"
                  value={generateDates.end}
                  onChange={(e) => setGenerateDates({ ...generateDates, end: e.target.value })}
                  className="w-full px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
                  required
                />
              </div>
              <div className="flex justify-end gap-3 pt-4 border-t border-lsc-border dark:border-earth-700">
                <button
                  onClick={() => setShowGenerateModal(false)}
                  disabled={isGenerating}
                  className="px-4 py-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-earth-700 rounded-xl font-medium disabled:opacity-50"
                >
                  Cancel
                </button>
                <button
                  onClick={handleGenerateBilling}
                  disabled={isGenerating || !generateDates.start || !generateDates.end}
                  className="px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-xl font-medium flex items-center gap-2 disabled:opacity-50"
                >
                  {isGenerating ? (
                    <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
                  ) : (
                    <Check className="w-4 h-4" />
                  )}
                  Generate
                </button>
              </div>
            </div>
          </div>
        </ModalBackdrop>
      )}
    </div>
  )
}

export default BillingTab
