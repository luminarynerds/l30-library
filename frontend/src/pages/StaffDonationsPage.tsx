/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect, useCallback } from 'react'
import { useAuth } from '../contexts/AuthContext'
import {
  Gift, Check, X, Loader2, Plus,
  ClipboardList, History, Eye, EyeOff, Package,
} from 'lucide-react'
import toast from 'react-hot-toast'
import {
  listDonations, createDonation, reviewDonation, processDonation,
  getDonationStats,
  DonationRecord, DonationStatus, DonationCreate, DonationProcessRequest, DonationStats,
} from '@/api/donations-api'
import { AdminShell } from '../components/shells/AdminShell'
import { t } from '@/i18n'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'
import { parseDate } from '@/utils/format-utils'
import PageContainer from '@/components/layout/PageContainer'

// ============ Constants ============

const STATUS_OPTIONS: { value: DonationStatus | ''; label: string }[] = [
  { value: '', label: 'All Statuses' },
  { value: 'pending', label: 'Pending' },
  { value: 'under_review', label: 'Under Review' },
  { value: 'accepted', label: 'Accepted' },
  { value: 'declined', label: 'Declined' },
  { value: 'processed', label: 'Processed' },
]

const MATERIAL_TYPES = [
  { value: '', label: 'Select type...' },
  { value: 'book', label: 'Book' },
  { value: 'audiobook', label: 'Audiobook' },
  { value: 'dvd', label: 'DVD/Blu-ray' },
  { value: 'cd', label: 'CD' },
  { value: 'magazine', label: 'Magazine/Periodical' },
  { value: 'graphic_novel', label: 'Graphic Novel' },
  { value: 'other', label: 'Other' },
]

// ============ Helper Components ============

function StatusBadge({ status }: { status: DonationStatus }) {
  const styles: Record<string, string> = {
    pending: 'bg-status-warning-100 text-status-warning-800 dark:bg-status-warning-900/30 dark:text-status-warning-400',
    under_review: 'bg-earth-100 text-earth-800 dark:bg-earth-800/30 dark:text-lsc-rose-light',
    accepted: 'bg-status-success-100 text-status-success-800 dark:bg-status-success-900/30 dark:text-status-success-400',
    declined: 'bg-status-danger-100 text-status-danger-800 dark:bg-status-danger-900/30 dark:text-status-danger-400',
    processed: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-400',
  }
  const labels: Record<string, string> = {
    pending: 'Pending',
    under_review: 'Under Review',
    accepted: 'Accepted',
    declined: 'Declined',
    processed: 'Processed',
  }
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${styles[status] || styles.pending}`}>
      {labels[status] || status}
    </span>
  )
}

// ============ Form State ============

interface IntakeFormState {
  donor_name: string
  donor_email: string
  donor_phone: string
  donor_address: string
  is_anonymous: boolean
  tax_receipt_requested: boolean
  title: string
  author: string
  isbn: string
  material_type: string
  quantity: number
  condition_notes: string
  estimated_value: number | undefined
  staff_notes: string
}

const EMPTY_FORM: IntakeFormState = {
  donor_name: '', donor_email: '', donor_phone: '', donor_address: '',
  is_anonymous: false, tax_receipt_requested: false,
  title: '', author: '', isbn: '', material_type: '', quantity: 1,
  condition_notes: '', estimated_value: undefined, staff_notes: '',
}

// ============ Main Component ============

export default function StaffDonationsPage(): React.ReactElement {
  const { token } = useAuth()
  const [activeTab, setActiveTab] = useState<'intake' | 'queue' | 'history'>('intake')

  // ─── Intake tab state ───
  const [intakeForm, setIntakeForm] = useState<IntakeFormState>({ ...EMPTY_FORM })
  const [isSubmitting, setIsSubmitting] = useState(false)

  // ─── Queue tab state ───
  const [queueDonations, setQueueDonations] = useState<DonationRecord[]>([])
  const [queueLoading, setQueueLoading] = useState(false)
  const [queueFilter, setQueueFilter] = useState<DonationStatus | ''>('')
  const [queuePage, setQueuePage] = useState(1)

  // ─── History tab state ───
  const [historyDonations, setHistoryDonations] = useState<DonationRecord[]>([])
  const [historyLoading, setHistoryLoading] = useState(false)
  const [historyPage, setHistoryPage] = useState(1)

  // ─── Stats ───
  const [stats, setStats] = useState<DonationStats | null>(null)

  // ─── Modals ───
  const [declineModal, setDeclineModal] = useState<{ id: number; title: string | null } | null>(null)
  const [declineReason, setDeclineReason] = useState('')
  const [processModal, setProcessModal] = useState<{ id: number; title: string | null } | null>(null)
  const [processForm, setProcessForm] = useState({ catalog_item_id: '', create_new: true, location: '' })

  // ============ Data Loading ============

  const loadQueue = useCallback(async () => {
    if (!token) return
    setQueueLoading(true)
    try {
      // Queue shows actionable items: pending, under_review, accepted
      const params: Parameters<typeof listDonations>[1] = {
        page: queuePage,
        per_page: 20,
      }
      if (queueFilter) params.status = queueFilter
      const data = await listDonations(token, params)
      // Filter to actionable statuses if no specific filter
      if (!queueFilter) {
        setQueueDonations(data.filter(d =>
          d.status === 'pending' || d.status === 'under_review' || d.status === 'accepted'
        ))
      } else {
        setQueueDonations(data)
      }
    } catch {
      toast.error(t('toast.staffDonations.failedToLoadDonationQueue'))
    } finally {
      setQueueLoading(false)
    }
  }, [token, queueFilter, queuePage])

  const loadHistory = useCallback(async () => {
    if (!token) return
    setHistoryLoading(true)
    try {
      const data = await listDonations(token, { page: historyPage, per_page: 20 })
      setHistoryDonations(data)
    } catch {
      toast.error(t('toast.staffDonations.failedToLoadDonationHistory'))
    } finally {
      setHistoryLoading(false)
    }
  }, [token, historyPage])

  const loadStats = useCallback(async () => {
    if (!token) return
    try {
      const data = await getDonationStats(token)
      setStats(data)
    } catch { /* silent */ }
  }, [token])

  useEffect(() => {
    if (activeTab === 'queue') loadQueue()
    if (activeTab === 'history') loadHistory()
    loadStats()
  }, [activeTab, loadQueue, loadHistory, loadStats])

  // ============ Intake Handlers ============

  const handleIntakeSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!token) return
    setIsSubmitting(true)
    try {
      const payload: DonationCreate = {
        is_anonymous: intakeForm.is_anonymous,
        tax_receipt_requested: intakeForm.tax_receipt_requested,
        quantity: intakeForm.quantity,
      }
      // Only include non-empty strings
      if (intakeForm.donor_name) payload.donor_name = intakeForm.donor_name
      if (intakeForm.donor_email) payload.donor_email = intakeForm.donor_email
      if (intakeForm.donor_phone) payload.donor_phone = intakeForm.donor_phone
      if (intakeForm.donor_address) payload.donor_address = intakeForm.donor_address
      if (intakeForm.title) payload.title = intakeForm.title
      if (intakeForm.author) payload.author = intakeForm.author
      if (intakeForm.isbn) payload.isbn = intakeForm.isbn
      if (intakeForm.material_type) payload.material_type = intakeForm.material_type
      if (intakeForm.condition_notes) payload.condition_notes = intakeForm.condition_notes
      if (intakeForm.staff_notes) payload.staff_notes = intakeForm.staff_notes
      if (intakeForm.estimated_value != null) payload.estimated_value = intakeForm.estimated_value

      await createDonation(token, payload)
      toast.success(t('toast.staffDonations.donationLoggedSuccessfully'))
      setIntakeForm({ ...EMPTY_FORM })
      loadStats()
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : t('toast.staffDonations.failedToLogDonation'))
    } finally {
      setIsSubmitting(false)
    }
  }

  // ============ Queue Handlers ============

  const handleAccept = async (id: number) => {
    if (!token) return
    try {
      await reviewDonation(token, id, { action: 'accept' })
      toast.success(t('toast.staffDonations.donationAccepted'))
      loadQueue()
      loadStats()
    } catch {
      toast.error(t('toast.staffDonations.failedToAcceptDonation'))
    }
  }

  const handleDeclineSubmit = async () => {
    if (!token || !declineModal || !declineReason.trim()) return
    try {
      await reviewDonation(token, declineModal.id, {
        action: 'decline',
        decline_reason: declineReason,
      })
      toast.success(t('toast.staffDonations.donationDeclined'))
      setDeclineModal(null)
      setDeclineReason('')
      loadQueue()
      loadStats()
    } catch {
      toast.error(t('toast.staffDonations.failedToDeclineDonation'))
    }
  }

  const handleProcessSubmit = async () => {
    if (!token || !processModal) return
    try {
      const processPayload: DonationProcessRequest = {
        create_new_catalog_item: processForm.create_new,
      }
      if (!processForm.create_new && processForm.catalog_item_id) {
        processPayload.catalog_item_id = parseInt(processForm.catalog_item_id)
      }
      if (processForm.location) {
        processPayload.location = processForm.location
      }
      await processDonation(token, processModal.id, processPayload)
      toast.success(t('toast.staffDonations.donationProcessedIntoCatalog'))
      setProcessModal(null)
      setProcessForm({ catalog_item_id: '', create_new: true, location: '' })
      loadQueue()
      loadStats()
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : t('toast.staffDonations.failedToProcessDonation'))
    }
  }

  // ============ Render ============

  return (

    <AdminShell title="Donations">    <PageContainer width="wide" className="py-8">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream flex items-center gap-3">
          <Gift className="w-7 h-7 text-brand-600" />
          Donation Intake
        </h1>
        <p className="mt-1 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
          Log, review, and process incoming material donations
        </p>
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="grid grid-cols-3 md:grid-cols-6 gap-3 mb-6">
          {[
            { label: 'Total', value: stats.total, color: 'text-lsc-dark dark:text-lsc-cream' },
            { label: 'Pending', value: stats.by_status.pending || 0, color: 'text-status-warning-600 dark:text-status-warning-400' },
            { label: 'Under Review', value: stats.by_status.under_review || 0, color: 'text-status-warning-600 dark:text-status-warning-400' },
            { label: 'Accepted', value: stats.by_status.accepted || 0, color: 'text-status-success-600 dark:text-status-success-400' },
            { label: 'Declined', value: stats.by_status.declined || 0, color: 'text-status-danger-600 dark:text-status-danger-400' },
            { label: 'Processed', value: stats.by_status.processed || 0, color: 'text-emerald-600 dark:text-emerald-400' },
          ].map(s => (
            <div key={s.label} className="bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700 p-3 text-center">
              <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{s.label}</p>
              <p className={`text-xl font-bold ${s.color}`}>{s.value}</p>
            </div>
          ))}
        </div>
      )}

      {/* Tabs */}
      <div className="flex border-b border-lsc-border dark:border-earth-700 mb-6 gap-1">
        {[
          { key: 'intake' as const, label: 'New Intake', icon: <Plus className="w-4 h-4" /> },
          { key: 'queue' as const, label: 'Review Queue', icon: <ClipboardList className="w-4 h-4" /> },
          { key: 'history' as const, label: 'History', icon: <History className="w-4 h-4" /> },
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

      {/* ========== Intake Tab ========== */}
      {activeTab === 'intake' && (
        <form onSubmit={handleIntakeSubmit} className="space-y-6">
          {/* Donor Info */}
          <div className="bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700 p-5">
            <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
              Donor Information
              <button
                type="button"
                onClick={() => setIntakeForm(f => ({ ...f, is_anonymous: !f.is_anonymous }))}
                className="ml-auto inline-flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-lg border border-lsc-border dark:border-earth-600 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-earth-700"
              >
                {intakeForm.is_anonymous ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                {intakeForm.is_anonymous ? 'Anonymous' : 'Named Donor'}
              </button>
            </h3>
            {!intakeForm.is_anonymous && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label htmlFor="donation-donor-name" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Name</label>
                  <input
                    id="donation-donor-name"
                    type="text"
                    maxLength={255}
                    value={intakeForm.donor_name || ''}
                    onChange={e => setIntakeForm(f => ({ ...f, donor_name: e.target.value }))}
                    placeholder={t('placeholder.staffDonations.donorFullName')}
                    className="w-full px-3 py-2 border border-lsc-border dark:border-earth-600 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream text-sm"
                  />
                </div>
                <div>
                  <label htmlFor="donation-donor-email" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Email</label>
                  <input
                    id="donation-donor-email"
                    type="email"
                    maxLength={255}
                    value={intakeForm.donor_email || ''}
                    onChange={e => setIntakeForm(f => ({ ...f, donor_email: e.target.value }))}
                    placeholder={t('placeholder.staffDonations.donorexamplecom')}
                    className="w-full px-3 py-2 border border-lsc-border dark:border-earth-600 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream text-sm"
                  />
                </div>
                <div>
                  <label htmlFor="donation-donor-phone" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Phone</label>
                  <input
                    id="donation-donor-phone"
                    type="tel"
                    maxLength={50}
                    value={intakeForm.donor_phone || ''}
                    onChange={e => setIntakeForm(f => ({ ...f, donor_phone: e.target.value }))}
                    placeholder={t('placeholder.guestPassForm.5551234567')}
                    className="w-full px-3 py-2 border border-lsc-border dark:border-earth-600 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream text-sm"
                  />
                </div>
                <div>
                  <label htmlFor="donation-donor-address" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Address</label>
                  <input
                    id="donation-donor-address"
                    type="text"
                    value={intakeForm.donor_address || ''}
                    onChange={e => setIntakeForm(f => ({ ...f, donor_address: e.target.value }))}
                    placeholder={t('placeholder.staffDonations.streetCityStateZip')}
                    className="w-full px-3 py-2 border border-lsc-border dark:border-earth-600 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream text-sm"
                  />
                </div>
              </div>
            )}
            <div className="flex items-center gap-4 mt-4">
              <label className="flex items-center gap-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 cursor-pointer">
                <input
                  type="checkbox"
                  checked={intakeForm.tax_receipt_requested || false}
                  onChange={e => setIntakeForm(f => ({ ...f, tax_receipt_requested: e.target.checked }))}
                  className="rounded border-lsc-border text-brand-600 focus:ring-brand-500"
                />
                Tax receipt requested
              </label>
            </div>
          </div>

          {/* Item Info */}
          <div className="bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700 p-5">
            <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4">Item Details</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="md:col-span-2">
                <label htmlFor="donation-title" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Title</label>
                <input
                  id="donation-title"
                  type="text"
                  maxLength={500}
                  value={intakeForm.title || ''}
                  onChange={e => setIntakeForm(f => ({ ...f, title: e.target.value }))}
                  placeholder={t('placeholder.staffDonations.bookmaterialTitle')}
                  className="w-full px-3 py-2 border border-lsc-border dark:border-earth-600 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream text-sm"
                />
              </div>
              <div>
                <label htmlFor="donation-author" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Author</label>
                <input
                  id="donation-author"
                  type="text"
                  maxLength={500}
                  value={intakeForm.author || ''}
                  onChange={e => setIntakeForm(f => ({ ...f, author: e.target.value }))}
                  placeholder={t('placeholder.interlibraryLoan.authorName')}
                  className="w-full px-3 py-2 border border-lsc-border dark:border-earth-600 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream text-sm"
                />
              </div>
              <div>
                <label htmlFor="donation-isbn" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">ISBN</label>
                <input
                  id="donation-isbn"
                  type="text"
                  maxLength={20}
                  value={intakeForm.isbn || ''}
                  onChange={e => setIntakeForm(f => ({ ...f, isbn: e.target.value }))}
                  placeholder={t('placeholder.issuesTab.978')}
                  className="w-full px-3 py-2 border border-lsc-border dark:border-earth-600 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream text-sm"
                />
              </div>
              <div>
                <label htmlFor="donation-material-type" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Material Type</label>
                <select
                  id="donation-material-type"
                  value={intakeForm.material_type || ''}
                  onChange={e => setIntakeForm(f => ({ ...f, material_type: e.target.value }))}
                  className="w-full px-3 py-2 border border-lsc-border dark:border-earth-600 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream text-sm"
                >
                  {MATERIAL_TYPES.map(mt => <option key={mt.value} value={mt.value}>{mt.label}</option>)}
                </select>
              </div>
              <div>
                <label htmlFor="donation-quantity" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Quantity</label>
                <input
                  id="donation-quantity"
                  type="number"
                  min={1}
                  value={intakeForm.quantity || 1}
                  onChange={e => setIntakeForm(f => ({ ...f, quantity: parseInt(e.target.value) || 1 }))}
                  className="w-full px-3 py-2 border border-lsc-border dark:border-earth-600 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream text-sm"
                />
              </div>
              <div>
                <label htmlFor="donation-estimated-value" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Estimated Value ($)</label>
                <input
                  id="donation-estimated-value"
                  type="number"
                  min={0}
                  step="0.01"
                  value={intakeForm.estimated_value ? (intakeForm.estimated_value / 100).toFixed(2) : ''}
                  onChange={e => {
                    const val = parseFloat(e.target.value)
                    setIntakeForm(f => {
                      const next = { ...f }
                      next.estimated_value = isNaN(val) ? undefined : Math.round(val * 100)
                      return next
                    })
                  }}
                  placeholder={t('placeholder.staff.000')}
                  className="w-full px-3 py-2 border border-lsc-border dark:border-earth-600 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream text-sm"
                />
              </div>
              <div className="md:col-span-2">
                <label htmlFor="donation-condition-notes" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Condition Notes</label>
                <textarea
                  id="donation-condition-notes"
                  rows={2}
                  value={intakeForm.condition_notes || ''}
                  onChange={e => setIntakeForm(f => ({ ...f, condition_notes: e.target.value }))}
                  placeholder={t('placeholder.staffDonations.describePhysicalConditionOf')}
                  className="w-full px-3 py-2 border border-lsc-border dark:border-earth-600 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream text-sm"
                />
              </div>
              <div className="md:col-span-2">
                <label htmlFor="donation-staff-notes" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Staff Notes</label>
                <textarea
                  id="donation-staff-notes"
                  rows={2}
                  value={intakeForm.staff_notes || ''}
                  onChange={e => setIntakeForm(f => ({ ...f, staff_notes: e.target.value }))}
                  placeholder={t('placeholder.staffDonations.internalNotesAboutThis')}
                  className="w-full px-3 py-2 border border-lsc-border dark:border-earth-600 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream text-sm"
                />
              </div>
            </div>
          </div>

          <div className="flex justify-end">
            <button
              type="submit"
              disabled={isSubmitting}
              className="inline-flex items-center gap-2 px-6 py-2.5 text-sm font-medium bg-brand-600 text-white rounded-lg hover:bg-brand-700 disabled:opacity-50 transition-colors"
            >
              {isSubmitting ? <Loader2 className="w-4 h-4 motion-safe:animate-spin" /> : <Gift className="w-4 h-4" />}
              Log Donation
            </button>
          </div>
        </form>
      )}

      {/* ========== Queue Tab ========== */}
      {activeTab === 'queue' && (
        <>
          {/* Filter */}
          <div className="flex items-center gap-3 mb-4">
            <select
              value={queueFilter}
              onChange={e => { setQueueFilter(e.target.value as DonationStatus | ''); setQueuePage(1) }}
              aria-label={t('aria.staffDonations.filterDonationQueueByStatus', 'Filter donation queue by status')}
              className="px-3 py-2 text-sm border border-lsc-border dark:border-earth-600 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
            >
              <option value="">Actionable (Pending/Accepted)</option>
              {STATUS_OPTIONS.filter(o => o.value !== '').map(o => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
            <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 ml-auto">
              {queueDonations.length} donation{queueDonations.length !== 1 ? 's' : ''}
            </span>
          </div>

          {queueLoading ? (
            <div className="text-center py-12">
              <Loader2 className="w-8 h-8 mx-auto motion-safe:animate-spin text-lsc-dark/70 dark:text-lsc-cream/70" />
            </div>
          ) : queueDonations.length === 0 ? (
            <div className="text-center py-12 text-lsc-dark/70 dark:text-lsc-cream/70">
              <Gift className="w-12 h-12 mx-auto text-earth-600 dark:text-earth-600 mb-3" />
              <p>No donations in queue</p>
            </div>
          ) : (
            <div className="space-y-3">
              {queueDonations.map(don => (
                <div
                  key={don.id}
                  className="bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700 p-4"
                >
                  <div className="flex items-start gap-3">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
                          {don.title || 'Untitled Donation'}
                        </h3>
                        <StatusBadge status={don.status} />
                        {don.quantity > 1 && (
                          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-status-info-100 text-status-info-800 dark:bg-status-info-900/30 dark:text-status-info-400">
                            Qty: {don.quantity}
                          </span>
                        )}
                      </div>
                      {don.author && <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">by {don.author}</p>}
                      <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                        {don.isbn && <span>ISBN: {don.isbn}</span>}
                        {don.material_type && <span>Type: {don.material_type}</span>}
                        {don.is_anonymous ? (
                          <span className="italic">Anonymous donor</span>
                        ) : don.donor_name ? (
                          <span>Donor: {don.donor_name}</span>
                        ) : null}
                        <span>Received: {parseDate(don.received_date)?.toLocaleDateString() ?? '-'}</span>
                        {don.received_by_name && <span>By: {don.received_by_name}</span>}
                      </div>
                      {don.condition_notes && (
                        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                          Condition: {don.condition_notes}
                        </p>
                      )}
                      {don.staff_notes && (
                        <p className="text-xs text-lsc-rose dark:text-lsc-rose-light mt-1">
                          Staff note: {don.staff_notes}
                        </p>
                      )}
                      {don.estimated_value != null && don.estimated_value > 0 && (
                        <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                          Est. value: ${(don.estimated_value / 100).toFixed(2)}
                        </p>
                      )}
                      {don.tax_receipt_requested && (
                        <span className="inline-flex items-center mt-1 px-2 py-0.5 rounded-full text-xs font-medium bg-category-100 text-category-800 dark:bg-category-900/30 dark:text-category-400">
                          Tax receipt requested
                        </span>
                      )}
                    </div>

                    {/* Actions */}
                    <div className="flex flex-col gap-1.5 flex-shrink-0">
                      {(don.status === 'pending' || don.status === 'under_review') && (
                        <>
                          <button
                            onClick={() => handleAccept(don.id)}
                            className="inline-flex items-center px-3 py-1.5 text-xs bg-status-success-600 text-white rounded-lg hover:bg-status-success-700"
                          >
                            <Check className="w-3.5 h-3.5 mr-1" /> Accept
                          </button>
                          <button
                            onClick={() => { setDeclineModal({ id: don.id, title: don.title }); setDeclineReason('') }}
                            className="inline-flex items-center px-3 py-1.5 text-xs bg-status-danger-600 text-white rounded-lg hover:bg-status-danger-700"
                          >
                            <X className="w-3.5 h-3.5 mr-1" /> Decline
                          </button>
                        </>
                      )}
                      {don.status === 'accepted' && (
                        <button
                          onClick={() => {
                            setProcessModal({ id: don.id, title: don.title })
                            setProcessForm({ catalog_item_id: '', create_new: true, location: '' })
                          }}
                          className="inline-flex items-center px-3 py-1.5 text-xs bg-emerald-600 text-white rounded-lg hover:bg-emerald-700"
                        >
                          <Package className="w-3.5 h-3.5 mr-1" /> Process
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              ))}

              {/* Pagination */}
              {queueDonations.length >= 20 && (
                <div className="flex justify-center gap-2 mt-4">
                  <button
                    onClick={() => setQueuePage(Math.max(1, queuePage - 1))}
                    disabled={queuePage === 1}
                    className="px-3 py-1.5 text-sm border rounded-lg disabled:opacity-50 dark:border-earth-600 dark:text-lsc-cream/70"
                  >
                    Previous
                  </button>
                  <span className="px-3 py-1.5 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                    Page {queuePage}
                  </span>
                  <button
                    onClick={() => setQueuePage(queuePage + 1)}
                    className="px-3 py-1.5 text-sm border rounded-lg dark:border-earth-600 dark:text-lsc-cream/70"
                  >
                    Next
                  </button>
                </div>
              )}
            </div>
          )}
        </>
      )}

      {/* ========== History Tab ========== */}
      {activeTab === 'history' && (
        <>
          {historyLoading ? (
            <div className="text-center py-12">
              <Loader2 className="w-8 h-8 mx-auto motion-safe:animate-spin text-lsc-dark/70 dark:text-lsc-cream/70" />
            </div>
          ) : historyDonations.length === 0 ? (
            <div className="text-center py-12 text-lsc-dark/70 dark:text-lsc-cream/70">
              <History className="w-12 h-12 mx-auto text-earth-600 dark:text-earth-600 mb-3" />
              <p>No donation history yet</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full divide-y divide-lsc-border dark:divide-earth-700">
                <thead className="bg-lsc-cream dark:bg-earth-800">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 uppercase tracking-wider">Title</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 uppercase tracking-wider">Author</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 uppercase tracking-wider">Donor</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 uppercase tracking-wider">Date</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 uppercase tracking-wider">Status</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 uppercase tracking-wider">Reviewed By</th>
                  </tr>
                </thead>
                <tbody className="bg-lsc-white dark:bg-earth-800 divide-y divide-lsc-border dark:divide-earth-700">
                  {historyDonations.map(don => (
                    <tr key={don.id} className="hover:bg-lsc-cream dark:hover:bg-earth-700/50">
                      <td className="px-4 py-3 text-sm text-lsc-dark dark:text-lsc-cream">
                        {don.title || 'Untitled'}
                        {don.catalog_item_id && (
                          <span className="ml-2 text-xs text-emerald-600 dark:text-emerald-400">
                            Catalog #{don.catalog_item_id}
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{don.author || '--'}</td>
                      <td className="px-4 py-3 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                        {don.is_anonymous ? <span className="italic">Anonymous</span> : don.donor_name || '--'}
                      </td>
                      <td className="px-4 py-3 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                        {parseDate(don.received_date)?.toLocaleDateString() ?? '-'}
                      </td>
                      <td className="px-4 py-3"><StatusBadge status={don.status} /></td>
                      <td className="px-4 py-3 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                        {don.reviewed_by_name || '--'}
                        {don.decline_reason && (
                          <p className="text-xs text-status-danger-500 mt-0.5 truncate max-w-[12.5rem]" title={don.decline_reason}>
                            {don.decline_reason}
                          </p>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>

              {/* Pagination */}
              {historyDonations.length >= 20 && (
                <div className="flex justify-center gap-2 mt-4">
                  <button
                    onClick={() => setHistoryPage(Math.max(1, historyPage - 1))}
                    disabled={historyPage === 1}
                    className="px-3 py-1.5 text-sm border rounded-lg disabled:opacity-50 dark:border-earth-600 dark:text-lsc-cream/70"
                  >
                    Previous
                  </button>
                  <span className="px-3 py-1.5 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                    Page {historyPage}
                  </span>
                  <button
                    onClick={() => setHistoryPage(historyPage + 1)}
                    className="px-3 py-1.5 text-sm border rounded-lg dark:border-earth-600 dark:text-lsc-cream/70"
                  >
                    Next
                  </button>
                </div>
              )}
            </div>
          )}
        </>
      )}

      {/* ========== Decline Modal ========== */}
      {declineModal && (
        <ModalBackdrop onClose={() => setDeclineModal(null)} title="Decline Donation" role="alertdialog">
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg max-w-md w-full mx-4 p-6">
            <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-2">Decline Donation</h3>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
              "{declineModal.title || 'Untitled Donation'}"
            </p>
            <textarea
              rows={3}
              required
              value={declineReason}
              onChange={e => setDeclineReason(e.target.value)}
              placeholder={t('placeholder.staffDonations.reasonForDecliningThis')}
              className="w-full px-3 py-2 border border-lsc-border dark:border-earth-600 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream text-sm mb-4"
            />
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setDeclineModal(null)}
                className="px-4 py-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark"
              >
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

      {/* ========== Process Modal ========== */}
      {processModal && (
        <ModalBackdrop onClose={() => setProcessModal(null)} title="Process Donation into Catalog">
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg max-w-md w-full mx-4 p-6">
            <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-2">Process Donation into Catalog</h3>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
              "{processModal.title || 'Untitled Donation'}"
            </p>

            <div className="space-y-4">
              <div>
                <label className="flex items-center gap-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 cursor-pointer">
                  <input
                    type="radio"
                    name="process_mode"
                    checked={processForm.create_new}
                    onChange={() => setProcessForm(f => ({ ...f, create_new: true, catalog_item_id: '' }))}
                    className="text-brand-600 focus:ring-brand-500"
                  />
                  Create new catalog item
                </label>
              </div>
              <div>
                <label className="flex items-center gap-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 cursor-pointer">
                  <input
                    type="radio"
                    name="process_mode"
                    checked={!processForm.create_new}
                    onChange={() => setProcessForm(f => ({ ...f, create_new: false }))}
                    className="text-brand-600 focus:ring-brand-500"
                  />
                  Add copy to existing catalog item
                </label>
                {!processForm.create_new && (
                  <input
                    type="number"
                    min={1}
                    value={processForm.catalog_item_id}
                    onChange={e => setProcessForm(f => ({ ...f, catalog_item_id: e.target.value }))}
                    placeholder={t('placeholder.staffDonations.catalogItemId')}
                    className="mt-2 w-full px-3 py-2 border border-lsc-border dark:border-earth-600 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream text-sm"
                  />
                )}
              </div>
              <div>
                <label htmlFor="donation-process-location" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                  Shelving Location (optional)
                </label>
                <input
                  id="donation-process-location"
                  type="text"
                  value={processForm.location}
                  onChange={e => setProcessForm(f => ({ ...f, location: e.target.value }))}
                  placeholder={t('placeholder.staffDonations.egAdultFictionA3')}
                  className="w-full px-3 py-2 border border-lsc-border dark:border-earth-600 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream text-sm"
                />
              </div>
            </div>

            <div className="flex justify-end gap-3 mt-6">
              <button
                onClick={() => setProcessModal(null)}
                className="px-4 py-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark"
              >
                Cancel
              </button>
              <button
                onClick={handleProcessSubmit}
                disabled={!processForm.create_new && !processForm.catalog_item_id}
                className="px-4 py-2 text-sm bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 disabled:opacity-50"
              >
                Process into Catalog
              </button>
            </div>
          </div>
        </ModalBackdrop>
      )}
    </PageContainer>
  </AdminShell>
  )
}
