/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import { useState, useCallback } from "react"
import {
  getTerminalStats,
  getTransactionStats,
  TerminalStats,
  TransactionStats,
} from "@/api/sip2-api"

export function useSIP2Stats(token: string | null) {
  const [terminalStats, setTerminalStats] = useState<TerminalStats | null>(null)
  const [transactionStats, setTransactionStats] = useState<TransactionStats | null>(null)

  const fetchStats = useCallback(async () => {
    if (!token) return
    try {
      const [tStats, txStats] = await Promise.all([
        getTerminalStats(token),
        getTransactionStats(token, { days: 7 }),
      ])
      setTerminalStats(tStats)
      setTransactionStats(txStats)
    } catch (error: unknown) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
    }
  }, [token])

  return { terminalStats, transactionStats, fetchStats }
}
