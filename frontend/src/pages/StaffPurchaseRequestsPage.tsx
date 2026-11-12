/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect, useCallback } from 'react'
import { useAuth } from '../contexts/AuthContext'
import {
  BookOpen, Check, X, Loader2, BarChart3,
  Package, AlertTriangle, Star, Filter, CheckSquare, Square, FileText, List
} from 'lucide-react'
import toast from 'react-hot-toast'
import {
  getReviewQueue, approveRequest, declineRequest, bulkApprove, bulkDecline,
  linkToOrder, markReceived, getFulfillmentStats, getDeclineTemplates,
  createDeclineTemplate, deleteDeclineTemplate, addPurchaseRequestToSelection,
  PurchaseRequestStaff, PurchaseRequestStatus, FulfillmentStats, DeclineReasonTemplate
} from '@/api/purchase-requests-api'
import { useTranslation} from '@/i18n'
import ConfirmDialog from "@/components/ConfirmDialog"
import { AdminShell } from '../components/shells/AdminShell'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'
import PageContainer from '@/components/layout/PageContainer'

const STATUS_OPTIONS: { value: PurchaseRequestStatus | ''; label: string }[] = [
  { value: '', label: 'All Statuses' },
  { value: 'pending', label: 'Pending' },
  { value: 'under_review', label: 'Under Review' },
  { value: 'approved', label: 'Approved' },
  { value: 'ordered', label: 'Ordered' },
  { value: 'received', label: 'Received' },
  { value: 'declined', label: 'Declined' },
  { value: 'cancelled', label: 'Cancelled' },
]

function StatusBadge({ status }: { status: PurchaseRequestStatus }) {
  const styles: Record<string, string> = {
    pending: 'bg-status-warning-100 text-status-warning-800 dark:bg-status-warning-900/30 dark:text-status-warning-400',
    under_review: 'bg-earth-100 text-earth-800 dark:bg-earth-800/30 dark:text-lsc-rose-light',
    approved: 'bg-status-success-100 text-status-success-800 dark:bg-status-success-900/30 dark:text-status-success-400',
    ordered: 'bg-lsc-rose/10 text-lsc-rose dark:bg-lsc-rose/20 dark:text-lsc-rose-light',
    received: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-400',
    declined: 'bg-status-danger-100 text-status-danger-800 dark:bg-status-danger-900/30 dark:text-status-danger-400',
    cancelled: 'bg-lsc-cream text-lsc-dark/70 dark:bg-earth-700/30 dark:text-lsc-cream/70',
  }
  const labels: Record<string, string> = {
    pending: 'Pending',
    under_review: 'Under Review',
    approved: 'Approved',
    ordered: 'Ordered',
    received: 'Received',
    declined: 'Declined',
    cancelled: 'Cancelled',
  }
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${styles[status] || styles.pending}`}>
      {labels[status] || status}
    </span>
  )
}

export default function StaffPurchaseRequestsPage(): React.ReactElement {
  const { t } = useTranslation()
  const { token } = useAuth()
  const [activeTab, setActiveTab] = useState<'queue' | 'stats' | 'templates'>('queue')
  const [isLoading, setIsLoading] = useState(false)

  // Queue state
  const [requests, setRequests] = useState<PurchaseRequestStaff[]>([])
  const [totalRequests, setTotalRequests] = useState(0)
  const [page, setPage] = useState(1)
  const [statusFilter, setStatusFilter] = useState<PurchaseRequestStatus | ''>('')
  const [dupFilter, setDupFilter] = useState<boolean | undefined>(undefined)

  // Selection for bulk ops
  const [selected, setSelected] = useState<Set<number>>(new Set())
  const [showBulkDecline, setShowBulkDecline] = useState(false)
  const [bulkDeclineReason, setBulkDeclineReason] = useState('')

  // Individual action modals
  const [declineModal, setDeclineModal] = useState<{ id: number; title: string } | null>(null)
  const [declineReason, setDeclineReason] = useState('')
  const [orderLinkModal, setOrderLinkModal] = useState<{ id: number; title: string } | null>(null)
  const [orderLinkId, setOrderLinkId] = useState('')

  // Stats
  const [stats, setStats] = useState<FulfillmentStats | null>(null)

  // Templates
  const [templates, setTemplates] = useState<DeclineReasonTemplate[]>([])
  const [newTemplateLabel, setNewTemplateLabel] = useState('')
  const [newTemplateMessage, setNewTemplateMessage] = useState('')
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [pendingAction, setPendingAction] = useState<(() => void) | null>(null)

  const loadQueue = useCallback(async () => {
    if (!token) return
    setIsLoading(true)
    try {
      const data = await getReviewQueue(
        token, page,
        statusFilter || undefined,
        dupFilter,
      )
      setRequests(data.items)
      setTotalRequests(data.total)
    } catch {
      toast.error(t('staffPurchaseRequests.failedToLoadReviewQueue'))
    } finally {
      setIsLoading(false)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, page, statusFilter, dupFilter])

  useEffect(() => {
    if (activeTab === 'queue') loadQueue()
  }, [activeTab, loadQueue])

  useEffect(() => {
    if (activeTab === 'stats' && token) {
      getFulfillmentStats(token).then(setStats).catch(() => toast.error(t('staffPurchaseRequests.failedToLoadStats')))
    }
    if (activeTab === 'templates' && token) {
      getDeclineTemplates(token).then(setTemplates).catch(() => toast.error(t('staffPurchaseRequests.failedToLoadTemplates')))
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab, token])

  // Bulk selection
  const toggleSelect = (id: number) => {
    const next = new Set(selected)
    if (next.has(id)) next.delete(id)
    else next.add(id)
    setSelected(next)
  }

  const toggleSelectAll = () => {
    if (selected.size === requests.length) {
      setSelected(new Set())
    } else {
      setSelected(new Set(requests.map(r => r.id)))
    }
  }

  const actionableSelected = requests.filter(
    r => selected.has(r.id) && (r.status === 'pending' || r.status === 'under_review')
  )

  // Actions
  const handleApprove = async (id: number) => {
    if (!token) return
    try {
      await approveRequest(id, token)
      toast.success(t('staffPurchaseRequests.toast.requestApproved'))
      loadQueue()
    } catch {
      toast.error(t('staffPurchaseRequests.toast.approveFailed'))
    }
  }

  const handleDeclineSubmit = async () => {
    if (!token || !declineModal || !declineReason.trim()) return
    try {
      await declineRequest(declineModal.id, token, declineReason)
      toast.success(t('staffPurchaseRequests.toast.requestDeclined'))
      setDeclineModal(null)
      setDeclineReason('')
      loadQueue()
    } catch {
      toast.error(t('staffPurchaseRequests.toast.declineFailed'))
    }
  }

  const handleBulkApprove = async () => {
    if (!token || actionableSelected.length === 0) return
    try {
      const result = await bulkApprove(actionableSelected.map(r => r.id), token)
      toast.success(t('staffPurchaseRequests.toast.bulkApproved', { succeeded: result.succeeded, total: result.total_requested }))
      setSelected(new Set())
      loadQueue()
    } catch {
      toast.error(t('staffPurchaseRequests.toast.bulkApproveFailed'))
    }
  }

  const handleBulkDeclineSubmit = async () => {
    if (!token || actionableSelected.length === 0 || !bulkDeclineReason.trim()) return
    try {
      const result = await bulkDecline(actionableSelected.map(r => r.id), token, bulkDeclineReason)
      toast.success(t('staffPurchaseRequests.toast.bulkDeclined', { succeeded: result.succeeded, total: result.total_requested }))
      setSelected(new Set())
      setShowBulkDecline(false)
      setBulkDeclineReason('')
      loadQueue()
    } catch {
      toast.error(t('staffPurchaseRequests.toast.bulkDeclineFailed'))
    }
  }

  const handleLinkOrder = async () => {
    if (!token || !orderLinkModal || !orderLinkId) return
    try {
      await linkToOrder(orderLinkModal.id, parseInt(orderLinkId), token)
      toast.success(t('staffPurchaseRequests.linkedToPurchaseOrderPatron'))
      setOrderLinkModal(null)
      setOrderLinkId('')
      loadQueue()
    } catch {
      toast.error(t('staffPurchaseRequests.failedToLinkOrder'))
    }
  }

  const handleMarkReceived = async (id: number) => {
    if (!token) return
    try {
      await markReceived(id, token)
      toast.success(t('staffPurchaseRequests.markedAsReceivedPatronNotified'))
      loadQueue()
    } catch {
      toast.error(t('staffPurchaseRequests.failedToMarkReceived'))
    }
  }

  const handleAddToSelection = async (requestId: number) => {
    if (!token) return
    try {
      await addPurchaseRequestToSelection(requestId, token)
      toast.success(t('staffPurchaseRequests.toast.addedToSelectionList'))
      loadQueue()
    } catch (error: unknown) {
      toast.error(error instanceof Error ? error.message : t('staffPurchaseRequests.toast.addToSelectionListFailed'))
    }
  }

  const handleCreateTemplate = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!token || !newTemplateLabel.trim() || !newTemplateMessage.trim()) return
    try {
      await createDeclineTemplate(newTemplateLabel, newTemplateMessage, token)
      toast.success(t('staffPurchaseRequests.toast.templateCreated'))
      setNewTemplateLabel('')
      setNewTemplateMessage('')
      const updated = await getDeclineTemplates(token)
      setTemplates(updated)
    } catch {
      toast.error(t('staffPurchaseRequests.failedToCreateTemplate'))
    }
  }

  const handleDeleteTemplate = (id: number) => {
    if (!token) return
    setPendingAction(() => async () => {
      try {
        await deleteDeclineTemplate(id, token)
        setTemplates(templates.filter(t => t.id !== id))
        toast.success(t('staffPurchaseRequests.toast.templateDeleted'))
      } catch {
        toast.error(t('staffPurchaseRequests.toast.deleteTemplateFailed'))
      }
    })
    setConfirmOpen(true)
  }

  const applyTemplate = (message: string) => {
    if (declineModal) {
      setDeclineReason(message)
    } else if (showBulkDecline) {
      setBulkDeclineReason(message)
    }
  }

  return (

    <AdminShell title="Purchase Requests">    <PageContainer width="wide" className="py-8">
      <div className="mb-6">
        <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream flex items-center gap-3">
          <BookOpen className="w-7 h-7 text-brand-600" />
          Purchase Request Review
        </h1>
        <p className="mt-1 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
          Review, approve, or decline patron purchase requests
        </p>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-lsc-border dark:border-earth-700 mb-6 gap-1">
        {[
          { key: 'queue' as const, label: 'Review Queue', icon: <Filter className="w-4 h-4" /> },
          { key: 'stats' as const, label: 'Fulfillment Stats', icon: <BarChart3 className="w-4 h-4" /> },
          { key: 'templates' as const, label: 'Decline Templates', icon: <FileText className="w-4 h-4" /> },
        ].map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
              activeTab === tab.key
                ? 'border-brand-600 text-brand-600 dark:text-brand-400'
                : 'border-transparent text-lsc-dark/70 hover:text-lsc-dark/70 dark:text-lsc-cream/70'
            }`}
          >
            {tab.icon}
            {tab.label}
          </button>
        ))}
      </div>

      {/* ========== Queue Tab ========== */}
      {activeTab === 'queue' && (
        <>
          {/* Filters */}
          <div className="flex flex-wrap items-center gap-3 mb-4">
            <select
              value={statusFilter}
              onChange={e => { setStatusFilter(e.target.value as PurchaseRequestStatus | ''); setPage(1) }}
              className="px-3 py-2 text-sm border border-lsc-border dark:border-earth-600 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
            >
              {STATUS_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
            <select
              value={dupFilter === undefined ? '' : String(dupFilter)}
              onChange={e => { setDupFilter(e.target.value === '' ? undefined : e.target.value === 'true'); setPage(1) }}
              className="px-3 py-2 text-sm border border-lsc-border dark:border-earth-600 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
            >
              <option value="">All Items</option>
              <option value="true">Has Catalog Duplicate</option>
              <option value="false">No Duplicate</option>
            </select>
            <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 ml-auto">
              {totalRequests} request{totalRequests !== 1 ? 's' : ''}
            </span>
          </div>

          {/* Bulk Actions */}
          {selected.size > 0 && (
            <div className="flex items-center gap-3 mb-4 p-3 bg-brand-50 dark:bg-brand-900/20 border border-brand-200 dark:border-brand-800 rounded-lg">
              <span className="text-sm font-medium text-brand-800 dark:text-brand-300">
                {actionableSelected.length} actionable selected
              </span>
              <button
                onClick={handleBulkApprove}
                disabled={actionableSelected.length === 0}
                className="inline-flex items-center px-3 py-1.5 text-sm bg-status-success-600 text-white rounded-lg hover:bg-status-success-700 disabled:opacity-50"
              >
                <Check className="w-4 h-4 mr-1" /> Approve All
              </button>
              <button
                onClick={() => setShowBulkDecline(true)}
                disabled={actionableSelected.length === 0}
                className="inline-flex items-center px-3 py-1.5 text-sm bg-status-danger-600 text-white rounded-lg hover:bg-status-danger-700 disabled:opacity-50"
              >
                <X className="w-4 h-4 mr-1" /> Decline All
              </button>
              <button
                onClick={() => setSelected(new Set())}
                className="text-sm text-lsc-dark/70 hover:text-lsc-dark/70 dark:text-lsc-cream/70 ml-auto"
              >
                Clear selection
              </button>
            </div>
          )}

          {/* Request List */}
          {isLoading ? (
            <div className="text-center py-12 text-lsc-dark/70 dark:text-lsc-cream/70">
              <Loader2 className="w-8 h-8 mx-auto motion-safe:animate-spin mb-2" />
            </div>
          ) : requests.length === 0 ? (
            <div className="text-center py-12 text-lsc-dark/70 dark:text-lsc-cream/70">
              <BookOpen className="w-12 h-12 mx-auto text-earth-600 dark:text-earth-600 mb-3" />
              <p>{t('staffPurchaseRequests.noPurchaseRequestsFound')}</p>
            </div>
          ) : (
            <div className="space-y-3">
              {/* Select all */}
              <div className="flex items-center gap-2 px-4 py-2">
                <button
                  onClick={toggleSelectAll}
                  aria-label={selected.size === requests.length
                    ? t('aria.staffPurchaseRequests.deselectAllRequests', 'Deselect all requests')
                    : t('aria.staffPurchaseRequests.selectAllRequests', 'Select all requests')}
                  className="text-earth-600 dark:text-earth-600 hover:text-earth-600 dark:hover:text-earth-300"
                >
                  {selected.size === requests.length
                    ? <CheckSquare className="w-5 h-5 text-brand-600" aria-hidden="true" />
                    : <Square className="w-5 h-5" aria-hidden="true" />
                  }
                </button>
                <span className="text-xs text-earth-600 dark:text-earth-400">Select all</span>
              </div>

              {requests.map(req => (
                <div
                  key={req.id}
                  className={`bg-lsc-white dark:bg-earth-800 rounded-lg border p-4 ${
                    selected.has(req.id)
                      ? 'border-brand-300 dark:border-brand-700 ring-1 ring-brand-200'
                      : 'border-lsc-border dark:border-earth-700'
                  }`}
                >
                  <div className="flex items-start gap-3">
                    <button
                      onClick={() => toggleSelect(req.id)}
                      aria-label={selected.has(req.id)
                        ? t('aria.staffPurchaseRequests.deselectRequest', 'Deselect request')
                        : t('aria.staffPurchaseRequests.selectRequest', 'Select request')}
                      className="mt-1 text-earth-600 dark:text-earth-600 hover:text-earth-600 dark:hover:text-earth-300"
                    >
                      {selected.has(req.id)
                        ? <CheckSquare className="w-5 h-5 text-brand-600" aria-hidden="true" />
                        : <Square className="w-5 h-5" aria-hidden="true" />
                      }
                    </button>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">{req.title}</h3>
                        <StatusBadge status={req.status} />
                        {req.duplicate_of_catalog_id && (
                          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-status-warning-100 text-status-warning-800 dark:bg-status-warning-900/30 dark:text-status-warning-400">
                            <AlertTriangle className="w-3 h-3 mr-1" />
                            Duplicate: {req.duplicate_title || `#${req.duplicate_of_catalog_id}`}
                          </span>
                        )}
                        {req.review_source_checked && req.review_source_rating && (
                          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-category-100 text-category-800 dark:bg-category-900/30 dark:text-category-400">
                            <Star className="w-3 h-3 mr-1" />
                            {req.review_source_rating.toFixed(1)}
                          </span>
                        )}
                      </div>
                      {req.author && <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">by {req.author}</p>}
                      <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                        {req.isbn && <span>ISBN: {req.isbn}</span>}
                        <span>Type: {req.material_type}</span>
                        <span>Patron: {req.patron_name || `#${req.patron_id}`}</span>
                        <span>Submitted: {new Date(req.created_at).toLocaleDateString()}</span>
                      </div>
                      {req.patron_notes && (
                        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1 italic">"{req.patron_notes}"</p>
                      )}
                      {req.staff_notes && (
                        <p className="text-xs text-lsc-rose dark:text-lsc-rose-light mt-1">Staff note: {req.staff_notes}</p>
                      )}
                    </div>

                    {/* Action buttons */}
                    <div className="flex flex-col gap-1.5 flex-shrink-0">
                      {(req.status === 'pending' || req.status === 'under_review') && (
                        <>
                          <button
                            onClick={() => handleApprove(req.id)}
                            className="inline-flex items-center px-3 py-1.5 text-xs bg-status-success-600 text-white rounded-lg hover:bg-status-success-700"
                          >
                            <Check className="w-3.5 h-3.5 mr-1" /> Approve
                          </button>
                          <button
                            onClick={() => { setDeclineModal({ id: req.id, title: req.title }); setDeclineReason('') }}
                            className="inline-flex items-center px-3 py-1.5 text-xs bg-status-danger-600 text-white rounded-lg hover:bg-status-danger-700"
                          >
                            <X className="w-3.5 h-3.5 mr-1" /> Decline
                          </button>
                        </>
                      )}
                      {req.status === 'approved' && (
                        <>
                          <button
                            onClick={() => handleAddToSelection(req.id)}
                            className="inline-flex items-center px-3 py-1.5 text-xs bg-brand-600 text-white rounded-lg hover:bg-brand-700"
                          >
                            <List className="w-3.5 h-3.5 mr-1" /> Add to Selection
                          </button>
                          <button
                            onClick={() => { setOrderLinkModal({ id: req.id, title: req.title }); setOrderLinkId('') }}
                            className="inline-flex items-center px-3 py-1.5 text-xs bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90"
                          >
                            <Package className="w-3.5 h-3.5 mr-1" /> Link Order
                          </button>
                          <button
                            onClick={() => handleMarkReceived(req.id)}
                            className="inline-flex items-center px-3 py-1.5 text-xs bg-emerald-600 text-white rounded-lg hover:bg-emerald-700"
                          >
                            <Check className="w-3.5 h-3.5 mr-1" /> Received
                          </button>
                        </>
                      )}
                      {req.status === 'ordered' && (
                        <button
                          onClick={() => handleMarkReceived(req.id)}
                          className="inline-flex items-center px-3 py-1.5 text-xs bg-emerald-600 text-white rounded-lg hover:bg-emerald-700"
                        >
                          <Check className="w-3.5 h-3.5 mr-1" /> Received
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              ))}

              {/* Pagination */}
              {totalRequests > 20 && (
                <div className="flex justify-center gap-2 mt-4">
                  <button
                    onClick={() => setPage(Math.max(1, page - 1))}
                    disabled={page === 1}
                    className="px-3 py-1.5 text-sm border rounded-lg disabled:opacity-50"
                  >
                    Previous
                  </button>
                  <span className="px-3 py-1.5 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                    Page {page} of {Math.ceil(totalRequests / 20)}
                  </span>
                  <button
                    onClick={() => setPage(page + 1)}
                    disabled={page * 20 >= totalRequests}
                    className="px-3 py-1.5 text-sm border rounded-lg disabled:opacity-50"
                  >
                    Next
                  </button>
                </div>
              )}
            </div>
          )}
        </>
      )}

      {/* ========== Stats Tab ========== */}
      {activeTab === 'stats' && (
        <div>
          {!stats ? (
            <div className="text-center py-12"><Loader2 className="w-8 h-8 mx-auto motion-safe:animate-spin" /></div>
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {[
                { label: 'Total Requests', value: stats.total_requests, color: 'text-lsc-dark' },
                { label: 'Pending', value: stats.pending_count, color: 'text-status-warning-600' },
                { label: 'Under Review', value: stats.under_review_count, color: 'text-lsc-rose dark:text-lsc-rose-light' },
                { label: 'Approved', value: stats.approved_count, color: 'text-status-success-600' },
                { label: 'Ordered', value: stats.ordered_count, color: 'text-lsc-rose' },
                { label: 'Received', value: stats.received_count, color: 'text-emerald-600' },
                { label: 'Declined', value: stats.declined_count, color: 'text-status-danger-600' },
                { label: 'Cancelled', value: stats.cancelled_count, color: 'text-earth-600 dark:text-earth-400' },
              ].map(stat => (
                <div key={stat.label} className="bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700 p-4">
                  <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{stat.label}</p>
                  <p className={`text-2xl font-bold ${stat.color} dark:text-lsc-cream mt-1`}>{stat.value}</p>
                </div>
              ))}
              <div className="md:col-span-2 bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700 p-4">
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Fulfillment Rate</p>
                <p className="text-3xl font-bold text-brand-600 dark:text-brand-400 mt-1">{stats.fulfillment_rate}%</p>
                <div className="w-full bg-earth-200 dark:bg-earth-700 rounded-full h-2 mt-2">
                  <div className="bg-brand-600 h-2 rounded-full" style={{ width: `${Math.min(100, stats.fulfillment_rate)}%` }} />
                </div>
              </div>
              <div className="bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700 p-4">
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{t('staffPurchaseRequests.avgDaysToReview')}</p>
                <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream mt-1">
                  {stats.avg_days_to_review !== null ? stats.avg_days_to_review : '--'}
                </p>
              </div>
              <div className="bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700 p-4">
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{t('staffPurchaseRequests.avgDaysToFulfill')}</p>
                <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream mt-1">
                  {stats.avg_days_to_fulfill !== null ? stats.avg_days_to_fulfill : '--'}
                </p>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ========== Templates Tab ========== */}
      {activeTab === 'templates' && (
        <div className="space-y-6">
          <form onSubmit={handleCreateTemplate} className="bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700 p-5 space-y-4">
            <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">New Decline Template</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <input
                type="text"
                required
                maxLength={100}
                value={newTemplateLabel}
                onChange={e => setNewTemplateLabel(e.target.value)}
                placeholder={t('staffPurchaseRequests.labelEGBudgetConstraints')}
                className="px-3 py-2 border border-lsc-border dark:border-earth-600 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream text-sm"
              />
              <input
                type="text"
                required
                maxLength={2000}
                value={newTemplateMessage}
                onChange={e => setNewTemplateMessage(e.target.value)}
                placeholder={t('staffPurchaseRequests.messageShownToPatron')}
                className="md:col-span-2 px-3 py-2 border border-lsc-border dark:border-earth-600 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream text-sm"
              />
            </div>
            <button type="submit" className="px-4 py-2 text-sm bg-brand-600 text-white rounded-lg hover:bg-brand-700">
              Create Template
            </button>
          </form>

          <div className="space-y-3">
            {templates.length === 0 ? (
              <p className="text-center py-8 text-lsc-dark/70 dark:text-lsc-cream/70">{t('staffPurchaseRequests.noDeclineTemplatesYetCreate')}</p>
            ) : (
              templates.map(t => (
                <div key={t.id} className="bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700 p-4 flex items-start justify-between gap-4">
                  <div>
                    <p className="font-medium text-lsc-dark dark:text-lsc-cream">{t.label}</p>
                    <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">{t.message}</p>
                    <p className="text-xs text-earth-600 dark:text-earth-400 mt-1">Used {t.usage_count} times</p>
                  </div>
                  <div className="flex gap-2 flex-shrink-0">
                    {(declineModal || showBulkDecline) && (
                      <button
                        onClick={() => applyTemplate(t.message)}
                        className="px-3 py-1.5 text-xs bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90"
                      >
                        Use
                      </button>
                    )}
                    <button
                      onClick={() => handleDeleteTemplate(t.id)}
                      className="px-3 py-1.5 text-xs text-status-danger-600 border border-status-danger-300 rounded-lg hover:bg-status-danger-50 dark:hover:bg-status-danger-900/20"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* ========== Decline Modal ========== */}
      {declineModal && (
        <ModalBackdrop onClose={() => setDeclineModal(null)} title="Decline Request" role="alertdialog">
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg max-w-md w-full mx-4 p-6">
            <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-2">Decline Request</h3>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">"{declineModal.title}"</p>

            {/* Quick templates */}
            {templates.length > 0 && (
              <div className="mb-3">
                <p className="text-xs text-earth-600 dark:text-earth-400 mb-1">Quick templates:</p>
                <div className="flex flex-wrap gap-1">
                  {templates.slice(0, 5).map(t => (
                    <button
                      key={t.id}
                      onClick={() => setDeclineReason(t.message)}
                      className="px-2 py-1 text-xs bg-lsc-cream dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70 rounded hover:bg-earth-200 dark:hover:bg-earth-600"
                    >
                      {t.label}
                    </button>
                  ))}
                </div>
              </div>
            )}

            <textarea
              rows={3}
              required
              value={declineReason}
              onChange={e => setDeclineReason(e.target.value)}
              placeholder={t('staffPurchaseRequests.reasonShownToPatron')}
              className="w-full px-3 py-2 border border-lsc-border dark:border-earth-600 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream text-sm mb-4"
            />
            <div className="flex justify-end gap-3">
              <button onClick={() => setDeclineModal(null)} className="px-4 py-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark">
                Cancel
              </button>
              <button
                onClick={handleDeclineSubmit}
                disabled={!declineReason.trim()}
                className="px-4 py-2 text-sm bg-status-danger-600 text-white rounded-lg hover:bg-status-danger-700 disabled:opacity-50"
              >
                Decline
              </button>
            </div>
          </div>
        </ModalBackdrop>
      )}

      {/* ========== Bulk Decline Modal ========== */}
      {showBulkDecline && (
        <ModalBackdrop onClose={() => { setShowBulkDecline(false); setBulkDeclineReason('') }} title="Bulk Decline" role="alertdialog">
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg max-w-md w-full mx-4 p-6">
            <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-2">
              Bulk Decline ({actionableSelected.length} requests)
            </h3>

            {templates.length > 0 && (
              <div className="mb-3">
                <p className="text-xs text-earth-600 dark:text-earth-400 mb-1">Quick templates:</p>
                <div className="flex flex-wrap gap-1">
                  {templates.slice(0, 5).map(t => (
                    <button
                      key={t.id}
                      onClick={() => setBulkDeclineReason(t.message)}
                      className="px-2 py-1 text-xs bg-lsc-cream dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70 rounded hover:bg-earth-200 dark:hover:bg-earth-600"
                    >
                      {t.label}
                    </button>
                  ))}
                </div>
              </div>
            )}

            <textarea
              rows={3}
              required
              value={bulkDeclineReason}
              onChange={e => setBulkDeclineReason(e.target.value)}
              placeholder={t('staffPurchaseRequests.reasonForAllSelectedShown')}
              className="w-full px-3 py-2 border border-lsc-border dark:border-earth-600 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream text-sm mb-4"
            />
            <div className="flex justify-end gap-3">
              <button onClick={() => { setShowBulkDecline(false); setBulkDeclineReason('') }} className="px-4 py-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                Cancel
              </button>
              <button
                onClick={handleBulkDeclineSubmit}
                disabled={!bulkDeclineReason.trim()}
                className="px-4 py-2 text-sm bg-status-danger-600 text-white rounded-lg hover:bg-status-danger-700 disabled:opacity-50"
              >
                Decline All
              </button>
            </div>
          </div>
        </ModalBackdrop>
      )}

      {/* ========== Link Order Modal ========== */}
      {orderLinkModal && (
        <ModalBackdrop onClose={() => setOrderLinkModal(null)} title="Link to Purchase Order">
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg max-w-md w-full mx-4 p-6">
            <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-2">{t('staffPurchaseRequests.linkToPurchaseOrder')}</h3>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">"{orderLinkModal.title}"</p>
            <input
              type="number"
              min={1}
              required
              value={orderLinkId}
              onChange={e => setOrderLinkId(e.target.value)}
              placeholder={t('placeholder.staffPurchaseRequests.purchaseOrderId')}
              className="w-full px-3 py-2 border border-lsc-border dark:border-earth-600 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream text-sm mb-4"
            />
            <div className="flex justify-end gap-3">
              <button onClick={() => setOrderLinkModal(null)} className="px-4 py-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                Cancel
              </button>
              <button
                onClick={handleLinkOrder}
                disabled={!orderLinkId}
                className="px-4 py-2 text-sm bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 disabled:opacity-50"
              >
                Link & Notify Patron
              </button>
            </div>
          </div>
        </ModalBackdrop>
      )}
    </PageContainer>
    <ConfirmDialog
      isOpen={confirmOpen}
      title="Delete this template?"
      message="This cannot be undone."
      confirmText="Delete"
      confirmVariant="danger"
      onConfirm={() => { pendingAction?.(); setConfirmOpen(false); setPendingAction(null) }}
      onCancel={() => { setConfirmOpen(false); setPendingAction(null) }}
    />
  </AdminShell>
  )
}
