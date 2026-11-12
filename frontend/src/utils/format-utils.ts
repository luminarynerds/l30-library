import { getCurrentLocale } from '@/i18n'
/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
export function formatStatus(status: string): string {
  return status
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ")
}

export function parseDate(input: string | Date | null | undefined): Date | null {
  if (input === null || input === undefined || input === "") return null
  if (input instanceof Date) {
    return Number.isNaN(input.getTime()) ? null : input
  }
  // Bare YYYY-MM-DD → treat as local midnight to avoid UTC-to-local shift.
  const bareDate = /^\d{4}-\d{2}-\d{2}$/.test(input) ? `${input}T00:00:00` : input
  const parsed = new Date(bareDate)
  return Number.isNaN(parsed.getTime()) ? null : parsed
}

export function formatDate(dateString: string | null | undefined): string {
  const parsedDate = parseDate(dateString)
  if (parsedDate === null) return "-"

  return parsedDate.toLocaleDateString(getCurrentLocale(), {
    month: "short",
    day: "numeric",
    year: "numeric",
  })
}

export function formatDateTime(dateString: string | null | undefined): string {
  const parsedDate = parseDate(dateString)
  if (parsedDate === null) return "-"

  return parsedDate.toLocaleString(getCurrentLocale(), {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  })
}

export function formatCurrency(amount: number | null | undefined): string {
  if (amount === null || amount === undefined) return "-"
  return `$${amount.toFixed(2)}`
}

export function formatGenre(genre: string): string {
  return genre
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase())
}

export function formatEnumLabel(v: string | null | undefined): string {
  if (v === null || v === undefined) return ""
  const m = /^[A-Z][A-Za-z]+\.([A-Z_]+)$/.exec(v)
  if (m && m[1] !== undefined) return m[1].toLowerCase()
  return v
}
