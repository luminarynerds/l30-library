/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useCallback } from "react"
import { listTransactions, SIP2Transaction } from "@/api/sip2-api"
import { useTranslation } from "@/i18n"
import { clean } from "@/lib/utils"
import toast from "react-hot-toast"
import { PAGE_SIZE } from "../types"

export function useSIP2Transactions(token: string | null) {
  const { t } = useTranslation()

  const [transactions, setTransactions] = useState<SIP2Transaction[]>([])
  const [transactionPage, setTransactionPage] = useState(1)
  const [transactionTotal, setTransactionTotal] = useState(0)
  const [isLoading, setIsLoading] = useState(true)
  const [transactionFilters, setTransactionFilters] = useState({
    terminal_id: "",
    command: "",
    success: "" as "" | "true" | "false",
  })

  const transactionTotalPages = Math.ceil(transactionTotal / PAGE_SIZE)

  const fetchTransactions = useCallback(async () => {
    if (!token) return
    setIsLoading(true)
    try {
      const response = await listTransactions(token, clean({
        page: transactionPage,
        limit: PAGE_SIZE,
        ...(transactionFilters.terminal_id ? { terminal_id: transactionFilters.terminal_id } : {}),
        ...(transactionFilters.command ? { command: transactionFilters.command } : {}),
        success: transactionFilters.success === "" ? undefined : transactionFilters.success === "true",
      }))
      setTransactions(response.transactions)
      setTransactionTotal(response.total)
    } catch (error: unknown) {
      toast.error(error instanceof Error ? error.message : t('toast.acquisition.failedToLoadTransactions'))
    } finally {
      setIsLoading(false)
    }
  }, [token, transactionPage, transactionFilters, t])

  return {
    transactions,
    transactionPage,
    setTransactionPage,
    transactionTotal,
    transactionTotalPages,
    transactionFilters,
    setTransactionFilters,
    isLoading,
    fetchTransactions,
  }
}
