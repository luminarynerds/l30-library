/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
export type AnalyticsTab = "circulation" | "popular" | "fines" | "patrons" | "collection"

export interface DateRange {
  startDate: string
  endDate: string
}
