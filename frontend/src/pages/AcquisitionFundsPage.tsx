/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  DollarSign,
  Plus,
  Edit,
  RefreshCw,
  TrendingUp,
  AlertTriangle,
  Loader2,
  X,
  PieChart,
} from 'lucide-react'
import toast from 'react-hot-toast'
import {
  getFunds,
  createFund,
  updateFund,
  rolloverFunds,
  type Fund,
  type FundCreateData,
} from '@/api/api'
import { useTranslation} from '@/i18n'
import { AdminShell } from '../components/shells/AdminShell'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'
import PageContainer from '@/components/layout/PageContainer'

export default function AcquisitionFundsPage(): React.ReactElement {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const currentYear = new Date().getFullYear()

  const [fiscalYear, setFiscalYear] = useState(currentYear)
  const [statusFilter, setStatusFilter] = useState('')
  const [showModal, setShowModal] = useState(false)
  const [editingFund, setEditingFund] = useState<Fund | null>(null)
  const [showRolloverModal, setShowRolloverModal] = useState(false)
  const [rolloverTarget, setRolloverTarget] = useState(currentYear + 1)

  // Form state
  const [formData, setFormData] = useState<FundCreateData>({
    name: '',
    code: '',
    description: '',
    fiscal_year: currentYear,
    allocated_amount: 0,
  })

  // Queries
  const { data: fundsData, isLoading } = useQuery({
    queryKey: ['acquisition', 'funds', fiscalYear, statusFilter],
    queryFn: () => getFunds({
      fiscal_year: fiscalYear,
      ...(statusFilter ? { status: statusFilter } : {}),
    }),
  })

  // Mutations
  const createMutation = useMutation({
    mutationFn: createFund,
    onSuccess: () => {
      toast.success(t('toast.acquisitionFunds.fundCreated'))
      queryClient.invalidateQueries({ queryKey: ['acquisition', 'funds'] })
      setShowModal(false)
      resetForm()
    },
    onError: () => toast.error(t('acquisitionFunds.failedToCreateFund')),
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<FundCreateData> }) => updateFund(id, data),
    onSuccess: () => {
      toast.success(t('toast.acquisitionFunds.fundUpdated'))
      queryClient.invalidateQueries({ queryKey: ['acquisition', 'funds'] })
      setShowModal(false)
      setEditingFund(null)
      resetForm()
    },
    onError: () => toast.error(t('acquisitionFunds.failedToUpdateFund')),
  })

  const rolloverMutation = useMutation({
    mutationFn: rolloverFunds,
    onSuccess: (data) => {
      toast.success(t('toast.acquisitionFunds.fundscreatedFundsRolledOverTo', { fundscreated: data.funds_created, rolloverTarget: rolloverTarget }))
      queryClient.invalidateQueries({ queryKey: ['acquisition', 'funds'] })
      setShowRolloverModal(false)
    },
    onError: () => toast.error(t('acquisitionFunds.failedToRolloverFunds')),
  })

  const resetForm = () => {
    setFormData({
      name: '',
      code: '',
      description: '',
      fiscal_year: currentYear,
      allocated_amount: 0,
    })
  }

  const openEditModal = (fund: Fund) => {
    setEditingFund(fund)
    setFormData({
      name: fund.name,
      code: fund.code ?? '',
      description: fund.description || '',
      fiscal_year: fund.fiscal_year ?? currentYear,
      allocated_amount: fund.allocated_amount ?? 0,
    })
    setShowModal(true)
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (editingFund) {
      updateMutation.mutate({ id: editingFund.id, data: { name: formData.name, ...(formData.description ? { description: formData.description } : {}) } })
    } else {
      createMutation.mutate(formData)
    }
  }

  const getStatusBadge = (status: string) => {
    const colors: Record<string, string> = {
      active: 'bg-status-success-100 text-status-success-800 dark:bg-status-success-900/30 dark:text-status-success-400',
      inactive: 'bg-earth-100 text-earth-800 dark:bg-earth-800/30 dark:text-lsc-rose-light',
      closed: 'bg-earth-100 text-earth-800 dark:bg-earth-900/30 dark:text-earth-300',
    }
    return colors[status] || colors.active
  }

  const getUtilizationColor = (spent: number, initial: number) => {
    const pct = initial > 0 ? (spent / initial) * 100 : 0
    if (pct >= 90) return 'bg-status-danger-500'
    if (pct >= 75) return 'bg-status-warning-500'
    if (pct >= 50) return 'bg-status-warning-500'
    return 'bg-status-success-500'
  }

  // Calculate totals
  const totals = fundsData?.items.reduce(
    (acc, fund) => ({
      initial: acc.initial + Number(fund.allocated_amount),
      current: acc.current + Number(fund.available_amount),
      encumbered: acc.encumbered + Number(fund.encumbered_amount),
      spent: acc.spent + Number(fund.spent_amount),
    }),
    { initial: 0, current: 0, encumbered: 0, spent: 0 }
  ) || { initial: 0, current: 0, encumbered: 0, spent: 0 }

  return (
    <AdminShell title="Acquisition Funds">
    <div className="min-h-screen bg-lsc-cream dark:bg-earth-900">
      <PageContainer width="wide" className="py-8">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
          <div>
            <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream flex items-center gap-3">
              <DollarSign className="w-8 h-8 text-lsc-rose" />
              Acquisition Funds
            </h1>
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">{t('acquisitionFunds.manageBudgetAllocationsAndTrack')}</p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowRolloverModal(true)}
              className="flex items-center gap-2 px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-earth-100 dark:bg-earth-700 dark:hover:bg-earth-700"
            >
              <RefreshCw className="w-4 h-4" />
              Rollover
            </button>
            <button
              onClick={() => { resetForm(); setEditingFund(null); setShowModal(true) }}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-lsc-rose text-white hover:bg-lsc-rose/90"
            >
              <Plus className="w-4 h-4" />
              New Fund
            </button>
          </div>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap gap-4 mb-6">
          <select
            id="funds-fiscal-year-filter"
            aria-label={t('acquisitionFunds.filterByFiscalYear')}
            value={fiscalYear}
            onChange={(e) => setFiscalYear(parseInt(e.target.value))}
            className="px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream"
          >
            {[currentYear - 2, currentYear - 1, currentYear, currentYear + 1].map((year) => (
              <option key={year} value={year}>FY {year}</option>
            ))}
          </select>
          <select
            id="funds-status-filter"
            aria-label={t('aria.acquisition.filterByStatus')}
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream"
          >
            <option value="">All Statuses</option>
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
            <option value="closed">Closed</option>
          </select>
        </div>

        {/* Summary Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-sm border border-lsc-border dark:border-earth-700 p-5">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Total Budget</p>
                <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">${totals.initial.toLocaleString()}</p>
              </div>
              <div className="p-3 rounded-full bg-earth-100 dark:bg-earth-800/30">
                <PieChart className="w-6 h-6 text-lsc-rose dark:text-lsc-rose-light" />
              </div>
            </div>
          </div>
          <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-sm border border-lsc-border dark:border-earth-700 p-5">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Available</p>
                <p className="text-2xl font-bold text-status-success-600 dark:text-status-success-400">${totals.current.toLocaleString()}</p>
              </div>
              <div className="p-3 rounded-full bg-status-success-100 dark:bg-status-success-900/30">
                <DollarSign className="w-6 h-6 text-status-success-600 dark:text-status-success-400" />
              </div>
            </div>
          </div>
          <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-sm border border-lsc-border dark:border-earth-700 p-5">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Encumbered</p>
                <p className="text-2xl font-bold text-status-warning-600 dark:text-status-warning-400">${totals.encumbered.toLocaleString()}</p>
              </div>
              <div className="p-3 rounded-full bg-status-warning-100 dark:bg-status-warning-900/30">
                <AlertTriangle className="w-6 h-6 text-status-warning-600 dark:text-status-warning-400" />
              </div>
            </div>
          </div>
          <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-sm border border-lsc-border dark:border-earth-700 p-5">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Spent</p>
                <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">${totals.spent.toLocaleString()}</p>
              </div>
              <div className="p-3 rounded-full bg-category-100 dark:bg-category-900/30">
                <TrendingUp className="w-6 h-6 text-category-600 dark:text-category-400" />
              </div>
            </div>
          </div>
        </div>

        {/* Funds Table */}
        {isLoading ? (
          <div className="flex items-center justify-center h-64">
            <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" />
          </div>
        ) : (
          <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-sm border border-lsc-border dark:border-earth-700 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-lsc-border dark:border-earth-700 bg-earth-50 dark:bg-earth-900/50">
                    <th className="text-left py-3 px-4 text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Fund</th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Code</th>
                    <th className="text-right py-3 px-4 text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Initial</th>
                    <th className="text-right py-3 px-4 text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Available</th>
                    <th className="text-right py-3 px-4 text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Encumbered</th>
                    <th className="text-right py-3 px-4 text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Spent</th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Utilization</th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Status</th>
                    <th className="text-right py-3 px-4 text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {fundsData?.items.map((fund) => {
                    const utilization = Number(fund.allocated_amount) > 0
                      ? ((Number(fund.spent_amount) + Number(fund.encumbered_amount)) / Number(fund.allocated_amount)) * 100
                      : 0
                    return (
                      <tr key={fund.id} className="border-b border-earth-100 dark:border-earth-700/50 hover:bg-earth-50 dark:bg-earth-900 dark:hover:bg-earth-700/30">
                        <td className="py-3 px-4">
                          <div>
                            <p className="font-medium text-lsc-dark dark:text-lsc-cream">{fund.name}</p>
                            {fund.description && (
                              <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{fund.description}</p>
                            )}
                          </div>
                        </td>
                        <td className="py-3 px-4 font-mono text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{fund.code}</td>
                        <td className="py-3 px-4 text-right text-lsc-dark dark:text-lsc-cream">${Number(fund.allocated_amount).toLocaleString()}</td>
                        <td className="py-3 px-4 text-right text-status-success-600 dark:text-status-success-400">${Number(fund.available_amount).toLocaleString()}</td>
                        <td className="py-3 px-4 text-right text-status-warning-600 dark:text-status-warning-400">${Number(fund.encumbered_amount).toLocaleString()}</td>
                        <td className="py-3 px-4 text-right text-lsc-dark dark:text-lsc-cream">${Number(fund.spent_amount).toLocaleString()}</td>
                        <td className="py-3 px-4">
                          <div className="flex items-center gap-2">
                            <div className="w-20 bg-earth-200 dark:bg-earth-700 rounded-full h-2">
                              <div
                                className={`h-2 rounded-full ${getUtilizationColor(Number(fund.spent_amount) + Number(fund.encumbered_amount), Number(fund.allocated_amount))}`}
                                style={{ width: `${Math.min(100, utilization)}%` }}
                              />
                            </div>
                            <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{utilization.toFixed(0)}%</span>
                          </div>
                        </td>
                        <td className="py-3 px-4">
                          <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusBadge(fund.status)}`}>
                            {fund.status}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-right">
                          <button
                            onClick={() => openEditModal(fund as unknown as Fund)}
                            aria-label={t('aria.acquisitionFunds.editFund', 'Edit fund {{name}}').replace('{{name}}', fund.name)}
                            className="p-1 text-earth-600 hover:text-lsc-dark/70 dark:text-lsc-cream/70 dark:hover:text-earth-200"
                          >
                            <Edit className="w-4 h-4" />
                          </button>
                        </td>
                      </tr>
  )
                  })}
                </tbody>
              </table>
            </div>

            {fundsData?.items.length === 0 && (
              <div className="p-8 text-center text-lsc-dark/70 dark:text-lsc-cream/70">
                No funds found for FY {fiscalYear}.
              </div>
            )}
          </div>
        )}

        {/* Create/Edit Modal */}
        {showModal && (
          <ModalBackdrop onClose={() => { setShowModal(false); setEditingFund(null) }} title="Dialog">
            <div className="bg-lsc-white dark:bg-earth-800 rounded-lg max-w-md w-full">
              <div className="p-4 border-b border-lsc-border dark:border-earth-700 flex items-center justify-between">
                <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
                  {editingFund ? 'Edit Fund' : 'New Fund'}
                </h3>
                <button onClick={() => { setShowModal(false); setEditingFund(null) }} aria-label={t('aria.acquisitionFunds.closeDialog', 'Close')} className="text-earth-600 hover:text-lsc-dark/70 dark:text-lsc-cream/70 dark:hover:text-earth-200">
                  <X className="w-5 h-5" />
                </button>
              </div>
              <form onSubmit={handleSubmit} className="p-4 space-y-4">
                <div>
                  <label htmlFor="fund-form-name" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Fund Name *</label>
                  <input
                    id="fund-form-name"
                    type="text"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    required
                    className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                  />
                </div>
                {!editingFund && (
                  <>
                    <div>
                      <label htmlFor="fund-form-code" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Fund Code *</label>
                      <input
                        id="fund-form-code"
                        type="text"
                        value={formData.code}
                        onChange={(e) => setFormData({ ...formData, code: e.target.value.toUpperCase() })}
                        required
                        placeholder={t('placeholder.acquisitionFunds.egAdultfic')}
                        className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                      />
                    </div>
                    <div>
                      <label htmlFor="fund-form-fiscal-year" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Fiscal Year *</label>
                      <select
                        id="fund-form-fiscal-year"
                        value={formData.fiscal_year}
                        onChange={(e) => setFormData({ ...formData, fiscal_year: parseInt(e.target.value) })}
                        className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                      >
                        {[currentYear - 1, currentYear, currentYear + 1].map((year) => (
                          <option key={year} value={year}>FY {year}</option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label htmlFor="fund-form-amount" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Initial Amount *</label>
                      <div className="relative">
                        <span className="absolute left-3 top-1/2 -translate-y-1/2 text-lsc-dark/70 dark:text-lsc-cream/70">$</span>
                        <input
                          id="fund-form-amount"
                          type="number"
                          value={formData.allocated_amount}
                          onChange={(e) => setFormData({ ...formData, allocated_amount: parseFloat(e.target.value) || 0 })}
                          required
                          min="0"
                          step="0.01"
                          className="w-full pl-7 pr-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                        />
                      </div>
                    </div>
                  </>
                )}
                <div>
                  <label htmlFor="fund-form-description" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Description</label>
                  <textarea
                    id="fund-form-description"
                    value={formData.description}
                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                    rows={2}
                    className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                  />
                </div>
              </form>
              <div className="p-4 border-t border-lsc-border dark:border-earth-700 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => { setShowModal(false); setEditingFund(null) }}
                  className="px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70"
                >
                  Cancel
                </button>
                <button
                  onClick={handleSubmit}
                  disabled={createMutation.isPending || updateMutation.isPending}
                  className="px-4 py-2 rounded-lg bg-lsc-rose text-white hover:bg-lsc-rose/90 disabled:opacity-50"
                >
                  {createMutation.isPending || updateMutation.isPending ? (
                    <Loader2 className="w-5 h-5 motion-safe:animate-spin" />
                  ) : editingFund ? 'Update' : 'Create'}
                </button>
              </div>
            </div>
          </ModalBackdrop>
        )}

        {/* Rollover Modal */}
        {showRolloverModal && (
          <ModalBackdrop onClose={() => setShowRolloverModal(false)} title="Rollover Funds">
            <div className="bg-lsc-white dark:bg-earth-800 rounded-lg max-w-md w-full">
              <div className="p-4 border-b border-lsc-border dark:border-earth-700">
                <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">Rollover Funds</h3>
              </div>
              <div className="p-4 space-y-4">
                <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
                  Create new funds for the next fiscal year based on current FY {fiscalYear} funds.
                </p>
                <div>
                  <label htmlFor="rollover-target-year" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Target Fiscal Year</label>
                  <select
                    id="rollover-target-year"
                    value={rolloverTarget}
                    onChange={(e) => setRolloverTarget(parseInt(e.target.value))}
                    className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                  >
                    <option value={currentYear + 1}>FY {currentYear + 1}</option>
                    <option value={currentYear + 2}>FY {currentYear + 2}</option>
                  </select>
                </div>
                <div className="p-3 bg-status-warning-50 dark:bg-status-warning-900/20 rounded-lg">
                  <p className="text-sm text-status-warning-700 dark:text-status-warning-400">
                    <AlertTriangle className="w-4 h-4 inline mr-1" />
                    This will create new funds with zero balances. Initial amounts must be set separately.
                  </p>
                </div>
              </div>
              <div className="p-4 border-t border-lsc-border dark:border-earth-700 flex justify-end gap-2">
                <button
                  onClick={() => setShowRolloverModal(false)}
                  className="px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70"
                >
                  Cancel
                </button>
                <button
                  onClick={() => rolloverMutation.mutate({ source_fiscal_year: fiscalYear, target_fiscal_year: rolloverTarget })}
                  disabled={rolloverMutation.isPending}
                  className="px-4 py-2 rounded-lg bg-lsc-rose text-white hover:bg-lsc-rose/90 disabled:opacity-50"
                >
                  {rolloverMutation.isPending ? <Loader2 className="w-5 h-5 motion-safe:animate-spin" /> : 'Rollover'}
                </button>
              </div>
            </div>
          </ModalBackdrop>
        )}
      </PageContainer>
    </div>
    </AdminShell>
  )
}
