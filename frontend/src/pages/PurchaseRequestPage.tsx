/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import ConfirmDialog from '@/components/ConfirmDialog'
import { useState, useEffect } from 'react'
import { useAuth } from '../contexts/AuthContext'
import {
  BookOpen, Send, Clock, CheckCircle, XCircle, Package, Loader2, AlertTriangle, X, Search
} from 'lucide-react'
import toast from 'react-hot-toast'
import {
  submitPurchaseRequest, getMyRequests, cancelMyRequest, checkDuplicate,
  PurchaseRequest, PurchaseRequestCreate, PurchaseRequestStatus, RequestMaterialType,
  DuplicateCheckResult
} from '@/api/purchase-requests-api'
import { useTranslation} from '@/i18n'
import { clean } from '@/lib/utils'
import PageContainer from '@/components/layout/PageContainer'

const MATERIAL_TYPES: { value: RequestMaterialType; label: string }[] = [
  { value: 'book', label: 'Book' },
  { value: 'audiobook', label: 'Audiobook' },
  { value: 'ebook', label: 'E-Book' },
  { value: 'dvd', label: 'DVD/Blu-ray' },
  { value: 'cd', label: 'CD/Music' },
  { value: 'magazine', label: 'Magazine' },
  { value: 'other', label: 'Other' },
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
    pending: 'Pending Review',
    under_review: 'Under Review',
    approved: 'Approved',
    ordered: 'Ordered',
    received: 'Ready for Pickup',
    declined: 'Declined',
    cancelled: 'Cancelled',
  }
  const icons: Record<string, React.ReactNode> = {
    pending: <Clock className="w-3.5 h-3.5 mr-1" />,
    under_review: <Search className="w-3.5 h-3.5 mr-1" />,
    approved: <CheckCircle className="w-3.5 h-3.5 mr-1" />,
    ordered: <Package className="w-3.5 h-3.5 mr-1" />,
    received: <CheckCircle className="w-3.5 h-3.5 mr-1" />,
    declined: <XCircle className="w-3.5 h-3.5 mr-1" />,
    cancelled: <X className="w-3.5 h-3.5 mr-1" />,
  }
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${styles[status] || styles.pending}`}>
      {icons[status]}
      {labels[status] || status}
    </span>
  )
}

export default function PurchaseRequestPage(): React.ReactElement {
  const { t } = useTranslation()
  const { token } = useAuth()
  const [activeTab, setActiveTab] = useState<'request' | 'history'>('request')
  const [isLoading, setIsLoading] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [pendingCancelId, setPendingCancelId] = useState<number | null>(null)

  // Form state
  const [form, setForm] = useState<PurchaseRequestCreate>({
    title: '',
    author: '',
    isbn: '',
    material_type: 'book',
    publisher: '',
    patron_notes: '',
  })

  // Duplicate check
  const [dupCheck, setDupCheck] = useState<DuplicateCheckResult | null>(null)
  const [isCheckingDup, setIsCheckingDup] = useState(false)

  // History
  const [requests, setRequests] = useState<PurchaseRequest[]>([])
  const [totalRequests, setTotalRequests] = useState(0)
  const [page, setPage] = useState(1)

  const loadRequests = async () => {
    if (!token) return
    setIsLoading(true)
    try {
      const data = await getMyRequests(token, page)
      setRequests(data.items)
      setTotalRequests(data.total)
    } catch {
      toast.error(t('purchaseRequest.failedToLoadYourRequests'))
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    if (activeTab === 'history') {
      loadRequests()
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab, page, token])

  const handleDuplicateCheck = async () => {
    if (!token || !form.title.trim()) return
    setIsCheckingDup(true)
    try {
      const result = await checkDuplicate(form.title, token, form.author || undefined, form.isbn || undefined)
      setDupCheck(result)
    } catch {
      // Silently fail - dup check is optional
    } finally {
      setIsCheckingDup(false)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!token || !form.title.trim()) return
    setIsSubmitting(true)
    try {
      await submitPurchaseRequest(clean({
        ...form,
        author: form.author || undefined,
        isbn: form.isbn || undefined,
        publisher: form.publisher || undefined,
        patron_notes: form.patron_notes || undefined,
      }), token)
      toast.success('Purchase request submitted! We\'ll review it soon.')
      setForm({ title: '', author: '', isbn: '', material_type: 'book', publisher: '', patron_notes: '' })
      setDupCheck(null)
      setActiveTab('history')
      setPage(1)
    } catch (err: unknown) {
      const msg = (err instanceof Error ? err.message : null) || 'Failed to submit request'
      toast.error(msg)
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleCancelClick = (id: number) => {
    setPendingCancelId(id)
    setConfirmOpen(true)
  }

  const handleCancelConfirm = async () => {
    if (!token || pendingCancelId === null) return
    setConfirmOpen(false)
    try {
      await cancelMyRequest(pendingCancelId, token)
      toast.success(t('toast.interlibraryLoan.requestCancelled'))
      loadRequests()
    } catch {
      toast.error(t('purchaseRequest.failedToCancelRequest'))
    } finally {
      setPendingCancelId(null)
    }
  }

  return (
    <PageContainer className="py-8">
      <div className="mb-8">
        <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream flex items-center gap-3">
          <BookOpen className="w-8 h-8 text-brand-600" />
          Suggest a Purchase
        </h1>
        <p className="mt-2 text-lsc-dark/70 dark:text-lsc-cream/70">
          Can't find what you're looking for? Let us know and we'll consider adding it to our collection.
        </p>
      </div>

      {/* Tab Navigation */}
      <div className="flex border-b border-lsc-border dark:border-earth-700 mb-6">
        <button
          onClick={() => setActiveTab('request')}
          className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
            activeTab === 'request'
              ? 'border-brand-600 text-brand-600 dark:text-brand-400'
              : 'border-transparent text-lsc-dark/70 hover:text-lsc-dark/70 dark:text-lsc-cream/70'
          }`}
        >
          <Send className="w-4 h-4 inline mr-2" />
          New Request
        </button>
        <button
          onClick={() => setActiveTab('history')}
          className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
            activeTab === 'history'
              ? 'border-brand-600 text-brand-600 dark:text-brand-400'
              : 'border-transparent text-lsc-dark/70 hover:text-lsc-dark/70 dark:text-lsc-cream/70'
          }`}
        >
          <Clock className="w-4 h-4 inline mr-2" />
          My Requests ({totalRequests})
        </button>
      </div>

      {/* New Request Form */}
      {activeTab === 'request' && (
        <form onSubmit={handleSubmit} className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm border border-lsc-border dark:border-earth-700 p-6 space-y-5">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                Title <span className="text-status-danger-500">*</span>
              </label>
              <input
                type="text"
                required
                maxLength={500}
                value={form.title}
                onChange={(e) => { setForm({ ...form, title: e.target.value }); setDupCheck(null) }}
                onBlur={handleDuplicateCheck}
                placeholder={t('placeholder.readingLogEntryForm.egTheGreatGatsby')}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-600 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-brand-500 focus:border-transparent"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Author</label>
              <input
                type="text"
                maxLength={255}
                value={form.author}
                onChange={(e) => { setForm({ ...form, author: e.target.value }); setDupCheck(null) }}
                onBlur={handleDuplicateCheck}
                placeholder={t('placeholder.readingLogEntryForm.egFScottFitzgerald')}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-600 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-brand-500 focus:border-transparent"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">ISBN</label>
              <input
                type="text"
                maxLength={20}
                value={form.isbn}
                onChange={(e) => { setForm({ ...form, isbn: e.target.value }); setDupCheck(null) }}
                onBlur={handleDuplicateCheck}
                placeholder={t('placeholder.purchaseRequest.eg9780743273565')}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-600 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-brand-500 focus:border-transparent"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Material Type</label>
              <select
                value={form.material_type}
                onChange={(e) => setForm({ ...form, material_type: e.target.value as RequestMaterialType })}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-600 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-brand-500 focus:border-transparent"
              >
                {MATERIAL_TYPES.map((t) => (
                  <option key={t.value} value={t.value}>{t.label}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Publisher</label>
              <input
                type="text"
                maxLength={255}
                value={form.publisher}
                onChange={(e) => setForm({ ...form, publisher: e.target.value })}
                placeholder={t('placeholder.cashDrawer.optional')}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-600 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-brand-500 focus:border-transparent"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Publication Year</label>
              <input
                type="number"
                min={1800}
                max={2100}
                value={form.publication_year || ''}
                onChange={(e) => setForm({ ...form, ...(e.target.value ? { publication_year: parseInt(e.target.value) } : {}) })}
                placeholder={t('placeholder.cashDrawer.optional')}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-600 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-brand-500 focus:border-transparent"
              />
            </div>

            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                Why would you like us to get this?
              </label>
              <textarea
                rows={3}
                maxLength={1000}
                value={form.patron_notes}
                onChange={(e) => setForm({ ...form, patron_notes: e.target.value })}
                placeholder={t('purchaseRequest.tellUsWhyYouD')}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-600 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-brand-500 focus:border-transparent"
              />
            </div>
          </div>

          {/* Duplicate warning */}
          {isCheckingDup && (
            <div className="flex items-center text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
              <Loader2 className="w-4 h-4 mr-2 motion-safe:animate-spin" />
              Checking our catalog...
            </div>
          )}
          {dupCheck?.has_duplicate && (
            <div className="flex items-start gap-3 p-4 bg-status-warning-50 dark:bg-status-warning-900/20 border border-status-warning-200 dark:border-status-warning-800 rounded-lg">
              <AlertTriangle className="w-5 h-5 text-status-warning-600 dark:text-status-warning-400 mt-0.5 flex-shrink-0" />
              <div>
                <p className="text-sm font-medium text-status-warning-800 dark:text-status-warning-300">
                  We may already have this item!
                </p>
                <p className="text-sm text-status-warning-700 dark:text-status-warning-400 mt-1">
                  Found: <strong>{dupCheck.catalog_title}</strong>
                  {dupCheck.catalog_author && <> by {dupCheck.catalog_author}</>}
                  {' '}(matched by {dupCheck.match_type === 'isbn' ? 'ISBN' : 'title & author'})
                </p>
                <p className="text-sm text-status-warning-600 dark:text-status-warning-500 mt-1">
                  You can still submit a request if you believe this is a different item or edition.
                </p>
              </div>
            </div>
          )}

          <div className="flex justify-end">
            <button
              type="submit"
              disabled={isSubmitting || !form.title.trim()}
              className="inline-flex items-center px-6 py-2.5 bg-brand-600 text-white font-medium rounded-lg hover:bg-brand-700 focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {isSubmitting ? <Loader2 className="w-4 h-4 mr-2 motion-safe:animate-spin" /> : <Send className="w-4 h-4 mr-2" />}
              Submit Request
            </button>
          </div>
        </form>
      )}

      {/* Request History */}
      {activeTab === 'history' && (
        <div className="space-y-4">
          {isLoading ? (
            <div className="text-center py-12 text-lsc-dark/70 dark:text-lsc-cream/70">
              <Loader2 className="w-8 h-8 mx-auto motion-safe:animate-spin mb-2" />
              Loading your requests...
            </div>
          ) : requests.length === 0 ? (
            <div className="text-center py-12">
              <BookOpen className="w-12 h-12 mx-auto text-earth-600 dark:text-earth-600 mb-3" />
              <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('purchaseRequest.youHavenTSubmittedAny')}</p>
              <button
                onClick={() => setActiveTab('request')}
                className="mt-3 text-brand-600 dark:text-brand-400 hover:underline text-sm font-medium"
              >
                Submit your first request
              </button>
            </div>
          ) : (
            <>
              {requests.map((req) => (
                <div key={req.id} className="bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700 p-5">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-1">
                        <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">{req.title}</h3>
                        <StatusBadge status={req.status} />
                      </div>
                      {req.author && <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">by {req.author}</p>}
                      {req.isbn && <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-0.5">ISBN: {req.isbn}</p>}
                      {req.patron_notes && (
                        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-2 italic">"{req.patron_notes}"</p>
                      )}
                      {req.decline_reason && (
                        <div className="mt-2 p-3 bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-200 dark:border-status-danger-800 rounded-lg">
                          <p className="text-sm text-status-danger-700 dark:text-status-danger-400">
                            <strong>Reason:</strong> {req.decline_reason}
                          </p>
                        </div>
                      )}
                      <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-2">
                        Submitted {new Date(req.created_at).toLocaleDateString()}
                      </p>
                    </div>
                    {(req.status === 'pending' || req.status === 'under_review') && (
                      <button
                        onClick={() => handleCancelClick(req.id)}
                        className="text-sm text-lsc-dark/70 hover:text-status-danger-600 dark:text-lsc-cream/70 dark:hover:text-status-danger-400 transition-colors"
                        title="Cancel request"
                      >
                        <X className="w-5 h-5" />
                      </button>
                    )}
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
            </>
          )}
        </div>
      )}

      <ConfirmDialog
        isOpen={confirmOpen}
        title="Cancel this request?"
        message="Are you sure you want to cancel this purchase request?"
        confirmText="Cancel request"
        confirmVariant="danger"
        onConfirm={handleCancelConfirm}
        onCancel={() => { setConfirmOpen(false); setPendingCancelId(null) }}
      />
    </PageContainer>
  )
}
