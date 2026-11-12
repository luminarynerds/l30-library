/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import type { Hold, Patron, PatronCheckout } from "../../api/api"
import type { Fine } from "../../api/staff-api"

export type StatusFilter = "all" | "active" | "blocked"
export type FinesSubTab = "unpaid" | "history" | "payments" | "plan" | "analytics"
export type CommunicationSubTab = "notes" | "messages" | "compose"

export interface ReadingHistoryItem {
  id: number
  item_id: number
  item_title: string
  item_author: string | null
  checked_out_at: string
  returned_at: string
}

export interface PatronDetail extends Patron {
  checkouts?: PatronCheckout[]
  holds?: Hold[]
  fines?: Fine[]
  reading_history?: ReadingHistoryItem[]
}
