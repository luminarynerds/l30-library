/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import {
  Loader2,
  Activity,
  CheckCircle,
  XCircle,
  ChevronLeft,
  ChevronRight,
} from "lucide-react"
import {
  getCommandLabel,
  SIP2_COMMANDS,
  SIP2Terminal,
  SIP2Transaction,
} from "@/api/sip2-api"
import { formatDate } from "../types"
import { useTranslation } from "@/i18n"

interface TransactionListProps {
  transactions: SIP2Transaction[]
  terminals: SIP2Terminal[]
  isLoading: boolean
  transactionFilters: {
    terminal_id: string
    command: string
    success: "" | "true" | "false"
  }
  setTransactionFilters: (filters: {
    terminal_id: string
    command: string
    success: "" | "true" | "false"
  }) => void
  transactionPage: number
  setTransactionPage: (v: number) => void
  transactionTotalPages: number
}

export function TransactionList({
  transactions,
  terminals,
  isLoading,
  transactionFilters,
  setTransactionFilters,
  transactionPage,
  setTransactionPage,
  transactionTotalPages,
}: TransactionListProps) {
  const { t } = useTranslation()
  return (
    <>
      {/* Filters */}
      <div className="flex flex-wrap items-center gap-4">
        <select
          value={transactionFilters.terminal_id}
          onChange={(e) => setTransactionFilters({ ...transactionFilters, terminal_id: e.target.value })}
          aria-label={t('aria.sip2TransactionList.filterByTerminal', 'Filter by terminal')}
          className="px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
        >
          <option value="">All Terminals</option>
          {terminals.map((t) => (
            <option key={t.terminal_id} value={t.terminal_id}>{t.name}</option>
          ))}
        </select>
        <select
          value={transactionFilters.command}
          onChange={(e) => setTransactionFilters({ ...transactionFilters, command: e.target.value })}
          aria-label={t('aria.sip2TransactionList.filterByCommand', 'Filter by command')}
          className="px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
        >
          <option value="">All Commands</option>
          {SIP2_COMMANDS.map((c) => (
            <option key={c.value} value={c.value}>{c.label}</option>
          ))}
        </select>
        <select
          value={transactionFilters.success}
          onChange={(e) => setTransactionFilters({ ...transactionFilters, success: e.target.value as "" | "true" | "false" })}
          aria-label={t('aria.sip2TransactionList.filterByResult', 'Filter by result')}
          className="px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
        >
          <option value="">All Results</option>
          <option value="true">Successful</option>
          <option value="false">Failed</option>
        </select>
      </div>

      {/* Transactions table */}
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm overflow-hidden">
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose dark:text-lsc-rose-light" />
          </div>
        ) : transactions.length === 0 ? (
          <div className="p-8 text-center">
            <Activity className="w-12 h-12 mx-auto text-lsc-dark/30 dark:text-lsc-cream/60 mb-4" />
            <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-2">
              No Transactions Found
            </h3>
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
              No SIP2 transactions match your filters.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <caption className="sr-only">SIP2 transaction log</caption>
              <thead className="bg-lsc-cream dark:bg-earth-700">
                <tr>
                  <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 uppercase tracking-wider">
                    Time
                  </th>
                  <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 uppercase tracking-wider">
                    Terminal
                  </th>
                  <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 uppercase tracking-wider">
                    Command
                  </th>
                  <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 uppercase tracking-wider">
                    Patron / Item
                  </th>
                  <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 uppercase tracking-wider">
                    Status
                  </th>
                  <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 uppercase tracking-wider">
                    Time (ms)
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-lsc-border dark:divide-earth-700">
                {transactions.map((tx) => (
                  <tr
                    key={tx.id}
                    className="hover:bg-lsc-cream/50 dark:hover:bg-lsc-brown/20 transition-colors"
                  >
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-lsc-dark dark:text-lsc-cream">
                      {formatDate(tx.created_at)}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-lsc-dark dark:text-lsc-cream">
                      {tx.terminal_id || "-"}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <span className="px-2 py-1 text-xs font-medium rounded-full bg-earth-100 dark:bg-earth-800/30 text-lsc-rose dark:text-lsc-rose-light">
                        {getCommandLabel(tx.command)}
                      </span>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                      {tx.patron_id && <span>Patron: {tx.patron_id}</span>}
                      {tx.patron_id && tx.item_id && " \u2022 "}
                      {tx.item_id && <span>Item: {tx.item_id}</span>}
                      {!tx.patron_id && !tx.item_id && "-"}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      {tx.success ? (
                        <span className="flex items-center gap-1 text-status-success-600 dark:text-status-success-400">
                          <CheckCircle className="w-4 h-4" />
                          Success
                        </span>
                      ) : (
                        <span className="flex items-center gap-1 text-status-danger-600 dark:text-status-danger-400">
                          <XCircle className="w-4 h-4" />
                          Failed
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                      {tx.processing_time_ms ?? "-"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination */}
        {transactionTotalPages > 1 && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-lsc-border dark:border-earth-700">
            <div className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
              Page {transactionPage} of {transactionTotalPages}
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setTransactionPage(Math.max(1, transactionPage - 1))}
                disabled={transactionPage === 1}
                aria-label={t('aria.sip2TransactionList.previousPage', 'Previous page')}
                className="p-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-rose dark:hover:text-lsc-rose-light hover:bg-lsc-cream dark:hover:bg-lsc-brown/30 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <ChevronLeft className="w-5 h-5" />
              </button>
              <button
                onClick={() => setTransactionPage(Math.min(transactionTotalPages, transactionPage + 1))}
                disabled={transactionPage === transactionTotalPages}
                aria-label={t('aria.sip2TransactionList.nextPage', 'Next page')}
                className="p-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-rose dark:hover:text-lsc-rose-light hover:bg-lsc-cream dark:hover:bg-lsc-brown/30 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <ChevronRight className="w-5 h-5" />
              </button>
            </div>
          </div>
        )}
      </div>
    </>
  )
}
