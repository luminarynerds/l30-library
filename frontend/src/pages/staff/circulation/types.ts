import { getCurrentLocale } from '@/i18n'
/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
export { type Patron, type PatronCheckout } from "@/api/api"

export const isValidBarcodeFormat = (value: string): boolean => {
  if (value.length < 4) return false
  return /^[\dA-Z-]{4,20}$/i.test(value.trim())
}

export const formatDate = (d: string) =>
  new Date(d).toLocaleDateString(getCurrentLocale(), { month: "short", day: "numeric", year: "numeric" })

export const isOverdue = (d: string) => new Date(d) < new Date()
