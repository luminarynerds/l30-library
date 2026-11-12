/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Package,
  Search,
  Plus,
  Edit,
  Trash2,
  ScanBarcode,
  ClipboardList,
  CheckCircle,
  XCircle,
  History,
  Filter,
  ChevronDown,
  Loader2,
} from 'lucide-react'
import toast from 'react-hot-toast'
import {
  getInventoryCopies,
  withdrawCopy,
  getCopyConditionHistory,
  logConditionChange,
  lookupByBarcode,
  getInventoryAudits,
  getInventoryAudit,
  startInventoryAudit,
  scanAuditItem,
  completeInventoryAudit,
  type ItemCopy,
  type InventoryAudit,
} from '@/api/api'
import ConfirmDialog from '@/components/ConfirmDialog'
import { useTranslation} from '@/i18n'
import { AdminShell } from '../components/shells/AdminShell'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'
import PageContainer from '@/components/layout/PageContainer'

type TabType = 'copies' | 'audits' | 'lookup'

const CONDITIONS = ['new', 'good', 'fair', 'poor', 'damaged', 'withdrawn'] as const
const STATUSES = ['available', 'checked_out', 'on_hold', 'in_transit', 'in_repair', 'lost', 'withdrawn'] as const

// eslint-disable-next-line complexity
export default function InventoryManagementPage(): React.ReactElement {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const [activeTab, setActiveTab] = useState<TabType>('copies')
  const [page, setPage] = useState(1)
  const [filters, setFilters] = useState({ location: '', condition: '', status: '' })
  const [showFilters, setShowFilters] = useState(false)
  const [barcode, setBarcode] = useState('')
  const [lookupResult, setLookupResult] = useState<ItemCopy | null>(null)
  const [lookupError, setLookupError] = useState('')
  const [selectedCopy, setSelectedCopy] = useState<ItemCopy | null>(null)
  const [showHistoryModal, setShowHistoryModal] = useState(false)
  const [showConditionModal, setShowConditionModal] = useState(false)
  const [showWithdrawConfirm, setShowWithdrawConfirm] = useState(false)
  const [newCondition, setNewCondition] = useState('')
  const [conditionNotes, setConditionNotes] = useState('')
  const [selectedAudit, setSelectedAudit] = useState<InventoryAudit | null>(null)
  const [auditBarcode, setAuditBarcode] = useState('')
  const [showNewAuditModal, setShowNewAuditModal] = useState(false)
  const [newAuditName, setNewAuditName] = useState('')
  const [newAuditLocation, setNewAuditLocation] = useState('')

  // Queries
  const { data: copiesData, isLoading: loadingCopies, error: copiesError, refetch: refetchCopies } = useQuery({
    queryKey: ['inventory', 'copies', page, filters],
    queryFn: () => getInventoryCopies({ ...filters, page, per_page: 20 }),
    enabled: activeTab === 'copies',
  })

  const { data: auditsData, isLoading: loadingAudits } = useQuery({
    queryKey: ['inventory', 'audits'],
    queryFn: () => getInventoryAudits({ per_page: 50 }),
    enabled: activeTab === 'audits',
  })

  const { data: conditionHistory } = useQuery({
    queryKey: ['inventory', 'condition-history', selectedCopy?.id],
    queryFn: () => getCopyConditionHistory(selectedCopy!.id),
    enabled: showHistoryModal && !!selectedCopy,
  })

  const { data: auditDetail } = useQuery({
    queryKey: ['inventory', 'audit', selectedAudit?.id],
    queryFn: () => getInventoryAudit(selectedAudit!.id),
    enabled: !!selectedAudit,
  })

  // Mutations
  const lookupMutation = useMutation({
    mutationFn: lookupByBarcode,
    onSuccess: (data) => {
      setLookupResult(data)
      setLookupError('')
    },
    onError: () => {
      setLookupResult(null)
      setLookupError('Item not found')
    },
  })

  const conditionMutation = useMutation({
    mutationFn: ({ copyId, data }: { copyId: number; data: { new_condition: string; repair_notes?: string } }) =>
      logConditionChange(copyId, data),
    onSuccess: () => {
      toast.success(t('toast.inventoryManagement.conditionUpdated'))
      queryClient.invalidateQueries({ queryKey: ['inventory'] })
      setShowConditionModal(false)
      setNewCondition('')
      setConditionNotes('')
    },
    onError: () => toast.error(t('inventoryManagement.failedToUpdateCondition')),
  })

  const withdrawMutation = useMutation({
    mutationFn: (copyId: number) => withdrawCopy(copyId),
    onSuccess: () => {
      toast.success(t('toast.inventoryManagement.itemWithdrawn'))
      queryClient.invalidateQueries({ queryKey: ['inventory'] })
      setShowWithdrawConfirm(false)
      setSelectedCopy(null)
    },
    onError: () => toast.error(t('inventoryManagement.failedToWithdrawItem')),
  })

  const startAuditMutation = useMutation({
    mutationFn: (data: { name: string; location_filter?: string }) => startInventoryAudit(data),
    onSuccess: (audit) => {
      toast.success(t('toast.inventoryManagement.auditStarted'))
      queryClient.invalidateQueries({ queryKey: ['inventory', 'audits'] })
      setSelectedAudit(audit)
      setShowNewAuditModal(false)
      setNewAuditName('')
      setNewAuditLocation('')
    },
    onError: () => toast.error(t('inventoryManagement.failedToStartAudit')),
  })

  const scanAuditMutation = useMutation({
    mutationFn: ({ auditId, barcode }: { auditId: number; barcode: string }) => scanAuditItem(auditId, barcode),
    onSuccess: (result) => {
      if (result.status === 'found') {
        toast.success(t('toast.inventoryManagement.foundTitle', { title: result.title }))
      } else if (result.status === 'unexpected') {
        toast(`Unexpected item: ${result.title}`, { icon: '!' })
      } else {
        toast(`Already scanned: ${result.title}`)
      }
      queryClient.invalidateQueries({ queryKey: ['inventory', 'audit', selectedAudit?.id] })
      setAuditBarcode('')
    },
    onError: () => toast.error(t('toast.inventoryManagement.scanFailed')),
  })

  const completeAuditMutation = useMutation({
    mutationFn: (auditId: number) => completeInventoryAudit(auditId),
    onSuccess: () => {
      toast.success(t('toast.inventoryManagement.auditCompleted'))
      queryClient.invalidateQueries({ queryKey: ['inventory', 'audits'] })
      setSelectedAudit(null)
    },
    onError: () => toast.error(t('inventoryManagement.failedToCompleteAudit')),
  })

  const handleLookup = (e: React.FormEvent) => {
    e.preventDefault()
    if (barcode.trim()) {
      lookupMutation.mutate(barcode.trim())
    }
  }

  const handleScanAudit = (e: React.FormEvent) => {
    e.preventDefault()
    if (auditBarcode.trim() && selectedAudit) {
      scanAuditMutation.mutate({ auditId: selectedAudit.id, barcode: auditBarcode.trim() })
    }
  }

  const getStatusBadge = (status: string) => {
    const colors: Record<string, string> = {
      available: 'bg-status-success-100 text-status-success-800 dark:bg-status-success-900/30 dark:text-status-success-400',
      checked_out: 'bg-earth-100 text-earth-800 dark:bg-earth-800/30 dark:text-lsc-rose-light',
      on_hold: 'bg-status-warning-100 text-status-warning-800 dark:bg-status-warning-900/30 dark:text-status-warning-400',
      in_transit: 'bg-category-100 text-category-800 dark:bg-category-900/30 dark:text-category-400',
      in_repair: 'bg-status-warning-100 text-status-warning-800 dark:bg-status-warning-900/30 dark:text-status-warning-400',
      lost: 'bg-status-danger-100 text-status-danger-800 dark:bg-status-danger-900/30 dark:text-status-danger-400',
      withdrawn: 'bg-earth-100 text-earth-800 dark:bg-earth-900/30 dark:text-earth-300',
    }
    return colors[status] || colors.available
  }

  const getConditionBadge = (condition: string) => {
    const colors: Record<string, string> = {
      new: 'bg-status-success-100 text-status-success-800 dark:bg-status-success-900/30 dark:text-status-success-400',
      good: 'bg-earth-100 text-earth-800 dark:bg-earth-800/30 dark:text-lsc-rose-light',
      fair: 'bg-status-warning-100 text-status-warning-800 dark:bg-status-warning-900/30 dark:text-status-warning-400',
      poor: 'bg-status-warning-100 text-status-warning-800 dark:bg-status-warning-900/30 dark:text-status-warning-400',
      damaged: 'bg-status-danger-100 text-status-danger-800 dark:bg-status-danger-900/30 dark:text-status-danger-400',
      withdrawn: 'bg-earth-100 text-earth-800 dark:bg-earth-900/30 dark:text-earth-300',
    }
    return colors[condition] || colors.good
  }

  return (

    <AdminShell title="Inventory Management" subtitle={t('inventoryManagement.manageItemCopiesConductAudits')}>    <div className="min-h-screen bg-lsc-cream dark:bg-earth-900">
      <PageContainer width="wide" className="py-8">
        {/* Header */}
        <div className="mb-8 flex items-center justify-between flex-wrap gap-4">
          <div></div>
          <a
            href="/staff/inventory/scan"
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-lsc-rose text-white hover:bg-lsc-rose/90 font-medium"
          >
            <ScanBarcode className="w-4 h-4" />
            Mobile Scan
          </a>
        </div>

        {/* Tabs */}
        <div className="flex gap-2 mb-6">
          {[
            { id: 'copies' as const, label: 'Item Copies', icon: Package },
            { id: 'audits' as const, label: 'Audits', icon: ClipboardList },
            { id: 'lookup' as const, label: 'Barcode Lookup', icon: ScanBarcode },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors ${
                activeTab === tab.id
                  ? 'bg-lsc-rose text-white'
                  : 'bg-lsc-white dark:bg-earth-800 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-earth-100 dark:hover:bg-earth-700'
              }`}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
            </button>
          ))}
        </div>

        {/* Copies Tab */}
        {activeTab === 'copies' && (
          <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-sm border border-lsc-border dark:border-earth-700">
            {/* Filters */}
            <div className="p-4 border-b border-lsc-border dark:border-earth-700">
              <button
                onClick={() => setShowFilters(!showFilters)}
                className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-earth-900 dark:hover:text-earth-100"
              >
                <Filter className="w-4 h-4" />
                Filters
                <ChevronDown className={`w-4 h-4 transition-transform ${showFilters ? 'rotate-180' : ''}`} />
              </button>
              {showFilters && (
                <div className="mt-4 grid grid-cols-1 sm:grid-cols-3 gap-4">
                  <input
                    type="text"
                    placeholder={t('placeholder.inventoryManagement.location')}
                    value={filters.location}
                    onChange={(e) => setFilters({ ...filters, location: e.target.value })}
                    className="px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                  />
                  <select
                    value={filters.condition}
                    onChange={(e) => setFilters({ ...filters, condition: e.target.value })}
                    className="px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                  >
                    <option value="">All Conditions</option>
                    {CONDITIONS.map((c) => (
                      <option key={c} value={c}>{c}</option>
                    ))}
                  </select>
                  <select
                    value={filters.status}
                    onChange={(e) => setFilters({ ...filters, status: e.target.value })}
                    className="px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                  >
                    <option value="">All Statuses</option>
                    {STATUSES.map((s) => (
                      <option key={s} value={s}>{s.replace('_', ' ')}</option>
                    ))}
                  </select>
                </div>
              )}
            </div>

            {/* Table */}
            {loadingCopies ? (
              <div className="flex items-center justify-center h-64">
                <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" />
              </div>
            ) : copiesError ? (
              <div className="text-center py-12">
                <XCircle className="w-10 h-10 mx-auto mb-3 text-status-danger-400" />
                <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-3">{t('inventory.loadError', 'Unable to load inventory data.')}</p>
                <button
                  onClick={() => refetchCopies()}
                  className="px-4 py-2 text-sm font-medium bg-lsc-rose text-white rounded-xl hover:bg-lsc-rose/90 transition-colors"
                >
                  {t('common.retry', 'Try Again')}
                </button>
              </div>
            ) : !copiesData?.items?.length ? (
              <div className="text-center py-12">
                <Package className="w-10 h-10 mx-auto mb-3 text-earth-300 dark:text-earth-600" />
                <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('inventory.noCopies', 'No copies found matching your filters.')}</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-lsc-border dark:border-earth-700 bg-earth-50 dark:bg-earth-900/50">
                      <th className="text-left py-3 px-4 text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Barcode</th>
                      <th className="text-left py-3 px-4 text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Title</th>
                      <th className="text-left py-3 px-4 text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Location</th>
                      <th className="text-left py-3 px-4 text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Condition</th>
                      <th className="text-left py-3 px-4 text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Status</th>
                      <th className="text-right py-3 px-4 text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {copiesData?.items.map((copy) => (
                      <tr key={copy.id} className="border-b border-earth-100 dark:border-earth-700/50 hover:bg-earth-50 dark:bg-earth-900 dark:hover:bg-earth-700/30">
                        <td className="py-3 px-4 text-sm font-mono text-lsc-dark dark:text-lsc-cream">{copy.barcode}</td>
                        <td className="py-3 px-4 text-sm text-lsc-dark dark:text-lsc-cream">{copy.catalog_item?.title ?? '-'}</td>
                        <td className="py-3 px-4 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{copy.location}</td>
                        <td className="py-3 px-4">
                          <span className={`px-2 py-1 rounded-full text-xs font-medium ${getConditionBadge(copy.condition)}`}>
                            {copy.condition}
                          </span>
                        </td>
                        <td className="py-3 px-4">
                          <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusBadge(copy.status)}`}>
                            {copy.status.replace('_', ' ')}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-right">
                          <div className="flex items-center justify-end gap-2">
                            <button
                              onClick={() => { setSelectedCopy(copy); setShowHistoryModal(true) }}
                              className="p-1 text-earth-600 hover:text-lsc-dark/70 dark:text-lsc-cream/70 dark:hover:text-earth-200"
                              title="View History"
                            >
                              <History className="w-4 h-4" />
                            </button>
                            <button
                              onClick={() => { setSelectedCopy(copy); setNewCondition(copy.condition); setShowConditionModal(true) }}
                              className="p-1 text-earth-600 hover:text-lsc-dark/70 dark:text-lsc-cream/70 dark:hover:text-earth-200"
                              title="Update Condition"
                            >
                              <Edit className="w-4 h-4" />
                            </button>
                            {copy.status !== 'withdrawn' && (
                              <button
                                onClick={() => { setSelectedCopy(copy); setShowWithdrawConfirm(true) }}
                                className="p-1 text-status-danger-500 hover:text-status-danger-700 dark:text-status-danger-300"
                                title="Withdraw"
                              >
                                <Trash2 className="w-4 h-4" />
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {/* Pagination */}
            {copiesData && copiesData.total > 20 && (
              <div className="flex items-center justify-between p-4 border-t border-lsc-border dark:border-earth-700">
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                  Showing {((page - 1) * 20) + 1} - {Math.min(page * 20, copiesData.total)} of {copiesData.total}
                </p>
                <div className="flex gap-2">
                  <button
                    onClick={() => setPage(page - 1)}
                    disabled={page === 1}
                    className="px-3 py-1 rounded bg-earth-100 dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70 disabled:opacity-50"
                  >
                    Previous
                  </button>
                  <button
                    onClick={() => setPage(page + 1)}
                    disabled={page * 20 >= copiesData.total}
                    className="px-3 py-1 rounded bg-earth-100 dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70 disabled:opacity-50"
                  >
                    Next
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Audits Tab */}
        {activeTab === 'audits' && (
          <div className="space-y-6">
            {selectedAudit ? (
              /* Active Audit View */
              <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-sm border border-lsc-border dark:border-earth-700 p-6">
                <div className="flex items-center justify-between mb-6">
                  <div>
                    <h2 className="font-serif text-xl font-bold text-lsc-dark dark:text-lsc-cream">{selectedAudit.name}</h2>
                    <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{selectedAudit.location_filter || 'All locations'}</p>
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => setSelectedAudit(null)}
                      className="px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70"
                    >
                      Back
                    </button>
                    {selectedAudit.completed_at === null && (
                      <button
                        onClick={() => completeAuditMutation.mutate(selectedAudit.id)}
                        disabled={completeAuditMutation.isPending}
                        className="px-4 py-2 rounded-lg bg-status-success-600 text-white hover:bg-status-success-700 disabled:opacity-50"
                      >
                        Complete Audit
                      </button>
                    )}
                  </div>
                </div>

                {/* Audit Stats */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
                  <div className="p-4 bg-earth-50 dark:bg-earth-700/50 rounded-lg">
                    <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Expected</p>
                    <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">{auditDetail?.items_expected ?? 0}</p>
                  </div>
                  <div className="p-4 bg-status-success-50 dark:bg-status-success-900/20 rounded-lg">
                    <p className="text-sm text-status-success-600 dark:text-status-success-400">Scanned</p>
                    <p className="text-2xl font-bold text-status-success-700 dark:text-status-success-300">{auditDetail?.items_found ?? 0}</p>
                  </div>
                  <div className="p-4 bg-status-danger-50 dark:bg-status-danger-900/20 rounded-lg">
                    <p className="text-sm text-status-danger-600 dark:text-status-danger-400">Missing</p>
                    <p className="text-2xl font-bold text-status-danger-700 dark:text-status-danger-300">{auditDetail?.items_missing ?? 0}</p>
                  </div>
                  <div className="p-4 bg-status-warning-50 dark:bg-status-warning-900/20 rounded-lg">
                    <p className="text-sm text-status-warning-600 dark:text-status-warning-400">Misplaced</p>
                    <p className="text-2xl font-bold text-status-warning-700 dark:text-status-warning-300">{auditDetail?.items_misplaced ?? 0}</p>
                  </div>
                </div>

                {/* Scan Form */}
                {selectedAudit.completed_at === null && (
                  <form onSubmit={handleScanAudit} className="mb-6">
                    <div className="flex gap-2">
                      <input
                        type="text"
                        value={auditBarcode}
                        onChange={(e) => setAuditBarcode(e.target.value)}
                        placeholder={t('inventoryManagement.scanOrEnterBarcode')}
                        autoFocus
                        className="flex-1 px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                      />
                      <button
                        type="submit"
                        disabled={scanAuditMutation.isPending}
                        className="px-6 py-2 rounded-lg bg-lsc-rose text-white hover:bg-lsc-rose/90 disabled:opacity-50"
                      >
                        {scanAuditMutation.isPending ? <Loader2 className="w-5 h-5 motion-safe:animate-spin" /> : 'Scan'}
                      </button>
                    </div>
                  </form>
                )}
              </div>
            ) : (
              /* Audits List */
              <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-sm border border-lsc-border dark:border-earth-700">
                <div className="p-4 border-b border-lsc-border dark:border-earth-700 flex items-center justify-between">
                  <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">Inventory Audits</h2>
                  <button
                    onClick={() => setShowNewAuditModal(true)}
                    className="flex items-center gap-2 px-4 py-2 rounded-lg bg-lsc-rose text-white hover:bg-lsc-rose/90"
                  >
                    <Plus className="w-4 h-4" />
                    New Audit
                  </button>
                </div>

                {loadingAudits ? (
                  <div className="flex items-center justify-center h-64">
                    <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" />
                  </div>
                ) : (
                  <div className="divide-y divide-earth-200 dark:divide-earth-700">
                    {auditsData?.items.map((audit) => (
                      <div
                        key={audit.id}
                        className="p-4 hover:bg-earth-50 dark:bg-earth-900 dark:hover:bg-earth-700/30 cursor-pointer"
                        onClick={() => setSelectedAudit(audit)} tabIndex={0} role="button" onKeyDown={(e: React.KeyboardEvent) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); (() => setSelectedAudit(audit))(); } }}
                      >
                        <div className="flex items-center justify-between">
                          <div>
                            <h3 className="font-medium text-lsc-dark dark:text-lsc-cream">{audit.name}</h3>
                            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                              {audit.location_filter || 'All locations'} &bull; Started {new Date(audit.started_at).toLocaleDateString()}
                            </p>
                          </div>
                          <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                            audit.completed_at
                              ? 'bg-status-success-100 text-status-success-800 dark:bg-status-success-900/30 dark:text-status-success-400'
                              : 'bg-earth-100 text-earth-800 dark:bg-earth-800/30 dark:text-lsc-rose-light'
                          }`}>
                            {audit.completed_at ? 'completed' : 'in progress'}
                          </span>
                        </div>
                      </div>
                    ))}
                    {auditsData?.items.length === 0 && (
                      <div className="p-8 text-center text-lsc-dark/70 dark:text-lsc-cream/70">
                        No audits found. Start a new audit to track inventory.
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Barcode Lookup Tab */}
        {activeTab === 'lookup' && (
          <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-sm border border-lsc-border dark:border-earth-700 p-6">
            <form onSubmit={handleLookup} className="max-w-xl mx-auto">
              <div className="flex gap-2">
                <div className="relative flex-1">
                  <ScanBarcode className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
                  <input
                    type="text"
                    value={barcode}
                    onChange={(e) => setBarcode(e.target.value)}
                    placeholder={t('inventoryManagement.scanOrEnterBarcode2')}
                    autoFocus
                    className="w-full pl-10 pr-4 py-3 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream text-lg"
                  />
                </div>
                <button
                  type="submit"
                  disabled={lookupMutation.isPending}
                  className="px-6 py-3 rounded-lg bg-lsc-rose text-white hover:bg-lsc-rose/90 disabled:opacity-50"
                >
                  {lookupMutation.isPending ? <Loader2 className="w-5 h-5 motion-safe:animate-spin" /> : <Search className="w-5 h-5" />}
                </button>
              </div>
            </form>

            {lookupError && (
              <div className="mt-6 p-4 bg-status-danger-50 dark:bg-status-danger-900/20 rounded-lg text-center">
                <XCircle className="w-8 h-8 text-status-danger-500 mx-auto mb-2" />
                <p className="text-status-danger-700 dark:text-status-danger-400">{lookupError}</p>
              </div>
            )}

            {lookupResult && (
              <div className="mt-6 p-6 bg-earth-50 dark:bg-earth-700/50 rounded-lg">
                <div className="flex items-start gap-4">
                  <CheckCircle className="w-8 h-8 text-status-success-500 flex-shrink-0" />
                  <div className="flex-1">
                    <h3 className="font-serif text-xl font-bold text-lsc-dark dark:text-lsc-cream">
                      {lookupResult.catalog_item?.title ?? 'Unknown Item'}
                    </h3>
                    <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{lookupResult.catalog_item?.author ?? '-'}</p>
                    <div className="mt-4 grid grid-cols-2 gap-4">
                      <div>
                        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Barcode</p>
                        <p className="font-mono text-lsc-dark dark:text-lsc-cream">{lookupResult.barcode}</p>
                      </div>
                      <div>
                        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Call Number</p>
                        <p className="text-lsc-dark dark:text-lsc-cream">{lookupResult.call_number}</p>
                      </div>
                      <div>
                        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Location</p>
                        <p className="text-lsc-dark dark:text-lsc-cream">{lookupResult.location}</p>
                      </div>
                      <div>
                        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Status</p>
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusBadge(lookupResult.status)}`}>
                          {lookupResult.status.replace('_', ' ')}
                        </span>
                      </div>
                      <div>
                        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Condition</p>
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${getConditionBadge(lookupResult.condition)}`}>
                          {lookupResult.condition}
                        </span>
                      </div>
                    </div>
                    <div className="mt-4 flex gap-2">
                      <button
                        onClick={() => { setSelectedCopy(lookupResult); setShowHistoryModal(true) }}
                        className="px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-earth-100 dark:bg-earth-700 dark:hover:bg-earth-700"
                      >
                        View History
                      </button>
                      <button
                        onClick={() => { setSelectedCopy(lookupResult); setNewCondition(lookupResult.condition); setShowConditionModal(true) }}
                        className="px-4 py-2 rounded-lg bg-lsc-rose text-white hover:bg-lsc-rose/90"
                      >
                        Update Condition
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Condition History Modal */}
        {showHistoryModal && selectedCopy && (
          <ModalBackdrop onClose={() => setShowHistoryModal(false)} title="Condition History">
            <div className="bg-lsc-white dark:bg-earth-800 rounded-lg max-w-lg w-full max-h-[80vh] overflow-hidden">
              <div className="p-4 border-b border-lsc-border dark:border-earth-700 flex items-center justify-between">
                <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">Condition History</h3>
                <button onClick={() => setShowHistoryModal(false)} className="text-earth-600 hover:text-lsc-dark/70 dark:text-lsc-cream/70 dark:hover:text-earth-200">
                  <XCircle className="w-5 h-5" />
                </button>
              </div>
              <div className="p-4 overflow-y-auto max-h-96">
                {conditionHistory?.length === 0 ? (
                  <p className="text-center text-lsc-dark/70 dark:text-lsc-cream/70">{t('inventoryManagement.noConditionChangesRecorded')}</p>
                ) : (
                  <div className="space-y-4">
                    {conditionHistory?.map((entry) => (
                      <div key={entry.id} className="flex items-start gap-3 p-3 bg-earth-50 dark:bg-earth-700/50 rounded-lg">
                        <History className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70 mt-0.5" />
                        <div>
                          <p className="text-sm text-lsc-dark dark:text-lsc-cream">
                            <span className={`px-2 py-0.5 rounded text-xs ${getConditionBadge(entry.old_condition)}`}>{entry.old_condition}</span>
                            {' → '}
                            <span className={`px-2 py-0.5 rounded text-xs ${getConditionBadge(entry.new_condition)}`}>{entry.new_condition}</span>
                          </p>
                          {entry.notes && <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">{entry.notes}</p>}
                          <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                            {new Date(entry.changed_at).toLocaleString()} by {entry.changed_by_name ?? 'Unknown'}
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </ModalBackdrop>
        )}

        {/* Update Condition Modal */}
        {showConditionModal && selectedCopy && (
          <ModalBackdrop onClose={() => setShowConditionModal(false)} title="Update Condition">
            <div className="bg-lsc-white dark:bg-earth-800 rounded-lg max-w-md w-full">
              <div className="p-4 border-b border-lsc-border dark:border-earth-700">
                <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">Update Condition</h3>
              </div>
              <div className="p-4 space-y-4">
                <div>
                  <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">New Condition</label>
                  <select
                    value={newCondition}
                    onChange={(e) => setNewCondition(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                  >
                    {CONDITIONS.map((c) => (
                      <option key={c} value={c}>{c}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Notes (optional)</label>
                  <textarea
                    value={conditionNotes}
                    onChange={(e) => setConditionNotes(e.target.value)}
                    rows={3}
                    className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                  />
                </div>
              </div>
              <div className="p-4 border-t border-lsc-border dark:border-earth-700 flex justify-end gap-2">
                <button
                  onClick={() => setShowConditionModal(false)}
                  className="px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70"
                >
                  Cancel
                </button>
                <button
                  onClick={() => conditionMutation.mutate({ copyId: selectedCopy.id, data: { new_condition: newCondition, ...(conditionNotes ? { repair_notes: conditionNotes } : {}),} })}
                  disabled={conditionMutation.isPending || newCondition === selectedCopy.condition}
                  className="px-4 py-2 rounded-lg bg-lsc-rose text-white hover:bg-lsc-rose/90 disabled:opacity-50"
                >
                  {conditionMutation.isPending ? <Loader2 className="w-5 h-5 motion-safe:animate-spin" /> : 'Update'}
                </button>
              </div>
            </div>
          </ModalBackdrop>
        )}

        {/* New Audit Modal */}
        {showNewAuditModal && (
          <ModalBackdrop onClose={() => setShowNewAuditModal(false)} title="Start New Audit">
            <div className="bg-lsc-white dark:bg-earth-800 rounded-lg max-w-md w-full">
              <div className="p-4 border-b border-lsc-border dark:border-earth-700">
                <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">Start New Audit</h3>
              </div>
              <div className="p-4 space-y-4">
                <div>
                  <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Audit Name *</label>
                  <input
                    type="text"
                    value={newAuditName}
                    onChange={(e) => setNewAuditName(e.target.value)}
                    placeholder={t('placeholder.inventoryManagement.egJanuary2026Fiction')}
                    className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Location (optional)</label>
                  <input
                    type="text"
                    value={newAuditLocation}
                    onChange={(e) => setNewAuditLocation(e.target.value)}
                    placeholder={t('inventoryManagement.leaveBlankForAllLocations')}
                    className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                  />
                </div>
              </div>
              <div className="p-4 border-t border-lsc-border dark:border-earth-700 flex justify-end gap-2">
                <button
                  onClick={() => setShowNewAuditModal(false)}
                  className="px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70"
                >
                  Cancel
                </button>
                <button
                  onClick={() => startAuditMutation.mutate({ name: newAuditName, ...(newAuditLocation ? { location_filter: newAuditLocation } : {}),})}
                  disabled={startAuditMutation.isPending || !newAuditName.trim()}
                  className="px-4 py-2 rounded-lg bg-lsc-rose text-white hover:bg-lsc-rose/90 disabled:opacity-50"
                >
                  {startAuditMutation.isPending ? <Loader2 className="w-5 h-5 motion-safe:animate-spin" /> : 'Start Audit'}
                </button>
              </div>
            </div>
          </ModalBackdrop>
        )}

        {/* Withdraw Confirmation */}
        <ConfirmDialog
          isOpen={showWithdrawConfirm}
          onClose={() => setShowWithdrawConfirm(false)}
          onConfirm={() => { if (selectedCopy) withdrawMutation.mutate(selectedCopy.id) }}
          title="Withdraw Item"
          message={`Are you sure you want to withdraw "${selectedCopy?.catalog_item?.title ?? 'this item'}"? This action cannot be undone.`}
          confirmLabel="Withdraw"
          confirmVariant="danger"
        />
      </PageContainer>
    </div>
  </AdminShell>
  )
}
