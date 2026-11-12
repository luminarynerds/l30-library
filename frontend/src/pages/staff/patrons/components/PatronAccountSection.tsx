/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { Wallet, Plus, ArrowUpDown, Loader2 } from "lucide-react"
import toast from "react-hot-toast"
import { fetchApi } from "../../../../api/fetchApi"
import { useTranslation, formatCurrency as formatCurrencyI18n, getCurrentLocale } from "@/i18n"

interface AccountBalance {
  id: number
  patron_id: number
  balance: string
  total_deposited: string
  total_spent: string
  is_active: boolean
  low_balance_threshold: string
  last_deposit_at: string | null
  last_charge_at: string | null
}

interface Transaction {
  id: number
  transaction_type: string
  status: string
  amount: string
  balance_before: string
  balance_after: string
  payment_method: string | null
  description: string
  notes: string | null
  created_at: string
}

interface TransactionList {
  items: Transaction[]
  total: number
  page: number
  per_page: number
}

const PAYMENT_METHODS = [
  { value: "cash", label: "Cash" },
  { value: "credit_card", label: "Credit Card" },
  { value: "debit_card", label: "Debit Card" },
] as const

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(getCurrentLocale(), {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  })
}

function txTypeLabel(type: string): string {
  switch (type) {
    case "deposit": return "Deposit"
    case "charge": return "Charge"
    case "refund": return "Refund"
    case "adjustment": return "Adjustment"
    default: return type
  }
}

function txTypeColor(type: string): string {
  switch (type) {
    case "deposit": return "text-status-success-600"
    case "refund": return "text-status-info-600"
    case "charge": return "text-status-danger-600"
    default: return "text-lsc-dark/70 dark:text-lsc-cream/70"
  }
}

function txAmountPrefix(type: string): string {
  return type === "charge" ? "-" : "+"
}

interface PatronAccountSectionProps {
  patronId: number
}

export function PatronAccountSection({ patronId }: PatronAccountSectionProps) {
  const { t, language } = useTranslation()
  const formatCurrency = (value: string | number): string => formatCurrencyI18n(Number(value), language, 'USD')
  const queryClient = useQueryClient()
  const [showDeposit, setShowDeposit] = useState(false)
  const [depositAmount, setDepositAmount] = useState("")
  const [paymentMethod, setPaymentMethod] = useState("cash")
  const [depositNotes, setDepositNotes] = useState("")

  const { data: account, isLoading: isLoadingAccount } = useQuery<AccountBalance>({
    queryKey: ["patron-account", patronId],
    queryFn: () => fetchApi(`/staff/patron/${patronId}/account`),
  })

  const { data: transactions, isLoading: isLoadingTx } = useQuery<TransactionList>({
    queryKey: ["patron-transactions", patronId],
    queryFn: () => fetchApi(`/staff/patron/${patronId}/transactions?per_page=5`),
    enabled: !!account,
  })

  const depositMutation = useMutation({
    mutationFn: (payload: { amount: number; payment_method: string; notes?: string }) =>
      fetchApi(`/staff/patron/${patronId}/deposit`, {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["patron-account", patronId] })
      queryClient.invalidateQueries({ queryKey: ["patron-transactions", patronId] })
      toast.success("Deposit recorded")
      setShowDeposit(false)
      setDepositAmount("")
      setPaymentMethod("cash")
      setDepositNotes("")
    },
    onError: (err: Error) => {
      toast.error(err.message || "Failed to record deposit")
    },
  })

  const handleDeposit = () => {
    const amt = parseFloat(depositAmount)
    if (!amt || amt <= 0 || amt > 1000) {
      toast.error("Amount must be between $0.01 and $1,000")
      return
    }
    depositMutation.mutate({
      amount: amt,
      payment_method: paymentMethod,
      notes: depositNotes || undefined,
    })
  }

  // Persistent live region: survives the loading/loaded swap below so
  // screen readers get one announcement instead of a torn-down node.
  const accountStatusRegion = (
    <div role="status" aria-live="polite" className="sr-only">
      {isLoadingAccount
        ? t('aria.patronAccount.loadingAccount', 'Loading account…')
        : t('aria.patronAccount.accountLoaded', 'Account loaded')}
    </div>
  )

  if (isLoadingAccount) {
    return (
      <div className="bg-lsc-cream dark:bg-lsc-brown/50 rounded-xl p-6">
        {accountStatusRegion}
        <div className="flex items-center gap-2 mb-4">
          <Wallet className="w-5 h-5 text-lsc-rose" />
          <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
            Prepaid Account
          </h3>
        </div>
        <div className="flex items-center justify-center py-4">
          <Loader2 className="w-5 h-5 motion-safe:animate-spin text-lsc-rose" aria-hidden="true" />
        </div>
      </div>
    )
  }

  if (!account) {
    return (
      <div className="bg-lsc-cream dark:bg-lsc-brown/50 rounded-xl p-6">
        {accountStatusRegion}
        <div className="flex items-center gap-2 mb-4">
          <Wallet className="w-5 h-5 text-lsc-rose" />
          <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
            Prepaid Account
          </h3>
        </div>
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/50">
          No prepaid account found for this patron.
        </p>
      </div>
    )
  }

  return (
    <div className="bg-lsc-cream dark:bg-lsc-brown/50 rounded-xl p-6">
      {accountStatusRegion}
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream flex items-center gap-2">
          <Wallet className="w-5 h-5 text-lsc-rose" />
          Prepaid Account
        </h3>
        <button
          onClick={() => setShowDeposit(!showDeposit)}
          className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-lsc-rose border border-lsc-rose/30 rounded-lg hover:bg-lsc-rose/5"
        >
          <Plus className="w-3 h-3" /> Deposit
        </button>
      </div>

      {/* Balance summary */}
      <div className="grid grid-cols-3 gap-3 mb-4">
        <div className="text-center p-3 bg-lsc-white/50 dark:bg-earth-800/50 rounded-lg">
          <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/50">Balance</div>
          <div className={`text-lg font-bold ${Number(account.balance) > 0 ? "text-status-success-600" : "text-lsc-dark dark:text-lsc-cream"}`}>
            {formatCurrency(account.balance)}
          </div>
        </div>
        <div className="text-center p-3 bg-lsc-white/50 dark:bg-earth-800/50 rounded-lg">
          <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/50">Total Deposited</div>
          <div className="text-lg font-bold text-lsc-dark dark:text-lsc-cream">
            {formatCurrency(account.total_deposited)}
          </div>
        </div>
        <div className="text-center p-3 bg-lsc-white/50 dark:bg-earth-800/50 rounded-lg">
          <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/50">Total Spent</div>
          <div className="text-lg font-bold text-lsc-dark dark:text-lsc-cream">
            {formatCurrency(account.total_spent)}
          </div>
        </div>
      </div>

      {/* Deposit form */}
      {showDeposit && (
        <div className="p-3 bg-lsc-rose/5 border border-lsc-rose/20 rounded-lg space-y-2 mb-4">
          <div className="grid grid-cols-2 gap-2">
            <input
              type="number"
              placeholder="Amount"
              aria-label={t('aria.patronAccount.depositAmount', 'Deposit amount')}
              min={0.01}
              max={1000}
              step={0.01}
              value={depositAmount}
              onChange={(e) => setDepositAmount(e.target.value)}
              className="px-3 py-1.5 text-sm border border-sage/30 rounded-lg bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream"
            />
            <select
              value={paymentMethod}
              onChange={(e) => setPaymentMethod(e.target.value)}
              aria-label={t('aria.patronAccount.paymentMethod', 'Payment method')}
              className="px-3 py-1.5 text-sm border border-sage/30 rounded-lg bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream"
            >
              {PAYMENT_METHODS.map((m) => (
                <option key={m.value} value={m.value}>{m.label}</option>
              ))}
            </select>
          </div>
          <input
            type="text"
            placeholder="Notes (optional)"
            aria-label={t('aria.patronAccount.depositNotes', 'Deposit notes')}
            value={depositNotes}
            onChange={(e) => setDepositNotes(e.target.value)}
            maxLength={500}
            className="w-full px-3 py-1.5 text-sm border border-sage/30 rounded-lg bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream"
          />
          <button
            onClick={handleDeposit}
            disabled={depositMutation.isPending || !depositAmount}
            className="px-3 py-1.5 text-xs font-medium text-white bg-lsc-rose rounded-lg hover:bg-lsc-rose/90 disabled:opacity-50"
          >
            {depositMutation.isPending ? <Loader2 className="w-3 h-3 inline motion-safe:animate-spin mr-1" /> : null}
            Record Deposit
          </button>
        </div>
      )}

      {/* Recent transactions */}
      <div>
        <h4 className="text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/60 flex items-center gap-1 mb-2">
          <ArrowUpDown className="w-3.5 h-3.5" /> Recent Transactions
        </h4>
        {/* Persistent live region: survives the loading/results swap below so
            screen readers get one announcement instead of a torn-down node. */}
        <div role="status" aria-live="polite" className="sr-only">
          {isLoadingTx
            ? t('aria.patronAccount.loadingTransactions', 'Loading transactions…')
            : transactions && transactions.items.length > 0
              ? t('aria.patronAccount.transactionsLoaded', { count: String(transactions.items.length) })
              : t('aria.patronAccount.noTransactions', 'No transactions yet')}
        </div>
        {isLoadingTx ? (
          <div className="flex items-center justify-center py-3">
            <Loader2 className="w-4 h-4 motion-safe:animate-spin text-lsc-rose" aria-hidden="true" />
          </div>
        ) : transactions && transactions.items.length > 0 ? (
          <div className="space-y-1">
            {transactions.items.map((tx) => (
              <div
                key={tx.id}
                className="flex items-center justify-between text-sm py-1.5 px-2 rounded-lg hover:bg-lsc-white/30 dark:hover:bg-earth-800/30"
              >
                <div className="flex-1 min-w-0">
                  <span className={`font-medium ${txTypeColor(tx.transaction_type)}`}>
                    {txTypeLabel(tx.transaction_type)}
                  </span>
                  <span className="text-lsc-dark/50 dark:text-lsc-cream/40 mx-1.5">&middot;</span>
                  <span className="text-lsc-dark/70 dark:text-lsc-cream/60 truncate">
                    {tx.description}
                  </span>
                </div>
                <div className="flex items-center gap-3 ml-2 shrink-0">
                  <span className={`font-mono text-sm font-medium ${txTypeColor(tx.transaction_type)}`}>
                    {txAmountPrefix(tx.transaction_type)}{formatCurrency(tx.amount)}
                  </span>
                  <span className="text-xs text-lsc-dark/40 dark:text-lsc-cream/30">
                    {formatDate(tx.created_at)}
                  </span>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-lsc-dark/50 dark:text-lsc-cream/40 py-2">
            No transactions yet.
          </p>
        )}
      </div>
    </div>
  )
}
