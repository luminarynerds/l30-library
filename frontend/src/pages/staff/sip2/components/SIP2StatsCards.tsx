/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Monitor, Wifi, Activity, CheckCircle } from "lucide-react"
import type { TerminalStats, TransactionStats } from "@/api/sip2-api"

interface SIP2StatsCardsProps {
  terminalStats: TerminalStats | null
  transactionStats: TransactionStats | null
}

export function SIP2StatsCards({ terminalStats, transactionStats }: SIP2StatsCardsProps) {
  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm">
        <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
          <Monitor className="w-4 h-4" />
          <span className="text-xs uppercase">Total Terminals</span>
        </div>
        <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">
          {terminalStats?.total_terminals ?? "-"}
        </p>
      </div>
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm">
        <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
          <Wifi className="w-4 h-4" />
          <span className="text-xs uppercase">Online Today</span>
        </div>
        <p className="text-2xl font-bold text-status-success-600 dark:text-status-success-400">
          {terminalStats?.terminals_online_today ?? "-"}
        </p>
      </div>
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm">
        <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
          <Activity className="w-4 h-4" />
          <span className="text-xs uppercase">Transactions (7d)</span>
        </div>
        <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">
          {transactionStats?.total_transactions ?? "-"}
        </p>
      </div>
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm">
        <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
          <CheckCircle className="w-4 h-4" />
          <span className="text-xs uppercase">Success Rate</span>
        </div>
        <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">
          {transactionStats && transactionStats.total_transactions > 0
            ? `${((transactionStats.successful_transactions / transactionStats.total_transactions) * 100).toFixed(1)}%`
            : "-"}
        </p>
      </div>
    </div>
  )
}
