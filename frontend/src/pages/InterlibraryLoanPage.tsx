/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient, keepPreviousData } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import {
  BookOpen,
  Search,
  Send,
  Truck,
  Clock,
  CheckCircle,
  XCircle,
  AlertCircle,
  Loader2,
  Plus,
  RefreshCw,
  Package,
  BarChart3,
  ArrowLeftRight,
  Printer,
  ChevronDown,
  ChevronUp,
  X,
  Building2,
} from 'lucide-react'
import toast from 'react-hot-toast'
import {
  getMyILLRequests,
  createILLRequest,
  cancelILLRequest,
  searchPartnerCatalogs,
  staffListILLRequests,
  staffUpdateILLRequest,
  staffAutoSearchAndSubmit,
  staffRenewILLRequest,
  staffListPartnerLibraries,
  getReturnShippingLabel,
  getDueReminders,
  getFillRateReport,
  getReciprocalLendingDashboard,
  type ILLPatronView,
  type ILLRequest,
  type ILLRequestStatus,
  type ILLFillRateReport,
  type ReciprocallLendingDashboard,
  type DueRemindersResponse,
} from '../api/interlibrary-loan-api'
import { listBranches, type Branch } from '../api/branch-api'
import { useTranslation, getCurrentLocale } from '@/i18n'
import { clean } from '@/lib/utils'
import { AdminShell } from '../components/shells/AdminShell'
import { t } from '@/i18n'
import PageContainer from '@/components/layout/PageContainer'

// ==================== Status Styles ====================

const STATUS_COLORS: Record<ILLRequestStatus, string> = {
  pending: 'bg-status-warning-100 text-status-warning-800 dark:bg-status-warning-900/30 dark:text-status-warning-400',
  searching: 'bg-earth-100 text-earth-800 dark:bg-earth-800/30 dark:text-lsc-rose-light',
  located: 'bg-lsc-rose/10 text-lsc-rose dark:bg-lsc-rose/20 dark:text-lsc-rose-light',
  not_found: 'bg-status-danger-100 text-status-danger-800 dark:bg-status-danger-900/30 dark:text-status-danger-400',
  submitted: 'bg-category-100 text-category-800 dark:bg-category-900/30 dark:text-category-400',
  approved: 'bg-status-success-100 text-status-success-800 dark:bg-status-success-900/30 dark:text-status-success-400',
  denied: 'bg-status-danger-100 text-status-danger-800 dark:bg-status-danger-900/30 dark:text-status-danger-400',
  in_transit: 'bg-earth-100 text-earth-800 dark:bg-earth-800/30 dark:text-lsc-rose-light',
  received: 'bg-teal-100 text-teal-800 dark:bg-teal-900/30 dark:text-teal-400',
  checked_out: 'bg-status-success-100 text-status-success-800 dark:bg-status-success-900/30 dark:text-status-success-400',
  returned: 'bg-status-warning-100 text-status-warning-800 dark:bg-status-warning-900/30 dark:text-status-warning-400',
  return_in_transit: 'bg-earth-100 text-earth-800 dark:bg-earth-800/30 dark:text-lsc-rose-light',
  completed: 'bg-earth-100 text-earth-800 dark:bg-earth-800 dark:text-earth-300',
  cancelled: 'bg-earth-100 text-earth-800 dark:bg-earth-800 dark:text-earth-300',
  lost: 'bg-status-danger-100 text-status-danger-800 dark:bg-status-danger-900/30 dark:text-status-danger-400',
}

const STATUS_LABEL_KEYS: Record<ILLRequestStatus, string> = {
  pending: 'interlibraryLoan.statusPending',
  searching: 'interlibraryLoan.statusSearching',
  located: 'interlibraryLoan.statusLocated',
  not_found: 'interlibraryLoan.statusNotFound',
  submitted: 'interlibraryLoan.statusSubmitted',
  approved: 'interlibraryLoan.statusApproved',
  denied: 'interlibraryLoan.statusDenied',
  in_transit: 'interlibraryLoan.statusInTransit',
  received: 'interlibraryLoan.statusReceived',
  checked_out: 'interlibraryLoan.statusCheckedOut',
  returned: 'interlibraryLoan.statusReturned',
  return_in_transit: 'interlibraryLoan.statusReturnInTransit',
  completed: 'interlibraryLoan.statusCompleted',
  cancelled: 'interlibraryLoan.statusCancelled',
  lost: 'interlibraryLoan.statusLost',
}

const STATUS_FALLBACKS: Record<ILLRequestStatus, string> = {
  pending: 'Pending',
  searching: 'Searching',
  located: 'Located',
  not_found: 'Not Found',
  submitted: 'Submitted',
  approved: 'Approved',
  denied: 'Denied',
  in_transit: 'In Transit',
  received: 'Received',
  checked_out: 'Checked Out',
  returned: 'Returned',
  return_in_transit: 'Return In Transit',
  completed: 'Completed',
  cancelled: 'Cancelled',
  lost: 'Lost',
}

function StatusBadge({ status }: { status: ILLRequestStatus }) {
  const { t } = useTranslation()
  const label = t(STATUS_LABEL_KEYS[status], STATUS_FALLBACKS[status])
  return (
    <span role="status" className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${STATUS_COLORS[status] || 'bg-earth-100 text-earth-800 dark:bg-earth-900/30 dark:text-earth-300'}`}>
      {label}
    </span>
  )
}

function formatDate(d: string | null): string {
  if (!d) return '--'
  const safe = /^\d{4}-\d{2}-\d{2}$/.test(d) ? d + 'T12:00:00' : d
  return new Date(safe).toLocaleDateString(getCurrentLocale(), { month: 'short', day: 'numeric', year: 'numeric' })
}

// ==================== Patron: Request Form ====================

function NewRequestForm({ token, onClose, initialTitle, initialAuthor, initialIsbn }: {
  token: string;
  onClose: () => void;
  initialTitle?: string | undefined;
  initialAuthor?: string | undefined;
  initialIsbn?: string | undefined;
}) {
  const { t } = useTranslation();
  const queryClient = useQueryClient()
  const [title, setTitle] = useState(initialTitle || '')
  const [author, setAuthor] = useState(initialAuthor || '')
  const [isbn, setIsbn] = useState(initialIsbn || '')
  const [notes, setNotes] = useState('')
  const [neededBy, setNeededBy] = useState('')
  const [pickupBranchId, setPickupBranchId] = useState<number | ''>('')
  const [branches, setBranches] = useState<Branch[]>([])

  useEffect(() => {
    listBranches({ active_only: true }).then(setBranches).catch(() => {})
  }, [])

  const { data: searchResults, isFetching: isSearching } = useQuery({
    queryKey: ['ill-partner-search', title, author, isbn],
    queryFn: () => searchPartnerCatalogs(token, title, author || undefined, isbn || undefined),
    enabled: title.length >= 3,
    staleTime: 30_000,
  })

  const createMutation = useMutation({
    mutationFn: () =>
      createILLRequest(token, clean({
        title,
        author: author || undefined,
        isbn: isbn || undefined,
        patron_notes: notes || undefined,
        needed_by: neededBy || undefined,
        pickup_branch_id: pickupBranchId || undefined,
      })),
    onSuccess: () => {
      toast.success(t('interlibraryLoan.interlibraryLoanRequestSubmitted'))
      queryClient.invalidateQueries({ queryKey: ['ill-my-requests'] })
      onClose()
    },
    onError: (err: Error) => toast.error(err.message),
  })

  const availablePartners = searchResults?.filter((r) => r.available) || []

  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-md p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
          {t('interlibraryLoan.requestFromAnotherLibrary', 'Request from Another Library')}
        </h3>
        <button onClick={onClose} className="text-earth-600 hover:text-earth-600 dark:text-earth-200 dark:hover:text-earth-300">
          <X className="w-5 h-5" />
        </button>
      </div>
      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
        {t('interlibraryLoan.weDontHaveItWell', "We don't have it? We'll get it for you! Fill in the details below and we'll search partner libraries.")}
      </p>

      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">{t('interlibraryLoan.titleLabel', 'Title *')}</label>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="w-full rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 px-3 py-2 text-sm text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-brand-500"
            placeholder={t('placeholder.interlibraryLoan.bookTitle')}
          />
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">{t('interlibraryLoan.authorLabel', 'Author')}</label>
            <input
              type="text"
              value={author}
              onChange={(e) => setAuthor(e.target.value)}
              className="w-full rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 px-3 py-2 text-sm text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-brand-500"
              placeholder={t('placeholder.interlibraryLoan.authorName')}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">{t('interlibraryLoan.isbnLabel', 'ISBN')}</label>
            <input
              type="text"
              value={isbn}
              onChange={(e) => setIsbn(e.target.value)}
              className="w-full rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 px-3 py-2 text-sm text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-brand-500"
              placeholder={t('placeholder.interlibraryLoan.isbnOptional')}
            />
          </div>
        </div>
        <div>
          <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">{t('interlibraryLoan.needByDateLabel', 'Need by date')}</label>
          <input
            type="date"
            value={neededBy}
            onChange={(e) => setNeededBy(e.target.value)}
            className="w-full rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 px-3 py-2 text-sm text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-brand-500"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">{t('interlibraryLoan.pickupBranchLabel', 'Pickup Branch')}</label>
          <select
            value={pickupBranchId}
            onChange={(e) => setPickupBranchId(e.target.value ? Number(e.target.value) : '')}
            className="w-full rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 px-3 py-2 text-sm text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-brand-500"
          >
            <option value="">{t('interlibraryLoan.selectABranchOptional', 'Select a branch (optional)')}</option>
            {branches.map((b) => (
              <option key={b.id} value={b.id}>{b.name}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">{t('interlibraryLoan.notesLabel', 'Notes')}</label>
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            rows={2}
            className="w-full rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 px-3 py-2 text-sm text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-brand-500"
            placeholder={t('placeholder.interlibraryLoan.anyAdditionalDetails')}
          />
        </div>

        {/* Live partner search results */}
        {title.length >= 3 && (
          <div className="border border-lsc-border dark:border-earth-700 rounded-lg p-4">
            <div className="flex items-center gap-2 mb-2">
              <Search className="w-4 h-4 text-brand-500" />
              <span className="text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">
                {t('interlibraryLoan.partnerLibraryAvailability', 'Partner Library Availability')}
              </span>
              {isSearching && <Loader2 className="w-4 h-4 motion-safe:animate-spin text-brand-500" />}
            </div>
            {availablePartners.length > 0 ? (
              <ul className="space-y-2">
                {availablePartners.map((r) => (
                  <li key={r.partner_library_id} className="flex items-center justify-between text-sm">
                    <div className="flex items-center gap-2">
                      <CheckCircle className="w-4 h-4 text-status-success-500" />
                      <span className="text-lsc-dark dark:text-lsc-cream">{r.partner_library_name}</span>
                    </div>
                    <span className="text-lsc-dark/70 dark:text-lsc-cream/70">
                      {t('interlibraryLoan.estimatedDeliveryDays', { days: r.estimated_delivery_days })} {r.lending_fee > 0 ? `($${r.lending_fee})` : t('interlibraryLoan.free', '(free)')}
                    </span>
                  </li>
                ))}
              </ul>
            ) : (
              !isSearching && (
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                  {t('interlibraryLoan.noResultsYetKeepTyping', 'No results yet. Keep typing to search partner catalogs.')}
                </p>
              )
            )}
          </div>
        )}

        <button
          onClick={() => createMutation.mutate()}
          disabled={!title || createMutation.isPending}
          className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-brand-600 text-white rounded-lg hover:bg-brand-700 disabled:opacity-50 disabled:cursor-not-allowed text-sm font-medium transition-colors"
        >
          {createMutation.isPending ? (
            <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
          ) : (
            <Send className="w-4 h-4" />
          )}
          {t('interlibraryLoan.submitRequestBtn', 'Submit Request')}
        </button>
      </div>
    </div>
  )
}

// ==================== Patron: My Requests ====================

function PatronRequestCard({
  request,
  token,
}: {
  request: ILLPatronView
  token: string
}) {
  const { t } = useTranslation()
  const [expanded, setExpanded] = useState(false)
  const queryClient = useQueryClient()

  const cancelMutation = useMutation({
    mutationFn: () => cancelILLRequest(token, request.id),
    onSuccess: () => {
      toast.success(t('toast.interlibraryLoan.requestCancelled'))
      queryClient.invalidateQueries({ queryKey: ['ill-my-requests'] })
    },
    onError: (err: Error) => toast.error(err.message),
  })

  const canCancel = ['pending', 'searching', 'located', 'submitted'].includes(request.status)

  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-sm border border-lsc-border dark:border-earth-700 p-4">
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <h4 className="text-sm font-semibold text-lsc-dark dark:text-lsc-cream truncate">
            {request.title || t('interlibraryLoan.untitledRequest', 'Untitled Request')}
          </h4>
          {request.author && (
            <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-0.5">{request.author}</p>
          )}
        </div>
        <StatusBadge status={request.status} />
      </div>

      <div className="mt-3 flex items-center gap-4 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
        <span className="flex items-center gap-1">
          <Clock className="w-3 h-3" />
          {t('interlibraryLoan.requestedOn', { date: formatDate(request.created_at) })}
        </span>
        {request.due_date && !['completed', 'cancelled', 'lost'].includes(request.status) && (
          <span className="flex items-center gap-1">
            <AlertCircle className="w-3 h-3" />
            {t('interlibraryLoan.dueOn', { date: formatDate(request.due_date) })}
          </span>
        )}
      </div>

      <p className="mt-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{request.status_label}</p>

      {/* Tracking Timeline */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="mt-2 flex items-center gap-1 text-xs text-brand-600 dark:text-brand-400 hover:underline"
      >
        {expanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
        {expanded
          ? t('interlibraryLoan.hideTrackingUpdates', { count: request.tracking_updates.length })
          : t('interlibraryLoan.showTrackingUpdates', { count: request.tracking_updates.length })}
      </button>

      {expanded && request.tracking_updates.length > 0 && (
        <div className="mt-3 space-y-2 border-l-2 border-brand-200 dark:border-brand-700 pl-4">
          {request.tracking_updates.map((update) => (
            <div key={update.id} className="text-xs">
              <span className="text-earth-600">{formatDate(update.created_at)}</span>
              <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{update.message}</p>
            </div>
          ))}
        </div>
      )}

      {canCancel && (
        <button
          onClick={() => cancelMutation.mutate()}
          disabled={cancelMutation.isPending}
          className="mt-3 text-xs text-status-danger-600 dark:text-status-danger-400 hover:underline flex items-center gap-1"
        >
          {cancelMutation.isPending ? <Loader2 className="w-3 h-3 motion-safe:animate-spin" /> : <XCircle className="w-3 h-3" />}
          {t('interlibraryLoan.cancelRequestBtn', 'Cancel request')}
        </button>
      )}
    </div>
  )
}

// ==================== Staff: Dashboard Cards ====================

function FillRateCard({ report }: { report: ILLFillRateReport }) {
  const { t } = useTranslation()
  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-sm border border-lsc-border dark:border-earth-700 p-4">
      <div className="flex items-center gap-2 mb-3">
        <BarChart3 className="w-5 h-5 text-brand-500" />
        <h3 className="text-sm font-semibold text-lsc-dark dark:text-lsc-cream">{t('interlibraryLoan.fillRateTitle', 'Fill Rate')}</h3>
      </div>
      <div className="text-3xl font-bold text-brand-600 dark:text-brand-400">
        {report.fill_rate_percent}%
      </div>
      <div className="mt-2 grid grid-cols-2 gap-2 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
        <div>{t('interlibraryLoan.totalLabel', { count: report.total_requests })}</div>
        <div>{t('interlibraryLoan.filledLabel', { count: report.filled_requests })}</div>
        <div>{t('interlibraryLoan.unfilledLabel', { count: report.unfilled_requests })}</div>
        <div>{t('interlibraryLoan.cancelledLabel', { count: report.cancelled_requests })}</div>
      </div>
      {report.average_turnaround_days && (
        <p className="mt-2 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
          {t('interlibraryLoan.avgTurnaround', { days: report.average_turnaround_days })}
        </p>
      )}
    </div>
  )
}

function ReciprocalCard({ dashboard }: { dashboard: ReciprocallLendingDashboard }) {
  const { t } = useTranslation()
  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-sm border border-lsc-border dark:border-earth-700 p-4">
      <div className="flex items-center gap-2 mb-3">
        <ArrowLeftRight className="w-5 h-5 text-brand-500" />
        <h3 className="text-sm font-semibold text-lsc-dark dark:text-lsc-cream">{t('interlibraryLoan.reciprocalLendingTitle', 'Reciprocal Lending')}</h3>
      </div>
      <div className="grid grid-cols-2 gap-3 text-sm">
        <div>
          <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{t('interlibraryLoan.partnersLabel', 'Partners')}</div>
          <div className="font-semibold text-lsc-dark dark:text-lsc-cream">
            {dashboard.active_partners}/{dashboard.total_partners}
          </div>
        </div>
        <div>
          <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{t('interlibraryLoan.netCostLabel', 'Net Cost')}</div>
          <div className="font-semibold text-lsc-dark dark:text-lsc-cream">${dashboard.net_cost}</div>
        </div>
        <div>
          <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{t('interlibraryLoan.borrowedLabel', 'Borrowed')}</div>
          <div className="font-semibold text-lsc-dark dark:text-lsc-cream">{dashboard.total_items_borrowed}</div>
        </div>
        <div>
          <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{t('interlibraryLoan.lentLabel', 'Lent')}</div>
          <div className="font-semibold text-lsc-dark dark:text-lsc-cream">{dashboard.total_items_lent}</div>
        </div>
      </div>
      {dashboard.partner_stats.length > 0 && (
        <div className="mt-3 space-y-2">
          <h4 className="text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70">{t('interlibraryLoan.byPartnerLabel', 'By Partner')}</h4>
          {dashboard.partner_stats.map((ps) => (
            <div
              key={ps.partner_library_id}
              className="flex items-center justify-between text-xs border-t border-earth-100 dark:border-earth-700 pt-1"
            >
              <span className="text-lsc-dark/70 dark:text-lsc-cream/70 truncate">{ps.partner_library_name}</span>
              <span className="text-lsc-dark/70 dark:text-lsc-cream/70 whitespace-nowrap ml-2">
                {t('interlibraryLoan.borrowedLentAbbrev', { borrowed: ps.items_borrowed, lent: ps.items_lent, percent: ps.fill_rate_percent })}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function DueRemindersCard({ reminders }: { reminders: DueRemindersResponse }) {
  const { t } = useTranslation()
  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-sm border border-lsc-border dark:border-earth-700 p-4">
      <div className="flex items-center gap-2 mb-3">
        <Clock className="w-5 h-5 text-status-warning-500" />
        <h3 className="text-sm font-semibold text-lsc-dark dark:text-lsc-cream">{t('interlibraryLoan.dueDateAlertsTitle', 'Due Date Alerts')}</h3>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div className="text-center p-3 rounded-lg bg-status-warning-50 dark:bg-status-warning-900/20">
          <div className="text-2xl font-bold text-status-warning-600 dark:text-status-warning-400">{reminders.upcoming_count}</div>
          <div className="text-xs text-status-warning-700 dark:text-status-warning-300">{t('interlibraryLoan.dueSoonLabel', 'Due Soon')}</div>
        </div>
        <div className="text-center p-3 rounded-lg bg-status-danger-50 dark:bg-status-danger-900/20">
          <div className="text-2xl font-bold text-status-danger-600 dark:text-status-danger-400">{reminders.overdue_count}</div>
          <div className="text-xs text-status-danger-700 dark:text-status-danger-300">{t('interlibraryLoan.overdueLabel', 'Overdue')}</div>
        </div>
      </div>
    </div>
  )
}

// ==================== Staff: Request Row ====================

function StaffRequestRow({
  request,
  token,
}: {
  request: ILLRequest
  token: string
}) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()

  const autoSearchMutation = useMutation({
    mutationFn: () => staffAutoSearchAndSubmit(token, request.id),
    onSuccess: () => {
      toast.success(t('interlibraryLoan.autoSearchCompletedAndRequest'))
      queryClient.invalidateQueries({ queryKey: ['ill-staff-requests'] })
    },
    onError: (err: Error) => toast.error(err.message),
  })

  const renewMutation = useMutation({
    mutationFn: () => staffRenewILLRequest(token, request.id),
    onSuccess: () => {
      toast.success(t('toast.interlibraryLoan.renewalApproved'))
      queryClient.invalidateQueries({ queryKey: ['ill-staff-requests'] })
    },
    onError: (err: Error) => toast.error(err.message),
  })

  const printLabelMutation = useMutation({
    mutationFn: () => getReturnShippingLabel(token, request.id),
    onSuccess: (data) => {
      toast.success(t('toast.interlibraryLoan.shippingLabelGeneratedForTolibrary', { tolibrary: data.to_library }))
    },
    onError: (err: Error) => toast.error(err.message),
  })

  const advanceStatus = (newStatus: ILLRequestStatus) => {
    staffUpdateILLRequest(token, request.id, { status: newStatus })
      .then(() => {
        toast.success(t('toast.interlibraryLoan.statusUpdatedToReplaceg', { replaceg: newStatus.replace(/_/g, ' ') }))
        queryClient.invalidateQueries({ queryKey: ['ill-staff-requests'] })
      })
      .catch((err: Error) => toast.error(err.message))
  }

  return (
    <tr className="border-b border-earth-100 dark:border-earth-700 hover:bg-earth-50 dark:hover:bg-earth-750">
      <td className="px-4 py-3 text-sm">
        <div className="font-medium text-lsc-dark dark:text-lsc-cream truncate max-w-[12.5rem]" title={request.title}>
          {request.title}
        </div>
        {request.author && (
          <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{request.author}</div>
        )}
      </td>
      <td className="px-4 py-3">
        <StatusBadge status={request.status} />
      </td>
      <td className="px-4 py-3 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
        {request.partner_library_name || '--'}
      </td>
      <td className="px-4 py-3 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
        {formatDate(request.due_date)}
      </td>
      <td className="px-4 py-3 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
        ${request.actual_cost || '0.00'}
      </td>
      <td className="px-4 py-3">
        <div className="flex items-center gap-1">
          {request.status === 'pending' && (
            <button
              onClick={() => autoSearchMutation.mutate()}
              disabled={autoSearchMutation.isPending}
              className="p-1 rounded text-brand-600 hover:bg-brand-50 dark:hover:bg-brand-900/30"
              title={t('interlibraryLoan.autoSearchPartnersTitle', 'Auto-search partners')}
            >
              {autoSearchMutation.isPending ? <Loader2 className="w-4 h-4 motion-safe:animate-spin" /> : <Search className="w-4 h-4" />}
            </button>
          )}
          {request.status === 'approved' && (
            <button
              onClick={() => advanceStatus('in_transit')}
              className="p-1 rounded text-lsc-rose dark:text-lsc-rose-light hover:bg-earth-50 dark:hover:bg-earth-800/30"
              title={t('interlibraryLoan.markAsShippedTitle', 'Mark as shipped')}
            >
              <Truck className="w-4 h-4" />
            </button>
          )}
          {request.status === 'in_transit' && (
            <button
              onClick={() => advanceStatus('received')}
              className="p-1 rounded text-teal-600 hover:bg-teal-50 dark:hover:bg-teal-900/30"
              title={t('interlibraryLoan.markAsReceivedTitle', 'Mark as received')}
            >
              <Package className="w-4 h-4" />
            </button>
          )}
          {request.status === 'received' && (
            <button
              onClick={() => advanceStatus('checked_out')}
              className="p-1 rounded text-status-success-600 hover:bg-status-success-50 dark:hover:bg-status-success-900/30"
              title={t('interlibraryLoan.checkOutToPatron')}
            >
              <BookOpen className="w-4 h-4" />
            </button>
          )}
          {request.status === 'checked_out' && (
            <>
              <button
                onClick={() => advanceStatus('returned')}
                className="p-1 rounded text-status-warning-600 hover:bg-status-warning-50 dark:hover:bg-status-warning-900/30"
                title={t('interlibraryLoan.patronReturnedTitle', 'Patron returned')}
              >
                <CheckCircle className="w-4 h-4" />
              </button>
              <button
                onClick={() => renewMutation.mutate()}
                disabled={renewMutation.isPending || request.renewal_count >= request.max_renewals}
                className="p-1 rounded text-brand-600 hover:bg-brand-50 dark:hover:bg-brand-900/30 disabled:opacity-30"
                title={t('interlibraryLoan.renewTitle', 'Renew')}
              >
                <RefreshCw className="w-4 h-4" />
              </button>
            </>
          )}
          {request.status === 'returned' && (
            <button
              onClick={() => printLabelMutation.mutate()}
              disabled={printLabelMutation.isPending}
              className="p-1 rounded text-earth-600 dark:text-earth-200 hover:bg-earth-50 dark:hover:bg-earth-900/30"
              title={t('interlibraryLoan.printReturnShippingLabel')}
            >
              <Printer className="w-4 h-4" />
            </button>
          )}
          {request.status === 'returned' && (
            <button
              onClick={() => advanceStatus('return_in_transit')}
              className="p-1 rounded text-lsc-rose dark:text-lsc-rose-light hover:bg-earth-50 dark:hover:bg-earth-800/30"
              title={t('interlibraryLoan.shipBackToLender')}
            >
              <Truck className="w-4 h-4" />
            </button>
          )}
          {request.status === 'return_in_transit' && (
            <button
              onClick={() => advanceStatus('completed')}
              className="p-1 rounded text-status-success-600 hover:bg-status-success-50 dark:hover:bg-status-success-900/30"
              title={t('interlibraryLoan.markCompletedTitle', 'Mark completed')}
            >
              <CheckCircle className="w-4 h-4" />
            </button>
          )}
        </div>
      </td>
    </tr>
  )
}

// ==================== Main Page ====================

type Tab = 'my-requests' | 'staff-requests' | 'partners' | 'reports'

export default function InterlibraryLoanPage() {
  const { token, user } = useAuth()
  const [searchParams] = useSearchParams()
  const isStaff = user && ['staff', 'admin', 'super_admin', 'director'].includes(user.role)
  const [activeTab, setActiveTab] = useState<Tab>(isStaff ? 'staff-requests' : 'my-requests')

  // Auto-open form if pre-filled from federated search
  const prefillTitle = searchParams.get('title') || undefined
  const prefillAuthor = searchParams.get('author') || undefined
  const prefillIsbn = searchParams.get('isbn') || undefined
  const hasPrefill = !!(prefillTitle || prefillAuthor || prefillIsbn)
  const [showNewForm, setShowNewForm] = useState(hasPrefill)
  const [statusFilter, setStatusFilter] = useState<string>('')

  // Patron queries
  const { data: myRequests, isLoading: loadingMyRequests } = useQuery({
    queryKey: ['ill-my-requests'],
    queryFn: () => getMyILLRequests(token!, false),
    enabled: !!token && activeTab === 'my-requests',
  })

  // Staff queries
  const { data: staffRequests, isLoading: loadingStaff } = useQuery({
    queryKey: ['ill-staff-requests', statusFilter],
    queryFn: () =>
      staffListILLRequests(token!, clean({
        status: (statusFilter || undefined) as ILLRequestStatus | undefined,
        active_only: !statusFilter,
      })),
    placeholderData: keepPreviousData,
    enabled: !!token && !!isStaff && activeTab === 'staff-requests',
  })

  const { data: partners } = useQuery({
    queryKey: ['ill-partners'],
    queryFn: () => staffListPartnerLibraries(token!),
    enabled: !!token && !!isStaff && activeTab === 'partners',
  })

  const { data: fillRate } = useQuery({
    queryKey: ['ill-fill-rate'],
    queryFn: () => getFillRateReport(token!),
    enabled: !!token && !!isStaff && activeTab === 'reports',
  })

  const { data: reciprocalDashboard } = useQuery({
    queryKey: ['ill-reciprocal'],
    queryFn: () => getReciprocalLendingDashboard(token!),
    enabled: !!token && !!isStaff && activeTab === 'reports',
  })

  const { data: dueReminders } = useQuery({
    queryKey: ['ill-due-reminders'],
    queryFn: () => getDueReminders(token!),
    enabled: !!token && !!isStaff && activeTab === 'reports',
  })

  if (!token) {
    return (
      <PageContainer className="py-12 text-center">
        <BookOpen className="w-12 h-12 text-brand-500 mx-auto mb-4" />
        <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-2">
          {t('interlibraryLoan.pageTitle', 'Interlibrary Loan')}
        </h1>
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
          {t('interlibraryLoan.signInToRequestItems', 'Please sign in to request items from other libraries.')}
        </p>
      </PageContainer>
    )
  }

  const tabs = [
    { id: 'my-requests' as Tab, label: t('interlibraryLoan.tabMyRequests', 'My Requests'), icon: BookOpen },
    ...(isStaff
      ? [
          { id: 'staff-requests' as Tab, label: t('interlibraryLoan.tabAllRequests', 'All Requests'), icon: Package },
          { id: 'partners' as Tab, label: t('interlibraryLoan.tabPartnerLibraries', 'Partner Libraries'), icon: Building2 },
          { id: 'reports' as Tab, label: t('interlibraryLoan.tabReportsDashboard', 'Reports & Dashboard'), icon: BarChart3 },
        ]
      : []),
  ]

  return (

    <AdminShell title={t('interlibraryLoan.pageTitle', 'Interlibrary Loan')}>    <PageContainer className="py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
            {t('interlibraryLoan.pageTitle', 'Interlibrary Loan')}
          </h1>
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
            {t('interlibraryLoan.pageSubtitle', 'Borrow materials from partner libraries')}
          </p>
        </div>
        <button
          onClick={() => setShowNewForm(true)}
          className="flex items-center gap-2 px-4 py-2 bg-brand-600 text-white rounded-lg hover:bg-brand-700 text-sm font-medium transition-colors"
        >
          <Plus className="w-4 h-4" />
          {t('interlibraryLoan.newRequestBtn', 'New Request')}
        </button>
      </div>

      {/* New Request Form */}
      {showNewForm && <NewRequestForm token={token} onClose={() => setShowNewForm(false)} initialTitle={prefillTitle} initialAuthor={prefillAuthor} initialIsbn={prefillIsbn} />}

      {/* Tabs */}
      <div className="border-b border-lsc-border dark:border-earth-700 mb-6">
        <nav aria-label={t('aria.interlibraryLoan.interlibraryLoanSections')} className="flex gap-6 -mb-px">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 pb-3 px-1 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tab.id
                  ? 'border-brand-500 text-brand-600 dark:text-brand-400'
                  : 'border-transparent text-earth-600 hover:text-lsc-dark/70 dark:text-lsc-cream/70 dark:hover:text-earth-300'
              }`}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      {activeTab === 'my-requests' && (
        <div>
          {loadingMyRequests ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-6 h-6 motion-safe:animate-spin text-brand-500" />
            </div>
          ) : myRequests && myRequests.length > 0 ? (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {myRequests.map((req) => (
                <PatronRequestCard key={req.id} request={req} token={token} />
              ))}
            </div>
          ) : (
            <div className="text-center py-12">
              <BookOpen className="w-10 h-10 text-earth-300 dark:text-earth-600 mx-auto mb-3" />
              <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
                {t('interlibraryLoan.noRequestsYet', 'No interlibrary loan requests yet.')}
              </p>
              <button
                onClick={() => setShowNewForm(true)}
                className="mt-3 text-sm text-brand-600 dark:text-brand-400 hover:underline"
              >
                {t('interlibraryLoan.requestFromAnotherLibraryLink', 'Request an item from another library')}
              </button>
            </div>
          )}
        </div>
      )}

      {activeTab === 'staff-requests' && isStaff && (
        <div>
          {/* Status filter */}
          <div className="mb-4 flex items-center gap-3">
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 px-3 py-2 text-sm text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-brand-500"
            >
              <option value="">{t('interlibraryLoan.filterActiveRequests', 'Active requests')}</option>
              <option value="pending">{t(STATUS_LABEL_KEYS.pending, STATUS_FALLBACKS.pending)}</option>
              <option value="searching">{t(STATUS_LABEL_KEYS.searching, STATUS_FALLBACKS.searching)}</option>
              <option value="located">{t(STATUS_LABEL_KEYS.located, STATUS_FALLBACKS.located)}</option>
              <option value="submitted">{t(STATUS_LABEL_KEYS.submitted, STATUS_FALLBACKS.submitted)}</option>
              <option value="approved">{t(STATUS_LABEL_KEYS.approved, STATUS_FALLBACKS.approved)}</option>
              <option value="in_transit">{t(STATUS_LABEL_KEYS.in_transit, STATUS_FALLBACKS.in_transit)}</option>
              <option value="received">{t(STATUS_LABEL_KEYS.received, STATUS_FALLBACKS.received)}</option>
              <option value="checked_out">{t(STATUS_LABEL_KEYS.checked_out, STATUS_FALLBACKS.checked_out)}</option>
              <option value="returned">{t(STATUS_LABEL_KEYS.returned, STATUS_FALLBACKS.returned)}</option>
              <option value="return_in_transit">{t(STATUS_LABEL_KEYS.return_in_transit, STATUS_FALLBACKS.return_in_transit)}</option>
              <option value="completed">{t(STATUS_LABEL_KEYS.completed, STATUS_FALLBACKS.completed)}</option>
              <option value="cancelled">{t(STATUS_LABEL_KEYS.cancelled, STATUS_FALLBACKS.cancelled)}</option>
            </select>
          </div>

          {loadingStaff ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-6 h-6 motion-safe:animate-spin text-brand-500" />
            </div>
          ) : staffRequests && staffRequests.length > 0 ? (
            <div className="overflow-x-auto rounded-lg border border-lsc-border dark:border-earth-700">
              <table className="w-full text-left">
                <thead className="bg-earth-50 dark:bg-earth-750">
                  <tr>
                    <th className="px-4 py-3 text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 uppercase">{t('interlibraryLoan.tableHeaderTitle', 'Title')}</th>
                    <th className="px-4 py-3 text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 uppercase">{t('interlibraryLoan.tableHeaderStatus', 'Status')}</th>
                    <th className="px-4 py-3 text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 uppercase">{t('interlibraryLoan.tableHeaderPartner', 'Partner')}</th>
                    <th className="px-4 py-3 text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 uppercase">{t('interlibraryLoan.tableHeaderDue', 'Due')}</th>
                    <th className="px-4 py-3 text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 uppercase">{t('interlibraryLoan.tableHeaderCost', 'Cost')}</th>
                    <th className="px-4 py-3 text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 uppercase">{t('interlibraryLoan.tableHeaderActions', 'Actions')}</th>
                  </tr>
                </thead>
                <tbody>
                  {staffRequests.map((req) => (
                    <StaffRequestRow key={req.id} request={req} token={token} />
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-center py-12 text-lsc-dark/70 dark:text-lsc-cream/70">
              {t('interlibraryLoan.noIllRequestsFound', 'No ILL requests found.')}
            </p>
          )}
        </div>
      )}

      {activeTab === 'partners' && isStaff && (
        <div>
          {partners && partners.length > 0 ? (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {partners.map((p) => (
                <div
                  key={p.id}
                  className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-sm border border-lsc-border dark:border-earth-700 p-4"
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <h4 className="text-sm font-semibold text-lsc-dark dark:text-lsc-cream">{p.name}</h4>
                      <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{p.code}</p>
                    </div>
                    <span
                      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                        p.status === 'active'
                          ? 'bg-status-success-100 text-status-success-800 dark:bg-status-success-900/30 dark:text-status-success-400'
                          : 'bg-earth-100 text-earth-800 dark:bg-earth-800 dark:text-earth-300'
                      }`}
                    >
                      {p.status}
                    </span>
                  </div>
                  {(p.city || p.state) && (
                    <p className="mt-2 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                      {[p.city, p.state].filter(Boolean).join(', ')}
                    </p>
                  )}
                  <div className="mt-3 grid grid-cols-2 gap-2 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                    <div>{t('interlibraryLoan.lendingFeeLabel', { fee: p.lending_fee })}</div>
                    <div>{t('interlibraryLoan.loanDaysLabel', { days: p.max_loan_days })}</div>
                    <div>{t('interlibraryLoan.renewalsLabel', { count: p.max_renewals })}</div>
                    <div>
                      {p.reciprocal_agreement ? (
                        <span className="text-status-success-600 dark:text-status-success-400">{t('interlibraryLoan.reciprocalBadge', 'Reciprocal')}</span>
                      ) : (
                        t('interlibraryLoan.noAgreementLabel', 'No agreement')
                      )}
                    </div>
                  </div>
                  {p.contact_name && (
                    <p className="mt-2 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                      {t('interlibraryLoan.contactInfo', { name: p.contact_name, email: p.contact_email ? `(${p.contact_email})` : '' })}
                    </p>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <p className="text-center py-12 text-lsc-dark/70 dark:text-lsc-cream/70">
              {t('interlibraryLoan.noPartnerLibrariesConfigured', 'No partner libraries configured yet.')}
            </p>
          )}
        </div>
      )}

      {activeTab === 'reports' && isStaff && (
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {fillRate && <FillRateCard report={fillRate} />}
          {reciprocalDashboard && <ReciprocalCard dashboard={reciprocalDashboard} />}
          {dueReminders && <DueRemindersCard reminders={dueReminders} />}
        </div>
      )}
    </PageContainer>
  </AdminShell>
  )
}
