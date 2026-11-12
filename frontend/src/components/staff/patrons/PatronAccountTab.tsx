/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React, { useState, useEffect, useCallback } from "react"
import {
  Wallet,
  Plus,
  Undo2,
  Loader2,
  ArrowUpRight,
  ArrowDownLeft,
  RefreshCcw,
  DollarSign,
  CreditCard,
  Banknote,
  Globe,
  ChevronLeft,
  ChevronRight,
} from "lucide-react"
import toast from "react-hot-toast"
import { Patron } from "../../../api/api"
import {
  getPatronAccountBalance,
  getPatronTransactions,
  staffDeposit,
  staffRefund,
  type PatronAccountBalance,
  type TransactionListResponse,
  type AccountPaymentMethod,
  type TransactionType,
} from "../../../api/domains/staff/patron-account-api"
import { useTranslation, formatCurrency, getCurrentLocale } from '@/i18n'
import { clean } from '@/lib/utils'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

interface PatronAccountTabProps {
  selectedPatron: Patron | null
  token: string | null
}

const PAYMENT_METHODS: { value: AccountPaymentMethod; label: string; icon: React.ReactNode }[] = [
  { value: "cash", label: "Cash", icon: <Banknote className="w-4 h-4" /> },
  { value: "credit_card", label: "Credit Card", icon: <CreditCard className="w-4 h-4" /> },
  { value: "debit_card", label: "Debit Card", icon: <CreditCard className="w-4 h-4" /> },
  { value: "online", label: "Online", icon: <Globe className="w-4 h-4" /> },
]

function getTransactionIcon(type: TransactionType) {
  switch (type) {
    case "deposit":
      return <ArrowDownLeft className="w-4 h-4 text-status-success-600 dark:text-status-success-400" />
    case "charge":
      return <ArrowUpRight className="w-4 h-4 text-status-danger-600 dark:text-status-danger-400" />
    case "refund":
      return <Undo2 className="w-4 h-4 text-lsc-rose dark:text-lsc-rose-light" />
    case "adjustment":
      return <RefreshCcw className="w-4 h-4 text-status-warning-600 dark:text-status-warning-400" />
  }
}

function getTransactionBadge(type: TransactionType) {
  const classes: Record<TransactionType, string> = {
    deposit: "bg-status-success-100 text-status-success-800 dark:bg-status-success-900/30 dark:text-status-success-400",
    charge: "bg-status-danger-100 text-status-danger-800 dark:bg-status-danger-900/30 dark:text-status-danger-400",
    refund: "bg-earth-100 text-earth-800 dark:bg-earth-800/30 dark:text-lsc-rose-light",
    adjustment: "bg-status-warning-100 text-status-warning-800 dark:bg-status-warning-900/30 dark:text-status-warning-400",
  }
  return classes[type]
}

export function PatronAccountTab({ selectedPatron, token }: PatronAccountTabProps) {
  const { t, language } = useTranslation()
  const fmt = (amount: number): string => formatCurrency(amount, language, 'USD')
  const [account, setAccount] = useState<PatronAccountBalance | null>(null)
  const [transactions, setTransactions] = useState<TransactionListResponse | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [txPage, setTxPage] = useState(1)
  const [txFilter, setTxFilter] = useState<TransactionType | "">("")

  // Deposit modal state
  const [showDepositModal, setShowDepositModal] = useState(false)
  const [depositAmount, setDepositAmount] = useState("")
  const [depositMethod, setDepositMethod] = useState<AccountPaymentMethod>("cash")
  const [depositNotes, setDepositNotes] = useState("")
  const [isDepositing, setIsDepositing] = useState(false)

  // Refund modal state
  const [showRefundModal, setShowRefundModal] = useState(false)
  const [refundAmount, setRefundAmount] = useState("")
  const [refundReason, setRefundReason] = useState("")
  const [refundNotes, setRefundNotes] = useState("")
  const [isRefunding, setIsRefunding] = useState(false)

  const loadAccount = useCallback(async () => {
    if (!token || !selectedPatron) return
    try {
      const data = await getPatronAccountBalance(token, selectedPatron.id)
      setAccount(data)
    } catch {
      // Account may not exist yet - that's okay
      setAccount(null)
    }
  }, [token, selectedPatron])

  const loadTransactions = useCallback(async () => {
    if (!token || !selectedPatron) return
    try {
      const data = await getPatronTransactions(token, selectedPatron.id, clean({
        page: txPage,
        per_page: 10,
        transaction_type: txFilter || undefined,
      }))
      setTransactions(data)
    } catch {
      setTransactions(null)
    }
  }, [token, selectedPatron, txPage, txFilter])

  const loadAll = useCallback(async () => {
    setIsLoading(true)
    await Promise.all([loadAccount(), loadTransactions()])
    setIsLoading(false)
  }, [loadAccount, loadTransactions])

  useEffect(() => {
    loadAll()
  }, [loadAll])

  const handleDeposit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!token || !selectedPatron) return
    const amount = parseFloat(depositAmount)
    if (isNaN(amount) || amount <= 0) {
      toast.error(t('components.staff.patronAccountTab.enterAValidAmount'))
      return
    }
    setIsDepositing(true)
    try {
      await staffDeposit(token, selectedPatron.id, clean({
        amount,
        payment_method: depositMethod,
        notes: depositNotes || undefined,
      }))
      toast.success(t('toast.depositRecorded', { amount: amount.toFixed(2) }))
      setShowDepositModal(false)
      setDepositAmount("")
      setDepositNotes("")
      loadAll()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : t('toast.depositFailed'))
    } finally {
      setIsDepositing(false)
    }
  }

  const handleRefund = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!token || !selectedPatron) return
    const amount = parseFloat(refundAmount)
    if (isNaN(amount) || amount <= 0) {
      toast.error(t('components.staff.patronAccountTab.enterAValidAmount2'))
      return
    }
    if (refundReason.length < 1) {
      toast.error(t('toast.reasonRequired'))
      return
    }
    setIsRefunding(true)
    try {
      await staffRefund(token, selectedPatron.id, clean({
        amount,
        reason: refundReason,
        notes: refundNotes || undefined,
      }))
      toast.success(t('toast.refundProcessed', { amount: amount.toFixed(2) }))
      setShowRefundModal(false)
      setRefundAmount("")
      setRefundReason("")
      setRefundNotes("")
      loadAll()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : t('toast.refundFailed'))
    } finally {
      setIsRefunding(false)
    }
  }

  if (!selectedPatron) return null

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-6 h-6 motion-safe:animate-spin text-lsc-rose" />
      </div>
    )
  }

  const balance = account ? account.balance : 0
  const totalDeposited = account ? account.total_deposited : 0
  const totalSpent = account ? account.total_spent : 0
  const totalPages = transactions ? Math.ceil(transactions.total / transactions.per_page) : 0

  return (
    <div className="space-y-6">
      {/* Balance Overview */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-lsc-cream/50 dark:bg-earth-700/50 rounded-xl p-4 border border-lsc-border dark:border-earth-600">
          <div className="flex items-center gap-2 mb-1">
            <Wallet className="w-4 h-4 text-lsc-rose" />
            <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Current Balance</span>
          </div>
          <p className={`text-2xl font-bold ${balance > 0 ? "text-status-success-700 dark:text-status-success-400" : balance < 0 ? "text-status-danger-700 dark:text-status-danger-400" : "text-lsc-dark dark:text-lsc-cream"}`}>
            {fmt(balance)}
          </p>
          {account && balance <= account.low_balance_threshold && balance >= 0 && (
            <p className="text-xs text-status-warning-600 dark:text-status-warning-400 mt-1">Low balance</p>
          )}
        </div>

        <div className="bg-lsc-cream/50 dark:bg-earth-700/50 rounded-xl p-4 border border-lsc-border dark:border-earth-600">
          <div className="flex items-center gap-2 mb-1">
            <ArrowDownLeft className="w-4 h-4 text-status-success-600 dark:text-status-success-400" />
            <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Total Deposited</span>
          </div>
          <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">
            {fmt(totalDeposited)}
          </p>
        </div>

        <div className="bg-lsc-cream/50 dark:bg-earth-700/50 rounded-xl p-4 border border-lsc-border dark:border-earth-600">
          <div className="flex items-center gap-2 mb-1">
            <ArrowUpRight className="w-4 h-4 text-status-danger-600 dark:text-status-danger-400" />
            <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Total Spent</span>
          </div>
          <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">
            {fmt(totalSpent)}
          </p>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="flex gap-3">
        <button
          onClick={() => setShowDepositModal(true)}
          className="flex items-center gap-2 px-4 py-2.5 bg-status-success-600 hover:bg-status-success-700 text-white rounded-lg font-medium transition-colors"
        >
          <Plus className="w-4 h-4" />
          Add Funds
        </button>
        <button
          onClick={() => setShowRefundModal(true)}
          className="flex items-center gap-2 px-4 py-2.5 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-lg font-medium transition-colors"
        >
          <Undo2 className="w-4 h-4" />
          Issue Refund
        </button>
        <button
          onClick={loadAll}
          className="flex items-center gap-2 px-4 py-2.5 bg-lsc-cream dark:bg-earth-700 hover:bg-lsc-border dark:hover:bg-earth-600 text-lsc-dark dark:text-lsc-cream rounded-lg font-medium transition-colors"
        >
          <RefreshCcw className="w-4 h-4" />
          Refresh
        </button>
      </div>

      {/* Transaction History */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
            Transaction History
          </h3>
          <select
            value={txFilter}
            onChange={(e) => {
              setTxFilter(e.target.value as TransactionType | "")
              setTxPage(1)
            }}
            className="px-3 py-1.5 rounded-lg border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-700 text-sm text-lsc-dark dark:text-lsc-cream"
          >
            <option value="">All Types</option>
            <option value="deposit">Deposits</option>
            <option value="charge">Charges</option>
            <option value="refund">Refunds</option>
            <option value="adjustment">Adjustments</option>
          </select>
        </div>

        {transactions && transactions.items.length > 0 ? (
          <div className="space-y-2">
            {transactions.items.map((tx) => (
              <div
                key={tx.id}
                className="flex items-center gap-3 p-3 bg-lsc-cream/30 dark:bg-earth-700/30 rounded-lg border border-lsc-border/50 dark:border-earth-600/50"
              >
                <div className="p-2 bg-lsc-white dark:bg-earth-700 rounded-lg">
                  {getTransactionIcon(tx.transaction_type)}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className={`px-2 py-0.5 rounded text-xs font-medium capitalize ${getTransactionBadge(tx.transaction_type)}`}>
                      {tx.transaction_type}
                    </span>
                    {tx.payment_method && (
                      <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60 capitalize">
                        {tx.payment_method.replace("_", " ")}
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 truncate mt-0.5" title={tx.description}>
                    {tx.description}
                  </p>
                  {tx.reference_type === "print_job" && (
                    <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60">Print Job</span>
                  )}
                </div>
                <div className="text-right shrink-0">
                  <p className={`font-semibold ${
                    tx.transaction_type === "deposit" || tx.transaction_type === "refund"
                      ? "text-status-success-700 dark:text-status-success-400"
                      : "text-status-danger-700 dark:text-status-danger-400"
                  }`}>
                    {tx.transaction_type === "deposit" || tx.transaction_type === "refund" ? "+" : "-"}
                    {fmt(tx.amount)}
                  </p>
                  <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60">
                    Bal: {fmt(tx.balance_after)}
                  </p>
                  <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60">
                    {new Date(tx.created_at).toLocaleDateString(getCurrentLocale(), {
                      month: "short",
                      day: "numeric",
                      hour: "numeric",
                      minute: "2-digit",
                    })}
                  </p>
                </div>
              </div>
            ))}

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between pt-2">
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/60">
                  Page {txPage} of {totalPages} ({transactions.total} transactions)
                </p>
                <div className="flex gap-2">
                  <button
                    onClick={() => setTxPage((p) => Math.max(1, p - 1))}
                    disabled={txPage <= 1}
                    className="p-1.5 rounded-lg hover:bg-lsc-cream dark:hover:bg-earth-700 disabled:opacity-30 text-lsc-dark dark:text-lsc-cream"
                  >
                    <ChevronLeft className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => setTxPage((p) => Math.min(totalPages, p + 1))}
                    disabled={txPage >= totalPages}
                    className="p-1.5 rounded-lg hover:bg-lsc-cream dark:hover:bg-earth-700 disabled:opacity-30 text-lsc-dark dark:text-lsc-cream"
                  >
                    <ChevronRight className="w-4 h-4" />
                  </button>
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="text-center py-8">
            <DollarSign className="w-12 h-12 text-lsc-dark/30 dark:text-lsc-cream/60 mx-auto mb-3" />
            <p className="text-lsc-dark/70 dark:text-lsc-cream/60">No transactions yet</p>
          </div>
        )}
      </div>

      {/* Deposit Modal */}
      {showDepositModal && (
        <ModalBackdrop onClose={() => setShowDepositModal(false)} title="Dialog">
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl max-w-md w-full">
            <div className="p-6 border-b border-lsc-border dark:border-earth-700">
              <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream flex items-center gap-2">
                <Plus className="w-5 h-5 text-status-success-600" />
                Add Funds
              </h2>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/60 mt-1">
                Deposit money into {selectedPatron.first_name}'s print account
              </p>
            </div>

            <form onSubmit={handleDeposit} className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                  Amount *
                </label>
                <div className="relative">
                  <span className="absolute left-3 top-1/2 -translate-y-1/2 text-lsc-dark/70 dark:text-lsc-cream/60">$</span>
                  <input
                    type="number"
                    step="0.01"
                    min="0.01"
                    max="1000"
                    value={depositAmount}
                    onChange={(e) => setDepositAmount(e.target.value)}
                    required
                    placeholder={t('placeholder.staff.000')}
                    className="w-full pl-7 pr-3 py-2 rounded-lg border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                  />
                </div>
                <div className="flex gap-2 mt-2">
                  {[1, 5, 10, 20].map((amt) => (
                    <button
                      key={amt}
                      type="button"
                      onClick={() => setDepositAmount(amt.toFixed(2))}
                      className="px-3 py-1 text-sm bg-lsc-cream dark:bg-earth-700 hover:bg-lsc-border dark:hover:bg-earth-600 text-lsc-dark dark:text-lsc-cream rounded-lg transition-colors"
                    >
                      ${amt}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                  Payment Method *
                </label>
                <div className="grid grid-cols-2 gap-2">
                  {PAYMENT_METHODS.map((method) => (
                    <button
                      key={method.value}
                      type="button"
                      onClick={() => setDepositMethod(method.value)}
                      className={`flex items-center gap-2 px-3 py-2 rounded-lg border text-sm transition-colors ${
                        depositMethod === method.value
                          ? "border-lsc-rose bg-lsc-rose/10 text-lsc-rose dark:text-lsc-rose-light"
                          : "border-lsc-border dark:border-earth-600 text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-earth-700"
                      }`}
                    >
                      {method.icon}
                      {method.label}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                  Notes
                </label>
                <textarea
                  value={depositNotes}
                  onChange={(e) => setDepositNotes(e.target.value)}
                  rows={2}
                  placeholder={t('placeholder.staff.optionalNotes')}
                  className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                />
              </div>

              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowDepositModal(false)}
                  className="px-4 py-2 text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-earth-700 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isDepositing}
                  className="flex items-center gap-2 px-4 py-2 bg-status-success-600 hover:bg-status-success-700 text-white rounded-lg disabled:opacity-50"
                >
                  {isDepositing && <Loader2 className="w-4 h-4 motion-safe:animate-spin" />}
                  Deposit
                </button>
              </div>
            </form>
          </div>
        </ModalBackdrop>
      )}

      {/* Refund Modal */}
      {showRefundModal && (
        <ModalBackdrop onClose={() => setShowRefundModal(false)} title="Dialog">
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl max-w-md w-full">
            <div className="p-6 border-b border-lsc-border dark:border-earth-700">
              <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream flex items-center gap-2">
                <Undo2 className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
                Issue Refund
              </h2>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/60 mt-1">
                Refund money to {selectedPatron.first_name}'s account
              </p>
            </div>

            <form onSubmit={handleRefund} className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                  Amount *
                </label>
                <div className="relative">
                  <span className="absolute left-3 top-1/2 -translate-y-1/2 text-lsc-dark/70 dark:text-lsc-cream/60">$</span>
                  <input
                    type="number"
                    step="0.01"
                    min="0.01"
                    max="1000"
                    value={refundAmount}
                    onChange={(e) => setRefundAmount(e.target.value)}
                    required
                    placeholder={t('placeholder.staff.000')}
                    className="w-full pl-7 pr-3 py-2 rounded-lg border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                  Reason *
                </label>
                <input
                  type="text"
                  value={refundReason}
                  onChange={(e) => setRefundReason(e.target.value)}
                  required
                  placeholder={t('placeholder.staff.egFailedPrintJob')}
                  className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                  Notes
                </label>
                <textarea
                  value={refundNotes}
                  onChange={(e) => setRefundNotes(e.target.value)}
                  rows={2}
                  placeholder={t('placeholder.staff.optionalNotes')}
                  className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                />
              </div>

              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowRefundModal(false)}
                  className="px-4 py-2 text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-earth-700 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isRefunding}
                  className="flex items-center gap-2 px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-lg disabled:opacity-50"
                >
                  {isRefunding && <Loader2 className="w-4 h-4 motion-safe:animate-spin" />}
                  Refund
                </button>
              </div>
            </form>
          </div>
        </ModalBackdrop>
      )}
    </div>
  )
}
