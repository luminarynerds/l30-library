/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import '@testing-library/jest-dom'
import { describe, it, expect, vi } from "vitest"
import { render, screen, within } from "@testing-library/react"
import { TransactionList } from "./TransactionList"
import type { SIP2Transaction } from "@/api/sip2-api"

// `t(key, fallback)` -> fallback string when one is given, else the key.
vi.mock('@/i18n', () => ({
  getCurrentLocale: () => 'en-US',
  useTranslation: () => ({
    t: (key: string, opt?: Record<string, unknown> | string) =>
      typeof opt === 'string' ? opt : key,
    language: 'en',
    isRTL: false,
  }),
}))

const tx = {
  id: 1,
  terminal_id: "T1",
  command: "11",
  patron_id: "P1",
  item_id: "I1",
  success: true,
  processing_time_ms: 12,
  created_at: "2026-06-01T10:00:00Z",
} as unknown as SIP2Transaction

describe("SIP2 TransactionList table semantics", () => {
  it("exposes a captioned table with column-scoped headers", () => {
    render(
      <TransactionList
        transactions={[tx]}
        terminals={[]}
        isLoading={false}
        transactionFilters={{ terminal_id: "", command: "", success: "" }}
        setTransactionFilters={() => {}}
        transactionPage={1}
        setTransactionPage={() => {}}
        transactionTotalPages={1}
      />
    )

    const table = screen.getByRole("table", { name: /sip2 transaction log/i })
    expect(table).toBeInTheDocument()

    const headers = within(table).getAllByRole("columnheader")
    expect(headers.length).toBe(6)
    headers.forEach((h) => expect(h).toHaveAttribute("scope", "col"))
  })
})
