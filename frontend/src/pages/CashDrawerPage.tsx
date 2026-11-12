/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Cash Drawer Management Page
 *
 * Daily cash reconciliation and till balancing for library staff.
 * Features: drawer selection, session open/close, transaction logging,
 * denomination counting, reconciliation, PDF reports, and session history.
 */

import { useState, useEffect, useMemo, useCallback } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import toast from "react-hot-toast"
import {
  Banknote,
  Plus,
  CheckCircle,
  AlertTriangle,
  FileText,
  Download,
  X,
  DollarSign,
  ArrowUpCircle,
  ArrowDownCircle,
  RotateCcw,
  History,
  Calculator,
} from "lucide-react"
import {
  listDrawers,
  getCurrentSession,
  openSession,
  closeSession,
  approveSession,
  createTransaction,
  listTransactions,
  voidTransaction,
  getSessionHistory,
  getReconciliationReport,
  getDepositSlip,
  type TransactionCategory,
  type TransactionDirection,
} from "@/api/domains/staff/cash-drawer-api"
import { useTranslation} from '@/i18n'
import { clean } from '@/lib/utils'
import { t } from '@/i18n'
import { AdminShell } from '../components/shells/AdminShell'

/** Safely coerce numeric DB values (may arrive as strings from NUMERIC columns) */
const num = (v: unknown): number => Number(v) || 0

// ==================== Constants ====================

const CATEGORY_LABELS: Record<TransactionCategory, string> = {
  fine_payment: "Fine Payment",
  print_fee: "Print Fee",
  copy_fee: "Copy Fee",
  room_fee: "Room Fee",
  card_replacement: "Card Replacement",
  makerspace_fee: "Makerspace Fee",
  petty_cash: "Petty Cash",
  other: "Other",
}

const DENOMINATION_CONFIG = [
  { key: "hundred", label: "$100", value: 100 },
  { key: "fifty", label: "$50", value: 50 },
  { key: "twenty", label: "$20", value: 20 },
  { key: "ten", label: "$10", value: 10 },
  { key: "five", label: "$5", value: 5 },
  { key: "one", label: "$1", value: 1 },
  { key: "quarter", label: "$0.25", value: 0.25 },
  { key: "dime", label: "$0.10", value: 0.10 },
  { key: "nickel", label: "$0.05", value: 0.05 },
  { key: "penny", label: "$0.01", value: 0.01 },
] as const

// ==================== Sub-Components ====================

function DenominationGrid({
  values,
  onChange,
}: {
  values: Record<string, number>
  onChange: (vals: Record<string, number>) => void
}) {
  const total = useMemo(
    () =>
      DENOMINATION_CONFIG.reduce(
        (sum, d) => sum + (values[d.key] || 0) * d.value,
        0
      ),
    [values]
  )

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
        {DENOMINATION_CONFIG.map((d) => (
          <div key={d.key} className="flex flex-col">
            <label className="text-xs font-medium text-earth-600 dark:text-earth-400 mb-1">
              {d.label}
            </label>
            <input
              type="number"
              min={0}
              value={values[d.key] || ""}
              onChange={(e) =>
                onChange({ ...values, [d.key]: parseInt(e.target.value) || 0 })
              }
              className="w-full px-2 py-1.5 rounded border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream text-sm"
              placeholder={t('placeholder.readingLogEntryForm.0')}
            />
          </div>
        ))}
      </div>
      <div className="text-right font-bold text-lsc-dark dark:text-lsc-cream">
        Denomination Total: ${total.toFixed(2)}
      </div>
    </div>
  )
}

function TransactionForm({
  sessionId,
  onSuccess,
}: {
  sessionId: number
  onSuccess: () => void
}) {
  const [direction, setDirection] = useState<TransactionDirection>("inflow")
  const [category, setCategory] = useState<TransactionCategory>("other")
  const [amount, setAmount] = useState("")
  const [amountTendered, setAmountTendered] = useState("")
  const [description, setDescription] = useState("")

  const mutation = useMutation({
    mutationFn: () =>
      createTransaction(sessionId, clean({
        direction,
        category,
        amount: parseFloat(amount),
        amount_tendered: amountTendered ? parseFloat(amountTendered) : undefined,
        description: description || undefined,
      })),
    onSuccess: () => {
      toast.success(t('toast.cashDrawer.transactionRecorded'))
      setAmount("")
      setAmountTendered("")
      setDescription("")
      onSuccess()
    },
    onError: (err: Error) => toast.error(err.message),
  })

  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow p-4 space-y-3">
      <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream flex items-center gap-2">
        <Plus size={18} /> Record Transaction
      </h3>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div>
          <label className="block text-xs font-medium text-earth-600 dark:text-earth-400 mb-1">
            Direction
          </label>
          <div className="flex gap-2">
            <button
              onClick={() => setDirection("inflow")}
              className={`flex-1 py-2 rounded text-sm font-medium transition ${
                direction === "inflow"
                  ? "bg-status-success-600 text-white"
                  : "bg-earth-100 dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70"
              }`}
            >
              <ArrowUpCircle size={14} className="inline mr-1" /> In
            </button>
            <button
              onClick={() => setDirection("outflow")}
              className={`flex-1 py-2 rounded text-sm font-medium transition ${
                direction === "outflow"
                  ? "bg-status-danger-600 text-white"
                  : "bg-earth-100 dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70"
              }`}
            >
              <ArrowDownCircle size={14} className="inline mr-1" /> Out
            </button>
          </div>
        </div>
        <div>
          <label className="block text-xs font-medium text-earth-600 dark:text-earth-400 mb-1">
            Category
          </label>
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value as TransactionCategory)}
            className="w-full px-3 py-2 rounded border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream text-sm"
          >
            {Object.entries(CATEGORY_LABELS).map(([val, label]) => (
              <option key={val} value={val}>
                {label}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs font-medium text-earth-600 dark:text-earth-400 mb-1">
            Amount ($)
          </label>
          <input
            type="number"
            min="0.01"
            step="0.01"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            className="w-full px-3 py-2 rounded border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream text-sm"
            placeholder={t('placeholder.staff.000')}
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-earth-600 dark:text-earth-400 mb-1">
            Amount Tendered ($)
          </label>
          <input
            type="number"
            min="0"
            step="0.01"
            value={amountTendered}
            onChange={(e) => setAmountTendered(e.target.value)}
            className="w-full px-3 py-2 rounded border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream text-sm"
            placeholder={t('placeholder.cashDrawer.optional')}
          />
        </div>
      </div>
      <div>
        <label className="block text-xs font-medium text-earth-600 dark:text-earth-400 mb-1">
          Description
        </label>
        <input
          type="text"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          className="w-full px-3 py-2 rounded border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream text-sm"
          placeholder={t('placeholder.cashDrawer.optionalNote')}
          maxLength={1000}
        />
      </div>
      <button
        onClick={() => mutation.mutate()}
        disabled={!amount || parseFloat(amount) <= 0 || mutation.isPending}
        className="w-full bg-earth-700 dark:bg-earth-600 text-white py-2 rounded font-medium hover:bg-earth-800 dark:hover:bg-earth-500 disabled:opacity-50 transition"
      >
        {mutation.isPending ? "Recording..." : "Record Transaction"}
      </button>
    </div>
  )
}

// ==================== Main Page ====================

// eslint-disable-next-line complexity
export default function CashDrawerPage() {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const [selectedDrawerId, setSelectedDrawerId] = useState<number | null>(null)
  const [tab, setTab] = useState<"session" | "history">("session")
  const [showReconcile, setShowReconcile] = useState(false)
  const [countedTotal, setCountedTotal] = useState("")
  const [denomValues, setDenomValues] = useState<Record<string, number>>({})
  const [useDenomGrid, setUseDenomGrid] = useState(false)
  const [closingNotes, setClosingNotes] = useState("")
  const [openFloat, setOpenFloat] = useState("")
  const [historyPage, setHistoryPage] = useState(1)

  // Queries
  const drawersQuery = useQuery({
    queryKey: ["cash-drawers"],
    queryFn: () => listDrawers(),
  })

  const sessionQuery = useQuery({
    queryKey: ["cash-drawer-session", selectedDrawerId],
    queryFn: () => getCurrentSession(selectedDrawerId!),
    enabled: !!selectedDrawerId,
    retry: false,
  })

  const txnQuery = useQuery({
    queryKey: ["cash-drawer-txns", sessionQuery.data?.id],
    queryFn: () => listTransactions(sessionQuery.data!.id),
    enabled: !!sessionQuery.data?.id,
    refetchInterval: 30000,
  })

  const historyQuery = useQuery({
    queryKey: ["cash-drawer-history", selectedDrawerId, historyPage],
    queryFn: () => getSessionHistory(selectedDrawerId!, historyPage),
    enabled: !!selectedDrawerId && tab === "history",
  })

  // Auto-select first drawer
  useEffect(() => {
    if (drawersQuery.data?.length && !selectedDrawerId) {
      setSelectedDrawerId(drawersQuery.data[0]!.id)
    }
  }, [drawersQuery.data, selectedDrawerId])

  const selectedDrawer = drawersQuery.data?.find((d) => d.id === selectedDrawerId)
  const session = sessionQuery.data
  const hasActiveSession = !!session && !sessionQuery.isError
  const noSession = sessionQuery.isError || (!session && !sessionQuery.isLoading)

  // Mutations
  const openMutation = useMutation({
    mutationFn: () =>
      openSession(selectedDrawerId!, {
        opening_float: parseFloat(openFloat) || num(selectedDrawer?.default_float) || 100,
      }),
    onSuccess: () => {
      toast.success(t('toast.cashDrawer.drawerSessionOpened'))
      setOpenFloat("")
      queryClient.invalidateQueries({ queryKey: ["cash-drawer-session"] })
    },
    onError: (err: Error) => toast.error(err.message),
  })

  const closeMutation = useMutation({
    mutationFn: () =>
      closeSession(selectedDrawerId!, clean({
        counted_total: parseFloat(countedTotal),
        denomination_breakdown: useDenomGrid ? denomValues : undefined,
        notes: closingNotes || undefined,
      })),
    onSuccess: (data) => {
      if (data.status === "pending_approval") {
        toast(t('cashDrawer.sessionNeedsManagerApprovalDiscrepancy'), { icon: "⚠️" })
      } else {
        toast.success(t('toast.cashDrawer.sessionClosedSuccessfully'))
      }
      setShowReconcile(false)
      setCountedTotal("")
      setDenomValues({})
      setClosingNotes("")
      queryClient.invalidateQueries({ queryKey: ["cash-drawer-session"] })
      queryClient.invalidateQueries({ queryKey: ["cash-drawer-history"] })
    },
    onError: (err: Error) => toast.error(err.message),
  })

  const approveMutation = useMutation({
    mutationFn: (sessionId: number) => approveSession(sessionId, {}),
    onSuccess: () => {
      toast.success(t('toast.cashDrawer.sessionApproved'))
      queryClient.invalidateQueries({ queryKey: ["cash-drawer-session"] })
      queryClient.invalidateQueries({ queryKey: ["cash-drawer-history"] })
    },
    onError: (err: Error) => toast.error(err.message),
  })

  const voidMutation = useMutation({
    mutationFn: ({ sessionId, txnId }: { sessionId: number; txnId: number }) =>
      voidTransaction(sessionId, txnId),
    onSuccess: () => {
      toast.success(t('toast.cashDrawer.transactionVoided'))
      queryClient.invalidateQueries({ queryKey: ["cash-drawer-txns"] })
      queryClient.invalidateQueries({ queryKey: ["cash-drawer-session"] })
    },
    onError: (err: Error) => toast.error(err.message),
  })

  const downloadPdf = useCallback(
    async (type: "reconciliation" | "deposit", sessionId: number) => {
      try {
        const blob =
          type === "reconciliation"
            ? await getReconciliationReport(sessionId)
            : await getDepositSlip(sessionId)
        const url = URL.createObjectURL(blob)
        const a = document.createElement("a")
        a.href = url
        a.download = `${type}-${sessionId}.pdf`
        a.click()
        URL.revokeObjectURL(url)
      } catch {
        toast.error(t('cashDrawer.failedToDownloadPdf'))
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    []
  )

  const refreshAll = () => {
    queryClient.invalidateQueries({ queryKey: ["cash-drawer-session"] })
    queryClient.invalidateQueries({ queryKey: ["cash-drawer-txns"] })
  }

  // Computed
  const summary = session?.summary
  const currentBalance = summary
    ? num(session?.opening_float) + num(summary.total_inflows) - num(summary.total_outflows)
    : null

  const denomTotal = useMemo(
    () =>
      DENOMINATION_CONFIG.reduce(
        (sum, d) => sum + (denomValues[d.key] || 0) * d.value,
        0
      ),
    [denomValues]
  )

  // Sync denomination total to counted total
  useEffect(() => {
    if (useDenomGrid && denomTotal > 0) {
      setCountedTotal(denomTotal.toFixed(2))
    }
  }, [denomTotal, useDenomGrid])

  return (
    <AdminShell title="Cash Drawer">
    <div className="min-h-screen bg-lsc-cream dark:bg-earth-900 p-4 md:p-8">
      <div className="max-w-5xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream flex items-center gap-2">
              <Banknote className="text-earth-600 dark:text-earth-400" />
              Cash Drawer
            </h1>
            <p className="text-sm text-earth-600 dark:text-earth-400 mt-1">
              Daily cash reconciliation and till management
            </p>
          </div>
          <div className="flex items-center gap-3">
            {/* Drawer Selector */}
            {drawersQuery.data && drawersQuery.data.length > 1 && (
              <select
                value={selectedDrawerId || ""}
                onChange={(e) => setSelectedDrawerId(Number(e.target.value))}
                className="px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream text-sm"
              >
                {drawersQuery.data.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.name}
                  </option>
                ))}
              </select>
            )}
            {/* Tab Switcher */}
            <div className="flex rounded-lg overflow-hidden border border-lsc-border dark:border-earth-600">
              <button
                onClick={() => setTab("session")}
                className={`px-4 py-2 text-sm font-medium transition ${
                  tab === "session"
                    ? "bg-earth-700 dark:bg-earth-600 text-white"
                    : "bg-lsc-white dark:bg-earth-800 text-lsc-dark/70 dark:text-lsc-cream/70"
                }`}
              >
                <DollarSign size={14} className="inline mr-1" /> Session
              </button>
              <button
                onClick={() => setTab("history")}
                className={`px-4 py-2 text-sm font-medium transition ${
                  tab === "history"
                    ? "bg-earth-700 dark:bg-earth-600 text-white"
                    : "bg-lsc-white dark:bg-earth-800 text-lsc-dark/70 dark:text-lsc-cream/70"
                }`}
              >
                <History size={14} className="inline mr-1" /> History
              </button>
            </div>
          </div>
        </div>

        {/* Loading / No drawers */}
        {drawersQuery.isLoading && (
          <div className="text-center py-12 text-earth-600">Loading drawers...</div>
        )}
        {drawersQuery.data?.length === 0 && (
          <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow p-8 text-center">
            <Banknote size={48} className="mx-auto text-earth-600 mb-4" />
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">
              No cash drawers configured.
            </p>
            <p className="text-sm text-earth-600">
              Contact your administrator to set up a cash drawer.
            </p>
          </div>
        )}

        {/* Session Tab */}
        {tab === "session" && selectedDrawerId && (
          <>
            {/* No Active Session - Open Drawer */}
            {noSession && (
              <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow p-6 max-w-md mx-auto text-center">
                <Banknote size={48} className="mx-auto text-earth-600 mb-4" />
                <h2 className="font-serif text-xl font-bold text-lsc-dark dark:text-lsc-cream mb-2">
                  Open Cash Drawer
                </h2>
                <p className="text-sm text-earth-600 dark:text-earth-400 mb-4">
                  Start a new session to begin tracking cash transactions.
                </p>
                <div className="mb-4">
                  <label className="block text-sm font-medium text-earth-600 dark:text-earth-400 mb-1">
                    Opening Float ($)
                  </label>
                  <input
                    type="number"
                    min="0"
                    step="0.01"
                    value={openFloat}
                    onChange={(e) => setOpenFloat(e.target.value)}
                    placeholder={String(num(selectedDrawer?.default_float) || 100)}
                    className="w-full px-3 py-2 rounded border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream text-center text-lg"
                  />
                </div>
                <button
                  onClick={() => openMutation.mutate()}
                  disabled={openMutation.isPending}
                  className="bg-status-success-600 text-white px-6 py-3 rounded-lg font-semibold hover:bg-status-success-700 disabled:opacity-50 transition flex items-center justify-center gap-2 mx-auto"
                >
                  {openMutation.isPending ? (
                    "Opening..."
                  ) : (
                    <>
                      <CheckCircle size={18} /> Open Drawer
                    </>
                  )}
                </button>
              </div>
            )}

            {/* Pending Approval */}
            {session?.status === "pending_approval" && (
              <div className="bg-status-warning-50 dark:bg-status-warning-900/20 border border-status-warning-300 dark:border-status-warning-700 rounded-lg p-6">
                <div className="flex items-start gap-3">
                  <AlertTriangle className="text-status-warning-600 flex-shrink-0 mt-1" size={24} />
                  <div className="flex-1">
                    <h3 className="font-serif font-bold text-status-warning-800 dark:text-status-warning-300">
                      Manager Approval Required
                    </h3>
                    <p className="text-sm text-status-warning-700 dark:text-status-warning-400 mt-1">
                      Discrepancy of ${Math.abs(num(session.discrepancy)).toFixed(2)} exceeds
                      threshold. A manager must approve before closing.
                    </p>
                    <div className="mt-3 flex gap-3">
                      <button
                        onClick={() => approveMutation.mutate(session.id)}
                        disabled={approveMutation.isPending}
                        className="bg-status-warning-600 text-white px-4 py-2 rounded font-medium hover:bg-status-warning-700 disabled:opacity-50 transition text-sm"
                      >
                        {approveMutation.isPending ? "Approving..." : "Approve & Close"}
                      </button>
                      <button
                        onClick={() => downloadPdf("reconciliation", session.id)}
                        className="border border-status-warning-400 text-status-warning-700 dark:text-status-warning-300 px-4 py-2 rounded font-medium hover:bg-status-warning-100 dark:hover:bg-status-warning-900/30 transition text-sm flex items-center gap-1"
                      >
                        <FileText size={14} /> View Report
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Active Session Dashboard */}
            {hasActiveSession && session.status === "open" && (
              <div className="space-y-4">
                {/* Summary Cards */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow p-4">
                    <div className="text-xs font-medium text-earth-600 dark:text-earth-400 uppercase tracking-wider">
                      Opening Float
                    </div>
                    <div className="text-xl font-bold text-lsc-dark dark:text-lsc-cream mt-1">
                      ${num(session.opening_float).toFixed(2)}
                    </div>
                  </div>
                  <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow p-4">
                    <div className="text-xs font-medium text-status-success-600 dark:text-status-success-400 uppercase tracking-wider flex items-center gap-1">
                      <ArrowUpCircle size={12} /> Inflows
                    </div>
                    <div className="text-xl font-bold text-status-success-700 dark:text-status-success-400 mt-1">
                      ${num(summary?.total_inflows).toFixed(2)}
                    </div>
                  </div>
                  <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow p-4">
                    <div className="text-xs font-medium text-status-danger-600 dark:text-status-danger-400 uppercase tracking-wider flex items-center gap-1">
                      <ArrowDownCircle size={12} /> Outflows
                    </div>
                    <div className="text-xl font-bold text-status-danger-700 dark:text-status-danger-400 mt-1">
                      ${num(summary?.total_outflows).toFixed(2)}
                    </div>
                  </div>
                  <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow p-4">
                    <div className="text-xs font-medium text-earth-600 dark:text-earth-400 uppercase tracking-wider">
                      Current Balance
                    </div>
                    <div className="text-xl font-bold text-lsc-dark dark:text-lsc-cream mt-1">
                      ${(currentBalance ?? 0).toFixed(2)}
                    </div>
                  </div>
                </div>

                {/* Quick-Add Buttons */}
                <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow p-4">
                  <h3 className="text-sm font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">
                    Quick Add
                  </h3>
                  <div className="flex flex-wrap gap-2">
                    {(
                      [
                        ["fine_payment", "inflow"],
                        ["print_fee", "inflow"],
                        ["copy_fee", "inflow"],
                        ["petty_cash", "outflow"],
                      ] as const
                    ).map(([cat, dir]) => (
                      <button
                        key={cat}
                        onClick={() => {
                          const amt = prompt(
                            `${CATEGORY_LABELS[cat]} amount ($):`,
                          )
                          if (amt && parseFloat(amt) > 0) {
                            createTransaction(session.id, {
                              direction: dir,
                              category: cat,
                              amount: parseFloat(amt),
                            }).then(() => {
                              toast.success(t('toast.cashDrawer.categorylabelscatRecorded', { CATEGORYLABELScat: CATEGORY_LABELS[cat] }))
                              refreshAll()
                            })
                          }
                        }}
                        className={`px-3 py-1.5 rounded text-xs font-medium transition ${
                          dir === "inflow"
                            ? "bg-status-success-100 dark:bg-status-success-900/30 text-status-success-800 dark:text-status-success-300 hover:bg-status-success-200"
                            : "bg-status-danger-100 dark:bg-status-danger-900/30 text-status-danger-800 dark:text-status-danger-300 hover:bg-status-danger-200"
                        }`}
                      >
                        {dir === "inflow" ? "+" : "-"} {CATEGORY_LABELS[cat]}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Transaction Form */}
                <TransactionForm sessionId={session.id} onSuccess={refreshAll} />

                {/* Transaction List */}
                <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow">
                  <div className="p-4 border-b border-lsc-border dark:border-earth-700 flex items-center justify-between">
                    <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
                      Transactions ({summary?.transaction_count || 0})
                    </h3>
                    <button
                      onClick={refreshAll}
                      className="text-earth-600 hover:text-lsc-dark/70 dark:text-lsc-cream/70 dark:hover:text-earth-300 transition"
                    >
                      <RotateCcw size={16} />
                    </button>
                  </div>
                  <div className="divide-y divide-earth-100 dark:divide-earth-700 max-h-80 overflow-y-auto">
                    {txnQuery.data?.transactions.map((txn) => (
                      <div
                        key={txn.id}
                        className={`px-4 py-3 flex items-center justify-between ${
                          txn.voided ? "opacity-50 line-through" : ""
                        }`}
                      >
                        <div className="flex items-center gap-3">
                          {txn.direction === "inflow" ? (
                            <ArrowUpCircle size={16} className="text-status-success-600" />
                          ) : (
                            <ArrowDownCircle size={16} className="text-status-danger-600" />
                          )}
                          <div>
                            <div className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
                              {CATEGORY_LABELS[txn.category] || txn.category}
                            </div>
                            {txn.description && (
                              <div className="text-xs text-earth-600">{txn.description}</div>
                            )}
                          </div>
                        </div>
                        <div className="flex items-center gap-3">
                          <span
                            className={`font-mono font-semibold text-sm ${
                              txn.direction === "inflow"
                                ? "text-status-success-700 dark:text-status-success-400"
                                : "text-status-danger-700 dark:text-status-danger-400"
                            }`}
                          >
                            {txn.direction === "inflow" ? "+" : "-"}$
                            {num(txn.amount).toFixed(2)}
                          </span>
                          {!txn.voided && (
                            <button
                              onClick={() =>
                                voidMutation.mutate({
                                  sessionId: session.id,
                                  txnId: txn.id,
                                })
                              }
                              className="text-earth-600 hover:text-status-danger-600 transition"
                              title="Void transaction"
                            >
                              <X size={14} />
                            </button>
                          )}
                        </div>
                      </div>
                    ))}
                    {(!txnQuery.data || txnQuery.data.transactions.length === 0) && (
                      <div className="px-4 py-6 text-center text-earth-600 text-sm">
                        No transactions yet
                      </div>
                    )}
                  </div>
                </div>

                {/* Reconcile Button */}
                {!showReconcile && (
                  <button
                    onClick={() => setShowReconcile(true)}
                    className="w-full bg-earth-700 dark:bg-earth-600 text-white py-3 rounded-lg font-semibold hover:bg-earth-800 dark:hover:bg-earth-500 transition flex items-center justify-center gap-2"
                  >
                    <Calculator size={18} /> Close & Reconcile
                  </button>
                )}

                {/* Reconciliation Form */}
                {showReconcile && (
                  <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow p-6 space-y-4 border-2 border-lsc-border dark:border-earth-600">
                    <div className="flex items-center justify-between">
                      <h3 className="font-serif text-lg font-bold text-lsc-dark dark:text-lsc-cream flex items-center gap-2">
                        <Calculator size={20} /> Reconcile & Close
                      </h3>
                      <button
                        onClick={() => setShowReconcile(false)}
                        className="text-earth-600 hover:text-earth-600 dark:text-earth-200"
                      >
                        <X size={20} />
                      </button>
                    </div>
                    <div className="bg-earth-50 dark:bg-earth-700/50 rounded p-3 text-sm">
                      <span className="font-medium">Expected total:</span>{" "}
                      <span className="font-bold">${(currentBalance ?? 0).toFixed(2)}</span>
                    </div>
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">
                          Counted Total ($)
                        </label>
                        <label className="flex items-center gap-1 text-xs text-earth-600 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={useDenomGrid}
                            onChange={(e) => setUseDenomGrid(e.target.checked)}
                            className="rounded"
                          />
                          Use denomination counter
                        </label>
                      </div>
                      {useDenomGrid ? (
                        <DenominationGrid values={denomValues} onChange={setDenomValues} />
                      ) : (
                        <input
                          type="number"
                          min="0"
                          step="0.01"
                          value={countedTotal}
                          onChange={(e) => setCountedTotal(e.target.value)}
                          className="w-full px-3 py-2 rounded border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream text-lg"
                          placeholder={t('placeholder.staff.000')}
                        />
                      )}
                    </div>
                    {countedTotal && (
                      <div
                        className={`p-3 rounded text-sm font-medium ${
                          Math.abs(parseFloat(countedTotal) - (currentBalance ?? 0)) <= num(selectedDrawer?.discrepancy_threshold || 5)
                            ? "bg-status-success-50 dark:bg-status-success-900/20 text-status-success-800 dark:text-status-success-300"
                            : "bg-status-danger-50 dark:bg-status-danger-900/20 text-status-danger-800 dark:text-status-danger-300"
                        }`}
                      >
                        Discrepancy: $
                        {(parseFloat(countedTotal) - (currentBalance ?? 0)).toFixed(2)}
                        {Math.abs(parseFloat(countedTotal) - (currentBalance ?? 0)) >
                          num(selectedDrawer?.discrepancy_threshold || 5) && (
                          <span className="ml-2">(exceeds threshold - will need manager approval)</span>
                        )}
                      </div>
                    )}
                    <div>
                      <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                        Notes (optional)
                      </label>
                      <textarea
                        value={closingNotes}
                        onChange={(e) => setClosingNotes(e.target.value)}
                        className="w-full px-3 py-2 rounded border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream text-sm"
                        rows={2}
                        maxLength={2000}
                      />
                    </div>
                    <button
                      onClick={() => closeMutation.mutate()}
                      disabled={!countedTotal || parseFloat(countedTotal) < 0 || closeMutation.isPending}
                      className="w-full bg-status-danger-600 text-white py-3 rounded-lg font-semibold hover:bg-status-danger-700 disabled:opacity-50 transition"
                    >
                      {closeMutation.isPending ? "Closing..." : "Close Session"}
                    </button>
                  </div>
                )}
              </div>
            )}

            {/* Loading session */}
            {sessionQuery.isLoading && (
              <div className="text-center py-12 text-earth-600">Loading session...</div>
            )}
          </>
        )}

        {/* History Tab */}
        {tab === "history" && selectedDrawerId && (
          <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow">
            <div className="p-4 border-b border-lsc-border dark:border-earth-700">
              <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
                Session History
              </h3>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-earth-50 dark:bg-earth-700/50 text-left">
                    <th className="px-4 py-3 font-medium text-earth-600 dark:text-earth-400">Date</th>
                    <th className="px-4 py-3 font-medium text-earth-600 dark:text-earth-400">Expected</th>
                    <th className="px-4 py-3 font-medium text-earth-600 dark:text-earth-400">Counted</th>
                    <th className="px-4 py-3 font-medium text-earth-600 dark:text-earth-400">Discrepancy</th>
                    <th className="px-4 py-3 font-medium text-earth-600 dark:text-earth-400">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-earth-100 dark:divide-earth-700">
                  {historyQuery.data?.sessions.map((s) => (
                    <tr key={s.id} className="hover:bg-earth-50 dark:hover:bg-earth-700/30">
                      <td className="px-4 py-3 text-lsc-dark dark:text-lsc-cream">
                        {s.closed_at ? new Date(s.closed_at).toLocaleDateString() : "-"}
                      </td>
                      <td className="px-4 py-3 font-mono">
                        ${num(s.expected_total).toFixed(2)}
                      </td>
                      <td className="px-4 py-3 font-mono">
                        ${num(s.counted_total).toFixed(2)}
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={`font-mono font-medium ${
                            s.discrepancy && num(s.discrepancy) !== 0
                              ? "text-status-danger-600 dark:text-status-danger-400"
                              : "text-status-success-600 dark:text-status-success-400"
                          }`}
                        >
                          ${num(s.discrepancy).toFixed(2)}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex gap-2">
                          <button
                            onClick={() => downloadPdf("reconciliation", s.id)}
                            className="text-earth-600 hover:text-lsc-dark/70 dark:text-lsc-cream/70 dark:hover:text-earth-300 transition"
                            title="Download reconciliation report"
                          >
                            <FileText size={16} />
                          </button>
                          <button
                            onClick={() => downloadPdf("deposit", s.id)}
                            className="text-earth-600 hover:text-lsc-dark/70 dark:text-lsc-cream/70 dark:hover:text-earth-300 transition"
                            title="Download deposit slip"
                          >
                            <Download size={16} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                  {(!historyQuery.data || historyQuery.data.sessions.length === 0) && (
                    <tr>
                      <td colSpan={5} className="px-4 py-8 text-center text-earth-600">
                        No session history yet
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
            {historyQuery.data && historyQuery.data.total > 20 && (
              <div className="p-4 border-t border-lsc-border dark:border-earth-700 flex justify-center gap-2">
                <button
                  onClick={() => setHistoryPage(Math.max(1, historyPage - 1))}
                  disabled={historyPage === 1}
                  className="px-3 py-1 rounded border border-lsc-border dark:border-earth-600 text-sm disabled:opacity-50"
                >
                  Previous
                </button>
                <span className="px-3 py-1 text-sm text-earth-600 dark:text-earth-400">
                  Page {historyPage}
                </span>
                <button
                  onClick={() => setHistoryPage(historyPage + 1)}
                  disabled={historyPage * 20 >= historyQuery.data.total}
                  className="px-3 py-1 rounded border border-lsc-border dark:border-earth-600 text-sm disabled:opacity-50"
                >
                  Next
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
    </AdminShell>
  )
}
