/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect } from "react"
import { useNavigate } from "react-router-dom"
import { useAuth } from "@/contexts/AuthContext"
import { AdminShell } from "@/components/shells/AdminShell"
import { Loader2, RefreshCw, Plus } from "lucide-react"
import toast from "react-hot-toast"
import { useTranslation } from "@/i18n"
import { useSIP2Stats } from "./hooks/useSIP2Stats"
import { useSIP2Terminals } from "./hooks/useSIP2Terminals"
import { useSIP2Transactions } from "./hooks/useSIP2Transactions"
import { SIP2StatsCards } from "./components/SIP2StatsCards"
import { ViewToggle } from "./components/ViewToggle"
import { TerminalList } from "./components/TerminalList"
import { TransactionList } from "./components/TransactionList"
import { TerminalModal } from "./components/TerminalModal"
import { DeleteTerminalModal } from "./components/DeleteTerminalModal"
import type { ViewMode } from "./types"

export default function StaffSIP2Page(): React.ReactElement {
  const { t } = useTranslation()
  const { user, token, isLoading: authLoading, isAuthenticated } = useAuth()
  const navigate = useNavigate()

  const [viewMode, setViewMode] = useState<ViewMode>("terminals")

  const { terminalStats, transactionStats, fetchStats } = useSIP2Stats(token)

  const terminals = useSIP2Terminals(token, fetchStats)
  const txns = useSIP2Transactions(token)

  // Auth check
  useEffect(() => {
    if (!authLoading && (!user || user.role === "patron")) {
      toast.error(t('toast.acquisitionManagement.staffAccessRequired'))
      navigate("/account")
    }
  }, [authLoading, isAuthenticated, user, navigate, t])

  useEffect(() => {
    if (token && isAuthenticated) {
      fetchStats()
    }
  }, [token, isAuthenticated, fetchStats])

  useEffect(() => {
    if (token && isAuthenticated) {
      if (viewMode === "terminals") {
        terminals.fetchTerminals()
      } else {
        txns.fetchTransactions()
      }
    }
  }, [token, isAuthenticated, viewMode, terminals.fetchTerminals, txns.fetchTransactions])

  if (authLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose dark:text-lsc-rose-light" />
      </div>
    )
  }

  if (!user || user.role === "patron") {
    return <></>
  }

  return (
    <AdminShell title="SIP2 Terminal Management">
      <div>
          {/* Header */}
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
                SIP2 Terminal Management
              </h1>
              <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
                Manage self-checkout terminals and view transaction logs
              </p>
            </div>
            <div className="flex items-center gap-3">
              <button
                onClick={() => {
                  fetchStats()
                  if (viewMode === "terminals") terminals.fetchTerminals()
                  else txns.fetchTransactions()
                }}
                className="flex items-center gap-2 px-4 py-2 text-lsc-rose dark:text-lsc-rose-light hover:bg-lsc-cream dark:hover:bg-lsc-brown/20 rounded-xl transition-colors"
              >
                <RefreshCw className="w-4 h-4" />
                Refresh
              </button>
              {viewMode === "terminals" && (
                <button
                  onClick={terminals.openCreateTerminal}
                  className="flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-xl hover:bg-lsc-rose/90 transition-colors"
                >
                  <Plus className="w-4 h-4" />
                  New Terminal
                </button>
              )}
            </div>
          </div>

          <SIP2StatsCards
            terminalStats={terminalStats}
            transactionStats={transactionStats}
          />

          <ViewToggle viewMode={viewMode} setViewMode={setViewMode} />

          {viewMode === "terminals" ? (
            <TerminalList
              terminals={terminals.terminals}
              isLoading={terminals.isLoading}
              terminalSearch={terminals.terminalSearch}
              setTerminalSearch={terminals.setTerminalSearch}
              terminalFilter={terminals.terminalFilter}
              setTerminalFilter={terminals.setTerminalFilter}
              terminalPage={terminals.terminalPage}
              setTerminalPage={terminals.setTerminalPage}
              terminalTotalPages={terminals.terminalTotalPages}
              onToggleActive={terminals.handleToggleActive}
              onEdit={terminals.openEditTerminal}
              onDelete={terminals.confirmDelete}
              onCreate={terminals.openCreateTerminal}
            />
          ) : (
            <TransactionList
              transactions={txns.transactions}
              terminals={terminals.terminals}
              isLoading={txns.isLoading}
              transactionFilters={txns.transactionFilters}
              setTransactionFilters={txns.setTransactionFilters}
              transactionPage={txns.transactionPage}
              setTransactionPage={txns.setTransactionPage}
              transactionTotalPages={txns.transactionTotalPages}
            />
          )}

      {terminals.modalType === "terminal" && (
        <TerminalModal
          isEditing={terminals.isEditing}
          isSaving={terminals.isSaving}
          terminalForm={terminals.terminalForm}
          setTerminalForm={terminals.setTerminalForm}
          onSave={terminals.handleSaveTerminal}
          onClose={terminals.closeModal}
        />
      )}

      {terminals.showDeleteConfirm && terminals.deletingTerminal && (
        <DeleteTerminalModal
          terminal={terminals.deletingTerminal}
          isDeleting={terminals.isDeleting}
          onConfirm={terminals.handleDeleteTerminal}
          onCancel={terminals.cancelDelete}
        />
      )}
      </div>
    </AdminShell>
  )
}
