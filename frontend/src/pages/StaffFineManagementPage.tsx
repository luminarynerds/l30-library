/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/* eslint-disable @typescript-eslint/no-unused-expressions */
import { useState, useEffect, useCallback } from "react"
import { useNavigate } from "react-router-dom"
import { useAuth } from "../contexts/AuthContext"
import { AdminShell } from '../components/shells/AdminShell'
import {
  Loader2, DollarSign, BarChart3, Clock, Search, AlertTriangle,
  CheckCircle, XCircle, CreditCard, Ban, FileText,
  Filter, Calendar, TrendingUp
} from "lucide-react"
import toast from "react-hot-toast"
import type {
  Fine, FineType, PaymentMethod, PendingCheck,
  PaymentPlan, FineAnalytics,
} from "../api/fines-api"
import * as finesApi from "../api/fines-api"
import { useTranslation, getCurrentLocale } from '@/i18n'
import { clean } from '@/lib/utils'
import { t } from '@/i18n'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

// ============ Constants ============

const TABS = [
  { id: "fines", label: "Active Fines", icon: DollarSign },
  { id: "plans", label: "Payment Plans", icon: Calendar },
  { id: "checks", label: "Pending Checks", icon: FileText },
  { id: "analytics", label: "Analytics", icon: BarChart3 },
]

const STATUS_COLORS: Record<string, string> = {
  unpaid: "bg-status-danger-100 dark:bg-status-danger-900/30 text-status-danger-700 dark:text-status-danger-300",
  partial: "bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-700 dark:text-status-warning-300",
  paid: "bg-status-success-100 dark:bg-status-success-900/30 text-status-success-700 dark:text-status-success-300",
  waived: "bg-earth-100 dark:bg-earth-700 text-earth-600 dark:text-earth-200",
}

const PLAN_STATUS_COLORS: Record<string, string> = {
  active: "bg-earth-100 dark:bg-earth-800/30 text-lsc-rose dark:text-lsc-rose-light",
  completed: "bg-status-success-100 dark:bg-status-success-900/30 text-status-success-700 dark:text-status-success-300",
  cancelled: "bg-earth-100 dark:bg-earth-700 text-earth-600 dark:text-earth-200",
  defaulted: "bg-status-danger-100 dark:bg-status-danger-900/30 text-status-danger-700 dark:text-status-danger-300",
}

const CHECK_STATUS_COLORS: Record<string, string> = {
  pending: "bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-700 dark:text-status-warning-300",
  cleared: "bg-status-success-100 dark:bg-status-success-900/30 text-status-success-700 dark:text-status-success-300",
  bounced: "bg-status-danger-100 dark:bg-status-danger-900/30 text-status-danger-700 dark:text-status-danger-300",
}

const FINE_TYPE_LABELS: Record<string, string> = {
  overdue: "Overdue",
  lost_item: "Lost Item",
  damaged_item: "Damaged",
  other: "Other",
}

const PAYMENT_METHOD_LABELS: Record<string, string> = {
  cash: "Cash",
  card: "Card",
  check: "Check",
  online: "Online",
  waiver: "Waiver",
  reading_minutes: "Reading Minutes",
  other: "Other",
}

function fineTypeIcon(type: FineType) {
  switch (type) {
    case "overdue": return <Clock className="h-4 w-4" />
    case "lost_item": return <Search className="h-4 w-4" />
    case "damaged_item": return <AlertTriangle className="h-4 w-4" />
    default: return <DollarSign className="h-4 w-4" />
  }
}

function formatCurrency(cents: number): string {
  return `$${(cents / 100).toFixed(2)}`
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(getCurrentLocale(), { month: "short", day: "numeric", year: "numeric" })
}

// ============ Active Fines Tab ============

function ActiveFinesTab({ token }: { token: string }) {
  const { t } = useTranslation();
  const [fines, setFines] = useState<Fine[]>([])
  const [loading, setLoading] = useState(true)
  const [statusFilter, setStatusFilter] = useState<string>("")
  const [typeFilter, setTypeFilter] = useState<string>("")
  const [selected, setSelected] = useState<Set<number>>(new Set())
  const [payModal, setPayModal] = useState<Fine | null>(null)
  const [waiveModal, setWaiveModal] = useState<Fine | null>(null)

  const loadFines = useCallback(async () => {
    setLoading(true)
    try {
      const result = await finesApi.getFines(token, clean({
        status: statusFilter || undefined,
        fine_type: typeFilter || undefined,
      }))
      setFines(result.fines || [])
    } catch (e: unknown) {
      toast.error((e instanceof Error ? e.message : null) || "Failed to load fines")
    } finally {
      setLoading(false)
    }
  }, [token, statusFilter, typeFilter])

  useEffect(() => { loadFines() }, [loadFines])

  const toggleSelect = (id: number) => {
    setSelected(prev => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }

  const toggleAll = () => {
    if (selected.size === fines.length) {
      setSelected(new Set())
    } else {
      setSelected(new Set(fines.map(f => f.id)))
    }
  }

  return (
    <div>
      {/* Filters */}
      <div className="flex flex-wrap gap-3 mb-4">
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-earth-600" />
          <select
            value={statusFilter}
            onChange={e => setStatusFilter(e.target.value)}
            className="text-sm border border-lsc-border dark:border-earth-600 rounded-lg px-3 py-1.5 bg-lsc-white dark:bg-earth-800 text-lsc-dark/70 dark:text-lsc-cream/70"
          >
            <option value="">All Statuses</option>
            <option value="unpaid">Unpaid</option>
            <option value="partial">Partial</option>
            <option value="paid">Paid</option>
            <option value="waived">Waived</option>
          </select>
        </div>
        <select
          value={typeFilter}
          onChange={e => setTypeFilter(e.target.value)}
          className="text-sm border border-lsc-border dark:border-earth-600 rounded-lg px-3 py-1.5 bg-lsc-white dark:bg-earth-800 text-lsc-dark/70 dark:text-lsc-cream/70"
        >
          <option value="">All Types</option>
          <option value="overdue">Overdue</option>
          <option value="lost_item">Lost Item</option>
          <option value="damaged_item">Damaged</option>
          <option value="other">Other</option>
        </select>
        {selected.size > 0 && (
          <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 self-center">
            {selected.size} selected
          </span>
        )}
      </div>

      {/* Table */}
      {loading ? (
        <div className="flex justify-center py-12">
          <Loader2 className="motion-safe:animate-spin h-8 w-8 text-lsc-green" />
        </div>
      ) : fines.length === 0 ? (
        <div className="text-center py-12 text-earth-600">
          <DollarSign className="h-12 w-12 mx-auto mb-3 opacity-30" />
          <p>{t('staffFineManagement.noFinesFoundMatchingYour')}</p>
        </div>
      ) : (
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-earth-50 dark:bg-earth-900/50 text-earth-600 dark:text-earth-400 text-left">
                  <th className="p-3 w-10">
                    <input
                      type="checkbox"
                      checked={selected.size === fines.length && fines.length > 0}
                      onChange={toggleAll}
                      aria-label={t('aria.staffFineManagement.selectAllFines', 'Select all fines')}
                      className="rounded border-lsc-border"
                    />
                  </th>
                  <th className="p-3">Patron</th>
                  <th className="p-3">Type</th>
                  <th className="p-3">Item</th>
                  <th className="p-3 text-right">Amount</th>
                  <th className="p-3 text-right">Balance</th>
                  <th className="p-3">Status</th>
                  <th className="p-3">Date</th>
                  <th className="p-3">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-earth-100 dark:divide-earth-700">
                {fines.map(fine => (
                  <tr key={fine.id} className="hover:bg-earth-50/50 dark:hover:bg-earth-700/30">
                    <td className="p-3">
                      <input
                        type="checkbox"
                        checked={selected.has(fine.id)}
                        onChange={() => toggleSelect(fine.id)}
                        aria-label={t('aria.staffFineManagement.selectFine', 'Select fine for {{name}}').replace('{{name}}', fine.patron_name || `Patron #${fine.user_id}`)}
                        className="rounded border-lsc-border"
                      />
                    </td>
                    <td className="p-3 font-medium text-earth-800 dark:text-earth-100">
                      {fine.patron_name || `Patron #${fine.user_id}`}
                    </td>
                    <td className="p-3">
                      <span className="flex items-center gap-1.5 text-lsc-dark/70 dark:text-lsc-cream/70">
                        {fineTypeIcon(fine.fine_type)}
                        {FINE_TYPE_LABELS[fine.fine_type] || fine.fine_type}
                      </span>
                    </td>
                    <td className="p-3 text-lsc-dark/70 dark:text-lsc-cream/70 max-w-[12.5rem] truncate" title={fine.item_title || "--"}>
                      {fine.item_title || "--"}
                    </td>
                    <td className="p-3 text-right font-mono text-lsc-dark/70 dark:text-lsc-cream/70">
                      {formatCurrency(fine.amount)}
                    </td>
                    <td className="p-3 text-right font-mono font-semibold text-earth-800 dark:text-earth-100">
                      {formatCurrency(fine.balance)}
                    </td>
                    <td className="p-3">
                      <span className={`inline-flex px-2 py-0.5 text-xs font-medium rounded-full ${STATUS_COLORS[fine.status] || ""}`}>
                        {fine.status}
                      </span>
                    </td>
                    <td className="p-3 text-earth-600 dark:text-earth-400 text-xs">
                      {formatDate(fine.created_at)}
                    </td>
                    <td className="p-3">
                      {(fine.status === "unpaid" || fine.status === "partial") && (
                        <div className="flex gap-1">
                          <button
                            onClick={() => setPayModal(fine)}
                            className="p-1.5 rounded-lg hover:bg-status-success-50 dark:hover:bg-status-success-900/20 text-status-success-600 dark:text-status-success-400"
                            title="Record Payment"
                          >
                            <CreditCard className="h-4 w-4" />
                          </button>
                          <button
                            onClick={() => setWaiveModal(fine)}
                            className="p-1.5 rounded-lg hover:bg-earth-100 dark:hover:bg-earth-700 text-earth-600 dark:text-earth-400"
                            title="Waive Fine"
                          >
                            <Ban className="h-4 w-4" />
                          </button>
                        </div>
                      )}
                      {fine.status === "paid" && (
                        <span className="text-status-success-500"><CheckCircle className="h-4 w-4" /></span>
                      )}
                      {fine.status === "waived" && (
                        <span className="text-earth-600 text-xs">{fine.waive_reason ? `Waived: ${fine.waive_reason}` : "Waived"}</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Pay Modal */}
      {payModal && (
        <PaymentModal
          fine={payModal}
          token={token}
          onClose={() => setPayModal(null)}
          onSuccess={() => { setPayModal(null); loadFines() }}
        />
      )}

      {/* Waive Modal */}
      {waiveModal && (
        <WaiveModal
          fine={waiveModal}
          token={token}
          onClose={() => setWaiveModal(null)}
          onSuccess={() => { setWaiveModal(null); loadFines() }}
        />
      )}
    </div>
  )
}

// ============ Payment Modal ============

function PaymentModal({ fine, token, onClose, onSuccess }: {
  fine: Fine; token: string; onClose: () => void; onSuccess: () => void
}) {
  const { t } = useTranslation()
  const [amount, setAmount] = useState(String((fine.balance / 100).toFixed(2)))
  const [method, setMethod] = useState<PaymentMethod>("cash")
  const [submitting, setSubmitting] = useState(false)
  const isPartial = parseFloat(amount) * 100 < fine.balance

  const handleSubmit = async () => {
    const cents = Math.round(parseFloat(amount) * 100)
    if (isNaN(cents) || cents <= 0) {
      toast.error(t('staffFineManagement.enterAValidAmount'))
      return
    }
    if (cents > fine.balance) {
      toast.error(t('toast.staffFineManagement.amountExceedsBalance'))
      return
    }
    setSubmitting(true)
    try {
      if (isPartial) {
        await finesApi.partialPayment(token, fine.id, { amount: cents, payment_method: method })
      } else {
        await finesApi.payFine(token, fine.id, { amount: cents, payment_method: method })
      }
      toast.success(isPartial ? "Partial payment recorded" : "Payment recorded")
      onSuccess()
    } catch (e: unknown) {
      toast.error((e instanceof Error ? e.message : null) || "Payment failed")
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <ModalBackdrop onClose={onClose} title="Record Payment">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg w-full max-w-md p-6 mx-4">
        <h3 className="font-serif text-lg font-bold text-earth-800 dark:text-earth-100 mb-1">Record Payment</h3>
        <p className="text-sm text-earth-600 dark:text-earth-400 mb-4">
          {fine.patron_name || `Patron #${fine.user_id}`} -- Balance: {formatCurrency(fine.balance)}
        </p>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Amount ($)</label>
            <input
              type="number"
              step="0.01"
              min="0.01"
              max={(fine.balance / 100).toFixed(2)}
              value={amount}
              onChange={e => setAmount(e.target.value)}
              className="w-full border border-lsc-border dark:border-earth-600 rounded-lg px-3 py-2 bg-lsc-white dark:bg-earth-900 text-earth-800 dark:text-earth-100"
            />
            {isPartial && (
              <p className="text-xs text-status-warning-700 dark:text-status-warning-400 mt-1">{t('staffFineManagement.thisWillBeRecordedAs')}</p>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Payment Method</label>
            <select
              value={method}
              onChange={e => setMethod(e.target.value as PaymentMethod)}
              className="w-full border border-lsc-border dark:border-earth-600 rounded-lg px-3 py-2 bg-lsc-white dark:bg-earth-900 text-earth-800 dark:text-earth-100"
            >
              {Object.entries(PAYMENT_METHOD_LABELS).map(([val, label]) => (
                <option key={val} value={val}>{label}</option>
              ))}
            </select>
          </div>
        </div>

        <div className="flex justify-end gap-3 mt-6">
          <button onClick={onClose} className="px-4 py-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-earth-100 dark:hover:bg-earth-700 rounded-lg">
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={submitting}
            className="px-4 py-2 text-sm bg-lsc-green text-white rounded-lg hover:bg-lsc-green/90 disabled:opacity-50 flex items-center gap-2"
          >
            {submitting && <Loader2 className="motion-safe:animate-spin h-4 w-4" />}
            {isPartial ? "Record Partial Payment" : "Record Full Payment"}
          </button>
        </div>
      </div>
    </ModalBackdrop>
  )
}

// ============ Waive Modal ============

function WaiveModal({ fine, token, onClose, onSuccess }: {
  fine: Fine; token: string; onClose: () => void; onSuccess: () => void
}) {
  const { t } = useTranslation()
  const [reason, setReason] = useState("")
  const [submitting, setSubmitting] = useState(false)

  const handleSubmit = async () => {
    if (!reason.trim()) {
      toast.error(t('toast.reasonRequired'))
      return
    }
    setSubmitting(true)
    try {
      await finesApi.waiveFine(token, fine.id, reason.trim())
      toast.success(t('toast.staffFineManagement.fineWaived'))
      onSuccess()
    } catch (e: unknown) {
      toast.error((e instanceof Error ? e.message : null) || "Waive failed")
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <ModalBackdrop onClose={onClose} title="Waive Fine" role="alertdialog">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg w-full max-w-md p-6 mx-4">
        <h3 className="font-serif text-lg font-bold text-earth-800 dark:text-earth-100 mb-1">Waive Fine</h3>
        <p className="text-sm text-earth-600 dark:text-earth-400 mb-4">
          {fine.patron_name || `Patron #${fine.user_id}`} -- {formatCurrency(fine.balance)} balance
        </p>

        <div>
          <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Reason (required)</label>
          <textarea
            value={reason}
            onChange={e => setReason(e.target.value)}
            rows={3}
            placeholder={t('staffFineManagement.enterReasonForWaivingThis')}
            className="w-full border border-lsc-border dark:border-earth-600 rounded-lg px-3 py-2 bg-lsc-white dark:bg-earth-900 text-earth-800 dark:text-earth-100 resize-none"
          />
        </div>

        <div className="flex justify-end gap-3 mt-6">
          <button onClick={onClose} className="px-4 py-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-earth-100 dark:hover:bg-earth-700 rounded-lg">
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={submitting || !reason.trim()}
            className="px-4 py-2 text-sm bg-status-warning-500 text-white rounded-lg hover:bg-status-warning-600 disabled:opacity-50 flex items-center gap-2"
          >
            {submitting && <Loader2 className="motion-safe:animate-spin h-4 w-4" />}
            Waive Fine
          </button>
        </div>
      </div>
    </ModalBackdrop>
  )
}

// ============ Payment Plans Tab ============

function PaymentPlansTab({ token }: { token: string }) {
  const [_plans, _setPlans] = useState<PaymentPlan[]>([])
  const [_loading, setLoading] = useState(true)
  const [_expandedPlan, _setExpandedPlan] = useState<number | null>(null)

  useEffect(() => {
    // Payment plans are per-patron, so we load from fines list and extract unique patrons
    // For now, this tab shows a placeholder until a patron search is implemented
    // eslint-disable-next-line react-hooks/set-state-in-effect -- placeholder tab clears initial loading state on mount
    setLoading(false)
  }, [token])

  return (
    <div>
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-6">
        <div className="flex items-center gap-3 mb-4">
          <Calendar className="h-5 w-5 text-lsc-green" />
          <h3 className="font-serif font-semibold text-earth-800 dark:text-earth-100">Payment Plans</h3>
        </div>
        <p className="text-sm text-earth-600 dark:text-earth-400 mb-4">
          Search for a patron to view or create payment plans. Payment plans allow patrons to pay off large fines in installments.
        </p>

        <PatronPlanSearch token={token} />
      </div>
    </div>
  )
}

function PatronPlanSearch({ token }: { token: string }) {
  const { t } = useTranslation();
  const [patronId, setPatronId] = useState("")
  const [plan, setPlan] = useState<PaymentPlan | null>(null)
  const [loading, setLoading] = useState(false)
  const [notFound, setNotFound] = useState(false)

  const search = async () => {
    const id = parseInt(patronId)
    if (isNaN(id)) { toast.error(t('staffFineManagement.enterAValidPatronId')); return }
    setLoading(true)
    setNotFound(false)
    setPlan(null)
    try {
      const result = await finesApi.getPaymentPlan(token, id)
      setPlan(result)
    } catch {
      setNotFound(true)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <div className="flex gap-2 mb-4">
        <input
          type="number"
          value={patronId}
          onChange={e => setPatronId(e.target.value)}
          placeholder={t('placeholder.staffFineManagement.patronId')}
          className="border border-lsc-border dark:border-earth-600 rounded-lg px-3 py-2 bg-lsc-white dark:bg-earth-900 text-earth-800 dark:text-earth-100 w-40"
          onKeyDown={e => e.key === "Enter" && search()}
        />
        <button
          onClick={search}
          disabled={loading}
          className="px-4 py-2 text-sm bg-lsc-green text-white rounded-lg hover:bg-lsc-green/90 disabled:opacity-50 flex items-center gap-2"
        >
          {loading ? <Loader2 className="motion-safe:animate-spin h-4 w-4" /> : <Search className="h-4 w-4" />}
          Search
        </button>
      </div>

      {notFound && (
        <p className="text-sm text-earth-600">{t('staffFineManagement.noActivePaymentPlanFound')}</p>
      )}

      {plan && (
        <div className="bg-earth-50 dark:bg-earth-900/50 rounded-xl p-4 space-y-3">
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium text-earth-800 dark:text-earth-100">{plan.patron_name || `Patron #${plan.user_id}`}</p>
              <span className={`inline-flex px-2 py-0.5 text-xs font-medium rounded-full ${PLAN_STATUS_COLORS[plan.status] || ""}`}>
                {plan.status}
              </span>
            </div>
            <div className="text-right">
              <p className="text-sm text-earth-600 dark:text-earth-400">
                {formatCurrency(plan.amount_paid)} / {formatCurrency(plan.total_amount)}
              </p>
              <p className="text-xs text-earth-600">{plan.payments_made} payments made</p>
            </div>
          </div>

          {/* Progress bar */}
          <div className="w-full bg-earth-200 dark:bg-earth-700 rounded-full h-2">
            <div
              className="bg-lsc-green h-2 rounded-full transition-all"
              style={{ width: `${plan.progress_percentage}%` }}
            />
          </div>

          <div className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <p className="text-earth-600 text-xs">Installment</p>
              <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{formatCurrency(plan.installment_amount)} / {plan.frequency}</p>
            </div>
            <div>
              <p className="text-earth-600 text-xs">Next Payment</p>
              <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{plan.next_payment_date ? formatDate(plan.next_payment_date) : "--"}</p>
            </div>
            <div>
              <p className="text-earth-600 text-xs">Remaining</p>
              <p className="font-medium text-earth-800 dark:text-earth-100">{formatCurrency(plan.remaining_balance)}</p>
            </div>
            <div>
              <p className="text-earth-600 text-xs">Start Date</p>
              <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{formatDate(plan.start_date)}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// ============ Pending Checks Tab ============

function PendingChecksTab({ token }: { token: string }) {
  const { t } = useTranslation();
  const [checks, setChecks] = useState<PendingCheck[]>([])
  const [loading, setLoading] = useState(true)

  const loadChecks = useCallback(async () => {
    setLoading(true)
    try {
      const result = await finesApi.getPendingChecks(token)
      setChecks(result.checks || [])
    } catch (e: unknown) {
      toast.error((e instanceof Error ? e.message : null) || "Failed to load pending checks")
    } finally {
      setLoading(false)
    }
  }, [token])

  useEffect(() => { loadChecks() }, [loadChecks])

  const handleClear = async (paymentId: number) => {
    try {
      await finesApi.markCheckCleared(token, paymentId)
      toast.success(t('staffFineManagement.checkMarkedAsCleared'))
      loadChecks()
    } catch (e: unknown) {
      toast.error((e instanceof Error ? e.message : null) || "Failed to clear check")
    }
  }

  const handleBounce = async (paymentId: number) => {
    try {
      await finesApi.markCheckBounced(token, paymentId)
      toast.success(t('staffFineManagement.checkMarkedAsBounced'))
      loadChecks()
    } catch (e: unknown) {
      toast.error((e instanceof Error ? e.message : null) || "Failed to mark bounced")
    }
  }

  if (loading) {
    return (
      <div className="flex justify-center py-12">
        <Loader2 className="motion-safe:animate-spin h-8 w-8 text-lsc-green" />
      </div>
    )
  }

  if (checks.length === 0) {
    return (
      <div className="text-center py-12 text-earth-600">
        <FileText className="h-12 w-12 mx-auto mb-3 opacity-30" />
        <p>{t('staffFineManagement.noPendingChecksToProcess')}</p>
      </div>
    )
  }

  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-earth-50 dark:bg-earth-900/50 text-earth-600 dark:text-earth-400 text-left">
              <th className="p-3">Receipt #</th>
              <th className="p-3">Patron</th>
              <th className="p-3 text-right">Amount</th>
              <th className="p-3">Status</th>
              <th className="p-3">Date</th>
              <th className="p-3">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-earth-100 dark:divide-earth-700">
            {checks.map(check => (
              <tr key={check.id} className="hover:bg-earth-50/50 dark:hover:bg-earth-700/30">
                <td className="p-3 font-mono text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{check.receipt_number}</td>
                <td className="p-3 font-medium text-earth-800 dark:text-earth-100">{check.patron_name || `Fine #${check.fine_id}`}</td>
                <td className="p-3 text-right font-mono text-lsc-dark/70 dark:text-lsc-cream/70">{formatCurrency(check.amount)}</td>
                <td className="p-3">
                  <span className={`inline-flex px-2 py-0.5 text-xs font-medium rounded-full ${CHECK_STATUS_COLORS[check.check_clearance_status] || ""}`}>
                    {check.check_clearance_status}
                  </span>
                </td>
                <td className="p-3 text-earth-600 dark:text-earth-400 text-xs">{formatDate(check.created_at)}</td>
                <td className="p-3">
                  {check.check_clearance_status === "pending" && (
                    <div className="flex gap-1">
                      <button
                        onClick={() => handleClear(check.id)}
                        className="p-1.5 rounded-lg hover:bg-status-success-50 dark:hover:bg-status-success-900/20 text-status-success-600 dark:text-status-success-400"
                        title="Mark Cleared"
                      >
                        <CheckCircle className="h-4 w-4" />
                      </button>
                      <button
                        onClick={() => handleBounce(check.id)}
                        className="p-1.5 rounded-lg hover:bg-status-danger-50 dark:hover:bg-status-danger-900/20 text-status-danger-600 dark:text-status-danger-400"
                        title="Mark Bounced"
                      >
                        <XCircle className="h-4 w-4" />
                      </button>
                    </div>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// ============ Analytics Tab ============

function AnalyticsTab({ token }: { token: string }) {
  const { t } = useTranslation();
  const [analytics, setAnalytics] = useState<FineAnalytics | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Load aggregate analytics from the fines list
    (async () => {
      try {
        const result = await finesApi.getFines(token)
        const fines = result.fines || []
        const analytics: FineAnalytics = {
          total_outstanding: fines.filter((f: Fine) => f.status === "unpaid" || f.status === "partial").reduce((s: number, f: Fine) => s + f.balance, 0),
          total_collected: fines.filter((f: Fine) => f.status === "paid" || f.status === "partial").reduce((s: number, f: Fine) => s + f.amount_paid, 0),
          total_waived: fines.filter((f: Fine) => f.status === "waived").reduce((s: number, f: Fine) => s + f.amount, 0),
          collection_rate: 0,
          fines_by_type: {},
          fines_by_status: {},
        }
        const totalOwed = fines.reduce((s: number, f: Fine) => s + f.amount, 0)
        analytics.collection_rate = totalOwed > 0 ? Math.round((analytics.total_collected / totalOwed) * 100) : 0

        for (const f of fines) {
          analytics.fines_by_type[f.fine_type] = (analytics.fines_by_type[f.fine_type] || 0) + 1
          analytics.fines_by_status[f.status] = (analytics.fines_by_status[f.status] || 0) + 1
        }
        setAnalytics(analytics)
      } catch {
        toast.error(t('staffFineManagement.failedToLoadAnalytics'))
      } finally {
        setLoading(false)
      }
    })()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token])

  if (loading) {
    return (
      <div className="flex justify-center py-12">
        <Loader2 className="motion-safe:animate-spin h-8 w-8 text-lsc-green" />
      </div>
    )
  }

  if (!analytics) return null

  const statCards = [
    { label: "Outstanding", value: formatCurrency(analytics.total_outstanding), icon: DollarSign, color: "text-status-danger-500" },
    { label: "Collected", value: formatCurrency(analytics.total_collected), icon: TrendingUp, color: "text-status-success-500" },
    { label: "Waived", value: formatCurrency(analytics.total_waived), icon: Ban, color: "text-earth-600" },
    { label: "Collection Rate", value: `${analytics.collection_rate}%`, icon: BarChart3, color: "text-earth-600" },
  ]

  return (
    <div className="space-y-6">
      {/* Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {statCards.map(card => (
          <div key={card.label} className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-4">
            <div className="flex items-center gap-3">
              <div className={`p-2 rounded-lg bg-earth-50 dark:bg-earth-900/50 ${card.color}`}>
                <card.icon className="h-5 w-5" />
              </div>
              <div>
                <p className="text-xs text-earth-600">{card.label}</p>
                <p className="text-xl font-bold text-earth-800 dark:text-earth-100">{card.value}</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Breakdowns */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-4">
          <h4 className="font-serif font-semibold text-earth-800 dark:text-earth-100 mb-3">By Type</h4>
          <div className="space-y-2">
            {Object.entries(analytics.fines_by_type).map(([type, count]) => (
              <div key={type} className="flex items-center justify-between">
                <span className="flex items-center gap-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                  {fineTypeIcon(type as FineType)}
                  {FINE_TYPE_LABELS[type] || type}
                </span>
                <span className="text-sm font-medium text-earth-800 dark:text-earth-100">{count}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-4">
          <h4 className="font-serif font-semibold text-earth-800 dark:text-earth-100 mb-3">By Status</h4>
          <div className="space-y-2">
            {Object.entries(analytics.fines_by_status).map(([status, count]) => (
              <div key={status} className="flex items-center justify-between">
                <span className={`inline-flex px-2 py-0.5 text-xs font-medium rounded-full ${STATUS_COLORS[status] || ""}`}>
                  {status}
                </span>
                <span className="text-sm font-medium text-earth-800 dark:text-earth-100">{count}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

// ============ Main Page ============

export default function StaffFineManagementPage(): React.ReactElement {
  const { user, token, isLoading: authLoading } = useAuth()
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState("fines")

  useEffect(() => {
    if (!authLoading && (!user || user.role === "patron")) {
      toast.error(t('toast.acquisitionManagement.staffAccessRequired'))
      navigate("/account")
    }
  }, [authLoading, user, navigate])

  if (authLoading || !token) {
    return (
      <div className="flex justify-center items-center min-h-[60vh]">
        <Loader2 className="motion-safe:animate-spin h-8 w-8 text-lsc-green" />
      </div>
    )
  }

  return (
    <AdminShell title="Fine Management" subtitle="Track fines, process payments, manage waivers and payment plans.">
        {/* Header */}
        <div className="mb-6">
          <div className="flex items-center gap-3 mb-1">
            <div className="p-2 bg-lsc-green/10 rounded-lg">
              <DollarSign className="h-6 w-6 text-lsc-green" />
            </div>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="flex gap-1 mb-6 bg-lsc-white dark:bg-earth-800 rounded-xl p-1 border border-lsc-border dark:border-earth-700 overflow-x-auto">
          {TABS.map(tab => {
            const Icon = tab.icon
            const isActive = activeTab === tab.id
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium whitespace-nowrap transition-colors ${
                  isActive
                    ? "bg-lsc-green text-white shadow-sm"
                    : "text-earth-600 dark:text-earth-400 hover:text-earth-700 dark:hover:text-earth-200 hover:bg-earth-50 dark:hover:bg-earth-700"
                }`}
              >
                <Icon className="h-4 w-4" />
                {tab.label}
              </button>
            )
          })}
        </div>

        {/* Tab Content */}
        {activeTab === "fines" && <ActiveFinesTab token={token} />}
        {activeTab === "plans" && <PaymentPlansTab token={token} />}
        {activeTab === "checks" && <PendingChecksTab token={token} />}
        {activeTab === "analytics" && <AnalyticsTab token={token} />}

    </AdminShell>
  )
}
